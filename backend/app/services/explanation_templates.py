"""
Deterministic, offline explanation engine for ProcessLens Phase 10.
Converts Phase 9 evidence audit dossiers into structured, executive-ready explanations
using pure Python templates, strict epistemic grounding, and zero external dependencies.
"""

from typing import List, Tuple, Optional, Dict, Any

from app.schemas.opportunity import OpportunityArchetype
from app.schemas.prioritisation import PortfolioCohort
from app.schemas.evidence import (
    EpistemicType,
    OpportunityEvidenceDossier,
    EvidenceAuditResponse,
    MetricDerivationAudit,
)
from app.schemas.explanation import (
    ExplanationSource,
    GroundingVerificationStatus,
    GroundingAudit,
    OpportunityExplanation,
    PortfolioExecutiveSummary,
    ExplanationResponse,
)


def _get_derivation(dossier: OpportunityEvidenceDossier, metric_id: str) -> Optional[MetricDerivationAudit]:
    """Retrieves a specific derivation audit record by metric ID."""
    for drv in dossier.derivations:
        if drv.metric_id == metric_id:
            return drv
    return None


def _build_executive_summary(dossier: OpportunityEvidenceDossier) -> str:
    """Constructs a high-level 2-3 sentence overview suitable for operational leadership."""
    cohort_labels = {
        PortfolioCohort.FOUNDATIONAL_DATA_QUALITY: "foundational data quality resolution",
        PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION: "immediate automation specification",
        PortfolioCohort.GUARDRAILED_AUTOMATION: "guardrailed automation with human oversight",
        PortfolioCohort.PROCESS_RESTRUCTURING: "operational process restructuring",
        PortfolioCohort.BUSINESS_CASE_VALIDATION: "business case and economic validation",
        PortfolioCohort.FEASIBILITY_INVESTIGATION: "technical feasibility investigation",
        PortfolioCohort.REVISE_OR_DEFERRED: "deferred consideration",
        PortfolioCohort.BLOCKED_BY_BARRIERS: "blocked status due to operational barriers",
    }
    cohort_desc = cohort_labels.get(dossier.portfolio_cohort, str(dossier.portfolio_cohort.value))
    archetype_title = dossier.archetype.value.replace("_", " ").title()

    score_text = (
        f"with a composite priority score of {dossier.composite_priority_score:.4f}"
        if dossier.composite_priority_score is not None
        else "in an unscored status awaiting economic parameters"
    )

    cap_drv = _get_derivation(dossier, "CAPACITY_VAL_V1")
    econ_summary = ""
    if cap_drv and cap_drv.output_value is not None:
        net_val = float(cap_drv.output_value)
        econ_summary = f" Evaluated capacity modeling projects up to ${net_val:,.0f} in net annual capacity value."
    else:
        econ_summary = " Financial returns remain unmonetized pending labor and cost inputs."

    return (
        f"Opportunity '{dossier.opportunity_id}' addresses a {archetype_title} pattern on target '{dossier.target_entity}'. "
        f"It is ranked #{dossier.rank_order} in the portfolio roadmap {score_text}, designated for {cohort_desc}."
        f"{econ_summary}"
    )


def _build_operational_problem_narrative(
    dossier: OpportunityEvidenceDossier,
) -> Tuple[str, List[str], List[str]]:
    """
    Constructs a concrete description of the observed operational pattern,
    referencing real exemplar traces and transition measurements.
    Returns (narrative, verified_numbers, verified_entities).
    """
    numbers: List[str] = []
    entities: List[str] = [dossier.target_entity]

    exemplar_count = len(dossier.exemplars)
    numbers.append(str(exemplar_count))

    if dossier.archetype == OpportunityArchetype.DELAY_COMPRESSION:
        narrative_parts = [
            f"Analysis of operational event traces identifies an elapsed milestone delay across transition '{dossier.target_entity}'."
        ]
        if " -> " in dossier.target_entity:
            s_act, t_act = dossier.target_entity.split(" -> ", 1)
            entities.extend([s_act, t_act])

        if dossier.exemplars:
            narrative_parts.append(
                f"Evaluation inspected {exemplar_count} exemplar trace(s) demonstrating significant milestone elapsed duration:"
            )
            for ex in dossier.exemplars:
                numbers.append(str(ex.exemplar_metric_value))
                if ex.total_case_duration_seconds is not None:
                    numbers.append(str(ex.total_case_duration_seconds))
                narrative_parts.append(
                    f"- Case '{ex.case_id}': elapsed transition duration of {ex.exemplar_metric_value:.2f}s "
                    f"(case total cycle time: {ex.total_case_duration_seconds or 0.0:.2f}s)."
                )
        else:
            narrative_parts.append(
                "No individual completed case traces met the exemplar duration threshold; pattern is based on aggregate transition statistics."
            )

        narrative_parts.append(
            "Note: Timestamp intervals reflect elapsed chronological time between logged milestones; they do not distinguish active touch labor from idle queue or wait time."
        )

    elif dossier.archetype == OpportunityArchetype.RECURRENCE_REDUCTION:
        narrative_parts = [
            f"Analysis identifies repeated execution loops for activity '{dossier.target_entity}' within individual case traces."
        ]
        if dossier.exemplars:
            narrative_parts.append(
                f"Inspection of {exemplar_count} exemplar trace(s) revealed repeated activity executions at distinct timestamps:"
            )
            for ex in dossier.exemplars:
                numbers.append(str(int(ex.exemplar_metric_value)))
                if ex.total_case_duration_seconds is not None:
                    numbers.append(str(ex.total_case_duration_seconds))
                narrative_parts.append(
                    f"- Case '{ex.case_id}': executed '{dossier.target_entity}' {int(ex.exemplar_metric_value)} times at distinct timestamps "
                    f"(case total cycle time: {ex.total_case_duration_seconds or 0.0:.2f}s)."
                )
        else:
            narrative_parts.append(
                "No individual case traces with multi-instance timestamps were isolated; pattern represents aggregate recurrence concentration."
            )

        narrative_parts.append(
            "Repeated activity executions at distinct timestamps indicate operational rework, clarification loops, or iterative data corrections."
        )

    elif dossier.archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION:
        narrative_parts = [
            f"Analysis reveals extreme cycle-time dispersion and statistical tail latency across '{dossier.target_entity}'."
        ]
        if dossier.exemplars:
            narrative_parts.append(
                f"The following {exemplar_count} outlier trace(s) exceeded the cycle-time upper fence threshold:"
            )
            for ex in dossier.exemplars:
                numbers.append(str(ex.exemplar_metric_value))
                narrative_parts.append(
                    f"- Case '{ex.case_id}': recorded extreme cycle time of {ex.exemplar_metric_value:.2f}s."
                )
        else:
            narrative_parts.append(
                "No individual case traces exceeded the statistical Tukey upper fence; variance pattern is distributed across the cycle-time distribution."
            )

        narrative_parts.append(
            "Extreme outlier durations skew process predictability and typically stem from unstandardized exception handling or external dependencies."
        )

    elif dossier.archetype == OpportunityArchetype.PATH_STANDARDIZATION:
        narrative_parts = [
            f"Process mining indicates structural routing variation and rare process pathways for '{dossier.target_entity}'."
        ]
        if dossier.exemplars:
            narrative_parts.append(
                f"Identified {exemplar_count} exemplar case(s) executing non-standard, low-frequency variant routes (<2% frequency):"
            )
            for ex in dossier.exemplars:
                numbers.append(str(ex.exemplar_metric_value))
                narrative_parts.append(
                    f"- Case '{ex.case_id}': executed rare pathway with cycle time {ex.exemplar_metric_value:.2f}s."
                )
        else:
            narrative_parts.append(
                "No individual rare variant cases were isolated in the sample; routing variance is reflected across variant frequency distributions."
            )

        narrative_parts.append(
            "Low-frequency custom pathways create process fragmentation, training overhead, and unpredictable execution quality."
        )

    elif dossier.archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        narrative_parts = [
            f"Foundational data quality assessment identified tracking limitations in '{dossier.target_entity}'."
        ]
        if dossier.exemplars:
            narrative_parts.append(
                f"Identified {exemplar_count} excluded source row anchor(s) due to missing fields or timestamp parsing defects:"
            )
            for ex in dossier.exemplars:
                anchors = ex.event_anchors
                if anchors:
                    anc = anchors[0]
                    numbers.extend([str(anc.row_index), str(anc.csv_line_number)])
                    narrative_parts.append(
                        f"- Data Row {anc.row_index} (CSV line {anc.csv_line_number}): excluded from reconstruction due to tracking defects."
                    )
                else:
                    narrative_parts.append(f"- Case reference '{ex.case_id}': excluded data row.")
        else:
            narrative_parts.append(
                "No individual row exclusions were recorded; discrepancy stems from aggregate milestone duration reconciliation."
            )

        narrative_parts.append(
            "Accurate process mining and reliable automation depend on complete, valid event telemetry; data defects must be resolved first."
        )
    else:
        narrative_parts = [
            f"Operational pattern observed for target '{dossier.target_entity}' under archetype '{dossier.archetype.value}'."
        ]

    narrative = " ".join(narrative_parts)
    return narrative, numbers, entities


def _build_economic_interpretation(
    dossier: OpportunityEvidenceDossier,
) -> Tuple[str, List[str]]:
    """
    Constructs transparent economic interpretation explaining labor hours,
    capacity valuation, and cost parameters, with strict non-additive caveats.
    Returns (economic_text, verified_numbers).
    """
    numbers: List[str] = []
    cap_drv = _get_derivation(dossier, "CAPACITY_VAL_V1")
    labor_drv = _get_derivation(dossier, "LABOR_EFFORT_V1")
    payback_drv = _get_derivation(dossier, "PAYBACK_PERIOD_V1")

    if not cap_drv or cap_drv.output_value is None:
        text = (
            "Economic inputs were not supplied for this opportunity. Annualized labor hours, gross capacity value, "
            "net annual benefit, and payback period remain unknown and unmonetized. Prioritization for this opportunity "
            "relies solely on operational frequency and concentration heuristics. To model financial return, provide "
            "hourly labor rates, touch times, and implementation cost estimates."
        )
        return text, numbers

    net_val = float(cap_drv.output_value)
    gross_val = float(cap_drv.intermediate_values.get("gross_capacity_valuation", net_val))
    rate = cap_drv.input_variables.get("hourly_labor_rate")
    rec_cost = cap_drv.input_variables.get("annual_recurring_cost", 0.0)
    impl_cost = payback_drv.input_variables.get("implementation_cost") if payback_drv else None
    payback_months = payback_drv.output_value if payback_drv else None

    numbers.append(str(round(net_val)))
    numbers.append(str(round(gross_val)))

    labor_hours_str = ""
    if labor_drv and labor_drv.output_value is not None:
        ann_hours = float(labor_drv.output_value)
        numbers.append(str(round(ann_hours)))
        labor_hours_str = f" Liberating an estimated {ann_hours:,.0f} annual active labor hours"
    else:
        labor_hours_str = " Liberating an unquantified volume of active labor hours"

    rate_str = f" at an assumed rate of ${float(rate):.2f}/hr" if rate is not None else ""
    if rate is not None:
        numbers.append(str(round(float(rate), 2)))

    cost_str = f", less ${float(rec_cost):,.0f} in annual recurring maintenance" if rec_cost else ""
    if rec_cost:
        numbers.append(str(round(float(rec_cost))))

    payback_str = ""
    if payback_months is not None:
        numbers.append(str(round(float(payback_months), 1)))
        if impl_cost is not None:
            numbers.append(str(round(float(impl_cost))))
            payback_str = (
                f" Based on an upfront implementation investment of ${float(impl_cost):,.0f}, "
                f"the estimated capacity payback period is {float(payback_months):.1f} months."
            )
        else:
            payback_str = f" The estimated capacity payback period is {float(payback_months):.1f} months."
    elif impl_cost is not None:
        numbers.append(str(round(float(impl_cost))))
        payback_str = f" Implementation cost is estimated at ${float(impl_cost):,.0f}, with payback undefined due to non-positive net benefit."

    disclaimer = (
        " Crucially, capacity valuation models liberated staff time redirected to other productive work; "
        "it does not constitute guaranteed cash savings or payroll budget reductions."
    )

    text = (
        f"Economic valuation models ${gross_val:,.0f} in gross annual capacity value{rate_str}{labor_hours_str}{cost_str}, "
        f"yielding a net annual capacity benefit of ${net_val:,.0f}.{payback_str}{disclaimer}"
    )
    return text, numbers


def _build_strategic_rationale(
    dossier: OpportunityEvidenceDossier,
) -> Tuple[str, List[str], List[str]]:
    """
    Explains cohort assignment, rank order, and strategic portfolio placement.
    Returns (strategic_text, verified_numbers, verified_entities).
    """
    numbers: List[str] = [str(dossier.rank_order)]
    entities: List[str] = [dossier.portfolio_cohort.value]

    score_str = ""
    if dossier.composite_priority_score is not None:
        numbers.append(str(dossier.composite_priority_score))
        score_str = f" with a composite priority score of {dossier.composite_priority_score:.4f}"
    else:
        score_str = " (unscored due to missing economic or domain inputs)"

    cohort_rationales = {
        PortfolioCohort.FOUNDATIONAL_DATA_QUALITY: (
            "under foundational data quality precedence, event log tracking and data reconciliation gaps must be resolved "
            "before committing resources to downstream automation."
        ),
        PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION: (
            "strong operational concentration, high system readiness, and compelling capacity return make this "
            "an immediate candidate for technical specification and automation deployment."
        ),
        PortfolioCohort.GUARDRAILED_AUTOMATION: (
            "favorable return indicators warrant automation, but operational complexity requires human-in-the-loop "
            "guardrails and exception oversight."
        ),
        PortfolioCohort.PROCESS_RESTRUCTURING: (
            "operational friction stems from upstream process design or policy variation, requiring operational workflow "
            "redesign rather than isolated task automation."
        ),
        PortfolioCohort.BUSINESS_CASE_VALIDATION: (
            "operational friction is evident, but financial return or implementation cost assumptions require empirical "
            "validation before allocating capital."
        ),
        PortfolioCohort.FEASIBILITY_INVESTIGATION: (
            "technical readiness or interface constraints require discovery and architectural investigation prior to solutioning."
        ),
        PortfolioCohort.REVISE_OR_DEFERRED: (
            "low operational priority or unviable return warrants deferring this opportunity from the active roadmap."
        ),
        PortfolioCohort.BLOCKED_BY_BARRIERS: (
            "regulatory, system, or operational barriers prohibit automation intervention at this time."
        ),
    }

    cohort_explanation = cohort_rationales.get(
        dossier.portfolio_cohort, "portfolio governance determines sequencing based on strategic criteria."
    )

    text = (
        f"Ranked #{dossier.rank_order} in the portfolio roadmap{score_str} and assigned to cohort '{dossier.portfolio_cohort.value}'. "
        f"Under portfolio governance rules, {cohort_explanation}"
    )
    return text, numbers, entities


def _build_key_assumptions_and_risks(dossier: OpportunityEvidenceDossier) -> List[str]:
    """
    Extracts assumptions, hypotheses, estimates, and boundary limitations from the dossier.
    Strictly preserves epistemic labels to prevent confusion between facts and projections.
    """
    items: List[str] = []

    for item in dossier.epistemic_ledger:
        if item.epistemic_type == EpistemicType.ASSUMPTION:
            items.append(f"[ASSUMPTION] {item.statement}")
        elif item.epistemic_type == EpistemicType.HYPOTHESIS:
            items.append(f"[HYPOTHESIS] {item.statement}")
        elif item.epistemic_type == EpistemicType.ESTIMATE:
            items.append(f"[ESTIMATE] {item.statement}")

    for limit in dossier.boundary_limitations:
        items.append(f"[LIMITATION] {limit}")

    return items


def _build_investigation_next_steps(dossier: OpportunityEvidenceDossier) -> List[str]:
    """
    Generates actionable, concrete next steps for human operations managers
    based on the opportunity archetype and cohort governance.
    """
    steps: List[str] = []

    if dossier.archetype == OpportunityArchetype.DELAY_COMPRESSION:
        steps.append(
            f"Conduct direct operational observation of transition '{dossier.target_entity}' to distinguish active touch time from queue waiting or batching."
        )
        steps.append(
            "Review workstation handover protocols and resource availability logs during peak delay periods."
        )
        steps.append(
            "Evaluate whether upstream task output formats cause downstream processing pauses."
        )

    elif dossier.archetype == OpportunityArchetype.RECURRENCE_REDUCTION:
        steps.append(
            f"Review cases exhibiting multiple instances of '{dossier.target_entity}' with frontline staff to categorize reasons for rework."
        )
        steps.append(
            "Audit initial submission quality to determine if input validation errors trigger reprocessing loops."
        )
        steps.append(
            "Determine whether repeat activity executions represent genuine errors or legitimate iterative collaboration."
        )

    elif dossier.archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION:
        steps.append(
            "Examine outlier case files exceeding the upper fence cycle-time threshold for external hold codes or supply delays."
        )
        steps.append(
            "Assess escalation pathways to determine why extreme cases bypassed standard processing windows."
        )
        steps.append(
            "Establish SLA alert triggers to intervene before cases drift into severe tail latency."
        )

    elif dossier.archetype == OpportunityArchetype.PATH_STANDARDIZATION:
        steps.append(
            "Interview operational teams following rare pathways to identify whether custom routing addresses unique business requirements or represents procedural drift."
        )
        steps.append(
            "Assess compliance and quality risks associated with non-standard routing paths."
        )
        steps.append(
            "Update Standard Operating Procedures (SOPs) and system routing rules to steer work onto the primary path."
        )

    elif dossier.archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        steps.append(
            "Audit event ingestion extract pipelines to resolve missing fields and timestamp parsing defects."
        )
        steps.append(
            "Verify system clock synchronization across disparate logging servers."
        )
        steps.append(
            "Implement schema validation checks at ingestion to prevent incomplete records from reaching analytics."
        )

    # Cohort-specific governance step
    if dossier.portfolio_cohort == PortfolioCohort.BUSINESS_CASE_VALIDATION:
        steps.append(
            "Collect empirical touch-labor measurements and vendor implementation quotes to populate missing economic parameters."
        )
    elif dossier.portfolio_cohort == PortfolioCohort.FEASIBILITY_INVESTIGATION:
        steps.append(
            "Conduct technical API discovery to assess system interface readiness and data extraction feasibility."
        )
    elif dossier.portfolio_cohort == PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION:
        steps.append(
            "Draft functional automation specification detailing exception handling, input schemas, and expected throughput."
        )

    return steps


def generate_opportunity_explanation(
    dossier: OpportunityEvidenceDossier,
) -> OpportunityExplanation:
    """
    Generates a deterministic, structured executive explanation for a single opportunity evidence dossier.
    Grounded strictly in observed data and epistemic ledger records.
    """
    exec_summary = _build_executive_summary(dossier)
    problem_narrative, prob_nums, prob_ents = _build_operational_problem_narrative(dossier)
    econ_text, econ_nums = _build_economic_interpretation(dossier)
    strat_text, strat_nums, strat_ents = _build_strategic_rationale(dossier)
    assumptions_risks = _build_key_assumptions_and_risks(dossier)
    next_steps = _build_investigation_next_steps(dossier)

    return OpportunityExplanation(
        opportunity_id=dossier.opportunity_id,
        archetype=dossier.archetype,
        portfolio_cohort=dossier.portfolio_cohort,
        rank_order=dossier.rank_order,
        composite_priority_score=dossier.composite_priority_score,
        target_entity=dossier.target_entity,
        executive_summary=exec_summary,
        operational_problem_narrative=problem_narrative,
        economic_interpretation=econ_text,
        strategic_rationale=strat_text,
        key_assumptions_and_risks=assumptions_risks,
        investigation_next_steps=next_steps,
        grounding_audit=None,
    )


def generate_portfolio_executive_summary(
    dossiers: List[OpportunityEvidenceDossier],
) -> PortfolioExecutiveSummary:
    """
    Synthesizes a portfolio-level executive briefing across all evaluated opportunities.
    Maintains strict ordering, cohort precedence, and non-additive economic boundaries.
    """
    total_count = len(dossiers)
    if total_count == 0:
        return PortfolioExecutiveSummary(
            overall_narrative="No improvement opportunities were detected in the evaluated process log.",
            top_recommended_actions=["Review event log ingestion parameters or expand observation timeframe."],
            foundational_prerequisites=["Ensure event logs contain complete case sequences and valid timestamps."],
            portfolio_economics_caveat="No capacity valuation models are active.",
        )

    # Tally cohorts
    cohort_counts: Dict[str, int] = {}
    for d in dossiers:
        c_val = d.portfolio_cohort.value
        cohort_counts[c_val] = cohort_counts.get(c_val, 0) + 1

    cohort_summary_parts = [f"{count} in '{cohort}'" for cohort, count in sorted(cohort_counts.items())]
    cohort_summary_str = ", ".join(cohort_summary_parts)

    top_dossier = dossiers[0]
    overall_narrative = (
        f"Evaluated {total_count} operational opportunity candidate(s) across the process lifecycle ({cohort_summary_str}). "
        f"Roadmap sequencing is led by opportunity '{top_dossier.opportunity_id}' targeting '{top_dossier.target_entity}' "
        f"assigned to cohort '{top_dossier.portfolio_cohort.value}' at rank #1."
    )

    # Top recommended actions (first 3 actionable opportunities)
    top_actions: List[str] = []
    actionable_cohorts = {
        PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,
        PortfolioCohort.GUARDRAILED_AUTOMATION,
        PortfolioCohort.PROCESS_RESTRUCTURING,
        PortfolioCohort.BUSINESS_CASE_VALIDATION,
        PortfolioCohort.FEASIBILITY_INVESTIGATION,
    }
    actionable_dossiers = [d for d in dossiers if d.portfolio_cohort in actionable_cohorts]

    for d in actionable_dossiers[:3]:
        score_info = f" (score: {d.composite_priority_score:.4f})" if d.composite_priority_score is not None else ""
        top_actions.append(
            f"Rank #{d.rank_order} [{d.portfolio_cohort.value}]: Advance '{d.opportunity_id}' targeting '{d.target_entity}'{score_info}."
        )

    if not top_actions:
        top_actions.append(
            f"Review top-ranked opportunity '{top_dossier.opportunity_id}' in cohort '{top_dossier.portfolio_cohort.value}'."
        )

    # Foundational prerequisites (Cohort 1 or data reconciliation)
    data_quality_opps = [d for d in dossiers if d.portfolio_cohort == PortfolioCohort.FOUNDATIONAL_DATA_QUALITY]
    prerequisites: List[str] = []
    if data_quality_opps:
        for dq in data_quality_opps:
            prerequisites.append(
                f"Prerequisite: Resolve data tracking defects in '{dq.target_entity}' (Opportunity '{dq.opportunity_id}') before automating dependent workflow stages."
            )
    else:
        prerequisites.append(
            "Event log telemetry satisfies baseline tracking consistency; no blocking data quality prerequisites were identified."
        )

    # Portfolio economics caveat (mandatory non-additive disclaimer)
    econ_caveat = (
        "Opportunity-level capacity valuations reflect isolated labor reallocation scenarios and may overlap across shared workflow steps. "
        "Estimated capacity values are non-additive and must NOT be summed across opportunities as cumulative portfolio savings or guaranteed financial budget reductions."
    )

    return PortfolioExecutiveSummary(
        overall_narrative=overall_narrative,
        top_recommended_actions=top_actions,
        foundational_prerequisites=prerequisites,
        portfolio_economics_caveat=econ_caveat,
    )


def generate_deterministic_explanation_response(
    audit_response: EvidenceAuditResponse,
    execution_duration_seconds: float = 0.0,
) -> ExplanationResponse:
    """
    Main entry point for deterministic template explanation generation.
    Converts full Phase 9 EvidenceAuditResponse into a structured ExplanationResponse.
    """
    explanations = [
        generate_opportunity_explanation(dossier) for dossier in audit_response.dossiers
    ]
    portfolio_summary = generate_portfolio_executive_summary(audit_response.dossiers)

    return ExplanationResponse(
        manifest=audit_response.manifest,
        portfolio_summary=portfolio_summary,
        explanations=explanations,
        explanation_source=ExplanationSource.DETERMINISTIC_TEMPLATE,
        model_identifier=None,
        execution_duration_seconds=execution_duration_seconds,
    )
