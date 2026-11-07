"""
Deterministic domain service for Phase 9 Evidence Architecture and Audit Dossier.
Produces auditable evidence dossiers connecting raw operational event data to
analytical findings, mathematical derivations, financial assumptions, readiness assessments,
and portfolio ranking decisions.
"""

import hashlib
from typing import List, Dict, Optional, Tuple, Any
from collections import defaultdict

from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import ProblemDetectionResult, FindingCategory
from app.schemas.opportunity import (
    OpportunityDetectionResult,
    OpportunityCandidate,
    OpportunityArchetype,
)
from app.schemas.readiness import ReadinessAssessmentResponse
from app.schemas.economics import (
    EconomicsEvaluationResponse,
    OpportunityEconomicsResult,
)
from app.schemas.prioritisation import (
    PrioritisationResponse,
    PrioritisedOpportunity,
    PrioritisationWeights,
)
from app.schemas.evidence import (
    EpistemicType,
    EpistemicItem,
    EventRowAnchor,
    CaseTraceExemplar,
    MetricDerivationAudit,
    OpportunityEvidenceDossier,
    EvidenceAuditManifest,
    EvidenceAuditSummary,
    EvidenceAuditResponse,
)


def extract_exemplars_for_opportunity(
    opp: PrioritisedOpportunity,
    candidate: OpportunityCandidate,
    reconstruction: ProcessReconstructionResult,
    analytics: ProcessAnalyticsResult,
    detection: ProblemDetectionResult,
) -> Tuple[List[CaseTraceExemplar], str, List[str]]:
    """
    Extracts up to 3 deterministic, relevant case trace exemplars for an opportunity
    based on its archetype, complete traces, and specific target entities.
    """
    exemplars: List[CaseTraceExemplar] = []
    policy_desc: str = ""
    caveats: List[str] = []

    complete_cases = [c for c in getattr(reconstruction, "cases", []) if getattr(c, "is_complete", True)]

    # 1. DELAY_COMPRESSION
    if opp.archetype == OpportunityArchetype.DELAY_COMPRESSION:
        policy_desc = (
            "Complete cases traversing transition sorted by (-max_transition_duration_seconds, case_id); "
            "up to 3 exemplars."
        )
        if " -> " in candidate.target_entity:
            source_act, target_act = candidate.target_entity.split(" -> ", 1)
        else:
            source_act, target_act = "unknown", "unknown"

        matching_cases: List[Tuple[float, Any, Any, Any]] = []
        for c in complete_cases:
            non_dup_events = [e for e in c.events if not e.is_duplicate]
            pairs: List[Tuple[float, Any, Any]] = []
            for i in range(len(non_dup_events) - 1):
                e1 = non_dup_events[i]
                e2 = non_dup_events[i + 1]
                if e1.activity == source_act and e2.activity == target_act:
                    dur = max(0.0, (e2.timestamp_parsed - e1.timestamp_parsed).total_seconds())
                    pairs.append((dur, e1, e2))
            if pairs:
                best_pair = max(pairs, key=lambda p: p[0])
                matching_cases.append((best_pair[0], c, best_pair[1], best_pair[2]))

        matching_cases.sort(key=lambda item: (-item[0], item[1].case_id))

        for dur, c, e_src, e_tgt in matching_cases[:3]:
            ct = (c.end_time - c.start_time).total_seconds() if (c.start_time and c.end_time) else 0.0
            src_anchor = EventRowAnchor(
                row_index=e_src.row_index,
                csv_line_number=e_src.row_index + 1,
                case_id=c.case_id,
                activity=e_src.activity,
                timestamp_raw=e_src.timestamp_raw,
                resource=e_src.resource,
                source_event_id=e_src.source_event_id,
                role_in_evidence="TRANSITION_SOURCE",
            )
            tgt_anchor = EventRowAnchor(
                row_index=e_tgt.row_index,
                csv_line_number=e_tgt.row_index + 1,
                case_id=c.case_id,
                activity=e_tgt.activity,
                timestamp_raw=e_tgt.timestamp_raw,
                resource=e_tgt.resource,
                source_event_id=e_tgt.source_event_id,
                role_in_evidence="TRANSITION_TARGET",
            )
            summary = (
                f"Case '{c.case_id}' traversed transition '{source_act}' -> '{target_act}' "
                f"with elapsed milestone duration of {dur:.2f}s."
            )
            exemplars.append(
                CaseTraceExemplar(
                    case_id=c.case_id,
                    exemplar_metric_value=round(dur, 2),
                    exemplar_metric_description=f"Elapsed milestone duration from '{source_act}' to '{target_act}'",
                    total_case_duration_seconds=round(ct, 2),
                    event_anchors=[src_anchor, tgt_anchor],
                    trace_summary=summary,
                )
            )

    # 2. RECURRENCE_REDUCTION
    elif opp.archetype == OpportunityArchetype.RECURRENCE_REDUCTION:
        policy_desc = (
            "Complete cases with repeated executions at distinct timestamps sorted by "
            "(-repetition_count, -total_case_duration_seconds, case_id); up to 3 exemplars."
        )
        target_act = candidate.target_entity
        matching_recurrences: List[Tuple[int, float, Any, List[Any]]] = []

        for c in complete_cases:
            matched_events = [e for e in c.events if e.activity == target_act]
            seen_ts = set()
            distinct_events: List[Any] = []
            for e in matched_events:
                if e.timestamp_parsed not in seen_ts:
                    seen_ts.add(e.timestamp_parsed)
                    distinct_events.append(e)

            if len(distinct_events) >= 2:
                rep_count = len(distinct_events) - 1
                ct = (c.end_time - c.start_time).total_seconds() if (c.start_time and c.end_time) else 0.0
                matching_recurrences.append((rep_count, ct, c, distinct_events))

        matching_recurrences.sort(key=lambda item: (-item[0], -item[1], item[2].case_id))

        for rep_count, ct, c, distinct_events in matching_recurrences[:3]:
            anchors = [
                EventRowAnchor(
                    row_index=e.row_index,
                    csv_line_number=e.row_index + 1,
                    case_id=c.case_id,
                    activity=e.activity,
                    timestamp_raw=e.timestamp_raw,
                    resource=e.resource,
                    source_event_id=e.source_event_id,
                    role_in_evidence="REPEATED_ACTIVITY",
                )
                for e in distinct_events
            ]
            summary = (
                f"Case '{c.case_id}' executed activity '{target_act}' {len(distinct_events)} times "
                f"at distinct timestamps ({rep_count} repeat executions)."
            )
            exemplars.append(
                CaseTraceExemplar(
                    case_id=c.case_id,
                    exemplar_metric_value=float(len(distinct_events)),
                    exemplar_metric_description=f"Executions of '{target_act}' at distinct timestamps in trace",
                    total_case_duration_seconds=round(ct, 2),
                    event_anchors=anchors,
                    trace_summary=summary,
                )
            )

    # 3. TAIL_VARIANCE_MITIGATION
    elif opp.archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION:
        policy_desc = (
            "Complete cases exceeding cycle-time upper fence threshold sorted by "
            "(-case_duration_seconds, case_id); up to 3 exemplars."
        )
        upper_fence = 0.0
        for f in detection.findings:
            if f.category == FindingCategory.CYCLE_TIME_OUTLIER and f.rule in ("CYCLE_TIME_TUKEY_OUTLIER", "CYCLE_TIME_OUTLIER_IQR"):
                upper_fence = float(f.metrics.get("upper_fence_seconds", f.metrics.get("outlier_threshold_seconds", 0.0)))
                break

        if upper_fence == 0.0 and complete_cases:
            case_durations = sorted([(c.end_time - c.start_time).total_seconds() for c in complete_cases if (c.start_time and c.end_time)])
            if case_durations:
                n = len(case_durations)
                q1 = case_durations[int(n * 0.25)]
                q3 = case_durations[int(n * 0.75)]
                iqr = q3 - q1
                if iqr > 0:
                    upper_fence = q3 + 1.5 * iqr

        matching_outliers: List[Tuple[float, Any]] = []
        for c in complete_cases:
            ct = (c.end_time - c.start_time).total_seconds() if (c.start_time and c.end_time) else 0.0
            if ct > upper_fence:
                matching_outliers.append((ct, c))

        matching_outliers.sort(key=lambda item: (-item[0], item[1].case_id))

        for ct, c in matching_outliers[:3]:
            anchors: List[EventRowAnchor] = []
            if c.events:
                e_start = c.events[0]
                e_end = c.events[-1]
                anchors.append(
                    EventRowAnchor(
                        row_index=e_start.row_index,
                        csv_line_number=e_start.row_index + 1,
                        case_id=c.case_id,
                        activity=e_start.activity,
                        timestamp_raw=e_start.timestamp_raw,
                        resource=e_start.resource,
                        source_event_id=e_start.source_event_id,
                        role_in_evidence="TRACE_START",
                    )
                )
                if len(c.events) > 1:
                    anchors.append(
                        EventRowAnchor(
                            row_index=e_end.row_index,
                            csv_line_number=e_end.row_index + 1,
                            case_id=c.case_id,
                            activity=e_end.activity,
                            timestamp_raw=e_end.timestamp_raw,
                            resource=e_end.resource,
                            source_event_id=e_end.source_event_id,
                            role_in_evidence="TRACE_END",
                        )
                    )

            summary = (
                f"Case '{c.case_id}' exhibited total cycle time of {ct:.2f}s, exceeding "
                f"the upper fence outlier threshold of {upper_fence:.2f}s."
            )
            exemplars.append(
                CaseTraceExemplar(
                    case_id=c.case_id,
                    exemplar_metric_value=round(ct, 2),
                    exemplar_metric_description=f"Complete case cycle time exceeding outlier threshold ({upper_fence:.2f}s)",
                    total_case_duration_seconds=round(ct, 2),
                    event_anchors=anchors,
                    trace_summary=summary,
                )
            )

    # 4. PATH_STANDARDIZATION
    elif opp.archetype == OpportunityArchetype.PATH_STANDARDIZATION:
        policy_desc = (
            "Complete cases executing rare process variants sorted by "
            "(variant_id, -case_duration_seconds, case_id); up to 3 exemplars."
        )
        rare_vars = [v for v in getattr(reconstruction, "variants", []) if v.percentage < 2.0]
        case_to_var: Dict[str, str] = {}
        for v in rare_vars:
            for cid in v.case_ids:
                case_to_var[cid] = v.variant_id

        matching_rare_cases: List[Tuple[str, float, Any]] = []
        for c in complete_cases:
            if c.case_id in case_to_var:
                ct = (c.end_time - c.start_time).total_seconds() if (c.start_time and c.end_time) else 0.0
                matching_rare_cases.append((case_to_var[c.case_id], ct, c))

        matching_rare_cases.sort(key=lambda item: (item[0], -item[1], item[2].case_id))

        for var_id, ct, c in matching_rare_cases[:3]:
            anchors: List[EventRowAnchor] = []
            if c.events:
                e_start = c.events[0]
                e_end = c.events[-1]
                anchors.append(
                    EventRowAnchor(
                        row_index=e_start.row_index,
                        csv_line_number=e_start.row_index + 1,
                        case_id=c.case_id,
                        activity=e_start.activity,
                        timestamp_raw=e_start.timestamp_raw,
                        resource=e_start.resource,
                        source_event_id=e_start.source_event_id,
                        role_in_evidence="TRACE_START",
                    )
                )
                if len(c.events) > 1:
                    anchors.append(
                        EventRowAnchor(
                            row_index=e_end.row_index,
                            csv_line_number=e_end.row_index + 1,
                            case_id=c.case_id,
                            activity=e_end.activity,
                            timestamp_raw=e_end.timestamp_raw,
                            resource=e_end.resource,
                            source_event_id=e_end.source_event_id,
                            role_in_evidence="TRACE_END",
                        )
                    )

            summary = (
                f"Case '{c.case_id}' followed rare variant '{var_id}' with total cycle time {ct:.2f}s "
                f"across sequence: {' -> '.join(c.activity_sequence)}."
            )
            exemplars.append(
                CaseTraceExemplar(
                    case_id=c.case_id,
                    exemplar_metric_value=round(ct, 2),
                    exemplar_metric_description=f"Rare variant ({var_id}) case cycle time",
                    total_case_duration_seconds=round(ct, 2),
                    event_anchors=anchors,
                    trace_summary=summary,
                )
            )

    # 5. DATA_INSTRUMENTATION
    elif opp.archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        policy_desc = (
            "Source data rows excluded from reconstruction sorted by row_index; up to 3 exemplars."
        )
        excluded_events = getattr(getattr(reconstruction, "exclusions", None), "excluded_events", [])
        sorted_excluded = sorted(excluded_events, key=lambda ex: ex.row_index)

        if sorted_excluded:
            for ex in sorted_excluded[:3]:
                raw = ex.raw_values or {}
                anchor = EventRowAnchor(
                    row_index=ex.row_index,
                    csv_line_number=ex.row_index + 1,
                    case_id=ex.case_id,
                    activity=str(raw.get("activity") or "") if raw.get("activity") else None,
                    timestamp_raw=str(raw.get("timestamp") or "") if raw.get("timestamp") else None,
                    resource=str(raw.get("resource") or "") if raw.get("resource") else None,
                    role_in_evidence="EXCLUDED_DATA_ROW",
                )
                summary = (
                    f"Row {ex.row_index} (CSV line {ex.row_index + 1}) excluded: {ex.details} ({ex.issue_type})."
                )
                exemplars.append(
                    CaseTraceExemplar(
                        case_id=ex.case_id or f"ROW_{ex.row_index}",
                        exemplar_metric_value=1.0,
                        exemplar_metric_description=f"Data exclusion issue: {ex.issue_type}",
                        total_case_duration_seconds=None,
                        event_anchors=[anchor],
                        trace_summary=summary,
                    )
                )
        else:
            caveats.append(
                "No individual data row exclusions were logged; discrepancy stems from aggregate "
                "transition duration vs cumulative cycle time accounting."
            )

    if not exemplars and not caveats:
        caveats.append(
            "No complete cases matched the required exemplar criteria; exemplar list is empty."
        )

    return exemplars, policy_desc, caveats


def build_derivations_for_opportunity(
    opp: PrioritisedOpportunity,
    candidate: OpportunityCandidate,
    economics_opp: Optional[OpportunityEconomicsResult],
    weights: PrioritisationWeights,
) -> List[MetricDerivationAudit]:
    """
    Constructs auditable derivations for all mathematical and decision calculations
    governing the prioritised opportunity.
    """
    derivations: List[MetricDerivationAudit] = []

    # 1. OPS_SCORE_V1 (Operational Priority Scoring)
    sb = candidate.score_breakdown
    raw_calc = round(sb.coverage_score + sb.concentration_score, 2)
    ev_str = str(candidate.evidence_strength.value if hasattr(candidate.evidence_strength, "value") else candidate.evidence_strength)
    derivations.append(
        MetricDerivationAudit(
            metric_id="OPS_SCORE_V1",
            formula_expression="final_score = round(raw_score * evidence_weight, 2) where raw_score = round(coverage_score + concentration_score, 2)",
            input_variables={
                "coverage_score": sb.coverage_score,
                "concentration_score": sb.concentration_score,
                "evidence_weight": sb.evidence_weight,
                "evidence_strength": ev_str,
            },
            intermediate_values={
                "raw_score_sum": raw_calc,
                "unquantized_final_score": round(sb.raw_score * sb.evidence_weight, 4),
            },
            output_value=candidate.operational_priority_score,
            quantization_rule="round(x, 2)",
            limitations_and_assumptions=[
                "Operational priority score ranks observed operational patterns solely for operational investigation.",
                "Does not establish avoidability, business value, ROI, savings, or automation readiness.",
            ],
        )
    )

    # 2. ANNUALIZATION_V1
    if economics_opp and economics_opp.observation_window:
        win = economics_opp.observation_window
        method_str = str(win.annualisation_method.value if hasattr(win.annualisation_method, "value") else win.annualisation_method)
        if method_str == "SAMPLE_BASIS_ONLY":
            ann_formula = "None (observation duration < 30 days; annualisation suppressed per Branch 1)"
        elif method_str == "EXPLICIT_OVERRIDE":
            ann_formula = "R_raw = evaluated_case_volume / sample_completed_cases (Branch 3 volume override)"
        elif method_str == "CALENDAR_EXTRAPOLATION":
            ann_formula = "R_raw = 365.25 / observation_duration_days (Branch 2 calendar projection)"
        else:
            ann_formula = "None (unscaled or degenerate window)"

        derivations.append(
            MetricDerivationAudit(
                metric_id="ANNUALIZATION_V1",
                formula_expression=ann_formula,
                input_variables={
                    "observation_duration_days": win.observation_duration_days,
                    "sample_completed_cases": win.sample_completed_cases,
                    "evaluated_case_volume": win.evaluated_case_volume,
                    "annualisation_method": method_str,
                },
                intermediate_values={
                    "annualisation_ratio_raw": win.annualisation_ratio,
                },
                output_value=win.annualisation_ratio,
                quantization_rule="Unrounded IEEE 754 precision retained in calculations; integer presentation rounded half-up",
                limitations_and_assumptions=win.caveats or [
                    "Annualization assumes observed operational sample is representative of full calendar year activity."
                ],
            )
        )

    # 3. LABOR_EFFORT_V1
    if economics_opp and economics_opp.labor_effort:
        lab = economics_opp.labor_effort
        if opp.archetype == OpportunityArchetype.DELAY_COMPRESSION:
            labor_formula = (
                "sample_active_hours = (cumulative_seconds / 3600.0) * (alpha / 100.0); "
                "annual_active_hours = sample_active_hours * R_raw"
            )
            labor_inputs = {
                "cumulative_transition_duration_seconds": candidate.cumulative_time_seconds,
                "active_labor_share_percentage": lab.active_labor_share_percentage,
                "sample_active_labor_hours": lab.sample_active_labor_hours,
                "annual_active_labor_hours": lab.annual_active_labor_hours,
            }
        elif opp.archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
            labor_formula = "None (data quality opportunity; labor hours not defined)"
            labor_inputs = {
                "sample_active_labor_hours": None,
                "annual_active_labor_hours": None,
            }
        else:
            labor_formula = (
                "sample_active_hours = (occurrences * touch_labor_minutes) / 60.0; "
                "annual_active_hours = sample_active_hours * R_raw"
            )
            labor_inputs = {
                "touch_labor_minutes_per_occurrence": lab.touch_labor_minutes_per_occurrence,
                "sample_occurrences": lab.sample_occurrences if lab.sample_occurrences is not None else lab.sample_affected_cases,
                "sample_active_labor_hours": lab.sample_active_labor_hours,
                "annual_active_labor_hours": lab.annual_active_labor_hours,
            }

        derivations.append(
            MetricDerivationAudit(
                metric_id="LABOR_EFFORT_V1",
                formula_expression=labor_formula,
                input_variables=labor_inputs,
                intermediate_values={
                    "sample_active_labor_hours_raw": lab.sample_active_labor_hours,
                    "annualisation_ratio": economics_opp.observation_window.annualisation_ratio if economics_opp.observation_window else None,
                },
                output_value=lab.annual_active_labor_hours,
                quantization_rule="Commercial half-up integer rounding for reported hours; internal IEEE 754 float precision",
                limitations_and_assumptions=lab.caveats or [
                    "Labor effort requires user-provided touch labor estimate; chronological milestone durations are never assumed to be active labor."
                ],
            )
        )

    # 4. CAPACITY_VAL_V1
    if economics_opp and economics_opp.capacity_valuation:
        cap = economics_opp.capacity_valuation
        derivations.append(
            MetricDerivationAudit(
                metric_id="CAPACITY_VAL_V1",
                formula_expression="gross_capacity = annual_addressable_hours * hourly_rate; net_capacity = gross_capacity - annual_recurring_cost",
                input_variables={
                    "hourly_labor_rate": cap.hourly_labor_rate,
                    "gross_annual_capacity_value": cap.gross_annual_capacity_value,
                    "annual_recurring_cost": cap.annual_recurring_cost,
                },
                intermediate_values={
                    "gross_capacity_valuation": cap.gross_annual_capacity_value,
                    "net_annual_capacity_benefit": cap.net_annual_capacity_benefit,
                },
                output_value=cap.net_annual_capacity_benefit,
                quantization_rule="Commercial half-up integer rounding for currency values",
                limitations_and_assumptions=cap.caveats or [
                    "Capacity valuation models liberated staff capacity reallocation scenario; it does not constitute guaranteed cash-flow savings or budget reduction."
                ],
            )
        )

    # 5. PAYBACK_PERIOD_V1
    if economics_opp and economics_opp.cash_flow and economics_opp.capacity_valuation:
        cf = economics_opp.cash_flow
        cap = economics_opp.capacity_valuation
        derivations.append(
            MetricDerivationAudit(
                metric_id="PAYBACK_PERIOD_V1",
                formula_expression="payback_months = (implementation_cost / net_annual_capacity_benefit) * 12.0 (if net benefit > 0 and cost >= 0)",
                input_variables={
                    "implementation_cost": cap.implementation_cost,
                    "net_annual_capacity_benefit": cap.net_annual_capacity_benefit,
                },
                intermediate_values={
                    "cash_roi_available": cf.cash_roi_available,
                    "payback_period_months": cap.payback_period_months,
                },
                output_value=cap.payback_period_months,
                quantization_rule="round(x, 1) if defined else None",
                limitations_and_assumptions=cf.caveats or [
                    "Payback period is based on capacity valuation return; realized financial payback depends on budget recapture."
                ],
            )
        )

    # 6. WEIGHT_REDIST_V1
    base_w = weights.model_dump()
    avail_factors = list(opp.factors.effective_weights.keys())
    sum_avail = sum(base_w.get(f"{k}_weight", 0.0) for k in avail_factors)
    derivations.append(
        MetricDerivationAudit(
            metric_id="WEIGHT_REDIST_V1",
            formula_expression="effective_weight_i = (base_weight_i / sum_available_weights) * 100.0",
            input_variables={
                "base_weights": base_w,
                "available_factors": avail_factors,
            },
            intermediate_values={
                "sum_available_base_weights": round(sum_avail, 4),
            },
            output_value=opp.factors.effective_weights,
            quantization_rule="round(x, 4)",
            limitations_and_assumptions=[
                "Missing factors dynamically redistribute weight across available factors to maintain sum-to-100 without fabricating neutral default scores."
            ],
        )
    )

    # 7. COMPOSITE_SCORE_V1
    derivations.append(
        MetricDerivationAudit(
            metric_id="COMPOSITE_SCORE_V1",
            formula_expression="composite_score_raw = sum(effective_weight_i * factor_score_i) / 100.0; composite_score = round_half_even(composite_score_raw, 4)",
            input_variables={
                "impact_score": opp.factors.impact_score,
                "readiness_score": opp.factors.readiness_score,
                "payback_score": opp.factors.payback_score,
                "effort_score": opp.factors.effort_score,
                "risk_score": opp.factors.risk_score,
                "confidence_score": opp.factors.confidence_score,
                "effective_weights": opp.factors.effective_weights,
            },
            intermediate_values={
                "composite_priority_score_raw": opp.composite_priority_score_raw,
            },
            output_value=opp.composite_priority_score,
            quantization_rule="ROUND_HALF_EVEN to 4 decimal places with positive-zero normalization",
            limitations_and_assumptions=[
                "Composite score is a weighted ranking heuristic; portfolio cohort precedence strictly determines roadmap sequencing."
            ],
        )
    )

    return derivations


def build_epistemic_ledger_for_opportunity(
    opp: PrioritisedOpportunity,
    candidate: OpportunityCandidate,
    economics_opp: Optional[OpportunityEconomicsResult],
    weights: PrioritisationWeights,
    reconstruction: ProcessReconstructionResult,
    detection: ProblemDetectionResult,
) -> List[EpistemicItem]:
    """
    Constructs a structured epistemic ledger classifying all statements and metrics
    associated with this opportunity as FACT, ASSUMPTION, HYPOTHESIS, ESTIMATE, or DECISION.
    """
    ledger: List[EpistemicItem] = []
    opp_id = opp.opportunity_id

    # 1. FACTS (Direct operational log observations and verification checks)
    for idx, fact in enumerate(candidate.observed_facts):
        ledger.append(
            EpistemicItem(
                item_id=f"fact_{opp_id}_obs_{idx+1}",
                epistemic_type=EpistemicType.FACT,
                statement=fact,
                source_or_basis="Direct operational event log reconstruction and milestone sequence aggregation",
                provenance_details=f"Source dataset: {reconstruction.filename}, complete cases: {reconstruction.complete_cases_count}",
            )
        )

    if detection.summary.reconciliation.reconciled:
        ledger.append(
            EpistemicItem(
                item_id=f"fact_{opp_id}_reconciliation",
                epistemic_type=EpistemicType.FACT,
                statement="Accounting reconciliation verified: total transition durations match cumulative cycle time within tolerance.",
                source_or_basis="Timestamp interval accounting check",
                provenance_details="Reconciliation discrepancy is within allowable tolerance (<1.0%)",
            )
        )

    # 2. ASSUMPTIONS (User-provided parameters and default configurations)
    if economics_opp and economics_opp.capacity_valuation and economics_opp.capacity_valuation.hourly_labor_rate is not None:
        rate = economics_opp.capacity_valuation.hourly_labor_rate
        prov = str(economics_opp.capacity_valuation.hourly_labor_rate_provenance.value if hasattr(economics_opp.capacity_valuation.hourly_labor_rate_provenance, "value") else economics_opp.capacity_valuation.hourly_labor_rate_provenance)
        ledger.append(
            EpistemicItem(
                item_id=f"assumption_{opp_id}_labor_rate",
                epistemic_type=EpistemicType.ASSUMPTION,
                statement=f"Fully burdened hourly labor rate assumed at ${rate:.2f}/hr.",
                source_or_basis=f"Economic input parameter ({prov})",
                provenance_details="Provided by process analyst or defaulted to baseline",
            )
        )

    ledger.append(
        EpistemicItem(
            item_id=f"assumption_{opp_id}_weights",
            epistemic_type=EpistemicType.ASSUMPTION,
            statement="Prioritisation factor weights reflect business strategic trade-off preferences.",
            source_or_basis="User-provided weights or approved system defaults summing to 100.0",
            provenance_details=f"Base weights: {weights.model_dump()}",
        )
    )

    # 3. HYPOTHESES (Investigation questions and candidate interventions)
    for idx, hyp in enumerate(candidate.investigation_hypotheses):
        ledger.append(
            EpistemicItem(
                item_id=f"hypothesis_{opp_id}_investigation_{idx+1}",
                epistemic_type=EpistemicType.HYPOTHESIS,
                statement=hyp,
                source_or_basis="Operational opportunity detection heuristic",
                provenance_details="To be validated with operational process owners",
            )
        )

    int_cat = str(candidate.intervention_category.value if hasattr(candidate.intervention_category, "value") else candidate.intervention_category)
    ledger.append(
        EpistemicItem(
            item_id=f"hypothesis_{opp_id}_intervention_candidate",
            epistemic_type=EpistemicType.HYPOTHESIS,
            statement=f"Candidate intervention category: {int_cat}.",
            source_or_basis="Analytical classification of problem pattern",
            provenance_details="Hypothesis for solution design; does not constitute proven remedy",
        )
    )

    # 4. ESTIMATES (Derived mathematical models and extrapolations)
    ledger.append(
        EpistemicItem(
            item_id=f"estimate_{opp_id}_ops_score",
            epistemic_type=EpistemicType.ESTIMATE,
            statement=f"Operational priority score calculated at {candidate.operational_priority_score:.2f}.",
            source_or_basis="Coverage and concentration piecewise scoring formula (OPS_SCORE_V1)",
            provenance_details=f"Score breakdown: {candidate.score_breakdown.model_dump()}",
        )
    )

    if economics_opp and economics_opp.capacity_valuation and economics_opp.capacity_valuation.net_annual_capacity_benefit is not None:
        net_val = economics_opp.capacity_valuation.net_annual_capacity_benefit
        ledger.append(
            EpistemicItem(
                item_id=f"estimate_{opp_id}_net_capacity_benefit",
                epistemic_type=EpistemicType.ESTIMATE,
                statement=f"Annual net capacity benefit modeled at ${net_val:,.0f}.",
                source_or_basis="Annualized labor effort and rate extrapolation scenario (CAPACITY_VAL_V1)",
                provenance_details="Models liberated staff capacity reallocation scenario; cash ROI unavailable",
            )
        )

    if opp.composite_priority_score is not None:
        ledger.append(
            EpistemicItem(
                item_id=f"estimate_{opp_id}_composite_score",
                epistemic_type=EpistemicType.ESTIMATE,
                statement=f"Composite priority score evaluated at {opp.composite_priority_score:.4f}.",
                source_or_basis="Multi-factor weighted average synthesis (COMPOSITE_SCORE_V1)",
                provenance_details=f"Effective weights: {opp.factors.effective_weights}",
            )
        )

    # 5. DECISIONS (Policy classifications, gating evaluations, and roadmap assignments)
    pt_val = str(candidate.priority_tier.value if hasattr(candidate.priority_tier, "value") else candidate.priority_tier)
    ledger.append(
        EpistemicItem(
            item_id=f"decision_{opp_id}_priority_tier",
            epistemic_type=EpistemicType.DECISION,
            statement=f"Assigned operational priority tier '{pt_val}'.",
            source_or_basis="Phase 5 priority tier threshold policy",
            provenance_details=f"Score: {candidate.operational_priority_score:.2f}, evidence: {candidate.evidence_strength}",
        )
    )

    rt_val = str(opp.economics.synthesis.overall_readiness.value if hasattr(opp.economics.synthesis.overall_readiness, "value") else opp.economics.synthesis.overall_readiness)
    ledger.append(
        EpistemicItem(
            item_id=f"decision_{opp_id}_readiness_tier",
            epistemic_type=EpistemicType.DECISION,
            statement=f"Assigned automation readiness tier '{rt_val}'.",
            source_or_basis="Phase 6 non-compensatory readiness gating policy",
            provenance_details="Evaluates system interfaces, business rules, and legal barriers",
        )
    )

    strat_val = str(opp.economics.synthesis.strategic_decision.value if hasattr(opp.economics.synthesis.strategic_decision, "value") else opp.economics.synthesis.strategic_decision)
    ledger.append(
        EpistemicItem(
            item_id=f"decision_{opp_id}_strategic_outcome",
            epistemic_type=EpistemicType.DECISION,
            statement=f"Assigned strategic synthesis outcome '{strat_val}'.",
            source_or_basis="Phase 7 64-cell strategic synthesis decision matrix",
            provenance_details="Synthesizes priority tier, readiness tier, and economic tier",
        )
    )

    coh_val = str(opp.portfolio_cohort.value if hasattr(opp.portfolio_cohort, "value") else opp.portfolio_cohort)
    ledger.append(
        EpistemicItem(
            item_id=f"decision_{opp_id}_cohort_ranking",
            epistemic_type=EpistemicType.DECISION,
            statement=f"Assigned to portfolio cohort '{coh_val}' at rank order {opp.rank_order}.",
            source_or_basis="Phase 8 portfolio cohort precedence and deterministic sort key",
            provenance_details="Precedence governs roadmap sequence before within-cohort score ordering",
        )
    )

    return ledger


def generate_evidence_audit_response(
    content_bytes: bytes,
    filename: str,
    reconstruction: ProcessReconstructionResult,
    analytics: ProcessAnalyticsResult,
    detection: ProblemDetectionResult,
    opportunity_result: OpportunityDetectionResult,
    readiness_result: ReadinessAssessmentResponse,
    economics_result: EconomicsEvaluationResponse,
    prioritisation_result: PrioritisationResponse,
    opportunity_id_filter: Optional[str] = None,
    weights_dict: Optional[Dict[str, float]] = None,
) -> EvidenceAuditResponse:
    """
    Executes the Phase 9 Evidence Engine to generate structured, auditable evidence dossiers
    for prioritised opportunities.
    """
    # 1. Compute Cryptographic Digest of Raw Upload Bytes
    file_sha256 = hashlib.sha256(content_bytes).hexdigest()

    # 2. Build Candidate and Economics Lookup Maps
    candidate_map: Dict[str, OpportunityCandidate] = {
        c.id: c for c in opportunity_result.opportunities
    }
    economics_map: Dict[str, OpportunityEconomicsResult] = {
        e.opportunity_id: e for e in economics_result.opportunities
    }

    # 3. Construct or Default Prioritisation Weights
    if weights_dict is not None:
        weights = PrioritisationWeights(**weights_dict)
    else:
        weights = PrioritisationWeights()

    # 4. Handle Optional Opportunity ID Filtering
    ranked = prioritisation_result.ranked_opportunities
    all_opp_ids = [o.opportunity_id for o in ranked]

    if opportunity_id_filter is not None and opportunity_id_filter.strip():
        clean_filter = opportunity_id_filter.strip()
        if clean_filter not in all_opp_ids:
            raise ValueError(
                f"Opportunity ID '{clean_filter}' not found in prioritised opportunities. "
                f"Valid IDs are: {', '.join(all_opp_ids)}"
            )
        target_ranked = [o for o in ranked if o.opportunity_id == clean_filter]
        filter_str = clean_filter
    else:
        target_ranked = ranked
        filter_str = None

    # 5. Build Dossier for Each Target Opportunity
    dossiers: List[OpportunityEvidenceDossier] = []
    base_limitations = [
        "Operational event logs record milestone timestamps and activity sequences; they do not observe cognitive work, active physical labor, or idle waiting time.",
        "Capacity valuations model theoretical labor reallocation scenarios and do not guarantee realized budget reductions or cash-flow savings.",
        "Identified opportunities and exemplar traces represent observed patterns for operational investigation; they do not prove causation or establish that an observed duration is avoidable.",
        "Roadmap rankings and readiness tiers provide decision support for solution specification and do not authorize automated deployment into production systems.",
    ]

    for opp in target_ranked:
        candidate = candidate_map.get(opp.opportunity_id)
        if candidate is None:
            continue

        econ_opp = economics_map.get(opp.opportunity_id)

        # Extract exemplars
        exemplars, policy_desc, exemplar_caveats = extract_exemplars_for_opportunity(
            opp=opp,
            candidate=candidate,
            reconstruction=reconstruction,
            analytics=analytics,
            detection=detection,
        )

        # Build derivations
        derivations = build_derivations_for_opportunity(
            opp=opp,
            candidate=candidate,
            economics_opp=econ_opp,
            weights=weights,
        )

        # Build epistemic ledger
        ledger = build_epistemic_ledger_for_opportunity(
            opp=opp,
            candidate=candidate,
            economics_opp=econ_opp,
            weights=weights,
            reconstruction=reconstruction,
            detection=detection,
        )

        # Combine limitations
        dossier_limitations = list(base_limitations)
        if exemplar_caveats:
            dossier_limitations.extend(exemplar_caveats)
        if candidate.limitations:
            dossier_limitations.extend(candidate.limitations)

        dossier = OpportunityEvidenceDossier(
            opportunity_id=opp.opportunity_id,
            archetype=opp.archetype,
            portfolio_cohort=opp.portfolio_cohort,
            rank_order=opp.rank_order,
            composite_priority_score=opp.composite_priority_score,
            target_entity=candidate.target_entity,
            exemplars=exemplars,
            exemplar_selection_policy=policy_desc,
            derivations=derivations,
            epistemic_ledger=ledger,
            boundary_limitations=dossier_limitations,
        )
        dossiers.append(dossier)

    # 6. Build Manifest and Summary
    recon_status = "RECONCILED" if detection.summary.reconciliation.reconciled else "DISCREPANCY_DETECTED"
    manifest = EvidenceAuditManifest(
        source_file_sha256=file_sha256,
        source_filename=filename,
        source_file_size_bytes=len(content_bytes),
        total_source_rows=reconstruction.total_source_rows,
        complete_cases_count=reconstruction.complete_cases_count,
        reconciliation_status=recon_status,
        effective_prioritisation_weights=weights.model_dump(),
        formula_version="v1.0",
        is_persisted_snapshot=False,
        notes="Dynamic evidence dossier recomputed on demand from raw operational data and deterministic analysis pipeline. Not a persisted historical snapshot.",
    )

    summary = EvidenceAuditSummary(
        total_opportunities_evaluated=len(ranked),
        dossiers_emitted=len(dossiers),
        filter_applied=filter_str,
        cohort_distribution=prioritisation_result.summary.cohort_distribution,
    )

    return EvidenceAuditResponse(
        manifest=manifest,
        summary=summary,
        dossiers=dossiers,
    )
