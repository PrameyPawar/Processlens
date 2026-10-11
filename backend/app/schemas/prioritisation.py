"""
Pydantic schemas for Phase 8 Opportunity Prioritisation & Portfolio Action Roadmap.
Defines typed models for portfolio cohorts, factor breakdowns, custom weights,
ranking results, and summary responses.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
import math
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator

from app.schemas.opportunity import OpportunityArchetype
from app.schemas.economics import (
    MetricProvenance,
    OpportunityEconomicsResult,
)


class PortfolioCohort(str, Enum):
    FOUNDATIONAL_DATA_QUALITY = "FOUNDATIONAL_DATA_QUALITY"
    IMMEDIATE_AUTOMATION_SPECIFICATION = "IMMEDIATE_AUTOMATION_SPECIFICATION"
    GUARDRAILED_AUTOMATION = "GUARDRAILED_AUTOMATION"
    PROCESS_RESTRUCTURING = "PROCESS_RESTRUCTURING"
    BUSINESS_CASE_VALIDATION = "BUSINESS_CASE_VALIDATION"
    FEASIBILITY_INVESTIGATION = "FEASIBILITY_INVESTIGATION"
    REVISE_OR_DEFERRED = "REVISE_OR_DEFERRED"
    BLOCKED_BY_BARRIERS = "BLOCKED_BY_BARRIERS"

    @property
    def precedence_index(self) -> int:
        """
        Deterministic numerical precedence (1 to 8).
        Lower number indicates higher roadmap precedence.
        """
        mapping = {
            PortfolioCohort.FOUNDATIONAL_DATA_QUALITY: 1,
            PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION: 2,
            PortfolioCohort.GUARDRAILED_AUTOMATION: 3,
            PortfolioCohort.PROCESS_RESTRUCTURING: 4,
            PortfolioCohort.BUSINESS_CASE_VALIDATION: 5,
            PortfolioCohort.FEASIBILITY_INVESTIGATION: 6,
            PortfolioCohort.REVISE_OR_DEFERRED: 7,
            PortfolioCohort.BLOCKED_BY_BARRIERS: 8,
        }
        return mapping[self]


class ImpactBasis(str, Enum):
    CALCULATED_CAPACITY_SCENARIO = "CALCULATED_CAPACITY_SCENARIO"
    OPERATIONAL_CONCENTRATION_BASELINE = "OPERATIONAL_CONCENTRATION_BASELINE"


class ScoringStatus(str, Enum):
    SCORED = "SCORED"
    UNSCORED = "UNSCORED"


class ConstraintStatus(str, Enum):
    FACTOR_DEFICIT = "FACTOR_DEFICIT"
    INTER_COHORT_PRECEDENCE = "INTER_COHORT_PRECEDENCE"
    UNSCORED_COMPARISON = "UNSCORED_COMPARISON"
    UNAVAILABLE = "UNAVAILABLE"


class PrioritisationWeights(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    impact_weight: float = Field(default=30.0, ge=0.0)
    readiness_weight: float = Field(default=25.0, ge=0.0)
    payback_weight: float = Field(default=20.0, ge=0.0)
    effort_weight: float = Field(default=10.0, ge=0.0)
    risk_weight: float = Field(default=5.0, ge=0.0)
    confidence_weight: float = Field(default=10.0, ge=0.0)

    @field_validator(
        "impact_weight",
        "readiness_weight",
        "payback_weight",
        "effort_weight",
        "risk_weight",
        "confidence_weight",
        mode="before",
    )
    @classmethod
    def validate_finite_weight(cls, v: Any, info: ValidationInfo) -> Any:
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError(
                    f"{info.field_name} must be a finite number; NaN and Infinity are prohibited"
                )
            if v < 0.0:
                raise ValueError(f"{info.field_name} must be non-negative (>= 0.0)")
        return v

    @classmethod
    def validate_sum_contract(cls, values: "PrioritisationWeights") -> None:
        """
        Validates the exact sum-to-100 contract with tolerance epsilon = 0.01.
        """
        total = (
            values.impact_weight
            + values.readiness_weight
            + values.payback_weight
            + values.effort_weight
            + values.risk_weight
            + values.confidence_weight
        )
        if abs(total - 100.0) > 0.01:
            raise ValueError(
                f"Prioritisation weights must sum to 100.0 (received sum: {total:.4f})."
            )


class FactorBreakdown(BaseModel):
    model_config = ConfigDict(extra="forbid")

    impact_score: Optional[float] = None
    impact_basis: ImpactBasis
    impact_provenance: MetricProvenance
    readiness_score: Optional[float] = None
    payback_score: Optional[float] = None
    effort_score: Optional[float] = None
    risk_score: Optional[float] = None
    confidence_score: float
    effective_weights: Dict[str, float] = Field(default_factory=dict)
    factor_caveats: List[str] = Field(default_factory=list)


class PrioritisedOpportunity(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rank_order: int
    opportunity_id: str
    archetype: OpportunityArchetype
    portfolio_cohort: PortfolioCohort
    scoring_status: ScoringStatus
    composite_priority_score_raw: Optional[float] = None
    composite_priority_score: Optional[float] = None
    score_bucket: Optional[float] = None
    factors: FactorBreakdown
    economics: OpportunityEconomicsResult
    operational_priority_score: float
    primary_strength: str
    primary_constraint: Optional[str] = None
    constraint_status: Optional[ConstraintStatus] = None


class PrioritisationSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_opportunities_prioritised: int
    cohort_distribution: Dict[str, int] = Field(default_factory=dict)
    top_opportunity_id: Optional[str] = None
    top_three_opportunity_ids: List[str] = Field(default_factory=list)
    top_three_cumulative_capacity_scenario: Optional[float] = None
    capacity_scenario_caveats: List[str] = Field(
        default_factory=lambda: [
            "Non-additive scenario estimate. Summing capacity across multiple opportunities "
            "may involve overlapping case traces or interdependent transition delays. "
            "Cross-opportunity interaction and portfolio non-overlap are not modeled in MVP."
        ]
    )


class PrioritisationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    summary: PrioritisationSummary
    ranked_opportunities: List[PrioritisedOpportunity] = Field(default_factory=list)
