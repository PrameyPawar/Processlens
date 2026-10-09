"""
Deterministic Process Reconstruction Engine.

Groups events by case_id, orders them chronologically, derives activity
sequences, and identifies process variants.

Reconstruction rules:
- Events missing case_id are excluded (cannot assign to a case).
- Events missing activity are excluded (cannot form a complete sequence).
- Events with missing or unparseable timestamps are excluded (cannot be ordered).
- Duplicate events (same case_id + activity + timestamp) are INCLUDED in traces
  but flagged as quality warnings on the affected case.
- Tie-breaking for equal timestamps: stable sort preserves original CSV row order.
- Variant identity is the exact ordered activity sequence (tuple). Repeated
  activities are preserved, not collapsed.
- Variant percentages use total reconstructed case_count as the denominator.
"""

import io
import csv
from typing import List, Dict, Any, Tuple
from collections import defaultdict

import pandas as pd

from app.schemas.reconstruction import (
    ProcessReconstructionResult,
    ReconstructedCase,
    ReconstructedEvent,
    CaseQualityWarning,
    ExclusionSummary,
    ExcludedEvent,
    ProcessVariant,
)


def reconstruct_process(content_bytes: bytes, filename: str) -> ProcessReconstructionResult:
    """
    Reconstruct process traces from raw CSV bytes.

    This function operates independently of the ingestion validator to avoid
    coupling. It applies its own eligibility filters aligned with reconstruction
    requirements.
    """
    try:
        text_content = content_bytes.decode("utf-8-sig")
    except UnicodeDecodeError:
        text_content = content_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(text_content))
    if not reader.fieldnames:
        raise ValueError("Uploaded file is empty or missing a valid CSV header.")

    # Map header names (case-insensitive)
    header_map = {c.strip().lower(): c for c in reader.fieldnames if c}

    required = ["case_id", "activity", "timestamp"]
    missing_headers = [r for r in required if r not in header_map]
    if missing_headers:
        raise ValueError(
            f"Missing required column(s): {', '.join(missing_headers)}. "
            f"Required: case_id, activity, timestamp"
        )

    col_case_id = header_map["case_id"]
    col_activity = header_map["activity"]
    col_timestamp = header_map["timestamp"]
    col_resource = header_map.get("resource")

    # Metadata columns: everything except the three required + resource
    meta_cols = {
        k_lower: k_orig
        for k_lower, k_orig in header_map.items()
        if k_lower not in ("case_id", "activity", "timestamp", "resource")
    }

    # ------------------------------------------------------------------ #
    # Pass 1: Parse all rows and classify as eligible or excluded
    # ------------------------------------------------------------------ #
    source_event_count = 0
    exclusion_summary = ExclusionSummary()

    # Eligible events grouped by case_id
    # Each entry: (row_index, activity, parsed_timestamp, resource, metadata_dict)
    case_events: Dict[str, List[Tuple[int, str, Any, str, Dict[str, Any]]]] = defaultdict(list)

    # Track duplicates per case for flagging
    seen_per_case: Dict[str, set] = defaultdict(set)
    duplicate_rows: Dict[str, List[Tuple[int, str, str]]] = defaultdict(list)

    for idx, row in enumerate(reader, start=1):
        source_event_count += 1

        raw_case_id = row.get(col_case_id, "") if col_case_id else ""
        raw_activity = row.get(col_activity, "") if col_activity else ""
        raw_timestamp = row.get(col_timestamp, "") if col_timestamp else ""

        case_id_val = str(raw_case_id).strip() if raw_case_id is not None else ""
        activity_val = str(raw_activity).strip() if raw_activity is not None else ""
        timestamp_val = str(raw_timestamp).strip() if raw_timestamp is not None else ""

        raw_vals = {
            "case_id": raw_case_id,
            "activity": raw_activity,
            "timestamp": raw_timestamp,
        }

        # --- Exclusion checks ---
        if not case_id_val:
            exclusion_summary.missing_case_id += 1
            exclusion_summary.excluded_events.append(
                ExcludedEvent(row_index=idx, reason="MISSING_CASE_ID", raw_values=raw_vals)
            )
            continue

        if not activity_val:
            exclusion_summary.missing_activity += 1
            exclusion_summary.excluded_events.append(
                ExcludedEvent(row_index=idx, reason="MISSING_ACTIVITY", raw_values=raw_vals)
            )
            continue

        if not timestamp_val:
            exclusion_summary.missing_or_invalid_timestamp += 1
            exclusion_summary.excluded_events.append(
                ExcludedEvent(row_index=idx, reason="MISSING_OR_INVALID_TIMESTAMP", raw_values=raw_vals)
            )
            continue

        try:
            parsed_ts = pd.to_datetime(timestamp_val, errors="raise")
        except Exception:
            exclusion_summary.missing_or_invalid_timestamp += 1
            exclusion_summary.excluded_events.append(
                ExcludedEvent(row_index=idx, reason="MISSING_OR_INVALID_TIMESTAMP", raw_values=raw_vals)
            )
            continue

        # --- Duplicate detection (included but flagged) ---
        event_key = (case_id_val, activity_val, timestamp_val)
        if event_key in seen_per_case[case_id_val]:
            exclusion_summary.duplicate_events_included += 1
            duplicate_rows[case_id_val].append((idx, activity_val, timestamp_val))
        else:
            seen_per_case[case_id_val].add(event_key)

        # --- Collect resource and metadata ---
        resource_val = ""
        if col_resource:
            raw_resource = row.get(col_resource, "")
            resource_val = str(raw_resource).strip() if raw_resource else ""

        metadata = {}
        for meta_lower, meta_orig in meta_cols.items():
            val = row.get(meta_orig, "")
            if val is not None and str(val).strip():
                metadata[meta_lower] = str(val).strip()

        case_events[case_id_val].append(
            (idx, activity_val, parsed_ts, resource_val, metadata)
        )

    # ------------------------------------------------------------------ #
    # Pass 2: Sort each case's events and build traces
    # ------------------------------------------------------------------ #
    excluded_event_count = (
        exclusion_summary.missing_case_id
        + exclusion_summary.missing_activity
        + exclusion_summary.missing_or_invalid_timestamp
    )
    eligible_event_count = source_event_count - excluded_event_count

    # Variant identification: map activity-sequence tuple -> list of case_ids
    variant_map: Dict[Tuple[str, ...], List[str]] = defaultdict(list)

    reconstructed_cases: List[ReconstructedCase] = []

    # Sort case_ids for deterministic output order
    for case_id in sorted(case_events.keys()):
        events = case_events[case_id]

        # Sort by (parsed_timestamp, row_index) for deterministic tie-breaking
        events.sort(key=lambda e: (e[2], e[0]))

        activity_sequence = [e[1] for e in events]
        variant_key = tuple(activity_sequence)
        variant_map[variant_key].append(case_id)

        # Build quality warnings for duplicates in this case
        warnings: List[CaseQualityWarning] = []
        if case_id in duplicate_rows:
            for dup_row, dup_act, dup_ts in duplicate_rows[case_id]:
                warnings.append(CaseQualityWarning(
                    row_index=dup_row,
                    warning_type="DUPLICATE_EVENT",
                    details=f"Duplicate event: activity='{dup_act}' timestamp='{dup_ts}'"
                ))

        reconstructed_events = [
            ReconstructedEvent(
                row_index=e[0],
                activity=e[1],
                timestamp=e[2].isoformat(),
                resource=e[3] if e[3] else None,
                metadata=e[4],
            )
            for e in events
        ]

        reconstructed_cases.append(ReconstructedCase(
            case_id=case_id,
            event_count=len(events),
            activity_sequence=activity_sequence,
            variant_id="",  # Assigned below
            has_quality_warnings=len(warnings) > 0,
            quality_warnings=warnings,
            events=reconstructed_events,
        ))

    # ------------------------------------------------------------------ #
    # Pass 3: Assign variant IDs and compute percentages
    # ------------------------------------------------------------------ #
    case_count = len(reconstructed_cases)

    # Sort variants by case count descending, then by sequence for stability
    sorted_variants = sorted(
        variant_map.items(),
        key=lambda item: (-len(item[1]), item[0])
    )

    # Build variant objects and a lookup from case_id -> variant_id
    case_to_variant: Dict[str, str] = {}
    variant_objects: List[ProcessVariant] = []

    for v_idx, (seq_tuple, case_ids) in enumerate(sorted_variants, start=1):
        vid = f"variant-{v_idx:03d}"
        sorted_case_ids = sorted(case_ids)
        for cid in sorted_case_ids:
            case_to_variant[cid] = vid

        pct = (len(case_ids) / case_count * 100) if case_count > 0 else 0.0
        variant_objects.append(ProcessVariant(
            variant_id=vid,
            activity_sequence=list(seq_tuple),
            case_count=len(case_ids),
            case_percentage=round(pct, 2),
            case_ids=sorted_case_ids,
        ))

    # Backfill variant_id on each case
    for case in reconstructed_cases:
        case.variant_id = case_to_variant.get(case.case_id, "unknown")

    return ProcessReconstructionResult(
        filename=filename,
        source_event_count=source_event_count,
        eligible_event_count=eligible_event_count,
        excluded_event_count=excluded_event_count,
        exclusions=exclusion_summary,
        case_count=case_count,
        cases=reconstructed_cases,
        variant_count=len(variant_objects),
        variants=variant_objects,
    )
