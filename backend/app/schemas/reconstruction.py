"""
Pydantic schemas for deterministic Process Reconstruction and Variant Derivation.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ReconstructedEvent(BaseModel):
    row_index: int = Field(..., description="1-indexed row position in the source CSV")
    activity: str = Field(..., description="Canonical activity name")
    timestamp_raw: str = Field(..., description="Raw timestamp string from source file")
    timestamp_parsed: datetime = Field(..., description="Parsed datetime object")
    resource: Optional[str] = Field(None, description="Resource or user executing the event")
    attributes: Dict[str, Any] = Field(default_factory=dict, description="Additional contextual attributes")
    is_duplicate: bool = Field(False, description="Flagged if identical case_id, activity, and timestamp occurred earlier")

class CaseTrace(BaseModel):
    case_id: str = Field(..., description="Unique case identifier")
    events: List[ReconstructedEvent] = Field(..., description="Chronologically ordered events for this case")
    activity_sequence: List[str] = Field(..., description="Exact ordered sequence of activity names")
    event_count: int = Field(..., description="Count of reconstructable events in this trace")
    is_complete: bool = Field(True, description="False if any source row for this case contained validation errors")
    warnings: List[str] = Field(default_factory=list, description="Exclusion or ordering warnings for this case")
    start_time: Optional[datetime] = Field(None, description="Earliest event timestamp")
    end_time: Optional[datetime] = Field(None, description="Latest event timestamp")

class ProcessVariant(BaseModel):
    variant_id: str = Field(..., description="Deterministic variant identifier (e.g. VAR-1)")
    activity_sequence: List[str] = Field(..., description="Exact ordered activity sequence defining this variant")
    case_count: int = Field(..., description="Number of complete cases following this variant")
    case_ids: List[str] = Field(..., description="Case IDs following this variant")
    percentage: float = Field(..., description="Percentage of complete reconstructed cases (0.0 to 100.0)")

class ReconstructionExclusions(BaseModel):
    missing_case_id_rows: List[int] = Field(default_factory=list, description="Row indices excluded due to missing case_id")
    missing_activity_rows: List[int] = Field(default_factory=list, description="Row indices excluded due to missing activity")
    missing_or_invalid_timestamp_rows: List[int] = Field(default_factory=list, description="Row indices excluded due to invalid/missing timestamp")
    total_excluded_rows: int = Field(0, description="Total source rows excluded from traces")
    incomplete_case_ids: List[str] = Field(default_factory=list, description="Cases with reconstruction errors excluded from variant statistics")

class ProcessReconstructionResult(BaseModel):
    filename: str = Field(..., description="Filename of processed CSV")
    total_source_rows: int = Field(..., description="Total rows in source CSV")
    eligible_event_count: int = Field(..., description="Total events successfully sequenced into traces")
    total_cases_found: int = Field(..., description="Total unique case IDs encountered in source data")
    reconstructed_cases_count: int = Field(..., description="Total cases with complete, reconstructable traces")
    variant_count: int = Field(..., description="Number of distinct process variants found")
    denominator_description: str = Field(
        "reconstructed_cases_count: percentage calculated over cases with complete, reconstructable traces",
        description="Formal description of the denominator used for variant percentage calculations"
    )
    exclusions: ReconstructionExclusions
    variants: List[ProcessVariant]
    cases: List[CaseTrace]
