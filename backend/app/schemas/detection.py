"""
Pydantic schemas for deterministic Problem Detection and Operational Signals (Phase 4).
Defines canonical fields and deprecated legacy compatibility fields.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FindingCategory(str, Enum):
    """
    High-level category of detected operational signals.
    Canonical value for transition elapsed time concentration is DURATION_CONCENTRATION.
    BOTTLENECK is deprecated and retained for backward compatibility.
    """
    DURATION_CONCENTRATION = "DURATION_CONCENTRATION"
    REPETITION = "REPETITION"
    CYCLE_TIME_OUTLIER = "CYCLE_TIME_OUTLIER"
    PATH_VARIATION = "PATH_VARIATION"
    DATA_QUALITY_LIMITATION = "DATA_QUALITY_LIMITATION"

    # Deprecated: Legacy category preserved for backward compatibility.
    # New consumers must use canonical DURATION_CONCENTRATION.
    BOTTLENECK = "BOTTLENECK"


class SignalLevel(str, Enum):
    """
    Signal prominence level reflecting pattern magnitude in observed data:
    HIGH, MEDIUM, LOW, INFO. Distinct from evidence strength; does not assert business impact.
    """
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


# Deprecated: Legacy alias for SignalLevel. New consumers must use SignalLevel.
SeverityLevel = SignalLevel


class EvidenceStrength(str, Enum):
    """
    Statistical confidence based strictly on evaluated sample size for that specific finding:
    HIGH (>=30), MODERATE (10-29), LIMITED (<10).
    """
    HIGH = "HIGH"
    MODERATE = "MODERATE"
    LIMITED = "LIMITED"


class ReconciliationStatus(BaseModel):
    reconciled: bool = Field(
        ...,
        description="True if total transition duration reconciles with cumulative cycle time within tolerance"
    )
    total_transition_duration_seconds: float = Field(
        ...,
        description="Sum of all transition durations across complete cases (seconds)"
    )
    cumulative_cycle_time_seconds: float = Field(
        ...,
        description="Sum of cycle times for all complete cases (seconds)"
    )
    discrepancy_seconds: float = Field(
        ...,
        description="Absolute difference between transition duration sum and cumulative cycle time"
    )
    discrepancy_percentage: float = Field(
        ...,
        description="Discrepancy as a percentage of cumulative complete-case cycle time"
    )
    tolerance_percentage: float = Field(
        1.0,
        description="Accounting tolerance threshold in percent (default 1.0%)"
    )
    duration_share_suppressed: bool = Field(
        ...,
        description="True if duration share calculations were suppressed due to reconciliation mismatch or zero cycle time"
    )
    limitation_note: str = Field(
        "A passing reconciliation check verifies arithmetic consistency between complete-case transition intervals and case spans. It does not independently prove that individual transition durations are correctly attributed, non-overlapping, or representative of active work.",
        description="Explicit limitation disclaimer for the accounting reconciliation check"
    )


class DetectionSummary(BaseModel):
    evaluated_cases_count: int = Field(
        ...,
        description="Number of complete cases evaluated for problem detection"
    )
    total_findings_count: int = Field(
        ...,
        description="Total problem findings emitted"
    )
    high_signal_count: int = Field(
        0,
        description="Canonical: Count of HIGH prominence findings"
    )
    medium_signal_count: int = Field(
        0,
        description="Canonical: Count of MEDIUM prominence findings"
    )
    low_signal_count: int = Field(
        0,
        description="Canonical: Count of LOW prominence findings"
    )
    info_signal_count: int = Field(
        0,
        description="Canonical: Count of INFO prominence findings"
    )
    # Deprecated legacy aliases
    high_severity_count: Optional[int] = Field(
        None,
        deprecated=True,
        description="Deprecated: Legacy alias for high_signal_count. New consumers must use canonical high_signal_count."
    )
    medium_severity_count: Optional[int] = Field(
        None,
        deprecated=True,
        description="Deprecated: Legacy alias for medium_signal_count. New consumers must use canonical medium_signal_count."
    )
    low_severity_count: Optional[int] = Field(
        None,
        deprecated=True,
        description="Deprecated: Legacy alias for low_signal_count. New consumers must use canonical low_signal_count."
    )
    info_severity_count: Optional[int] = Field(
        None,
        deprecated=True,
        description="Deprecated: Legacy alias for info_signal_count. New consumers must use canonical info_signal_count."
    )
    reconciliation: ReconciliationStatus = Field(
        ...,
        description="Accounting integrity check between transitions and cycle time"
    )


class ProblemFinding(BaseModel):
    id: str = Field(
        ...,
        description="Deterministic unique finding identifier (e.g. finding_transition_production_quality_inspection)"
    )
    category: FindingCategory = Field(
        ...,
        description="High-level category of detected operational signal (e.g. DURATION_CONCENTRATION, REPETITION). Canonical category for elapsed duration concentration is DURATION_CONCENTRATION."
    )
    rule: str = Field(
        ...,
        description="Deterministic rule or algorithm triggering the finding"
    )
    title: str = Field(
        ...,
        description="Short neutral descriptive title"
    )
    signal_level: SignalLevel = Field(
        ...,
        description="Canonical signal prominence level: HIGH, MEDIUM, LOW, INFO. Reflects magnitude/concentration in data; does not assert business impact."
    )
    severity: Optional[SignalLevel] = Field(
        None,
        deprecated=True,
        description="Deprecated: Legacy alias for signal_level. New consumers must use canonical signal_level."
    )
    evidence_strength: EvidenceStrength = Field(
        ...,
        description="Finding-specific evidence strength: HIGH, MODERATE, or LIMITED based strictly on evaluated sample size"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transparent deterministic metrics supporting the finding. New consumers must use canonical keys (e.g. recurrence_case_count). Legacy rework_* keys are deprecated."
    )
    explanation: str = Field(
        ...,
        description="Neutral explanation of evidence without asserting root causes, defects, waste, or bottlenecks"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit boundaries and disclaimers regarding the finding"
    )


class ProblemDetectionResult(BaseModel):
    filename: str = Field(
        ...,
        description="Filename of analyzed dataset"
    )
    summary: DetectionSummary = Field(
        ...,
        description="Summary of detection run and reconciliation status"
    )
    findings: List[ProblemFinding] = Field(
        default_factory=list,
        description="Deterministic list of detected problem findings"
    )
