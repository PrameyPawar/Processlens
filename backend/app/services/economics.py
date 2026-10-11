"""
Deterministic domain service for Phase 7 Business Impact & Financial Economics Analysis.
Implements observation window resolution, archetype-specific labor capacity scaling,
unrounded financial metrics derivation, economic tier classification, and strategic synthesis.
"""

import json
import math
from typing import List, Dict, Any, Optional, Tuple
from pydantic import ValidationError

from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.detection import ProblemFinding
from app.schemas.opportunity import (
    OpportunityCandidate,
    OpportunityArchetype,
    PriorityTier,
    OpportunityDetectionResult,
)
from app.schemas.readiness import (
    OverallReadinessTier,
    ReadinessAssessmentResponse,
)
from app.schemas.economics import (
    MetricProvenance,
    TimeBasis,
    AnnualisationMethod,
    EconomicTier,
    StrategicDecisionOutcome,
    OpportunityEconomicInput,
    ObservationWindowInfo,
    LaborEffortMetrics,
    CapacityValuationMetrics,
    CashFlowMetrics,
    StrategicSynthesis,
    OpportunityEconomicsResult,
    EconomicsSummary,
    EconomicsEvaluationResponse,
)


def round_half_up(val: float) -> int:
    """
    Commercial half-up integer rounding policy for presentation fields.
    0.4 -> 0, 0.5 -> 1, 2.49 -> 2, 2.50 -> 3, 2.51 -> 3.
    """
    return int(math.floor(val + 0.5))


def parse_economic_inputs_json(
    raw_json: Optional[str],
) -> Optional[List[OpportunityEconomicInput]]:
    """
    Parses and validates a JSON string representing a list of OpportunityEconomicInput objects.
    Raises ValueError with descriptive feedback on JSON syntax or schema invalidity.
    """
    if raw_json is None:
        return None
    stripped = raw_json.strip()
    if not stripped:
        return None

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in economic_inputs: {str(e)}")

    if not isinstance(data, list):
        raise ValueError("economic_inputs must be a JSON array of economic input objects.")

    parsed_inputs: List[OpportunityEconomicInput] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} in economic_inputs must be a JSON object.")
        try:
            parsed_inputs.append(OpportunityEconomicInput.model_validate(item))
        except ValidationError as e:
            raise ValueError(f"Validation error in economic_inputs at index {idx}: {str(e)}")

    return parsed_inputs


def extract_observation_window(
    reconstruction: ProcessReconstructionResult,
    volume_override: Optional[int] = None,
) -> ObservationWindowInfo:
    """
    Deterministically resolves the observation window and annualization parameters
    following strict 5-branch precedence:
      Branch 5: Degenerate / Empty Sample (N_sample == 0 -> suppresses extrapolation).
      Branch 3: Explicit Annual-Volume Override (N_sample >= 1 and V_override > 0).
      Branch 4: Missing Window (timestamps missing/unparseable).
      Branch 5: Degenerate Window (Delta T <= 0.0s).
      Branch 1: Short Window (Delta T < 30.0 days -> sample basis).
      Branch 2: Calendar Extrapolation (Delta T >= 30.0 days).
    """
    complete_cases = [c for c in reconstruction.cases if c.is_complete]
    n_sample = len(complete_cases)

    # Branch 5: Root Gate - Zero complete cases
    if n_sample == 0:
        return ObservationWindowInfo(
            earliest_timestamp=None,
            latest_timestamp=None,
            observation_duration_seconds=None,
            observation_duration_days=None,
            time_basis=TimeBasis.UNKNOWN,
            annualisation_method=AnnualisationMethod.NONE,
            annualisation_ratio=None,
            sample_completed_cases=0,
            evaluated_case_volume_raw=None,
            evaluated_case_volume=None,
            volume_provenance=MetricProvenance.CALCULATED_ESTIMATE,
            caveats=[
                "Zero complete cases reconstructed from event data. "
                "Annualized operational projections and financial evaluations are suppressed."
            ],
        )

    # Extract timestamps strictly from events of complete cases
    complete_case_timestamps = []
    for c in complete_cases:
        for e in c.events:
            if hasattr(e, "timestamp_parsed") and e.timestamp_parsed is not None:
                complete_case_timestamps.append(e.timestamp_parsed)

    earliest_dt = min(complete_case_timestamps) if complete_case_timestamps else None
    latest_dt = max(complete_case_timestamps) if complete_case_timestamps else None

    duration_sec: Optional[float] = None
    duration_days: Optional[float] = None
    if earliest_dt and latest_dt:
        duration_sec = (latest_dt - earliest_dt).total_seconds()
        duration_days = duration_sec / 86400.0

    earliest_str = earliest_dt.isoformat() if earliest_dt else None
    latest_str = latest_dt.isoformat() if latest_dt else None

    # Branch 3: Explicit Annual-Volume Override (Precedence over missing/zero/short windows when N >= 1)
    if volume_override is not None and volume_override > 0:
        r_raw = float(volume_override) / float(n_sample)
        caveats = [
            f"Annualization evaluated using explicit user-provided volume override ({volume_override} cases/year). "
            "Observation window timestamps are not used for case volume extrapolation."
        ]
        if duration_sec is None:
            caveats.append("Complete-case timestamps are unavailable in source log.")
        elif duration_sec <= 0.0:
            caveats.append("Complete-case timestamps exhibit zero elapsed calendar duration.")
        elif duration_days is not None and duration_days < 30.0:
            caveats.append(f"Complete-case timestamps span {duration_days:.1f} days (<30 days).")

        return ObservationWindowInfo(
            earliest_timestamp=earliest_str,
            latest_timestamp=latest_str,
            observation_duration_seconds=duration_sec,
            observation_duration_days=duration_days,
            time_basis=TimeBasis.ANNUAL,
            annualisation_method=AnnualisationMethod.EXPLICIT_OVERRIDE,
            annualisation_ratio=r_raw,
            sample_completed_cases=n_sample,
            evaluated_case_volume_raw=float(volume_override),
            evaluated_case_volume=volume_override,
            volume_provenance=MetricProvenance.USER_PROVIDED,
            caveats=caveats,
        )

    # Branch 4: Missing Window (no override and timestamps missing)
    if duration_sec is None or earliest_dt is None or latest_dt is None:
        return ObservationWindowInfo(
            earliest_timestamp=None,
            latest_timestamp=None,
            observation_duration_seconds=None,
            observation_duration_days=None,
            time_basis=TimeBasis.UNKNOWN,
            annualisation_method=AnnualisationMethod.NONE,
            annualisation_ratio=None,
            sample_completed_cases=n_sample,
            evaluated_case_volume_raw=None,
            evaluated_case_volume=None,
            volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            caveats=[
                "Observation window timestamps are missing or unparseable. "
                "Annualized operational projections and financial evaluations are suppressed."
            ],
        )

    # Branch 5: Degenerate Zero-Duration Window (no override and Delta T <= 0.0s)
    if duration_sec <= 0.0:
        return ObservationWindowInfo(
            earliest_timestamp=earliest_str,
            latest_timestamp=latest_str,
            observation_duration_seconds=duration_sec,
            observation_duration_days=duration_days,
            time_basis=TimeBasis.UNKNOWN,
            annualisation_method=AnnualisationMethod.NONE,
            annualisation_ratio=None,
            sample_completed_cases=n_sample,
            evaluated_case_volume_raw=None,
            evaluated_case_volume=None,
            volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            caveats=[
                "Observation window exhibits zero elapsed calendar duration (Delta T <= 0.0s). "
                "Calendar extrapolation is mathematically undefined; annual projections are suppressed."
            ],
        )

    # Branch 1: Short Observation Window (< 30.0 days without override)
    if duration_days is not None and duration_days < 30.0:
        return ObservationWindowInfo(
            earliest_timestamp=earliest_str,
            latest_timestamp=latest_str,
            observation_duration_seconds=duration_sec,
            observation_duration_days=duration_days,
            time_basis=TimeBasis.SAMPLE_WINDOW,
            annualisation_method=AnnualisationMethod.NONE,
            annualisation_ratio=None,
            sample_completed_cases=n_sample,
            evaluated_case_volume_raw=float(n_sample),
            evaluated_case_volume=n_sample,
            volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            caveats=[
                f"Observation window duration ({duration_days:.1f} days) is shorter than 30 days. "
                "Automatic annual calendar extrapolation is suppressed; metrics represent sample window observations only."
            ],
        )

    # Branch 2: Standard Calendar Extrapolation (>= 30.0 days without override)
    r_raw = (365.25 * 86400.0) / duration_sec
    evaluated_raw = float(n_sample) * r_raw
    evaluated_display = round_half_up(evaluated_raw)

    return ObservationWindowInfo(
        earliest_timestamp=earliest_str,
        latest_timestamp=latest_str,
        observation_duration_seconds=duration_sec,
        observation_duration_days=duration_days,
        time_basis=TimeBasis.ANNUAL,
        annualisation_method=AnnualisationMethod.CALENDAR_EXTRAPOLATION,
        annualisation_ratio=r_raw,
        sample_completed_cases=n_sample,
        evaluated_case_volume_raw=evaluated_raw,
        evaluated_case_volume=evaluated_display,
        volume_provenance=MetricProvenance.CALCULATED_ESTIMATE,
        caveats=[
            f"Annual projection derived via linear calendar extrapolation over {duration_days:.1f} days "
            f"(scaling factor: {r_raw:.4f}). Assumes sample arrival rate represents operational run-rate without seasonal adjustment."
        ],
    )


def classify_economic_tier(
    net_benefit: Optional[float],
    implementation_cost: Optional[float],
    payback_months: Optional[float],
    three_year_roi: Optional[float],
    tolerance: float = 1e-3,
) -> EconomicTier:
    """
    Deterministic classification of economic attractiveness following strict precedence:
      Step 1: Upfront validation of all inputs before early returns.
      Step 2: Mathematical consistency check against numeric tolerance.
      Step 3: Threshold-based tier assignment.
    """
    # -------------------------------------------------------------------------
    # STEP 1: Upfront Validation of All Inputs (No Early Returns)
    # -------------------------------------------------------------------------
    # Check net_benefit
    if net_benefit is None or not math.isfinite(net_benefit):
        return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # Check implementation_cost
    if implementation_cost is None or not math.isfinite(implementation_cost):
        return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
    if implementation_cost < 0.0:
        return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS  # Negative cost is invalid

    # Check payback_months
    if payback_months is not None:
        if not math.isfinite(payback_months) or payback_months < 0.0:
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # Check three_year_roi
    if three_year_roi is not None:
        if not math.isfinite(three_year_roi):
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # -------------------------------------------------------------------------
    # STEP 2: Mathematical Consistency & Contradiction Checks
    # -------------------------------------------------------------------------
    # Case A: Positive Net Benefit and Positive Cost (B_net > 0, C_impl > 0)
    if net_benefit > 0.0 and implementation_cost > 0.0:
        expected_payback = (implementation_cost / net_benefit) * 12.0
        if payback_months is None:
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
        if abs(payback_months - expected_payback) > tolerance:
            # Contradictory finite payback supplied
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

        if three_year_roi is not None:
            expected_roi = (((3.0 * net_benefit) - implementation_cost) / implementation_cost) * 100.0
            if abs(three_year_roi - expected_roi) > tolerance:
                # Contradictory finite ROI supplied
                return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # Case B: Positive Net Benefit and Zero Cost (B_net > 0, C_impl == 0)
    elif net_benefit > 0.0 and implementation_cost == 0.0:
        if payback_months is not None and abs(payback_months - 0.0) > tolerance:
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
        if three_year_roi is not None:
            # ROI is undefined for zero implementation cost (division by zero avoided)
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # Case C: Nonpositive Net Benefit (B_net <= 0)
    elif net_benefit <= 0.0:
        if payback_months is not None:
            return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
        if implementation_cost > 0.0 and three_year_roi is not None:
            expected_roi = (((3.0 * net_benefit) - implementation_cost) / implementation_cost) * 100.0
            if abs(three_year_roi - expected_roi) > tolerance:
                return EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # -------------------------------------------------------------------------
    # STEP 3: Deterministic Tier Assignment
    # -------------------------------------------------------------------------
    if net_benefit <= 0.0:
        return EconomicTier.MARGINAL_OR_UNECONOMICAL

    if implementation_cost == 0.0:
        return EconomicTier.COMPELLING_RETURN

    # Here: net_benefit > 0, implementation_cost > 0, payback_months is validated float
    if payback_months is not None:
        if payback_months <= 12.0:
            return EconomicTier.COMPELLING_RETURN
        if payback_months <= 36.0:
            return EconomicTier.MODERATE_RETURN

    return EconomicTier.MARGINAL_OR_UNECONOMICAL


def verify_internal_derivation_consistency(
    gross_benefit: Optional[float],
    recurring_cost: Optional[float],
    net_benefit: Optional[float],
    impl_cost: Optional[float],
    payback_months: Optional[float],
    three_year_roi: Optional[float],
    tolerance: float = 1e-3,
) -> bool:
    """
    Service-level mathematical consistency verification utility.
    """
    if None in (gross_benefit, recurring_cost, net_benefit):
        return False
    if abs(gross_benefit - recurring_cost - net_benefit) > tolerance:
        return False
    if net_benefit > 0.0 and impl_cost is not None and impl_cost > 0.0:
        expected_payback = (impl_cost / net_benefit) * 12.0
        if payback_months is None or abs(payback_months - expected_payback) > tolerance:
            return False
        if three_year_roi is not None:
            expected_roi = (((3.0 * net_benefit) - impl_cost) / impl_cost) * 100.0
            if abs(three_year_roi - expected_roi) > tolerance:
                return False
    return True


def calculate_labor_capacity_metrics(
    opportunity: OpportunityCandidate,
    window_info: ObservationWindowInfo,
    economic_input: Optional[OpportunityEconomicInput],
) -> Tuple[LaborEffortMetrics, CapacityValuationMetrics]:
    """
    Deterministically computes sample-basis observed metrics, unrounded annualized
    extrapolations (if time_basis is ANNUAL), and capacity valuation figures.
    """
    archetype = opportunity.archetype
    labor_caveats: List[str] = []
    valuation_caveats: List[str] = []

    # 1. Sample-Basis Active Labor Calculation
    sample_active_hours: Optional[float] = None
    alpha = economic_input.active_labor_share_percentage if economic_input else None
    m_occ = economic_input.touch_labor_minutes_per_occurrence if economic_input else None

    if archetype == OpportunityArchetype.DELAY_COMPRESSION:
        cum_sec = opportunity.cumulative_time_seconds
        if cum_sec is not None and alpha is not None:
            # Active labor derived from aggregate sample duration
            sample_active_hours = (cum_sec / 3600.0) * (alpha / 100.0)
            labor_caveats.append(
                f"Sample active labor derived from {cum_sec:.1f}s aggregate elapsed transition duration "
                f"using {alpha:.1f}% active-labor share assumption. Represents assumption-based capacity scenario."
            )
        else:
            labor_caveats.append(
                "Active labor share percentage (alpha) is missing; sample active labor hours are unavailable."
            )

    elif archetype == OpportunityArchetype.RECURRENCE_REDUCTION:
        occ_count = opportunity.occurrence_count
        if occ_count is not None and m_occ is not None:
            sample_active_hours = float(occ_count) * (m_occ / 60.0)
            labor_caveats.append(
                f"Sample active labor derived from {occ_count} re-execution occurrences "
                f"using {m_occ:.1f} minutes touch time per occurrence."
            )
        else:
            labor_caveats.append(
                "Touch labor minutes per occurrence is missing; sample active labor hours are unavailable."
            )

    elif archetype == OpportunityArchetype.PATH_STANDARDIZATION:
        rare_cases = opportunity.affected_case_count
        if rare_cases is not None and m_occ is not None:
            sample_active_hours = float(rare_cases) * (m_occ / 60.0)
            labor_caveats.append(
                f"Sample active labor derived from {rare_cases} cases executing rare variants "
                f"using {m_occ:.1f} minutes touch time per non-standard case. "
                f"Distinct rare variant count ({opportunity.occurrence_count}) is a structural graph property and remains unscaled."
            )
        else:
            labor_caveats.append(
                "Touch labor minutes per occurrence is missing; sample active labor hours are unavailable."
            )

    elif archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION:
        outlier_cases = opportunity.affected_case_count
        if outlier_cases is not None and m_occ is not None:
            sample_active_hours = float(outlier_cases) * (m_occ / 60.0)
            labor_caveats.append(
                f"Sample active labor derived from {outlier_cases} cycle-time outlier cases "
                f"using {m_occ:.1f} minutes touch time per outlier case."
            )
        else:
            labor_caveats.append(
                "Touch labor minutes per occurrence is missing; sample active labor hours are unavailable."
            )

    elif archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        sample_active_hours = None
        labor_caveats.append(
            "Data instrumentation is a data quality and tracking opportunity; labor hours are not defined."
        )

    # 2. Sample Addressable Hours & Sample Gross Valuation
    eta = economic_input.addressable_efficiency_percentage if economic_input else None
    sample_addressable_hours: Optional[float] = None
    if sample_active_hours is not None and eta is not None:
        sample_addressable_hours = sample_active_hours * (eta / 100.0)
    elif sample_active_hours is not None:
        labor_caveats.append(
            "Addressable efficiency percentage is missing; addressable labor hours are unavailable."
        )

    r_labor = economic_input.hourly_labor_rate if economic_input else None
    sample_gross_capacity_value: Optional[float] = None
    if sample_addressable_hours is not None and r_labor is not None:
        sample_gross_capacity_value = sample_addressable_hours * r_labor

    # 3. Annualized Extrapolations (Strictly when time_basis == ANNUAL)
    is_annual = window_info.time_basis == TimeBasis.ANNUAL and window_info.annualisation_ratio is not None
    r_raw = window_info.annualisation_ratio if is_annual else None

    annual_affected_cases_raw: Optional[float] = None
    annual_affected_cases: Optional[int] = None
    annual_occurrences_raw: Optional[float] = None
    annual_occurrences: Optional[int] = None
    annual_active_hours: Optional[float] = None
    annual_addressable_hours: Optional[float] = None
    gross_annual_capacity_value: Optional[float] = None

    if is_annual and r_raw is not None:
        annual_affected_cases_raw = float(opportunity.affected_case_count) * r_raw
        annual_affected_cases = round_half_up(annual_affected_cases_raw)

        if opportunity.occurrence_count is not None:
            if archetype == OpportunityArchetype.PATH_STANDARDIZATION:
                # Structural variant count is unscaled
                annual_occurrences_raw = float(opportunity.occurrence_count)
                annual_occurrences = opportunity.occurrence_count
            else:
                annual_occurrences_raw = float(opportunity.occurrence_count) * r_raw
                annual_occurrences = round_half_up(annual_occurrences_raw)

        if sample_active_hours is not None:
            annual_active_hours = sample_active_hours * r_raw
        if sample_addressable_hours is not None:
            annual_addressable_hours = sample_addressable_hours * r_raw
        if annual_addressable_hours is not None and r_labor is not None:
            gross_annual_capacity_value = annual_addressable_hours * r_labor
    else:
        if window_info.time_basis == TimeBasis.SAMPLE_WINDOW:
            labor_caveats.append(
                "Sample observation window (<30 days) suppresses annualization; annual estimates are None."
            )
        else:
            labor_caveats.append(
                "Observation window conditions suppress annualization; annual estimates are None."
            )

    # 4. Financial Net Benefit, Payback, ROI, and Tier Classification
    c_recurring = economic_input.annual_recurring_cost if economic_input else None
    c_impl = economic_input.implementation_cost if economic_input else None

    net_annual_capacity_benefit: Optional[float] = None
    payback_months: Optional[float] = None
    three_year_roi: Optional[float] = None
    three_year_net_value: Optional[float] = None

    if is_annual and gross_annual_capacity_value is not None and c_recurring is not None:
        net_annual_capacity_benefit = gross_annual_capacity_value - c_recurring
    elif is_annual and gross_annual_capacity_value is not None:
        valuation_caveats.append(
            "Annual recurring cost is missing (None); net annual capacity benefit is unavailable. "
            "Gross capacity value remains available as a theoretical scenario estimate."
        )

    if is_annual and net_annual_capacity_benefit is not None and c_impl is not None:
        if c_impl == 0.0:
            if net_annual_capacity_benefit > 0.0:
                payback_months = 0.0
                three_year_roi = None  # Division by zero avoided
                three_year_net_value = 3.0 * net_annual_capacity_benefit
            else:
                payback_months = None
                three_year_roi = None
                three_year_net_value = 3.0 * net_annual_capacity_benefit
        else:  # c_impl > 0.0
            if net_annual_capacity_benefit > 0.0:
                payback_months = (c_impl / net_annual_capacity_benefit) * 12.0
                three_year_roi = (((3.0 * net_annual_capacity_benefit) - c_impl) / c_impl) * 100.0
                three_year_net_value = (3.0 * net_annual_capacity_benefit) - c_impl
            else:
                payback_months = None
                three_year_roi = (((3.0 * net_annual_capacity_benefit) - c_impl) / c_impl) * 100.0
                three_year_net_value = (3.0 * net_annual_capacity_benefit) - c_impl
    elif is_annual and net_annual_capacity_benefit is not None:
        valuation_caveats.append(
            "Implementation cost is missing (None); payback period and 3-year ROI are unavailable."
        )

    # Assign Economic Tier
    if archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        economic_tier = EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
        valuation_caveats.append("Data instrumentation does not compute direct labor capacity ROI.")
    elif not is_annual:
        economic_tier = EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
        valuation_caveats.append("Annual financial classification requires an annual time basis.")
    else:
        economic_tier = classify_economic_tier(
            net_annual_capacity_benefit, c_impl, payback_months, three_year_roi
        )

    # Distinct Provenance
    affected_prov = MetricProvenance.MEASURED_IN_LOG
    labor_prov = (
        MetricProvenance.CALCULATED_ESTIMATE
        if sample_active_hours is not None
        else MetricProvenance.MEASURED_IN_LOG
    )
    r_labor_prov = (
        MetricProvenance.USER_PROVIDED if r_labor is not None else MetricProvenance.CALCULATED_ESTIMATE
    )
    c_rec_prov = (
        MetricProvenance.USER_PROVIDED if c_recurring is not None else MetricProvenance.CALCULATED_ESTIMATE
    )
    c_impl_prov = (
        MetricProvenance.USER_PROVIDED if c_impl is not None else MetricProvenance.CALCULATED_ESTIMATE
    )

    labor_metrics = LaborEffortMetrics(
        sample_affected_cases=opportunity.affected_case_count,
        sample_occurrences=opportunity.occurrence_count,
        sample_distinct_rare_variants=(
            opportunity.occurrence_count if archetype == OpportunityArchetype.PATH_STANDARDIZATION else None
        ),
        sample_active_labor_hours=sample_active_hours,
        sample_addressable_labor_hours=sample_addressable_hours,
        annual_affected_cases_raw=annual_affected_cases_raw,
        annual_affected_cases=annual_affected_cases,
        annual_occurrences_raw=annual_occurrences_raw,
        annual_occurrences=annual_occurrences,
        annual_active_labor_hours=annual_active_hours,
        annual_addressable_labor_hours=annual_addressable_hours,
        affected_cases_provenance=affected_prov,
        active_labor_share_percentage=alpha,
        touch_labor_minutes_per_occurrence=m_occ,
        addressable_efficiency_percentage=eta,
        labor_metrics_provenance=labor_prov,
        caveats=labor_caveats,
    )

    valuation_metrics = CapacityValuationMetrics(
        hourly_labor_rate=r_labor,
        hourly_labor_rate_provenance=r_labor_prov,
        sample_gross_capacity_value=sample_gross_capacity_value,
        gross_annual_capacity_value=gross_annual_capacity_value,
        annual_recurring_cost=c_recurring,
        annual_recurring_cost_provenance=c_rec_prov,
        net_annual_capacity_benefit=net_annual_capacity_benefit,
        implementation_cost=c_impl,
        implementation_cost_provenance=c_impl_prov,
        payback_period_months=payback_months,
        three_year_capacity_roi_percentage=three_year_roi,
        three_year_net_capacity_value=three_year_net_value,
        economic_tier=economic_tier,
        caveats=valuation_caveats,
    )

    return labor_metrics, valuation_metrics


def generate_data_instrumentation_rationale(
    source_finding: Optional[ProblemFinding],
    exclusions: Optional[Dict[str, Any]],
) -> str:
    """
    Constructs an evidence-backed rationale for DATA_INSTRUMENTATION from observed symptoms.
    """
    facts = []
    if source_finding and hasattr(source_finding, "metrics"):
        disc_pct = source_finding.metrics.get("discrepancy_percentage")
        disc_sec = source_finding.metrics.get("discrepancy_seconds")
        if disc_pct is not None and disc_sec is not None:
            facts.append(
                f"accounting reconciliation discrepancy of {disc_sec:.2f}s ({disc_pct:.2f}%) "
                "between transition intervals and case spans"
            )

    if exclusions:
        missing_cases = exclusions.get("missing_case_id_count", 0)
        invalid_ts = exclusions.get("missing_or_invalid_timestamp_count", 0)
        if missing_cases > 0:
            facts.append(f"{missing_cases} event rows missing case identifiers")
        if invalid_ts > 0:
            facts.append(f"{invalid_ts} event rows with unparseable timestamps")

    if facts:
        evidence_summary = "; ".join(facts)
        return (
            f"Data instrumentation opportunity identified from observed event log limitations: {evidence_summary}. "
            "Audit event logging, lifecycle tracking, and data pipeline extraction before attempting financial valuation."
        )

    return (
        "Data instrumentation opportunity identified from observed process event log limitations. "
        "Audit data tracking and event capture before attempting financial quantification."
    )


# -----------------------------------------------------------------------------
# Canonical 64-Cell Strategic Synthesis Matrix
# -----------------------------------------------------------------------------
SYNTHESIS_DECISION_MAP: Dict[Tuple[PriorityTier, OverallReadinessTier, EconomicTier], StrategicDecisionOutcome] = {
    # ---------------- TIER_1_HIGH PRIORITY ----------------
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.REVISE_SCOPE_OR_RENEGOTIATE,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.VALIDATE_BUSINESS_CASE_AND_SPECIFY,

    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.RESTRUCTURE_BEFORE_AUTOMATION,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.RESTRUCTURE_BEFORE_AUTOMATION,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.STANDARDIZE_AND_COLLECT_DATA,

    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.BLOCKED_UNKNOWN_ECONOMICS,

    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.PILOT_AND_MEASURE,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PILOT_AND_MEASURE,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_1_HIGH, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.INVESTIGATE_FEASIBILITY,

    # ---------------- TIER_2_MEDIUM PRIORITY ----------------
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.REVISE_SCOPE_OR_RENEGOTIATE,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.VALIDATE_BUSINESS_CASE_AND_SPECIFY,

    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.RESTRUCTURE_BEFORE_AUTOMATION,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.RESTRUCTURE_BEFORE_AUTOMATION,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.STANDARDIZE_AND_COLLECT_DATA,

    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.BLOCKED_UNKNOWN_ECONOMICS,

    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.PILOT_AND_MEASURE,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PILOT_AND_MEASURE,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_2_MEDIUM, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.INVESTIGATE_FEASIBILITY,

    # ---------------- TIER_3_LOW PRIORITY ----------------
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,

    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,

    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,

    (PriorityTier.TIER_3_LOW, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_3_LOW, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,

    # ---------------- TIER_4_EXPLORATORY PRIORITY ----------------
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,

    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PREREQUISITES_REQUIRED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,

    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,

    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.COMPELLING_RETURN): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MODERATE_RETURN): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.MARGINAL_OR_UNECONOMICAL): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    (PriorityTier.TIER_4_EXPLORATORY, OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE, EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS): StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
}


def synthesize_strategic_decision(
    priority: PriorityTier,
    readiness: OverallReadinessTier,
    economic_tier: EconomicTier,
    archetype: OpportunityArchetype,
    source_finding: Optional[ProblemFinding],
    exclusions: Optional[Dict[str, Any]],
) -> StrategicSynthesis:
    """
    Synthesizes operational priority, automation readiness, and financial economics
    into a definitive strategic decision outcome and transparent rationale.
    """
    if archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        decision = StrategicDecisionOutcome.RESOLVE_DATA_INSTRUMENTATION
        rationale = generate_data_instrumentation_rationale(source_finding, exclusions)
        return StrategicSynthesis(
            operational_priority=priority,
            overall_readiness=readiness,
            economic_tier=economic_tier,
            strategic_decision=decision,
            decision_rationale=rationale,
            decision_provenance=MetricProvenance.CALCULATED_ESTIMATE,
        )

    decision = SYNTHESIS_DECISION_MAP.get(
        (priority, readiness, economic_tier),
        StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
    )

    # Contextual decision rationale
    base_rationale = (
        f"Operational priority {priority.value} combined with {readiness.value} automation readiness "
        f"and {economic_tier.value} economics indicates {decision.value}."
    )

    if decision == StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION:
        rationale = (
            f"{base_rationale} Authorizes detailed solution design and requirements specification; "
            "does not authorize production automation deployment or autonomous process execution."
        )
    elif decision == StrategicDecisionOutcome.VALIDATE_BUSINESS_CASE_AND_SPECIFY:
        rationale = (
            f"{base_rationale} Technical characteristics support specification, but recurring costs, "
            "implementation investment, or annualized volume require validation to establish the financial business case."
        )
    elif decision in (
        StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL,
        StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY,
        StrategicDecisionOutcome.BLOCKED_UNKNOWN_ECONOMICS,
        StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL,
    ):
        rationale = (
            f"{base_rationale} Automated execution is prohibited by technical, legal, or governance barriers. "
            "Address fundamental blockers or focus on manual process simplification."
        )
    else:
        rationale = base_rationale

    return StrategicSynthesis(
        operational_priority=priority,
        overall_readiness=readiness,
        economic_tier=economic_tier,
        strategic_decision=decision,
        decision_rationale=rationale,
        decision_provenance=MetricProvenance.CALCULATED_ESTIMATE,
    )


def evaluate_opportunities_economics(
    opportunity_result: OpportunityDetectionResult,
    readiness_result: ReadinessAssessmentResponse,
    reconstruction: ProcessReconstructionResult,
    economic_inputs: Optional[List[OpportunityEconomicInput]],
    filename: str,
) -> EconomicsEvaluationResponse:
    """
    Main orchestration service for Phase 7. Evaluates observation window,
    labor effort, capacity valuation, and strategic synthesis for all candidates.
    """
    # Map readiness results by opportunity_id
    readiness_by_id = {r.opportunity_id: r for r in readiness_result.assessments}

    # Map economic inputs by opportunity_id and validate unknown IDs
    inputs_by_id: Dict[str, OpportunityEconomicInput] = {}
    valid_opportunity_ids = {opp.id for opp in opportunity_result.opportunities}

    volume_override: Optional[int] = None

    if economic_inputs:
        for inp in economic_inputs:
            if inp.opportunity_id not in valid_opportunity_ids:
                raise ValueError(
                    f"Unknown opportunity_id '{inp.opportunity_id}' in economic_inputs. "
                    f"Valid opportunities: {sorted(list(valid_opportunity_ids))}"
                )
            if inp.opportunity_id in inputs_by_id:
                raise ValueError(
                    f"Duplicate economic input for opportunity_id '{inp.opportunity_id}'. "
                    "Each opportunity candidate may only have one economic input per request."
                )
            inputs_by_id[inp.opportunity_id] = inp
            if inp.annual_case_volume_override is not None and volume_override is None:
                volume_override = inp.annual_case_volume_override

    # Extract observation window
    window_info = extract_observation_window(reconstruction, volume_override=volume_override)

    # Exclusions dictionary for DATA_INSTRUMENTATION
    exclusions_dict: Dict[str, Any] = {}
    if hasattr(reconstruction, "exclusions"):
        exclusions = reconstruction.exclusions
        exclusions_dict["missing_case_id_count"] = getattr(exclusions, "missing_case_id_count", 0)
        exclusions_dict["missing_or_invalid_timestamp_count"] = getattr(
            exclusions, "missing_or_invalid_timestamp_count", 0
        )

    # Evaluate each opportunity candidate
    evaluated_opportunities: List[OpportunityEconomicsResult] = []

    archetype_counts: Dict[str, int] = {}
    economic_tier_counts: Dict[str, int] = {}
    strategic_decision_counts: Dict[str, int] = {}

    total_sample_addr_hours: float = 0.0
    has_sample_addr_hours = False

    total_annual_addr_hours: float = 0.0
    has_annual_addr_hours = False

    total_gross_val: float = 0.0
    has_gross_val = False

    total_net_benefit: float = 0.0
    has_net_benefit = False

    for opp in opportunity_result.opportunities:
        econ_input = inputs_by_id.get(opp.id)
        readiness_eval = readiness_by_id.get(opp.id)
        readiness_tier = (
            readiness_eval.overall_readiness_tier
            if readiness_eval
            else OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE
        )

        labor_metrics, valuation_metrics = calculate_labor_capacity_metrics(
            opp, window_info, econ_input
        )
        cash_flow = CashFlowMetrics()

        synthesis = synthesize_strategic_decision(
            priority=opp.priority_tier,
            readiness=readiness_tier,
            economic_tier=valuation_metrics.economic_tier,
            archetype=opp.archetype,
            source_finding=None,
            exclusions=exclusions_dict,
        )

        result_item = OpportunityEconomicsResult(
            opportunity_id=opp.id,
            archetype=opp.archetype,
            observation_window=window_info,
            labor_effort=labor_metrics,
            capacity_valuation=valuation_metrics,
            cash_flow=cash_flow,
            synthesis=synthesis,
        )
        evaluated_opportunities.append(result_item)

        # Accumulate distributions
        arch_name = opp.archetype.value
        archetype_counts[arch_name] = archetype_counts.get(arch_name, 0) + 1

        tier_name = valuation_metrics.economic_tier.value
        economic_tier_counts[tier_name] = economic_tier_counts.get(tier_name, 0) + 1

        decision_name = synthesis.strategic_decision.value
        strategic_decision_counts[decision_name] = (
            strategic_decision_counts.get(decision_name, 0) + 1
        )

        # Accumulate totals
        if labor_metrics.sample_addressable_labor_hours is not None:
            total_sample_addr_hours += labor_metrics.sample_addressable_labor_hours
            has_sample_addr_hours = True

        if labor_metrics.annual_addressable_labor_hours is not None:
            total_annual_addr_hours += labor_metrics.annual_addressable_labor_hours
            has_annual_addr_hours = True

        if valuation_metrics.gross_annual_capacity_value is not None:
            total_gross_val += valuation_metrics.gross_annual_capacity_value
            has_gross_val = True

        if valuation_metrics.net_annual_capacity_benefit is not None:
            total_net_benefit += valuation_metrics.net_annual_capacity_benefit
            has_net_benefit = True

    summary = EconomicsSummary(
        total_opportunities_evaluated=len(evaluated_opportunities),
        evaluated_volume=window_info.evaluated_case_volume,
        total_sample_addressable_hours=(
            round(total_sample_addr_hours, 2) if has_sample_addr_hours else None
        ),
        total_annual_addressable_hours=(
            round(total_annual_addr_hours, 2) if has_annual_addr_hours else None
        ),
        total_gross_capacity_value=round(total_gross_val, 2) if has_gross_val else None,
        total_net_capacity_benefit=round(total_net_benefit, 2) if has_net_benefit else None,
        archetype_distribution=archetype_counts,
        economic_tier_distribution=economic_tier_counts,
        strategic_decision_distribution=strategic_decision_counts,
    )

    return EconomicsEvaluationResponse(
        filename=filename,
        summary=summary,
        opportunities=evaluated_opportunities,
    )
