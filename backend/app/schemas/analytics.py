"""
Pydantic schemas for deterministic Process Analytics (Phase 3).
"""

from typing import List
from pydantic import BaseModel, Field

class DurationStats(BaseModel):
    mean_seconds: float = Field(..., description="Arithmetic mean duration in seconds")
    median_seconds: float = Field(..., description="50th percentile duration in seconds")
    min_seconds: float = Field(..., description="Minimum recorded duration in seconds")
    max_seconds: float = Field(..., description="Maximum recorded duration in seconds")
    p90_seconds: float = Field(..., description="90th percentile duration in seconds using linear interpolation")

class ReconstructionSummary(BaseModel):
    total_source_rows: int = Field(..., description="Total rows in source CSV")
    eligible_event_count: int = Field(..., description="Total events successfully sequenced into traces")
    total_cases_found: int = Field(..., description="Total unique case IDs encountered in source data")
    complete_cases_count: int = Field(..., description="Total cases with complete, error-free traces")
    incomplete_cases_count: int = Field(..., description="Total cases with row-level validation defects")
    variant_count: int = Field(..., description="Number of distinct process variants found")

class ActivityFrequency(BaseModel):
    activity: str = Field(..., description="Activity name")
    total_occurrences: int = Field(..., description="Total executions across complete cases")
    case_count: int = Field(..., description="Number of complete cases containing this activity")
    case_coverage_percentage: float = Field(..., description="Percentage of complete cases executing this activity")
    repetition_ratio: float = Field(..., description="total_occurrences / case_count (indicator of recurrence, not process failure)")

class ActivityRework(BaseModel):
    activity: str = Field(..., description="Activity name")
    rework_case_count: int = Field(..., description="Count of complete cases with distinct-timestamp recurrences")
    rework_case_percentage: float = Field(..., description="Percentage of complete cases with distinct-timestamp recurrences")
    rework_occurrences: int = Field(..., description="Total distinct-timestamp repetitions beyond initial execution")
    duplicate_events_count: int = Field(..., description="Total identical-timestamp duplicate events recorded")

class ActivityTransition(BaseModel):
    source_activity: str = Field(..., description="Preceding activity")
    target_activity: str = Field(..., description="Succeeding activity")
    transition_count: int = Field(..., description="Total direct transitions observed across complete cases")
    case_count: int = Field(..., description="Count of complete cases containing this transition")
    duration_stats: DurationStats = Field(..., description="Transition elapsed duration statistics (milestone elapsed time, not waiting/processing)")

class CycleTimeSummary(BaseModel):
    evaluated_cases_count: int = Field(..., description="Total complete cases evaluated (including single-event cases at 0.0s)")
    duration_stats: DurationStats = Field(..., description="Case cycle time distribution statistics")

class ProcessAnalyticsResult(BaseModel):
    filename: str = Field(..., description="Filename of analyzed dataset")
    reconstruction_summary: ReconstructionSummary = Field(..., description="Typed summary of case reconstruction results")
    cycle_time: CycleTimeSummary = Field(..., description="Cycle time distribution across complete cases")
    activity_frequency: List[ActivityFrequency] = Field(..., description="Activity occurrences and coverage across complete cases")
    rework: List[ActivityRework] = Field(..., description="Repeated-activity indicators across complete cases")
    transitions: List[ActivityTransition] = Field(..., description="Direct step-to-step transition durations across complete cases")
