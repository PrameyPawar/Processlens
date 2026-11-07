"""
CSV Data Ingestion and Validation Engine.
Performs data quality checks without silently dropping or mutating bad records.
"""

import io
import csv
from typing import List, Dict, Any, Tuple
import pandas as pd
from app.core.config import settings
from app.schemas.ingestion import DataQualityReport, DataQualityIssue, QualitySummary
from app.services.csv_schema import find_source_event_id_column

def validate_csv_content(content_bytes: bytes, filename: str) -> DataQualityReport:
    """
    Parses and validates CSV content line-by-line against canonical schema requirements.
    Does NOT silently drop invalid records.
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

    # Check for required canonical columns (case-insensitive mapping)
    header_cols = [c.strip().lower() for c in reader.fieldnames if c]
    required_cols = [c.lower() for c in settings.CANONICAL_REQUIRED_COLUMNS]

    missing_header_cols = [c for c in required_cols if c not in header_cols]
    if missing_header_cols:
        raise ValueError(
            f"Missing required canonical column(s): {', '.join(missing_header_cols)}. "
            f"Required columns are: {', '.join(settings.CANONICAL_REQUIRED_COLUMNS)}"
        )

    # Map header names to exact dictionary keys
    header_map = {c.strip().lower(): c for c in reader.fieldnames if c}
    col_case_id = header_map.get("case_id")
    col_activity = header_map.get("activity")
    col_timestamp = header_map.get("timestamp")
    col_event_id = find_source_event_id_column(reader.fieldnames)

    issues: List[DataQualityIssue] = []
    summary = QualitySummary()
    seen_events: set = set()
    event_ids_by_operational_key: Dict[Tuple[str, str, str], set] = {}

    total_rows = 0
    valid_rows_count = 0
    invalid_rows_count = 0
    preview_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(reader, start=1):
        total_rows += 1
        row_has_issue = False
        extra_values = row.get(None)
        if extra_values:
            row_has_issue = True
            summary.malformed_row_count += 1
            issues.append(DataQualityIssue(
                row_index=idx,
                issue_type="MALFORMED_ROW",
                column_name="row",
                raw_value=", ".join(str(value) for value in extra_values),
                details=f"Row contains {len(extra_values)} value(s) beyond the {len(reader.fieldnames)} header columns",
            ))

        # Extract values
        raw_case_id = row.get(col_case_id, "") if col_case_id else ""
        raw_activity = row.get(col_activity, "") if col_activity else ""
        raw_timestamp = row.get(col_timestamp, "") if col_timestamp else ""
        raw_event_id = row.get(col_event_id, "") if col_event_id else ""

        case_id_val = str(raw_case_id).strip() if raw_case_id is not None else ""
        activity_val = str(raw_activity).strip() if raw_activity is not None else ""
        timestamp_val = str(raw_timestamp).strip() if raw_timestamp is not None else ""
        event_id_val = str(raw_event_id).strip() if raw_event_id is not None else ""

        # 1. Missing case_id check
        if not case_id_val:
            row_has_issue = True
            summary.missing_case_id_count += 1
            issues.append(DataQualityIssue(
                row_index=idx,
                issue_type="MISSING_CASE_ID",
                column_name=col_case_id or "case_id",
                raw_value=raw_case_id,
                details="case_id field is missing or empty"
            ))

        # 2. Missing activity check
        if not activity_val:
            row_has_issue = True
            summary.missing_activity_count += 1
            issues.append(DataQualityIssue(
                row_index=idx,
                issue_type="MISSING_ACTIVITY",
                column_name=col_activity or "activity",
                raw_value=raw_activity,
                details="activity field is missing or empty"
            ))

        # 3. Missing / Invalid timestamp check
        parsed_ts = None
        if not timestamp_val:
            row_has_issue = True
            summary.missing_timestamp_count += 1
            issues.append(DataQualityIssue(
                row_index=idx,
                issue_type="MISSING_TIMESTAMP",
                column_name=col_timestamp or "timestamp",
                raw_value=raw_timestamp,
                details="timestamp field is missing or empty"
            ))
        else:
            try:
                # Validate timestamp formatting with pandas
                parsed_ts = pd.to_datetime(timestamp_val, errors='raise')
            except Exception:
                row_has_issue = True
                summary.invalid_timestamp_count += 1
                issues.append(DataQualityIssue(
                    row_index=idx,
                    issue_type="INVALID_TIMESTAMP",
                    column_name=col_timestamp or "timestamp",
                    raw_value=timestamp_val,
                    details=f"Timestamp string '{timestamp_val}' could not be parsed into valid datetime format"
                ))

        # 4. Prefer source identity. Equal activity/timestamp values can be
        # distinct operational events, as in logs with a source event ID.
        if case_id_val and event_id_val:
            source_key = (case_id_val, event_id_val)
            if source_key in seen_events:
                row_has_issue = True
                summary.duplicate_event_count += 1
                issues.append(DataQualityIssue(
                    row_index=idx,
                    issue_type="DUPLICATE_EVENT",
                    column_name=col_event_id or "source_event_id",
                    raw_value=event_id_val,
                    details=f"Source event ID '{event_id_val}' is repeated within case '{case_id_val}'.",
                ))
            else:
                seen_events.add(source_key)

        if case_id_val and activity_val and timestamp_val:
            ts_key = str(parsed_ts) if parsed_ts is not None else timestamp_val
            operational_key = (case_id_val, activity_val, ts_key)
            prior_ids = event_ids_by_operational_key.setdefault(operational_key, set())
            missing_identity_match = (
                (not event_id_val and bool(prior_ids))
                or (bool(event_id_val) and None in prior_ids)
            )
            if missing_identity_match and not (event_id_val and (case_id_val, event_id_val) in seen_events and row_has_issue):
                summary.potential_duplicate_event_count += 1
                issues.append(DataQualityIssue(
                    row_index=idx,
                    issue_type="POTENTIAL_DUPLICATE_EVENT",
                    severity="WARNING",
                    column_name="multiple",
                    raw_value=f"{case_id_val} | {activity_val} | {timestamp_val}",
                    details="Case, activity, and timestamp match a row without a source event ID, so duplicate identity cannot be confirmed.",
                ))
            prior_ids.add(event_id_val or None)

        if row_has_issue:
            invalid_rows_count += 1
        else:
            valid_rows_count += 1

        # Populate preview (first 10 rows)
        if len(preview_rows) < 10:
            clean_row_dict = {k: v for k, v in row.items() if k}
            if extra_values:
                clean_row_dict["__extra_columns__"] = extra_values
            preview_rows.append(clean_row_dict)

    return DataQualityReport(
        filename=filename,
        total_rows=total_rows,
        valid_rows=valid_rows_count,
        invalid_rows=invalid_rows_count,
        summary=summary,
        issues=issues,
        preview=preview_rows
    )
