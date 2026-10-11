"""
Pydantic schemas for Phase 7 Business Impact & Financial Economics Analysis.
Defines typed models for annualization policies, labor capacity valuation,
financial return metrics, and strategic synthesis decisions.
"""

from enum import Enum
from typing import Any, Dict, List, Optional
import math
from pydantic import BaseModel, ConfigDict, Field, ValidationInfo, field_validator
from app.schemas.opportunity import OpportunityArchetype, PriorityTier
from app.schemas.readiness import OverallReadinessTier


class MetricProvenance(str, Enum):
    MEASURED_IN_LOG = "MEASURED_IN_LOG"
    USER_PROVIDED = "USER_PROVIDED"
    CALCULATED_ESTIMATE = "CALCULATED_ESTIMATE"
    HISTORICAL_OR_EXTERNAL = "HISTORICAL_OR_EXTERNAL"


class TimeBasis(str, Enum):
    SAMPLE_WINDOW = "SAMPLE_WINDOW"
    ANNUAL = "ANNUAL"
    UNKNOWN = "UNKNOWN"


class AnnualisationMethod(str, Enum):
    NONE = "NONE"
    CALENDAR_EXTRAPOLATION = "CALENDAR_EXTRAPOLATION"
    EXPLICIT_OVERRIDE = "EXPLICIT_OVERRIDE"


class EconomicTier(str, Enum):
    COMPELLING_RETURN = "COMPELLING_RETURN"
    MODERATE_RETURN = "MODERATE_RETURN"
    MARGINAL_OR_UNECONOMICAL = "MARGINAL_OR_UNECONOMICAL"
    INSUFFICIENT_ECONOMIC_INPUTS = "INSUFFICIENT_ECONOMIC_INPUTS"


class StrategicDecisionOutcome(str, Enum):
    SPECIFY_AUTOMATION_SOLUTION = "SPECIFY_AUTOMATION_SOLUTION"
    PROCEED_WITH_GUARDRAILS = "PROCEED_WITH_GUARDRAILS"
    VALIDATE_BUSINESS_CASE_AND_SPECIFY = "VALIDATE_BUSINESS_CASE_AND_SPECIFY"
    RESTRUCTURE_BEFORE_AUTOMATION = "RESTRUCTURE_BEFORE_AUTOMATION"
    STANDARDIZE_AND_COLLECT_DATA = "STANDARDIZE_AND_COLLECT_DATA"
    LOW_CAPITAL_STANDARDIZATION = "LOW_CAPITAL_STANDARDIZATION"
    REVISE_SCOPE_OR_RENEGOTIATE = "REVISE_SCOPE_OR_RENEGOTIATE"
    PILOT_AND_MEASURE = "PILOT_AND_MEASURE"
    INVESTIGATE_FEASIBILITY = "INVESTIGATE_FEASIBILITY"
    RESOLVE_DATA_INSTRUMENTATION = "RESOLVE_DATA_INSTRUMENTATION"
    BLOCKED_HIGH_POTENTIAL = "BLOCKED_HIGH_POTENTIAL"
    BLOCKED_LOW_PRIORITY = "BLOCKED_LOW_PRIORITY"
    BLOCKED_UNKNOWN_ECONOMICS = "BLOCKED_UNKNOWN_ECONOMICS"
    BLOCKED_AND_UNECONOMICAL = "BLOCKED_AND_UNECONOMICAL"
    DEFER_OR_ARCHIVE = "DEFER_OR_ARCHIVE"


class OpportunityEconomicInput(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

    opportunity_id: str
    hourly_labor_rate: Optional[float] = Field(default=None, ge=0.0)
    active_labor_share_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    touch_labor_minutes_per_occurrence: Optional[float] = Field(default=None, ge=0.0)
    addressable_efficiency_percentage: Optional[float] = Field(default=None, ge=0.0, le=100.0)
    implementation_cost: Optional[float] = Field(default=None, ge=0.0)
    annual_recurring_cost: Optional[float] = Field(default=None, ge=0.0)
    annual_case_volume_override: Optional[int] = Field(default=None, gt=0)

    @field_validator(
        "hourly_labor_rate",
        "active_labor_share_percentage",
        "touch_labor_minutes_per_occurrence",
        "addressable_efficiency_percentage",
        "implementation_cost",
        "annual_recurring_cost",
        mode="before",
    )
    @classmethod
    def validate_finite_numeric(cls, v: Any, info: ValidationInfo) -> Any:
        if v is None:
            return None
        if isinstance(v, (int, float)):
            if not math.isfinite(v):
                raise ValueError(
                    f"{info.field_name} must be a finite number; NaN and Infinity are prohibited"
                )
        return v

    @field_validator("annual_case_volume_override", mode="before")
    @classmethod
    def validate_volume_override(cls, v: Any) -> Any:
        if v is None:
            return None
        if isinstance(v, float) and not math.isfinite(v):
            raise ValueError(
                "annual_case_volume_override must be a finite integer; NaN and Infinity are prohibited"
            )
        if not isinstance(v, int) or isinstance(v, bool) or v <= 0:
            raise ValueError(
                "annual_case_volume_override must be a strictly positive integer (> 0)"
            )
        return v


class ObservationWindowInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    earliest_timestamp: Optional[str] = None
    latest_timestamp: Optional[str] = None
    observation_duration_seconds: Optional[float] = None
    observation_duration_days: Optional[float] = None
    time_basis: TimeBasis
    annualisation_method: AnnualisationMethod
    annualisation_ratio: Optional[float] = None
    sample_completed_cases: int
    evaluated_case_volume_raw: Optional[float] = None
    evaluated_case_volume: Optional[int] = None
    volume_provenance: MetricProvenance
    caveats: List[str] = Field(default_factory=list)


class LaborEffortMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Sample-basis observed metrics
    sample_affected_cases: int
    sample_occurrences: Optional[int] = None
    sample_distinct_rare_variants: Optional[int] = None
    sample_active_labor_hours: Optional[float] = None
    sample_addressable_labor_hours: Optional[float] = None

    # Annualized estimated metrics (populated strictly when time_basis == ANNUAL)
    annual_affected_cases_raw: Optional[float] = None
    annual_affected_cases: Optional[int] = None
    annual_occurrences_raw: Optional[float] = None
    annual_occurrences: Optional[int] = None
    annual_active_labor_hours: Optional[float] = None
    annual_addressable_labor_hours: Optional[float] = None

    # Domain intake parameters and provenance
    affected_cases_provenance: MetricProvenance
    active_labor_share_percentage: Optional[float] = None
    touch_labor_minutes_per_occurrence: Optional[float] = None
    addressable_efficiency_percentage: Optional[float] = None
    labor_metrics_provenance: MetricProvenance
    caveats: List[str] = Field(default_factory=list)


class CapacityValuationMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hourly_labor_rate: Optional[float] = None
    hourly_labor_rate_provenance: MetricProvenance

    # Sample-basis valuation (observed in window)
    sample_gross_capacity_value: Optional[float] = None

    # Annualized metrics (populated strictly when time_basis == ANNUAL)
    gross_annual_capacity_value: Optional[float] = None
    annual_recurring_cost: Optional[float] = None
    annual_recurring_cost_provenance: MetricProvenance
    net_annual_capacity_benefit: Optional[float] = None
    implementation_cost: Optional[float] = None
    implementation_cost_provenance: MetricProvenance
    payback_period_months: Optional[float] = None
    three_year_capacity_roi_percentage: Optional[float] = None
    three_year_net_capacity_value: Optional[float] = None

    economic_tier: EconomicTier
    caveats: List[str] = Field(default_factory=list)


class CashFlowMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    cash_roi_available: bool = False
    cash_payback_months: Optional[float] = None
    cash_net_present_value: Optional[float] = None
    caveats: List[str] = Field(
        default_factory=lambda: [
            "Cash-flow ROI and budget reduction require verified headcount, payroll, or external cost evidence. "
            "Capacity values represent theoretical reallocation capacity."
        ]
    )


class StrategicSynthesis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operational_priority: PriorityTier
    overall_readiness: OverallReadinessTier
    economic_tier: EconomicTier
    strategic_decision: StrategicDecisionOutcome
    decision_rationale: str
    decision_provenance: MetricProvenance = MetricProvenance.CALCULATED_ESTIMATE


class OpportunityEconomicsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str
    archetype: OpportunityArchetype
    observation_window: ObservationWindowInfo
    labor_effort: LaborEffortMetrics
    capacity_valuation: CapacityValuationMetrics
    cash_flow: CashFlowMetrics
    synthesis: StrategicSynthesis


class EconomicsSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    total_opportunities_evaluated: int
    evaluated_volume: Optional[int] = None
    total_sample_addressable_hours: Optional[float] = None
    total_annual_addressable_hours: Optional[float] = None
    total_gross_capacity_value: Optional[float] = None
    total_net_capacity_benefit: Optional[float] = None
    archetype_distribution: Dict[str, int] = Field(default_factory=dict)
    economic_tier_distribution: Dict[str, int] = Field(default_factory=dict)
    strategic_decision_distribution: Dict[str, int] = Field(default_factory=dict)


class EconomicsEvaluationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    filename: str
    summary: EconomicsSummary
    opportunities: List[OpportunityEconomicsResult] = Field(default_factory=list)
