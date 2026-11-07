"""
Process Reconstruction Service.
Deterministically reconstructs case traces, sequences, and variants from CSV event records.
Adheres strictly to the ProcessLens Data-Quality Policy:
- No silent record mutation or deletion
- Structured traceability for all excluded rows with original raw values
- Complete cases vs incomplete cases strictly separated
- Incomplete cases never contribute to variant statistics
- Deterministic timestamp sorting with row_index tie-breaking
"""

import io
import csv
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import pandas as pd
from app.core.config import settings
from app.schemas.reconstruction import (
    ReconstructionExcludedEvent,
    ReconstructedEvent,
    CaseTrace,
    ProcessVariant,
    ReconstructionExclusions,
    ProcessReconstructionResult
)
from app.services.csv_schema import find_source_event_id_column

def reconstruct_process_from_csv(content_bytes: bytes, filename: str) -> ProcessReconstructionResult:
    """
    Parses and reconstructs cases, chronological activity sequences, and process variants
    from uploaded CSV event log bytes.
    """
    try:
        text_content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_content = content_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise ValueError("Uploaded file is empty or missing a valid CSV header.")

    normalized_headers = [str(column).strip().casefold() if column is not None else "" for column in reader.fieldnames]
    if any(not column for column in normalized_headers):
        raise ValueError("CSV header contains an empty column name. Rename or remove the blank column.")
    if len(set(normalized_headers)) != len(normalized_headers):
        raise ValueError("CSV header contains duplicate column names (case-insensitive). Rename duplicate columns.")

    # Validate required canonical headers (exact parity with validator.py)
    header_cols = [c.strip().lower() for c in reader.fieldnames if c]
    required_cols = [c.lower() for c in settings.CANONICAL_REQUIRED_COLUMNS]

    missing_header_cols = [c for c in required_cols if c not in header_cols]
    if missing_header_cols:
        raise ValueError(
            f"Missing required canonical column(s): {', '.join(missing_header_cols)}. "
            f"Required columns are: {', '.join(settings.CANONICAL_REQUIRED_COLUMNS)}"
        )

    # Header lookup mapping
    header_map = {c.strip().lower(): c for c in reader.fieldnames if c}
    col_case_id = header_map.get("case_id")
    col_activity = header_map.get("activity")
    col_timestamp = header_map.get("timestamp")
    col_resource = header_map.get("resource")
    col_event_id = find_source_event_id_column(reader.fieldnames)

    # Exclusions tracking
    all_excluded_events: List[ReconstructionExcludedEvent] = []
    case_excluded_events: Dict[str, List[ReconstructionExcludedEvent]] = defaultdict(list)
    missing_case_id_count = 0
    missing_activity_count = 0
    missing_or_invalid_ts_count = 0

    # Per-case raw event staging
    case_raw_events: Dict[str, List[ReconstructedEvent]] = defaultdict(list)
    case_warnings: Dict[str, List[str]] = defaultdict(list)
    case_error_flags: Dict[str, bool] = defaultdict(bool)

    total_source_rows = 0
    eligible_event_count = 0
    unique_cases_seen: set = set()
    case_seen_event_ids: Dict[str, set] = defaultdict(set)
    case_event_ids_by_operational_key: Dict[str, Dict[Tuple[str, str], set]] = defaultdict(dict)

    for row_idx, row in enumerate(reader, start=1):
        total_source_rows += 1
        clean_row_dict = {k: v for k, v in row.items() if k is not None}
        extra_values = row.get(None)
        if extra_values:
            clean_row_dict["__extra_columns__"] = extra_values

        raw_case_id = row.get(col_case_id, "") if col_case_id else ""
        raw_activity = row.get(col_activity, "") if col_activity else ""
        raw_timestamp = row.get(col_timestamp, "") if col_timestamp else ""
        raw_resource = row.get(col_resource, "") if col_resource else None
        raw_event_id = row.get(col_event_id, "") if col_event_id else None

        case_id_val = str(raw_case_id).strip() if raw_case_id is not None else ""
        activity_val = str(raw_activity).strip() if raw_activity is not None else ""
        timestamp_val = str(raw_timestamp).strip() if raw_timestamp is not None else ""
        resource_val = str(raw_resource).strip() if raw_resource is not None and str(raw_resource).strip() else None
        event_id_val = str(raw_event_id).strip() if raw_event_id is not None and str(raw_event_id).strip() else None

        # 1. Check for missing case ID
        if not case_id_val:
            missing_case_id_count += 1
            excluded_item = ReconstructionExcludedEvent(
                row_index=row_idx,
                case_id=None,
                issue_type="MISSING_CASE_ID",
                raw_values=clean_row_dict,
                details="case_id field is missing or empty"
            )
            all_excluded_events.append(excluded_item)
            continue

        unique_cases_seen.add(case_id_val)

        if extra_values:
            case_error_flags[case_id_val] = True
            excluded_item = ReconstructionExcludedEvent(
                row_index=row_idx,
                case_id=case_id_val,
                issue_type="MALFORMED_ROW",
                raw_values=clean_row_dict,
                details=f"Row contains {len(extra_values)} value(s) beyond the {len(reader.fieldnames)} header columns; it was excluded from the trace.",
            )
            all_excluded_events.append(excluded_item)
            case_excluded_events[case_id_val].append(excluded_item)
            continue

        # 2. Check for missing activity
        if not activity_val:
            missing_activity_count += 1
            case_error_flags[case_id_val] = True
            excluded_item = ReconstructionExcludedEvent(
                row_index=row_idx,
                case_id=case_id_val,
                issue_type="MISSING_ACTIVITY",
                raw_values=clean_row_dict,
                details="activity field is missing or empty"
            )
            all_excluded_events.append(excluded_item)
            case_excluded_events[case_id_val].append(excluded_item)
            continue

        # 3. Check for missing or invalid timestamp
        if not timestamp_val:
            missing_or_invalid_ts_count += 1
            case_error_flags[case_id_val] = True
            excluded_item = ReconstructionExcludedEvent(
                row_index=row_idx,
                case_id=case_id_val,
                issue_type="MISSING_TIMESTAMP",
                raw_values=clean_row_dict,
                details="timestamp field is missing or empty"
            )
            all_excluded_events.append(excluded_item)
            case_excluded_events[case_id_val].append(excluded_item)
            continue

        try:
            parsed_dt = pd.to_datetime(timestamp_val, errors='raise').to_pydatetime(warn=False)
        except Exception:
            missing_or_invalid_ts_count += 1
            case_error_flags[case_id_val] = True
            excluded_item = ReconstructionExcludedEvent(
                row_index=row_idx,
                case_id=case_id_val,
                issue_type="INVALID_TIMESTAMP",
                raw_values=clean_row_dict,
                details=f"Timestamp string '{timestamp_val}' could not be parsed into valid datetime format"
            )
            all_excluded_events.append(excluded_item)
            case_excluded_events[case_id_val].append(excluded_item)
            continue

        # Extract extra contextual attributes
        excluded_keys = {col_case_id, col_activity, col_timestamp, col_resource, col_event_id}
        attributes = {k: v for k, v in row.items() if k not in excluded_keys and v is not None}

        # 4. Confirm duplicates by source event identity when available.
        # Repeated operational timestamps are valid; without an event ID they
        # are retained and marked as possible duplicates rather than excluded.
        event_key = (activity_val, str(parsed_dt))
        is_dup = False
        is_potential_dup = False
        prior_ids = case_event_ids_by_operational_key[case_id_val].setdefault(event_key, set())
        if event_id_val:
            if event_id_val in case_seen_event_ids[case_id_val]:
                is_dup = True
                case_warnings[case_id_val].append(
                    f"Row {row_idx}: Source event ID '{event_id_val}' repeats in case '{case_id_val}'."
                )
            else:
                case_seen_event_ids[case_id_val].add(event_id_val)
            is_potential_dup = None in prior_ids
        elif prior_ids:
            is_potential_dup = True
            case_warnings[case_id_val].append(
                f"Row {row_idx}: Event '{activity_val}' at {timestamp_val} matches an earlier event, but no source event ID is available to confirm duplication."
            )
        prior_ids.add(event_id_val or None)

        event = ReconstructedEvent(
            row_index=row_idx,
            activity=activity_val,
            timestamp_raw=timestamp_val,
            timestamp_parsed=parsed_dt,
            resource=resource_val,
            source_event_id=event_id_val,
            attributes=attributes,
            is_duplicate=is_dup,
            is_potential_duplicate=is_potential_dup,
        )

        case_raw_events[case_id_val].append(event)
        eligible_event_count += 1

    # Reconstruct individual case traces
    case_traces: List[CaseTrace] = []
    incomplete_case_ids: List[str] = []

    # Sort case IDs deterministically
    for case_id in sorted(unique_cases_seen):
        events = case_raw_events[case_id]
        has_errors = case_error_flags[case_id]
        warnings = list(case_warnings[case_id])
        excluded_for_case = case_excluded_events[case_id]

        # Deterministic chronological sort:
        # Secondary key is row_index to break equal timestamp ties stably
        events_sorted = sorted(events, key=lambda e: (e.timestamp_parsed, e.row_index))
        activity_seq = [e.activity for e in events_sorted]

        start_time = events_sorted[0].timestamp_parsed if events_sorted else None
        end_time = events_sorted[-1].timestamp_parsed if events_sorted else None
        is_complete = (not has_errors) and len(events_sorted) > 0

        if not is_complete:
            incomplete_case_ids.append(case_id)
            if excluded_for_case:
                warnings.append(
                    f"Case has {len(excluded_for_case)} excluded event(s) and is omitted from process variant statistics."
                )

        case_traces.append(CaseTrace(
            case_id=case_id,
            events=events_sorted,
            activity_sequence=activity_seq,
            event_count=len(events_sorted),
            is_complete=is_complete,
            excluded_events=excluded_for_case,
            warnings=warnings,
            start_time=start_time,
            end_time=end_time
        ))

    # Derive process variants ONLY from complete cases
    complete_cases = [c for c in case_traces if c.is_complete]
    complete_cases_count = len(complete_cases)
    incomplete_cases_count = len(incomplete_case_ids)

    variant_groups: Dict[Tuple[str, ...], List[str]] = defaultdict(list)
    for c in complete_cases:
        seq_key = tuple(c.activity_sequence)
        variant_groups[seq_key].append(c.case_id)

    # Sort variants deterministically:
    # Primary: case count descending
    # Secondary: activity sequence alphabetically
    sorted_variant_keys = sorted(
        variant_groups.keys(),
        key=lambda k: (-len(variant_groups[k]), k)
    )

    process_variants: List[ProcessVariant] = []
    for var_idx, seq_key in enumerate(sorted_variant_keys, start=1):
        cases_in_var = variant_groups[seq_key]
        count = len(cases_in_var)
        percentage = round((count / complete_cases_count * 100.0), 2) if complete_cases_count > 0 else 0.0

        process_variants.append(ProcessVariant(
            variant_id=f"VAR-{var_idx:03d}",
            activity_sequence=list(seq_key),
            case_count=count,
            case_ids=sorted(cases_in_var),
            percentage=percentage
        ))

    exclusions = ReconstructionExclusions(
        total_excluded_rows=len(all_excluded_events),
        missing_case_id_count=missing_case_id_count,
        missing_activity_count=missing_activity_count,
        missing_or_invalid_timestamp_count=missing_or_invalid_ts_count,
        excluded_events=all_excluded_events,
        incomplete_case_ids=incomplete_case_ids
    )

    return ProcessReconstructionResult(
        filename=filename,
        total_source_rows=total_source_rows,
        eligible_event_count=eligible_event_count,
        total_cases_found=len(unique_cases_seen),
        complete_cases_count=complete_cases_count,
        incomplete_cases_count=incomplete_cases_count,
        variant_count=len(process_variants),
        exclusions=exclusions,
        variants=process_variants,
        cases=case_traces
    )
