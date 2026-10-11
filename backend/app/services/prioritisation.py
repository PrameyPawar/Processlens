"""
Deterministic domain service for Phase 8 Opportunity Prioritisation & Portfolio Action Roadmap.
Implements:
- 8-cohort non-compensatory portfolio partitioning mapping all 15 Phase 7 strategic outcomes.
- 6-factor full-precision derivation and dynamic weight redistribution.
- Decimal quantization with ROUND_HALF_EVEN and post-quantization positive-zero normalization.
- Full-precision composite scoring with independent factor-contribution delta quantization.
- 8-tuple deterministic sorting with explicit None checks and zero-value preservation.
- Evidence-conditional, non-causal primary strength and constraint generation.
- Non-additive top-three portfolio capacity scenario evaluation.
"""

from decimal import Decimal, ROUND_HALF_EVEN
import json
import math
from typing import Dict, List, Optional, Tuple, Any

from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.opportunity import (
    OpportunityCandidate,
    OpportunityDetectionResult,
)
from app.schemas.readiness import (
    OverallReadinessTier,
    ReadinessAssessmentResponse,
    OpportunityReadinessResult,
)
from app.schemas.economics import (
    MetricProvenance,
    StrategicDecisionOutcome,
    OpportunityEconomicsResult,
    EconomicsEvaluationResponse,
)
from app.schemas.prioritisation import (
    PortfolioCohort,
    ImpactBasis,
    ScoringStatus,
    ConstraintStatus,
    PrioritisationWeights,
    FactorBreakdown,
    PrioritisedOpportunity,
    PrioritisationSummary,
    PrioritisationResponse,
)


def quantize_to_4_decimals(val: Optional[float]) -> Optional[float]:
    """
    Quantizes a floating-point value to 4 decimal places using Python's standard
    decimal module with ROUND_HALF_EVEN (Banker's rounding).
    Normalizes negative zero to positive 0.0 strictly when the quantized result equals zero.
    """
    if val is None:
        return None
    d = Decimal(str(val)).quantize(Decimal("0.0001"), rounding=ROUND_HALF_EVEN)
    result_float = float(d)
    if result_float == 0.0:
        return 0.0
    return result_float


def parse_prioritisation_weights_json(raw_json: Optional[str]) -> PrioritisationWeights:
    """
    Parses and validates optional JSON string representing custom PrioritisationWeights.
    If omitted or empty, returns standard default weights (30/25/20/10/5/10).
    Raises ValueError with descriptive feedback on JSON syntax or sum validation errors.
    """
    if raw_json is None:
        return PrioritisationWeights()
    stripped = raw_json.strip()
    if not stripped:
        return PrioritisationWeights()

    try:
        data = json.loads(stripped)
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON format in prioritisation_weights: {str(e)}")

    if not isinstance(data, dict):
        raise ValueError("prioritisation_weights must be a JSON object.")

    try:
        weights = PrioritisationWeights.model_validate(data)
    except Exception as e:
        raise ValueError(f"Validation error in prioritisation_weights: {str(e)}")

    PrioritisationWeights.validate_sum_contract(weights)
    return weights


# -----------------------------------------------------------------------------
# Canonical 15-Outcome to 8-Cohort Mapping Table
# -----------------------------------------------------------------------------
OUTCOME_TO_COHORT_MAP: Dict[StrategicDecisionOutcome, PortfolioCohort] = {
    # Cohort 1: Foundational Data Quality (Precedence 1)
    StrategicDecisionOutcome.RESOLVE_DATA_INSTRUMENTATION: PortfolioCohort.FOUNDATIONAL_DATA_QUALITY,

    # Cohort 2: Immediate Automation Specification (Precedence 2)
    StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION: PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,

    # Cohort 3: Guardrailed Automation (Precedence 3)
    StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS: PortfolioCohort.GUARDRAILED_AUTOMATION,

    # Cohort 4: Process Restructuring (Precedence 4)
    StrategicDecisionOutcome.RESTRUCTURE_BEFORE_AUTOMATION: PortfolioCohort.PROCESS_RESTRUCTURING,
    StrategicDecisionOutcome.LOW_CAPITAL_STANDARDIZATION: PortfolioCohort.PROCESS_RESTRUCTURING,

    # Cohort 5: Business Case Validation (Precedence 5)
    StrategicDecisionOutcome.VALIDATE_BUSINESS_CASE_AND_SPECIFY: PortfolioCohort.BUSINESS_CASE_VALIDATION,
    StrategicDecisionOutcome.STANDARDIZE_AND_COLLECT_DATA: PortfolioCohort.BUSINESS_CASE_VALIDATION,

    # Cohort 6: Feasibility Investigation (Precedence 6)
    StrategicDecisionOutcome.PILOT_AND_MEASURE: PortfolioCohort.FEASIBILITY_INVESTIGATION,
    StrategicDecisionOutcome.INVESTIGATE_FEASIBILITY: PortfolioCohort.FEASIBILITY_INVESTIGATION,

    # Cohort 7: Revise or Deferred (Precedence 7)
    StrategicDecisionOutcome.REVISE_SCOPE_OR_RENEGOTIATE: PortfolioCohort.REVISE_OR_DEFERRED,
    StrategicDecisionOutcome.DEFER_OR_ARCHIVE: PortfolioCohort.REVISE_OR_DEFERRED,

    # Cohort 8: Blocked by Barriers (Precedence 8)
    StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL: PortfolioCohort.BLOCKED_BY_BARRIERS,
    StrategicDecisionOutcome.BLOCKED_UNKNOWN_ECONOMICS: PortfolioCohort.BLOCKED_BY_BARRIERS,
    StrategicDecisionOutcome.BLOCKED_AND_UNECONOMICAL: PortfolioCohort.BLOCKED_BY_BARRIERS,
    StrategicDecisionOutcome.BLOCKED_LOW_PRIORITY: PortfolioCohort.BLOCKED_BY_BARRIERS,
}


def evaluate_factors(
    opp_econ: OpportunityEconomicsResult,
    opp_cand: OpportunityCandidate,
    readiness_assessment: Optional[OpportunityReadinessResult],
    complete_case_count: int,
) -> Tuple[
    Dict[str, Optional[float]],  # raw factor values (impact, readiness, payback, effort, risk, confidence)
    ImpactBasis,
    MetricProvenance,
    List[str],  # caveats
]:
    """
    Evaluates raw 0.0 to 100.0 factor values for an opportunity using full-precision
    calculations. Returns None for factors whose evidence is missing or unverified.
    """
    caveats: List[str] = []

    # 1. Factor 1: Business Impact
    net_benefit = opp_econ.capacity_valuation.net_annual_capacity_benefit
    if net_benefit is not None:
        impact_basis = ImpactBasis.CALCULATED_CAPACITY_SCENARIO
        impact_prov = MetricProvenance.CALCULATED_ESTIMATE
        if net_benefit <= 0.0:
            impact_score: Optional[float] = 0.0
        elif net_benefit <= 10000.0:
            impact_score = 4.0 * (net_benefit / 1000.0)
        elif net_benefit <= 50000.0:
            impact_score = 40.0 + 35.0 * ((net_benefit - 10000.0) / 40000.0)
        elif net_benefit <= 150000.0:
            impact_score = 75.0 + 20.0 * ((net_benefit - 50000.0) / 100000.0)
        else:
            impact_score = min(100.0, 95.0 + 5.0 * ((net_benefit - 150000.0) / 100000.0))
    else:
        impact_basis = ImpactBasis.OPERATIONAL_CONCENTRATION_BASELINE
        impact_prov = MetricProvenance.MEASURED_IN_LOG
        impact_score = float(opp_cand.operational_priority_score)
        caveats.append(
            "Impact derived from observed process pattern concentration; "
            "net annual capacity benefit is unverified."
        )

    # 2. Factor 2: Automation Readiness
    readiness_tier = opp_econ.synthesis.overall_readiness
    if readiness_tier == OverallReadinessTier.READY_FOR_SPECIFICATION:
        readiness_score: Optional[float] = 100.0
    elif readiness_tier == OverallReadinessTier.PREREQUISITES_REQUIRED:
        readiness_score = 60.0
    elif readiness_tier == OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE:
        readiness_score = 30.0
    elif readiness_tier == OverallReadinessTier.PROHIBITED_OR_BLOCKED:
        readiness_score = 0.0
    else:
        readiness_score = 30.0

    # 3. Factor 3: Economic Payback
    payback_months = opp_econ.capacity_valuation.payback_period_months
    if payback_months is not None:
        if payback_months == 0.0:
            payback_score: Optional[float] = 100.0
        elif payback_months <= 6.0:
            payback_score = 90.0 + 10.0 * ((6.0 - payback_months) / 6.0)
        elif payback_months <= 12.0:
            payback_score = 75.0 + 15.0 * ((12.0 - payback_months) / 6.0)
        elif payback_months <= 24.0:
            payback_score = 50.0 + 25.0 * ((24.0 - payback_months) / 12.0)
        elif payback_months <= 36.0:
            payback_score = 25.0 + 25.0 * ((36.0 - payback_months) / 12.0)
        else:
            payback_score = max(0.0, 25.0 - 25.0 * ((payback_months - 36.0) / 36.0))
    else:
        if net_benefit is not None and net_benefit <= 0.0:
            payback_score = 0.0
            caveats.append("Payback period is unachievable under nonpositive net capacity benefit.")
        else:
            payback_score = None
            caveats.append("Payback period is unverified; factor evaluates as None.")

    # 4. Factor 4: Implementation Investment Ease
    impl_cost = opp_econ.capacity_valuation.implementation_cost
    if impl_cost is not None:
        if impl_cost == 0.0:
            effort_score: Optional[float] = 100.0
        elif impl_cost <= 5000.0:
            effort_score = 100.0 - 20.0 * (impl_cost / 5000.0)
        elif impl_cost <= 25000.0:
            effort_score = 80.0 - 25.0 * ((impl_cost - 5000.0) / 20000.0)
        elif impl_cost <= 100000.0:
            effort_score = 55.0 - 30.0 * ((impl_cost - 25000.0) / 75000.0)
        else:
            effort_score = max(0.0, 25.0 - 25.0 * ((impl_cost - 100000.0) / 150000.0))
    else:
        effort_score = None
        caveats.append("Implementation cost is unassessed; factor evaluates as None.")

    # 5. Factor 5: Execution & Governance Risk
    has_domain_intake = False
    if readiness_assessment:
        dims = [
            getattr(readiness_assessment, "task_repeatability_and_rule_stability", None),
            getattr(readiness_assessment, "digital_inputs_and_outputs", None),
            getattr(readiness_assessment, "system_interface_accessibility", None),
            getattr(readiness_assessment, "exception_frequency_and_judgment", None),
            getattr(readiness_assessment, "safety_regulatory_and_governance", None),
            getattr(readiness_assessment, "evidence_completeness_and_uncertainty", None),
        ]
        for dim in dims:
            if dim is not None:
                s_val = getattr(dim, "state", None)
                s_str = s_val.value if hasattr(s_val, "value") else str(s_val)
                if s_str not in ("UNKNOWN", "DEFAULT_UNKNOWN", "None"):
                    has_domain_intake = True
                    break

    if has_domain_intake and readiness_assessment:
        penalties = 0.0
        # Exception & judgment oversight
        ex_dim = getattr(readiness_assessment, "exception_frequency_and_judgment", None)
        if ex_dim:
            s_str = ex_dim.state.value if hasattr(ex_dim.state, "value") else str(ex_dim.state)
            if s_str == "PREREQUISITE_REQUIRED":
                penalties += 20.0
            elif s_str == "PROHIBITIVE_BARRIER":
                penalties += 100.0

        # Safety & regulatory governance
        safe_dim = getattr(readiness_assessment, "safety_regulatory_and_governance", None)
        if safe_dim:
            s_str = safe_dim.state.value if hasattr(safe_dim.state, "value") else str(safe_dim.state)
            if s_str == "PREREQUISITE_REQUIRED":
                penalties += 20.0
            elif s_str == "PROHIBITIVE_BARRIER":
                penalties += 100.0

        # System interface accessibility
        sys_dim = getattr(readiness_assessment, "system_interface_accessibility", None)
        if sys_dim:
            s_str = sys_dim.state.value if hasattr(sys_dim.state, "value") else str(sys_dim.state)
            if s_str == "PREREQUISITE_REQUIRED":
                penalties += 15.0

        # Digital inputs & outputs data structure
        data_dim = getattr(readiness_assessment, "digital_inputs_and_outputs", None)
        if data_dim:
            s_str = data_dim.state.value if hasattr(data_dim.state, "value") else str(data_dim.state)
            if s_str == "PREREQUISITE_REQUIRED":
                penalties += 15.0

        discrepancies = getattr(readiness_assessment, "discrepancies", [])
        if discrepancies:
            disc_penalty = min(20.0, float(len(discrepancies)) * 10.0)
            penalties += disc_penalty

        risk_score: Optional[float] = max(0.0, 100.0 - penalties)
    else:
        risk_score = None
        caveats.append("Governance and operational risk is unassessed; factor evaluates as None.")

    # 6. Factor 6: Empirical Evidence & Confidence (Always available)
    if complete_case_count >= 100:
        conf_base = 50.0
    elif complete_case_count >= 30:
        conf_base = 35.0
    elif complete_case_count >= 10:
        conf_base = 20.0
    else:
        conf_base = 10.0

    conf_bonuses = 0.0
    win_info = opp_econ.observation_window
    if win_info.observation_duration_days is not None and win_info.observation_duration_days >= 30.0:
        conf_bonuses += 25.0
    elif win_info.annualisation_method.value == "EXPLICIT_OVERRIDE":
        conf_bonuses += 25.0

    if has_domain_intake:
        conf_bonuses += 15.0

    cap_val = opp_econ.capacity_valuation
    if cap_val.implementation_cost is not None and cap_val.annual_recurring_cost is not None:
        conf_bonuses += 10.0

    confidence_score: float = min(100.0, conf_base + conf_bonuses)

    factors_dict = {
        "impact": impact_score,
        "readiness": readiness_score,
        "payback": payback_score,
        "effort": effort_score,
        "risk": risk_score,
        "confidence": confidence_score,
    }

    return factors_dict, impact_basis, impact_prov, caveats


def make_sort_key(opp: PrioritisedOpportunity) -> Tuple:
    """
    Constructs the canonical 8-tuple sort key for global portfolio ranking.
    Preserves exact zero values, placing scored before unscored items, and breaks ties deterministically.
    """
    comp_score = opp.composite_priority_score
    net_benefit = opp.economics.capacity_valuation.net_annual_capacity_benefit
    payback = opp.economics.capacity_valuation.payback_period_months

    # Explicit handling of scores: 0.0 normalized to 0.0 (never -0.0)
    neg_score = (-comp_score) if comp_score is not None else 0.0
    if neg_score == 0.0:
        neg_score = 0.0

    # Explicit handling of net benefit: 0.0 normalized to 0.0, None -> +inf
    neg_benefit = (-net_benefit) if net_benefit is not None else float("inf")
    if neg_benefit == 0.0:
        neg_benefit = 0.0

    # Explicit handling of payback: 0.0 normalized to 0.0, None -> +inf
    payback_val = payback if payback is not None else float("inf")
    if payback_val == 0.0:
        payback_val = 0.0

    return (
        # 1. Cohort Precedence (Ascending, 1 to 8)
        opp.portfolio_cohort.precedence_index,
        # 2. Scored Placement (Ascending: 0 = Scored, 1 = Unscored)
        0 if comp_score is not None else 1,
        # 3. Quantized Score Bucket (Descending)
        neg_score,
        # 4. Net Annual Capacity Benefit (Descending; None -> +inf)
        neg_benefit,
        # 5. Payback Period Months (Ascending; None -> +inf)
        payback_val,
        # 6. Operational Priority Score (Descending)
        -opp.operational_priority_score,
        # 7. Sample Size of Completed Cases (Descending)
        -opp.economics.observation_window.sample_completed_cases,
        # 8. Deterministic Stable ID Tie-Breaker (Ascending)
        opp.opportunity_id.lower(),
    )


def generate_primary_strength(
    opp_econ: OpportunityEconomicsResult,
    cohort: PortfolioCohort,
    factors: Dict[str, Optional[float]],
    effective_weights: Dict[str, float],
    impact_basis: ImpactBasis,
) -> str:
    """
    Generates evidence-conditional primary strength description from the highest weighted contribution.
    """
    if cohort == PortfolioCohort.FOUNDATIONAL_DATA_QUALITY:
        return "remediates event log tracking and data pipeline observability gaps"

    # Compute weighted contribution C_k = (w_k^* / 100.0) * F_k
    contributions: Dict[str, float] = {}
    for k, val in factors.items():
        if val is not None:
            w = effective_weights.get(k, 0.0)
            contributions[k] = (w / 100.0) * val

    if not contributions:
        return f"evaluated under strategic outcome {opp_econ.synthesis.strategic_decision.value}"

    # Determine winning factor using tie-break precedence: impact -> readiness -> payback -> effort -> risk -> confidence
    factor_precedence = ["impact", "readiness", "payback", "effort", "risk", "confidence"]
    max_c = max(contributions.values())

    winning_factor = "confidence"
    for k in factor_precedence:
        if k in contributions and abs(contributions[k] - max_c) < 1e-9:
            winning_factor = k
            break

    # Strictly evidence-conditional templates
    if winning_factor == "impact":
        if impact_basis == ImpactBasis.CALCULATED_CAPACITY_SCENARIO:
            b_net = opp_econ.capacity_valuation.net_annual_capacity_benefit or 0.0
            return f"calculated capacity reallocation benefit estimate of ${b_net:,.2f}/year (unrealized capacity scenario)"
        else:
            score = factors.get("impact", 0.0)
            return f"observed process pattern concentration score of {score:.1f} in event log"

    elif winning_factor == "readiness":
        r_tier = opp_econ.synthesis.overall_readiness
        if r_tier == OverallReadinessTier.READY_FOR_SPECIFICATION:
            return "readiness assessment tier READY_FOR_SPECIFICATION (prerequisites satisfied for functional specification)"
        return f"readiness assessment tier {r_tier.value}"

    elif winning_factor == "payback":
        pb = opp_econ.capacity_valuation.payback_period_months
        if pb == 0.0:
            return "calculated payback of 0.0 months under assumed zero capital implementation cost"
        return f"projected payback period of {pb:.1f} months based on supplied cost assumptions"

    elif winning_factor == "effort":
        c_impl = opp_econ.capacity_valuation.implementation_cost or 0.0
        return f"user-supplied implementation cost assumption of ${c_impl:,.2f}"

    elif winning_factor == "risk":
        r_score = factors.get("risk", 100.0) or 100.0
        if r_score == 100.0:
            return "zero operational prerequisites or empirical discrepancies flagged in domain assessment"
        return f"governance risk score of {r_score:.1f} reflecting identified prerequisites/discrepancies"

    elif winning_factor == "confidence":
        n_cases = opp_econ.observation_window.sample_completed_cases
        if n_cases >= 100:
            return f"supported by an observed sample of {n_cases} complete cases"
        return f"supported by an observed sample of {n_cases} complete cases (preliminary sample size)"

    return f"evaluated under strategic outcome {opp_econ.synthesis.strategic_decision.value}"


def generate_primary_constraint(
    curr_opp: PrioritisedOpportunity,
    prev_opp: PrioritisedOpportunity,
    factors_curr: Dict[str, Optional[float]],
    factors_prev: Dict[str, Optional[float]],
    effective_weights_curr: Dict[str, float],
    effective_weights_prev: Dict[str, float],
) -> Tuple[Optional[str], Optional[ConstraintStatus]]:
    """
    Generates evidence-backed primary constraint relative strictly to the candidate at rank R-1.
    """
    # 1. Inter-Cohort Boundary
    if curr_opp.portfolio_cohort.precedence_index > prev_opp.portfolio_cohort.precedence_index:
        prev_cohort = prev_opp.portfolio_cohort
        curr_cohort = curr_opp.portfolio_cohort
        strat_dec = curr_opp.economics.synthesis.strategic_decision
        rationale = curr_opp.economics.synthesis.decision_rationale

        if (
            prev_cohort == PortfolioCohort.FOUNDATIONAL_DATA_QUALITY
            and curr_cohort == PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION
        ):
            text = (
                "Portfolio roadmap policy prioritizes foundational data quality remediation ahead of "
                f"solution specification. Candidate is evaluated as SPECIFY_AUTOMATION_SOLUTION: {rationale}"
            )
        else:
            text = (
                f"Portfolio roadmap policy prioritizes {prev_cohort.value} ahead of {curr_cohort.value}. "
                f"Candidate is evaluated as {strat_dec.value}: {rationale}"
            )
        return text, ConstraintStatus.INTER_COHORT_PRECEDENCE

    # 2. Intra-Cohort Boundary: Check Comparability
    avail_curr = {k for k, v in factors_curr.items() if v is not None}
    avail_prev = {k for k, v in factors_prev.items() if v is not None}
    same_basis = curr_opp.factors.impact_basis == prev_opp.factors.impact_basis
    is_scored_curr = curr_opp.scoring_status == ScoringStatus.SCORED
    is_scored_prev = prev_opp.scoring_status == ScoringStatus.SCORED

    if not (is_scored_curr and is_scored_prev and same_basis and avail_curr == avail_prev):
        if not is_scored_curr and is_scored_prev:
            return (
                "unscored priority status due to unweighted/missing factor inputs",
                ConstraintStatus.UNSCORED_COMPARISON,
            )
        diff_factors = avail_prev - avail_curr
        if diff_factors:
            diff_list = sorted(list(diff_factors))
            return (
                f"unverified {', '.join(diff_list)} data relative to rank #{prev_opp.rank_order}",
                ConstraintStatus.UNSCORED_COMPARISON,
            )
        return (
            f"incomparable factor evaluation basis relative to rank #{prev_opp.rank_order}",
            ConstraintStatus.UNSCORED_COMPARISON,
        )

    # 3. Intra-Cohort Comparable: Independent Delta Quantization
    quantized_deltas: Dict[str, float] = {}
    for k in avail_curr:
        raw_c_curr = (effective_weights_curr.get(k, 0.0) / 100.0) * (factors_curr[k] or 0.0)
        raw_c_prev = (effective_weights_prev.get(k, 0.0) / 100.0) * (factors_prev[k] or 0.0)
        raw_delta = raw_c_curr - raw_c_prev
        quant_delta = quantize_to_4_decimals(raw_delta)
        quantized_deltas[k] = quant_delta if quant_delta is not None else 0.0

    # Check for negative deltas (< 0.0)
    negative_deltas = {k: v for k, v in quantized_deltas.items() if v < 0.0}
    if negative_deltas:
        min_delta = min(negative_deltas.values())
        factor_precedence = ["payback", "impact", "effort", "readiness", "risk", "confidence"]
        deficit_factor = "confidence"
        for k in factor_precedence:
            if k in negative_deltas and abs(negative_deltas[k] - min_delta) < 1e-9:
                deficit_factor = k
                break

        curr_f_val = factors_curr.get(deficit_factor, 0.0) or 0.0
        prev_f_val = factors_prev.get(deficit_factor, 0.0) or 0.0
        text = f"lower {deficit_factor} contribution ({curr_f_val:.1f} vs {prev_f_val:.1f})"
        return text, ConstraintStatus.FACTOR_DEFICIT

    # No individual factor delta is negative. Check composite score buckets:
    bucket_curr = curr_opp.score_bucket or 0.0
    bucket_prev = prev_opp.score_bucket or 0.0

    if bucket_curr < bucket_prev:
        score_curr = curr_opp.composite_priority_score or 0.0
        score_prev = prev_opp.composite_priority_score or 0.0
        text = f"lower aggregate composite priority score ({score_curr:.4f} vs {score_prev:.4f}) across combined weighted factors"
        return text, ConstraintStatus.FACTOR_DEFICIT

    # Score buckets are identical (tied). Rationale cites governing tie-breaker:
    b_curr = curr_opp.economics.capacity_valuation.net_annual_capacity_benefit
    b_prev = prev_opp.economics.capacity_valuation.net_annual_capacity_benefit
    if b_curr != b_prev:
        return (
            f"lower net capacity benefit (${b_curr or 0.0:,.2f} vs ${b_prev or 0.0:,.2f}) under tied composite score",
            ConstraintStatus.FACTOR_DEFICIT,
        )

    pb_curr = curr_opp.economics.capacity_valuation.payback_period_months
    pb_prev = prev_opp.economics.capacity_valuation.payback_period_months
    if pb_curr != pb_prev:
        return (
            f"longer payback period ({pb_curr or 0.0:.1f}m vs {pb_prev or 0.0:.1f}m) under tied composite score",
            ConstraintStatus.FACTOR_DEFICIT,
        )

    op_curr = curr_opp.operational_priority_score
    op_prev = prev_opp.operational_priority_score
    if op_curr != op_prev:
        return (
            f"lower operational concentration score ({op_curr:.1f} vs {op_prev:.1f}) under tied composite score",
            ConstraintStatus.FACTOR_DEFICIT,
        )

    n_curr = curr_opp.economics.observation_window.sample_completed_cases
    n_prev = prev_opp.economics.observation_window.sample_completed_cases
    if n_curr != n_prev:
        return (
            f"smaller completed case sample size ({n_curr} vs {n_prev}) under tied composite score",
            ConstraintStatus.FACTOR_DEFICIT,
        )

    return (
        f"separated by deterministic identifier tie-breaker (opportunity_id: {curr_opp.opportunity_id}) under tied composite score",
        ConstraintStatus.FACTOR_DEFICIT,
    )


def prioritise_opportunities_portfolio(
    economics_response: EconomicsEvaluationResponse,
    opportunity_result: OpportunityDetectionResult,
    readiness_result: ReadinessAssessmentResponse,
    reconstruction: ProcessReconstructionResult,
    weights: PrioritisationWeights,
    filename: str,
) -> PrioritisationResponse:
    """
    Main orchestration service for Phase 8 Prioritisation.
    Partitions opportunities into 8 cohorts, computes 6 factors and full-precision composite scores,
    sorts using the 8-tuple sort contract, generates evidence-backed rationales, and compiles the response.
    """
    complete_cases = [c for c in reconstruction.cases if c.is_complete]
    n_complete = len(complete_cases)

    # Index candidates and readiness assessments by opportunity_id
    opp_cand_by_id: Dict[str, OpportunityCandidate] = {
        o.id: o for o in opportunity_result.opportunities
    }
    readiness_by_id: Dict[str, OpportunityReadinessResult] = {
        r.opportunity_id: r for r in readiness_result.assessments
    }

    base_weights = {
        "impact": weights.impact_weight,
        "readiness": weights.readiness_weight,
        "payback": weights.payback_weight,
        "effort": weights.effort_weight,
        "risk": weights.risk_weight,
        "confidence": weights.confidence_weight,
    }

    pre_ranked_items: List[PrioritisedOpportunity] = []
    cohort_counts: Dict[str, int] = {}
    temp_factors_by_id: Dict[str, Dict[str, Optional[float]]] = {}
    temp_eff_weights_by_id: Dict[str, Dict[str, float]] = {}

    for opp_econ in economics_response.opportunities:
        opp_id = opp_econ.opportunity_id
        opp_cand = opp_cand_by_id.get(opp_id)
        if not opp_cand:
            continue
        readiness_eval = readiness_by_id.get(opp_id)

        # 1. Cohort Placement (15 outcomes -> 8 cohorts)
        outcome = opp_econ.synthesis.strategic_decision
        cohort = OUTCOME_TO_COHORT_MAP.get(outcome, PortfolioCohort.REVISE_OR_DEFERRED)
        cohort_counts[cohort.value] = cohort_counts.get(cohort.value, 0) + 1

        # 2. Factor Derivation (Full-Precision)
        factors_dict, impact_basis, impact_prov, caveats = evaluate_factors(
            opp_econ, opp_cand, readiness_eval, n_complete
        )
        temp_factors_by_id[opp_id] = factors_dict

        # 3. Dynamic Weight Redistribution
        avail_factors = {k for k, v in factors_dict.items() if v is not None}
        w_avail = sum(base_weights[k] for k in avail_factors)

        effective_weights: Dict[str, float] = {}
        if w_avail > 0.0:
            for k in avail_factors:
                effective_weights[k] = base_weights[k] * (100.0 / w_avail)
            # Full-Precision Composite Score (normalized to 0.0 to 100.0 scale)
            comp_score_raw: Optional[float] = sum(
                (effective_weights[k] / 100.0) * (factors_dict[k] or 0.0) for k in avail_factors
            )
            score_bucket: Optional[float] = quantize_to_4_decimals(comp_score_raw)
            scoring_status = ScoringStatus.SCORED
        else:
            comp_score_raw = None
            score_bucket = None
            scoring_status = ScoringStatus.UNSCORED
            caveats.append("No factor inputs available with non-zero weight; candidate is unscored.")

        temp_eff_weights_by_id[opp_id] = effective_weights

        factor_breakdown = FactorBreakdown(
            impact_score=factors_dict["impact"],
            impact_basis=impact_basis,
            impact_provenance=impact_prov,
            readiness_score=factors_dict["readiness"],
            payback_score=factors_dict["payback"],
            effort_score=factors_dict["effort"],
            risk_score=factors_dict["risk"],
            confidence_score=factors_dict["confidence"] or 0.0,
            effective_weights={k: round(v, 4) for k, v in effective_weights.items()},
            factor_caveats=caveats,
        )

        item = PrioritisedOpportunity(
            rank_order=0,  # assigned after sorting
            opportunity_id=opp_id,
            archetype=opp_econ.archetype,
            portfolio_cohort=cohort,
            scoring_status=scoring_status,
            composite_priority_score_raw=comp_score_raw,
            composite_priority_score=score_bucket,
            score_bucket=score_bucket,
            factors=factor_breakdown,
            economics=opp_econ,
            operational_priority_score=opp_cand.operational_priority_score,
            primary_strength="",
            primary_constraint=None,
            constraint_status=None,
        )
        pre_ranked_items.append(item)

    # 4. Deterministic Global Sorting (8-Tuple Sort Contract)
    sorted_items = sorted(pre_ranked_items, key=make_sort_key)

    # 5. Rationale Generation & Rank Order Assignment
    final_ranked: List[PrioritisedOpportunity] = []
    for idx, opp in enumerate(sorted_items):
        rank = idx + 1
        opp.rank_order = rank

        # Primary Strength
        opp.primary_strength = generate_primary_strength(
            opp.economics,
            opp.portfolio_cohort,
            temp_factors_by_id[opp.opportunity_id],
            temp_eff_weights_by_id[opp.opportunity_id],
            opp.factors.impact_basis,
        )

        # Primary Constraint (Rank 2+)
        if rank > 1:
            prev_opp = final_ranked[idx - 1]
            constraint_text, c_status = generate_primary_constraint(
                curr_opp=opp,
                prev_opp=prev_opp,
                factors_curr=temp_factors_by_id[opp.opportunity_id],
                factors_prev=temp_factors_by_id[prev_opp.opportunity_id],
                effective_weights_curr=temp_eff_weights_by_id[opp.opportunity_id],
                effective_weights_prev=temp_eff_weights_by_id[prev_opp.opportunity_id],
            )
            opp.primary_constraint = constraint_text
            opp.constraint_status = c_status
        else:
            opp.primary_constraint = None
            opp.constraint_status = None

        final_ranked.append(opp)

    # 6. Cumulative Top-Three Capacity Scenario
    top_3_ids = [o.opportunity_id for o in final_ranked[:3]]
    top_3_benefits = [
        o.economics.capacity_valuation.net_annual_capacity_benefit
        for o in final_ranked[:3]
        if o.economics.capacity_valuation.net_annual_capacity_benefit is not None
    ]
    cumulative_capacity = (
        round(sum(top_3_benefits), 2) if top_3_benefits else None
    )

    summary = PrioritisationSummary(
        total_opportunities_prioritised=len(final_ranked),
        cohort_distribution=cohort_counts,
        top_opportunity_id=final_ranked[0].opportunity_id if final_ranked else None,
        top_three_opportunity_ids=top_3_ids,
        top_three_cumulative_capacity_scenario=cumulative_capacity,
    )

    return PrioritisationResponse(
        filename=filename,
        summary=summary,
        ranked_opportunities=final_ranked,
    )
