"""
Pydantic schemas for deterministic Problem and Bottleneck Detection (Phase 4).
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field


class FindingCategory(str, Enum):
    BOTTLENECK = "BOTTLENECK"
    REPETITION = "REPETITION"
    CYCLE_TIME_OUTLIER = "CYCLE_TIME_OUTLIER"
    PATH_VARIATION = "PATH_VARIATION"
    DATA_QUALITY_LIMITATION = "DATA_QUALITY_LIMITATION"


class SeverityLevel(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class EvidenceStrength(str, Enum):
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
    high_severity_count: int = Field(
        0,
        description="Count of HIGH severity findings"
    )
    medium_severity_count: int = Field(
        0,
        description="Count of MEDIUM severity findings"
    )
    low_severity_count: int = Field(
        0,
        description="Count of LOW severity findings"
    )
    info_severity_count: int = Field(
        0,
        description="Count of INFO severity findings"
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
        description="High-level category of detected operational signal"
    )
    rule: str = Field(
        ...,
        description="Deterministic rule or algorithm triggering the finding"
    )
    title: str = Field(
        ...,
        description="Short neutral descriptive title"
    )
    severity: SeverityLevel = Field(
        ...,
        description="Signal severity level: HIGH, MEDIUM, LOW, INFO"
    )
    evidence_strength: EvidenceStrength = Field(
        ...,
        description="Finding-specific evidence strength: HIGH, MODERATE, or LIMITED"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Transparent deterministic metrics supporting the finding"
    )
    explanation: str = Field(
        ...,
        description="Neutral explanation of evidence without asserting root causes or waste"
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
