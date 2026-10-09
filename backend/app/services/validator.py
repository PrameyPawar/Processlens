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

    issues: List[DataQualityIssue] = []
    summary = QualitySummary()
    seen_events: set = set()

    total_rows = 0
    valid_rows_count = 0
    invalid_rows_count = 0
    preview_rows: List[Dict[str, Any]] = []

    for idx, row in enumerate(reader, start=1):
        total_rows += 1
        row_has_issue = False

        # Extract values
        raw_case_id = row.get(col_case_id, "") if col_case_id else ""
        raw_activity = row.get(col_activity, "") if col_activity else ""
        raw_timestamp = row.get(col_timestamp, "") if col_timestamp else ""

        case_id_val = str(raw_case_id).strip() if raw_case_id is not None else ""
        activity_val = str(raw_activity).strip() if raw_activity is not None else ""
        timestamp_val = str(raw_timestamp).strip() if raw_timestamp is not None else ""

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

        # 4. Duplicate event check (case_id + activity + timestamp)
        if case_id_val and activity_val and timestamp_val:
            event_key = (case_id_val, activity_val, timestamp_val)
            if event_key in seen_events:
                row_has_issue = True
                summary.duplicate_event_count += 1
                issues.append(DataQualityIssue(
                    row_index=idx,
                    issue_type="DUPLICATE_EVENT",
                    column_name="multiple",
                    raw_value=f"{case_id_val} | {activity_val} | {timestamp_val}",
                    details="Duplicate event detected with identical case_id, activity, and timestamp"
                ))
            else:
                seen_events.add(event_key)

        if row_has_issue:
            invalid_rows_count += 1
        else:
            valid_rows_count += 1

        # Populate preview (first 10 rows)
        if len(preview_rows) < 10:
            clean_row_dict = {k: v for k, v in row.items() if k}
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
