"""
Pydantic models for CSV ingestion and data quality reporting.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

class DataQualityIssue(BaseModel):
    row_index: int = Field(..., description="1-indexed row position in original CSV")
    issue_type: str = Field(..., description="Category of error: MISSING_CASE_ID, MISSING_ACTIVITY, MISSING_TIMESTAMP, INVALID_TIMESTAMP, DUPLICATE_EVENT")
    column_name: str = Field(..., description="Affected column name")
    raw_value: Optional[str] = Field(None, description="Raw unparsed value from file")
    details: str = Field(..., description="Human-readable explanation of issue")

class QualitySummary(BaseModel):
    missing_case_id_count: int = 0
    missing_activity_count: int = 0
    missing_timestamp_count: int = 0
    invalid_timestamp_count: int = 0
    duplicate_event_count: int = 0

class DataQualityReport(BaseModel):
    filename: str
    total_rows: int
    valid_rows: int
    invalid_rows: int
    summary: QualitySummary
    issues: List[DataQualityIssue]
    preview: List[Dict[str, Any]]
