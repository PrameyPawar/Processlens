"""
Pydantic schemas for deterministic Process Improvement and Automation Opportunity Detection (Phase 5).
Defines candidate opportunity schemas, evidence links, and operational priority ranking models.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schemas.detection import EvidenceStrength


class OpportunityArchetype(str, Enum):
    """
    Operational opportunity archetype derived from underlying analytical evidence.
    """
    DELAY_COMPRESSION = "DELAY_COMPRESSION"
    RECURRENCE_REDUCTION = "RECURRENCE_REDUCTION"
    TAIL_VARIANCE_MITIGATION = "TAIL_VARIANCE_MITIGATION"
    PATH_STANDARDIZATION = "PATH_STANDARDIZATION"
    DATA_INSTRUMENTATION = "DATA_INSTRUMENTATION"


class InterventionCategory(str, Enum):
    """
    Categorical classification of candidate intervention approach.
    Interventions are hypotheses to investigate with process owners, not proven remedies.
    When operational evidence (e.g. elapsed duration concentration or recurrence prevalence)
    does not establish a specific intervention mechanism, UNDETERMINED_INVESTIGATION is assigned.
    """
    UNDETERMINED_INVESTIGATION = "UNDETERMINED_INVESTIGATION"
    PROCESS_SIMPLIFICATION = "PROCESS_SIMPLIFICATION"
    QUALITY_GATING = "QUALITY_GATING"
    EXCEPTION_MANAGEMENT = "EXCEPTION_MANAGEMENT"
    DATA_INSTRUMENTATION = "DATA_INSTRUMENTATION"
    TASK_AUTOMATION_CANDIDATE = "TASK_AUTOMATION_CANDIDATE"


class PriorityTier(str, Enum):
    """
    Categorical operational priority tier based on deterministic score and evidence strength:
    TIER_1_HIGH (score >= 60.0), TIER_2_MEDIUM (40.0 <= score < 60.0),
    TIER_3_LOW (20.0 <= score < 40.0), TIER_4_EXPLORATORY (score < 20.0 or evidence is LIMITED).
    """
    TIER_1_HIGH = "TIER_1_HIGH"
    TIER_2_MEDIUM = "TIER_2_MEDIUM"
    TIER_3_LOW = "TIER_3_LOW"
    TIER_4_EXPLORATORY = "TIER_4_EXPLORATORY"


class ScoreBreakdown(BaseModel):
    """
    Transparent breakdown of the deterministic operational priority score.
    Ranks measured operational patterns for operational investigation; it does NOT establish
    avoidability, business value, savings, ROI, or intervention/implementation readiness.
    """
    coverage_score: float = Field(
        ...,
        description="Coverage points (0.0 to 50.0) based on percentage of evaluated complete cases affected"
    )
    concentration_score: float = Field(
        ...,
        description="Concentration/magnitude points (0.0 to 50.0) based on archetype-specific operational metric"
    )
    raw_score: float = Field(
        ...,
        description="Sum of coverage and concentration scores (0.0 to 100.0)"
    )
    evidence_weight: float = Field(
        ...,
        description="Sample size discount weight: 1.0 (HIGH: >=30 cases), 0.75 (MODERATE: 10-29 cases), 0.40 (LIMITED: <10 cases)"
    )
    final_score: float = Field(
        ...,
        description="Final deterministic operational priority score = round(raw_score * evidence_weight, 2)"
    )


class OpportunityCandidate(BaseModel):
    """
    Typed, evidence-backed candidate improvement or automation opportunity.
    Represents an operational intervention hypothesis anchored in deterministic process findings.
    """
    id: str = Field(
        ...,
        description="Deterministic unique opportunity identifier (e.g. opp_delay_order_verification_inventory_check)"
    )
    title: str = Field(
        ...,
        description="Action-oriented title describing the candidate opportunity"
    )
    archetype: OpportunityArchetype = Field(
        ...,
        description="Operational opportunity archetype"
    )
    intervention_category: InterventionCategory = Field(
        ...,
        description="Candidate intervention approach"
    )
    target_entity: str = Field(
        ...,
        description="Target process entity (e.g. transition 'Order Verification -> Inventory Check' or activity 'Quality Inspection')"
    )
    source_finding_ids: List[str] = Field(
        ...,
        description="Deterministic IDs of supporting Phase 4 ProblemFinding instances providing evidence for this opportunity"
    )
    evidence_strength: EvidenceStrength = Field(
        ...,
        description="Sample size confidence level: HIGH (>=30), MODERATE (10-29), LIMITED (<10)"
    )

    # Quantified Operational Exposure
    affected_case_count: int = Field(
        ...,
        description="Count of complete cases affected by this operational pattern"
    )
    affected_case_percentage: float = Field(
        ...,
        description="Percentage of evaluated complete cases affected"
    )
    occurrence_count: int = Field(
        ...,
        description="Total occurrences or executions across complete cases"
    )
    cumulative_time_seconds: Optional[float] = Field(
        None,
        description="Total elapsed operational time involved in this transition or activity (where applicable)"
    )

    # Archetype-Specific Metrics (separate optional fields)
    duration_share_percentage: Optional[float] = Field(
        None,
        description="Percentage of cumulative complete-case cycle time accounted for by this transition"
    )
    recurrence_case_percentage: Optional[float] = Field(
        None,
        description="Percentage of complete cases exhibiting distinct-timestamp repetition of this activity"
    )
    outlier_case_percentage: Optional[float] = Field(
        None,
        description="Percentage of complete cases identified as cycle-time outliers"
    )
    variant_case_percentage: Optional[float] = Field(
        None,
        description="Percentage of complete cases traversing rare or unstandardized process variants"
    )

    # Distinction of Evidence Elements
    observed_facts: List[str] = Field(
        default_factory=list,
        description="Measured deterministic facts directly observed in operational event data"
    )
    investigation_hypotheses: List[str] = Field(
        default_factory=list,
        description="Targeted operational questions to investigate with process owners before committing changes"
    )
    candidate_actions: List[str] = Field(
        default_factory=list,
        description="Candidate improvement, standardization, or automation levers to evaluate"
    )
    candidate_interventions: List[str] = Field(
        default_factory=list,
        description="Synonym for candidate_actions provided for API consumer clarity"
    )
    rationale: str = Field(
        ...,
        description="Evidence-backed justification explaining why this candidate opportunity was formulated"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Explicit boundaries and disclaimers regarding data visibility, active work vs waiting, and automation suitability"
    )

    # Deterministic Operational Priority
    operational_priority_score: float = Field(
        ...,
        description="Deterministic score (0.0 to 100.0) ranking measured operational patterns for investigation. It does NOT establish avoidability, business value, savings, ROI, or intervention readiness."
    )
    priority_tier: PriorityTier = Field(
        ...,
        description="Categorical priority tier ranking operational patterns for investigation: TIER_1_HIGH, TIER_2_MEDIUM, TIER_3_LOW, TIER_4_EXPLORATORY. Always TIER_4_EXPLORATORY when evidence_strength is LIMITED"
    )
    score_breakdown: ScoreBreakdown = Field(
        ...,
        description="Transparent breakdown of coverage, concentration, and evidence weighting"
    )


class OpportunitySummary(BaseModel):
    """
    Summary metrics for detected opportunity candidates.
    """
    evaluated_cases_count: int = Field(
        ...,
        description="Total complete cases evaluated"
    )
    total_opportunities_count: int = Field(
        ...,
        description="Total opportunity candidates identified"
    )
    tier_1_count: int = Field(
        0,
        description="Count of Tier 1 (High operational priority) opportunities"
    )
    tier_2_count: int = Field(
        0,
        description="Count of Tier 2 (Medium operational priority) opportunities"
    )
    tier_3_count: int = Field(
        0,
        description="Count of Tier 3 (Low operational priority) opportunities"
    )
    tier_4_count: int = Field(
        0,
        description="Count of Tier 4 (Exploratory / Limited evidence) opportunities"
    )
    reconciliation_passed: bool = Field(
        ...,
        description="True if transition interval accounting reconciled with cumulative cycle time"
    )


class OpportunityDetectionResult(BaseModel):
    """
    Focused response schema for Opportunity Detection (Phase 5).
    """
    filename: str = Field(
        ...,
        description="Filename of analyzed dataset"
    )
    summary: OpportunitySummary = Field(
        ...,
        description="Summary of detected opportunities and tier counts"
    )
    opportunities: List[OpportunityCandidate] = Field(
        default_factory=list,
        description="Deterministically ranked opportunity candidates"
    )
