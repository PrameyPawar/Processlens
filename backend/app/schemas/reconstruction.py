"""
Pydantic models for process reconstruction output.

Defines structured schemas for case traces, process variants,
event exclusion reporting, and the full reconstruction response.
"""

from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class ReconstructedEvent(BaseModel):
    """A single event within a reconstructed case trace."""
    row_index: int = Field(..., description="1-indexed row position in original CSV")
    activity: str = Field(..., description="Activity name")
    timestamp: str = Field(..., description="Parsed ISO-format timestamp string")
    resource: Optional[str] = Field(None, description="Resource that performed the activity")
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional event-level metadata (department, order_value, etc.)"
    )


class CaseQualityWarning(BaseModel):
    """A quality warning attached to a specific case trace."""
    row_index: int = Field(..., description="1-indexed row position in original CSV")
    warning_type: str = Field(..., description="Type of warning: DUPLICATE_EVENT")
    details: str = Field(..., description="Human-readable explanation")


class ReconstructedCase(BaseModel):
    """A fully reconstructed case trace with ordered events."""
    case_id: str
    event_count: int = Field(..., description="Number of events in this case trace")
    activity_sequence: List[str] = Field(
        ..., description="Ordered list of activity names forming the case trace"
    )
    variant_id: str = Field(..., description="Identifier for the process variant this case belongs to")
    has_quality_warnings: bool = Field(
        False, description="True if this case has quality warnings (e.g. duplicate events)"
    )
    quality_warnings: List[CaseQualityWarning] = Field(default_factory=list)
    events: List[ReconstructedEvent] = Field(
        ..., description="Chronologically ordered events in this case"
    )


class ExcludedEvent(BaseModel):
    """An event excluded from reconstruction with the reason."""
    row_index: int = Field(..., description="1-indexed row position in original CSV")
    reason: str = Field(..., description="Why this event was excluded: MISSING_CASE_ID, MISSING_ACTIVITY, MISSING_OR_INVALID_TIMESTAMP")
    raw_values: Dict[str, Any] = Field(
        default_factory=dict,
        description="Raw field values from the excluded row"
    )


class ExclusionSummary(BaseModel):
    """Counts and details of events excluded from reconstruction."""
    missing_case_id: int = 0
    missing_activity: int = 0
    missing_or_invalid_timestamp: int = 0
    duplicate_events_included: int = Field(
        0,
        description="Duplicate events that were included in traces but flagged as warnings"
    )
    excluded_events: List[ExcludedEvent] = Field(default_factory=list)


class ProcessVariant(BaseModel):
    """A distinct process variant identified by its ordered activity sequence."""
    variant_id: str = Field(..., description="Stable identifier for this variant")
    activity_sequence: List[str] = Field(
        ..., description="The ordered activity sequence that defines this variant"
    )
    case_count: int = Field(..., description="Number of cases following this variant")
    case_percentage: float = Field(
        ..., description="Percentage of total reconstructed cases following this variant"
    )
    case_ids: List[str] = Field(
        ..., description="List of case IDs belonging to this variant"
    )


class ProcessReconstructionResult(BaseModel):
    """Complete process reconstruction output."""
    filename: str
    source_event_count: int = Field(
        ..., description="Total number of data rows in the uploaded CSV"
    )
    eligible_event_count: int = Field(
        ..., description="Events that passed eligibility checks for reconstruction"
    )
    excluded_event_count: int = Field(
        ..., description="Events excluded from reconstruction due to quality issues"
    )
    exclusions: ExclusionSummary
    case_count: int = Field(
        ..., description="Total number of distinct cases reconstructed"
    )
    cases: List[ReconstructedCase]
    variant_count: int = Field(
        ..., description="Total number of distinct process variants identified"
    )
    variants: List[ProcessVariant]
