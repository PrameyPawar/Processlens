"""
Process Reconstruction Service.
Deterministically reconstructs case traces, sequences, and variants from CSV event records.
Adheres strictly to the ProcessLens Data-Quality Policy:
- No silent record mutation or deletion
- Clear accounting of exclusions and data defects
- Deterministic timestamp sorting with row_index tie-breaking
- Strict variant derivation based on ordered activity sequence
"""

import io
import csv
from typing import List, Dict, Any, Tuple
from collections import defaultdict
import pandas as pd
from app.core.config import settings
from app.schemas.reconstruction import (
    ReconstructedEvent,
    CaseTrace,
    ProcessVariant,
    ReconstructionExclusions,
    ProcessReconstructionResult
)

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

    # Validate required canonical headers
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

    # Exclusions tracking
    missing_case_id_rows: List[int] = []
    missing_activity_rows: List[int] = []
    missing_or_invalid_ts_rows: List[int] = []
    
    # Per-case raw event staging
    case_raw_events: Dict[str, List[ReconstructedEvent]] = defaultdict(list)
    case_warnings: Dict[str, List[str]] = defaultdict(list)
    case_error_flags: Dict[str, bool] = defaultdict(bool)
    
    total_source_rows = 0
    eligible_event_count = 0
    unique_cases_seen: set = set()
    case_seen_event_keys: Dict[str, set] = defaultdict(set)

    for row_idx, row in enumerate(reader, start=1):
        total_source_rows += 1

        raw_case_id = row.get(col_case_id, "") if col_case_id else ""
        raw_activity = row.get(col_activity, "") if col_activity else ""
        raw_timestamp = row.get(col_timestamp, "") if col_timestamp else ""
        raw_resource = row.get(col_resource, "") if col_resource else None

        case_id_val = str(raw_case_id).strip() if raw_case_id is not None else ""
        activity_val = str(raw_activity).strip() if raw_activity is not None else ""
        timestamp_val = str(raw_timestamp).strip() if raw_timestamp is not None else ""
        resource_val = str(raw_resource).strip() if raw_resource is not None and str(raw_resource).strip() else None

        # 1. Check for missing case ID
        if not case_id_val:
            missing_case_id_rows.append(row_idx)
            continue

        unique_cases_seen.add(case_id_val)

        # 2. Check for missing activity
        if not activity_val:
            missing_activity_rows.append(row_idx)
            case_error_flags[case_id_val] = True
            case_warnings[case_id_val].append(
                f"Row {row_idx}: Event excluded from trace due to missing activity name."
            )
            continue

        # 3. Check for missing or invalid timestamp
        if not timestamp_val:
            missing_or_invalid_ts_rows.append(row_idx)
            case_error_flags[case_id_val] = True
            case_warnings[case_id_val].append(
                f"Row {row_idx}: Event '{activity_val}' excluded from trace due to missing timestamp."
            )
            continue

        try:
            parsed_dt = pd.to_datetime(timestamp_val, errors='raise').to_pydatetime(warn=False)
        except Exception:
            missing_or_invalid_ts_rows.append(row_idx)
            case_error_flags[case_id_val] = True
            case_warnings[case_id_val].append(
                f"Row {row_idx}: Event '{activity_val}' excluded from trace due to unparseable timestamp '{timestamp_val}'."
            )
            continue

        # Extract extra contextual attributes (excluding primary columns)
        excluded_keys = {col_case_id, col_activity, col_timestamp, col_resource}
        attributes = {k: v for k, v in row.items() if k not in excluded_keys and v is not None}

        # 4. Check for duplicate event (case_id + activity + timestamp)
        # Duplicate events are preserved in the sequence and flagged
        event_key = (activity_val, str(parsed_dt))
        is_dup = False
        if event_key in case_seen_event_keys[case_id_val]:
            is_dup = True
            case_warnings[case_id_val].append(
                f"Row {row_idx}: Event '{activity_val}' at {timestamp_val} is a duplicate of an earlier event in case '{case_id_val}'."
            )
        else:
            case_seen_event_keys[case_id_val].add(event_key)

        event = ReconstructedEvent(
            row_index=row_idx,
            activity=activity_val,
            timestamp_raw=timestamp_val,
            timestamp_parsed=parsed_dt,
            resource=resource_val,
            attributes=attributes,
            is_duplicate=is_dup
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
        warnings = case_warnings[case_id]

        # Deterministic chronological sort:
        # Secondary key is row_index to break equal timestamp ties stably
        events_sorted = sorted(events, key=lambda e: (e.timestamp_parsed, e.row_index))
        activity_seq = [e.activity for e in events_sorted]

        start_time = events_sorted[0].timestamp_parsed if events_sorted else None
        end_time = events_sorted[-1].timestamp_parsed if events_sorted else None
        is_complete = (not has_errors) and len(events_sorted) > 0

        if not is_complete:
            incomplete_case_ids.append(case_id)

        case_traces.append(CaseTrace(
            case_id=case_id,
            events=events_sorted,
            activity_sequence=activity_seq,
            event_count=len(events_sorted),
            is_complete=is_complete,
            warnings=warnings,
            start_time=start_time,
            end_time=end_time
        ))

    # Derive process variants from complete, reconstructable cases
    complete_cases = [c for c in case_traces if c.is_complete]
    reconstructed_cases_count = len(complete_cases)

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
        percentage = round((count / reconstructed_cases_count * 100.0), 2) if reconstructed_cases_count > 0 else 0.0

        process_variants.append(ProcessVariant(
            variant_id=f"VAR-{var_idx:03d}",
            activity_sequence=list(seq_key),
            case_count=count,
            case_ids=sorted(cases_in_var),
            percentage=percentage
        ))

    total_excluded_rows = (
        len(missing_case_id_rows) +
        len(missing_activity_rows) +
        len(missing_or_invalid_ts_rows)
    )

    exclusions = ReconstructionExclusions(
        missing_case_id_rows=missing_case_id_rows,
        missing_activity_rows=missing_activity_rows,
        missing_or_invalid_timestamp_rows=missing_or_invalid_ts_rows,
        total_excluded_rows=total_excluded_rows,
        incomplete_case_ids=incomplete_case_ids
    )

    return ProcessReconstructionResult(
        filename=filename,
        total_source_rows=total_source_rows,
        eligible_event_count=eligible_event_count,
        total_cases_found=len(unique_cases_seen),
        reconstructed_cases_count=reconstructed_cases_count,
        variant_count=len(process_variants),
        exclusions=exclusions,
        variants=process_variants,
        cases=case_traces
    )
