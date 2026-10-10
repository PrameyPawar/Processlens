"""
Deterministic domain service for Phase 6 Automation Readiness Assessment.
Evaluates opportunity candidates across six orthogonal dimensions, strictly separating
empirical event-log observations from domain-provided technical and governance intakes.
Enforces non-compensatory outcome precedence without arbitrary numeric scores.
"""

import json
from typing import List, Dict, Any, Optional, Set
from pydantic import ValidationError

from app.schemas.detection import EvidenceStrength
from app.schemas.opportunity import (
    OpportunityCandidate,
    OpportunityDetectionResult,
)
from app.schemas.readiness import (
    DimensionState,
    OverallReadinessTier,
    EvidenceProvenance,
    DigitalDataFormat,
    SystemInterfaceType,
    RuleDeterminism,
    HumanSupervisionRequirement,
    GovernanceConstraint,
    OpportunityDomainAssessmentInput,
    ReadinessDiscrepancy,
    DimensionDetail,
    OpportunityReadinessResult,
    ReadinessSummary,
    ReadinessAssessmentResponse,
)


def parse_domain_assessments_json(
    raw_json: Optional[str],
) -> Optional[List[OpportunityDomainAssessmentInput]]:
    """
    Parses and validates a JSON string representing a list of domain assessments.
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
        raise ValueError(f"Invalid JSON format in domain_assessments: {str(e)}")

    if not isinstance(data, list):
        raise ValueError("domain_assessments must be a JSON array of assessment objects.")

    parsed_inputs: List[OpportunityDomainAssessmentInput] = []
    for idx, item in enumerate(data):
        if not isinstance(item, dict):
            raise ValueError(f"Item at index {idx} in domain_assessments must be a JSON object.")
        try:
            parsed_inputs.append(OpportunityDomainAssessmentInput.model_validate(item))
        except ValidationError as e:
            raise ValueError(f"Validation error in domain_assessments at index {idx}: {str(e)}")

    return parsed_inputs


def assess_single_opportunity_readiness(
    opportunity: OpportunityCandidate,
    domain_input: Optional[OpportunityDomainAssessmentInput],
) -> OpportunityReadinessResult:
    """
    Deterministically evaluates automation readiness for a single OpportunityCandidate.
    Applies non-compensatory precedence:
      1. PROHIBITED_OR_BLOCKED (established prohibition)
      2. INSUFFICIENT_CRITICAL_EVIDENCE (missing critical domain intake or limited sample)
      3. PREREQUISITES_REQUIRED (prerequisites or controls needed)
      4. READY_FOR_SPECIFICATION (all dimensions favorable)
    """
    discrepancies: List[ReadinessDiscrepancy] = []
    hard_blockers: List[str] = []
    prerequisites: List[str] = []
    limitations: List[str] = [
        "Specification readiness indicates suitability for detailed technical specification and solution design; it does NOT authorize production deployment.",
        "Event log metrics capture empirical process characteristics; they do not establish business rule stability, software API access, or legal feasibility.",
        "Domain assessment inputs reflect user-reported architecture; technical interface verification and authentication testing are required during solution design.",
    ]

    has_domain = domain_input is not None

    # -------------------------------------------------------------------------
    # Dimension 1: Task Repeatability & Rule Stability
    # -------------------------------------------------------------------------
    d1_facts: List[str] = []
    d1_assumptions: List[str] = []
    d1_prereqs: List[str] = []
    d1_blockers: List[str] = []

    case_count = opportunity.affected_case_count
    case_pct = opportunity.affected_case_percentage
    occ_count = opportunity.occurrence_count

    # Provisional empirical volume heuristic
    d1_facts.append(
        f"Empirical observation: executed {occ_count} times across {case_count} complete cases ({case_pct:.1f}%)."
    )

    rule_det = domain_input.rule_determinism if has_domain else RuleDeterminism.UNKNOWN
    if rule_det == RuleDeterminism.DETERMINISTIC_RULES:
        d1_facts.append("Domain confirmed: task follows clear, documented IF-THEN rules.")
        if opportunity.evidence_strength == EvidenceStrength.LIMITED:
            d1_state = DimensionState.INSUFFICIENT_EVIDENCE
            d1_assumptions.append("Empirical volume is limited (<10 cases), preventing statistical confirmation of path consistency.")
        else:
            d1_state = DimensionState.FAVORABLE
    elif rule_det == RuleDeterminism.MIXED_RULES:
        d1_state = DimensionState.PREREQUISITE_REQUIRED
        d1_prereq_msg = "Codify and standardize edge-case business rules into deterministic decision tables."
        d1_prereqs.append(d1_prereq_msg)
        prerequisites.append(d1_prereq_msg)
    elif rule_det == RuleDeterminism.DISCRETIONARY:
        d1_state = DimensionState.PREREQUISITE_REQUIRED
        d1_prereq_msg = "Design an assistive decision-support workflow; task requires subjective discretion and cannot be fully unattended."
        d1_prereqs.append(d1_prereq_msg)
        prerequisites.append(d1_prereq_msg)
    else:  # UNKNOWN
        d1_state = DimensionState.UNKNOWN
        d1_assumptions.append("Business rule stability and determinism have not been assessed.")

    dim_repeatability = DimensionDetail(
        dimension_name="task_repeatability_and_rule_stability",
        state=d1_state,
        provenance=EvidenceProvenance.COMPUTED_SYNTHESIS if has_domain and rule_det != RuleDeterminism.UNKNOWN else EvidenceProvenance.LOG_MEASURED,
        observed_facts=d1_facts,
        assumptions=d1_assumptions,
        prerequisites=d1_prereqs,
        blockers=d1_blockers,
    )

    # -------------------------------------------------------------------------
    # Dimension 2: Digital Inputs & Outputs
    # -------------------------------------------------------------------------
    d2_facts: List[str] = []
    d2_assumptions: List[str] = []
    d2_prereqs: List[str] = []
    d2_blockers: List[str] = []

    data_format = domain_input.digital_data_format if has_domain else DigitalDataFormat.UNKNOWN
    if data_format == DigitalDataFormat.STRUCTURED_DIGITAL:
        d2_state = DimensionState.FAVORABLE
        d2_facts.append("Domain confirmed: task inputs and outputs are structured digital records (database/API/EDI).")
    elif data_format == DigitalDataFormat.SEMI_STRUCTURED:
        d2_state = DimensionState.PREREQUISITE_REQUIRED
        d2_prereq_msg = "Implement automated document extraction (OCR/Document AI) and schema validation for semi-structured documents (e.g. PDFs, emails)."
        d2_prereqs.append(d2_prereq_msg)
        prerequisites.append(d2_prereq_msg)
    elif data_format == DigitalDataFormat.UNSTRUCTURED_OR_PAPER:
        d2_state = DimensionState.PREREQUISITE_REQUIRED
        d2_prereq_msg = "Digitize physical paperwork, mail, or phone intake into electronic records prior to automation."
        d2_prereqs.append(d2_prereq_msg)
        prerequisites.append(d2_prereq_msg)
    else:  # UNKNOWN
        d2_state = DimensionState.UNKNOWN
        d2_assumptions.append("Digital structure of inputs and handoff payloads has not been assessed.")

    dim_digital = DimensionDetail(
        dimension_name="digital_inputs_and_outputs",
        state=d2_state,
        provenance=EvidenceProvenance.DOMAIN_INPUT if has_domain and data_format != DigitalDataFormat.UNKNOWN else EvidenceProvenance.DEFAULT_UNKNOWN,
        observed_facts=d2_facts,
        assumptions=d2_assumptions,
        prerequisites=d2_prereqs,
        blockers=d2_blockers,
    )

    # -------------------------------------------------------------------------
    # Dimension 3: System Interface Accessibility
    # -------------------------------------------------------------------------
    d3_facts: List[str] = []
    d3_assumptions: List[str] = []
    d3_prereqs: List[str] = []
    d3_blockers: List[str] = []

    sys_interface = domain_input.system_interface if has_domain else SystemInterfaceType.UNKNOWN
    if sys_interface == SystemInterfaceType.DIRECT_API_OR_DB:
        d3_state = DimensionState.FAVORABLE
        d3_facts.append("Domain confirmed: documented direct REST/SOAP API or database hook is available.")
    elif sys_interface == SystemInterfaceType.ACCESSIBLE_GUI:
        d3_state = DimensionState.PREREQUISITE_REQUIRED
        d3_prereq_msg = "Develop and test desktop/web UI automation (RPA) connector with robust selector resilience."
        d3_prereqs.append(d3_prereq_msg)
        prerequisites.append(d3_prereq_msg)
    elif sys_interface == SystemInterfaceType.RESTRICTED_OR_AIRGAPPED:
        d3_state = DimensionState.PREREQUISITE_REQUIRED
        d3_prereq_msg = "Establish secure gateway access, virtual desktop integration, or network clearance for automated service."
        d3_prereqs.append(d3_prereq_msg)
        prerequisites.append(d3_prereq_msg)
    elif sys_interface == SystemInterfaceType.PROHIBITED_ACCESS:
        d3_state = DimensionState.PROHIBITIVE_BARRIER
        d3_block_msg = "Vendor licensing, enterprise security policy, or legal terms strictly prohibit automated interface access."
        d3_blockers.append(d3_block_msg)
        hard_blockers.append(d3_block_msg)
    else:  # UNKNOWN
        d3_state = DimensionState.UNKNOWN
        d3_assumptions.append("System interface accessibility has not been assessed.")

    dim_interface = DimensionDetail(
        dimension_name="system_interface_accessibility",
        state=d3_state,
        provenance=EvidenceProvenance.DOMAIN_INPUT if has_domain and sys_interface != SystemInterfaceType.UNKNOWN else EvidenceProvenance.DEFAULT_UNKNOWN,
        observed_facts=d3_facts,
        assumptions=d3_assumptions,
        prerequisites=d3_prereqs,
        blockers=d3_blockers,
    )

    # -------------------------------------------------------------------------
    # Dimension 4: Exception Frequency & Human Judgment
    # -------------------------------------------------------------------------
    d4_facts: List[str] = []
    d4_assumptions: List[str] = []
    d4_prereqs: List[str] = []
    d4_blockers: List[str] = []

    rec_pct = opportunity.recurrence_case_percentage or 0.0
    out_pct = opportunity.outlier_case_percentage or 0.0
    var_pct = opportunity.variant_case_percentage or 0.0

    d4_facts.append(
        f"Empirical indicators: {rec_pct:.1f}% recurrence prevalence, {out_pct:.1f}% outlier share, {var_pct:.1f}% rare variant share."
    )

    supervision = domain_input.supervision_requirement if has_domain else HumanSupervisionRequirement.UNKNOWN
    if supervision == HumanSupervisionRequirement.UNATTENDED_FEASIBLE:
        # Check for contradictory evidence between unattended claim and empirical event data
        has_empirical_repetition = rec_pct >= 20.0
        has_empirical_outliers = out_pct >= 10.0
        has_empirical_variants = var_pct >= 30.0

        if has_empirical_repetition or has_empirical_outliers or has_empirical_variants:
            d4_state = DimensionState.PREREQUISITE_REQUIRED
            reasons = []
            if has_empirical_repetition:
                reasons.append(f"{rec_pct:.1f}% activity recurrence")
            if has_empirical_outliers:
                reasons.append(f"{out_pct:.1f}% cycle-time outliers")
            if has_empirical_variants:
                reasons.append(f"{var_pct:.1f}% rare variants")
            evidence_str = ", ".join(reasons)

            disc = ReadinessDiscrepancy(
                dimension="exception_frequency_and_judgment",
                domain_claim="Domain assessed task as suitable for unattended execution without human supervision.",
                observed_event_evidence=f"Event log exhibits notable process variation: {evidence_str}.",
                reconciliation_guidance=(
                    "Review whether repeated executions or path variations represent legitimate multi-pass procedures "
                    "or uncaptured process defects before specifying straight-through unattended automation."
                ),
            )
            discrepancies.append(disc)
            d4_prereq_msg = "Reconcile empirical process variation with unattended claim; define exception fallback procedures."
            d4_prereqs.append(d4_prereq_msg)
            prerequisites.append(d4_prereq_msg)
        else:
            d4_state = DimensionState.FAVORABLE
            d4_facts.append("Domain confirmed: routine task with low human discretion; supported by low empirical variation.")
    elif supervision == HumanSupervisionRequirement.HUMAN_IN_THE_LOOP:
        d4_state = DimensionState.PREREQUISITE_REQUIRED
        d4_prereq_msg = "Design human-in-the-loop review interface and supervisor approval checkpoints for exception handling."
        d4_prereqs.append(d4_prereq_msg)
        prerequisites.append(d4_prereq_msg)
    elif supervision == HumanSupervisionRequirement.EXCLUSIVELY_HUMAN:
        d4_state = DimensionState.PREREQUISITE_REQUIRED
        d4_prereq_msg = "Keep primary task execution strictly human; restrict automation candidates to non-discretionary preparatory tasks."
        d4_prereqs.append(d4_prereq_msg)
        prerequisites.append(d4_prereq_msg)
    else:  # UNKNOWN
        d4_state = DimensionState.UNKNOWN
        d4_assumptions.append("Required human supervision level and discretionary judgment have not been assessed.")

    dim_judgment = DimensionDetail(
        dimension_name="exception_frequency_and_judgment",
        state=d4_state,
        provenance=EvidenceProvenance.COMPUTED_SYNTHESIS if has_domain and supervision != HumanSupervisionRequirement.UNKNOWN else EvidenceProvenance.LOG_MEASURED,
        observed_facts=d4_facts,
        assumptions=d4_assumptions,
        prerequisites=d4_prereqs,
        blockers=d4_blockers,
    )

    # -------------------------------------------------------------------------
    # Dimension 5: Safety, Regulatory & Governance
    # -------------------------------------------------------------------------
    d5_facts: List[str] = []
    d5_assumptions: List[str] = []
    d5_prereqs: List[str] = []
    d5_blockers: List[str] = []

    gov_constraint = domain_input.governance_constraint if has_domain else GovernanceConstraint.UNKNOWN
    if gov_constraint == GovernanceConstraint.STANDARD_BUSINESS:
        d5_state = DimensionState.FAVORABLE
        d5_facts.append("Domain confirmed: standard business operations with standard procedural audit trail.")
    elif gov_constraint == GovernanceConstraint.REGULATED_AUDIT:
        d5_state = DimensionState.PREREQUISITE_REQUIRED
        d5_prereq_msg = "Implement immutable electronic audit logging and regulatory compliance validation (e.g. FDA 21 CFR Part 11 / SOX)."
        d5_prereqs.append(d5_prereq_msg)
        prerequisites.append(d5_prereq_msg)
    elif gov_constraint == GovernanceConstraint.PROHIBITED_BY_LAW:
        d5_state = DimensionState.PROHIBITIVE_BARRIER
        d5_block_msg = "Statutory or regulatory mandate strictly prohibits automated execution of this task."
        d5_blockers.append(d5_block_msg)
        hard_blockers.append(d5_block_msg)
    else:  # UNKNOWN
        d5_state = DimensionState.UNKNOWN
        d5_assumptions.append("Safety, legal, and regulatory compliance constraints have not been assessed.")

    dim_governance = DimensionDetail(
        dimension_name="safety_regulatory_and_governance",
        state=d5_state,
        provenance=EvidenceProvenance.DOMAIN_INPUT if has_domain and gov_constraint != GovernanceConstraint.UNKNOWN else EvidenceProvenance.DEFAULT_UNKNOWN,
        observed_facts=d5_facts,
        assumptions=d5_assumptions,
        prerequisites=d5_prereqs,
        blockers=d5_blockers,
    )

    # -------------------------------------------------------------------------
    # Dimension 6: Evidence Completeness & Uncertainty
    # -------------------------------------------------------------------------
    d6_facts: List[str] = []
    d6_assumptions: List[str] = []
    d6_prereqs: List[str] = []
    d6_blockers: List[str] = []

    critical_domain_missing = (
        data_format == DigitalDataFormat.UNKNOWN
        or sys_interface == SystemInterfaceType.UNKNOWN
        or rule_det == RuleDeterminism.UNKNOWN
    )
    sample_limited = opportunity.evidence_strength == EvidenceStrength.LIMITED

    if sample_limited:
        d6_state = DimensionState.INSUFFICIENT_EVIDENCE
        d6_assumptions.append("Event log sample size is limited (<10 complete cases); empirical evidence has low statistical power.")
    elif critical_domain_missing:
        d6_state = DimensionState.UNKNOWN
        d6_assumptions.append("Critical domain dimensions (data format, interface accessibility, rule determinism) remain unassessed.")
    else:
        d6_state = DimensionState.FAVORABLE
        d6_facts.append("Critical domain intakes and empirical event observations are documented.")

    dim_completeness = DimensionDetail(
        dimension_name="evidence_completeness_and_uncertainty",
        state=d6_state,
        provenance=EvidenceProvenance.COMPUTED_SYNTHESIS,
        observed_facts=d6_facts,
        assumptions=d6_assumptions,
        prerequisites=d6_prereqs,
        blockers=d6_blockers,
    )

    # -------------------------------------------------------------------------
    # Precedence Evaluation for Overall Readiness Tier
    # -------------------------------------------------------------------------
    all_dimensions = [
        dim_repeatability,
        dim_digital,
        dim_interface,
        dim_judgment,
        dim_governance,
        dim_completeness,
    ]

    has_prohibitive_barrier = any(d.state == DimensionState.PROHIBITIVE_BARRIER for d in all_dimensions)
    has_unknown_or_insufficient = any(
        d.state in (DimensionState.UNKNOWN, DimensionState.INSUFFICIENT_EVIDENCE)
        for d in all_dimensions
    )
    has_prerequisite_required = any(d.state == DimensionState.PREREQUISITE_REQUIRED for d in all_dimensions)

    if has_prohibitive_barrier:
        overall_tier = OverallReadinessTier.PROHIBITED_OR_BLOCKED
    elif has_unknown_or_insufficient:
        overall_tier = OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE
    elif has_prerequisite_required:
        overall_tier = OverallReadinessTier.PREREQUISITES_REQUIRED
    else:
        overall_tier = OverallReadinessTier.READY_FOR_SPECIFICATION

    return OpportunityReadinessResult(
        opportunity_id=opportunity.id,
        target_entity=opportunity.target_entity,
        archetype=opportunity.archetype,
        source_finding_ids=opportunity.source_finding_ids,
        overall_readiness_tier=overall_tier,
        task_repeatability_and_rule_stability=dim_repeatability,
        digital_inputs_and_outputs=dim_digital,
        system_interface_accessibility=dim_interface,
        exception_frequency_and_judgment=dim_judgment,
        safety_regulatory_and_governance=dim_governance,
        evidence_completeness_and_uncertainty=dim_completeness,
        discrepancies=discrepancies,
        hard_blockers=hard_blockers,
        prerequisites=prerequisites,
        limitations=limitations,
    )


def assess_opportunities_readiness(
    opportunities_result: OpportunityDetectionResult,
    domain_assessments: Optional[List[OpportunityDomainAssessmentInput]],
    filename: str,
) -> ReadinessAssessmentResponse:
    """
    Evaluates automation readiness for all opportunity candidates in an OpportunityDetectionResult.
    Validates submitted opportunity IDs against detected opportunities.
    Supports partial domain submissions without failing unassessed opportunities.
    """
    # 1. Map available opportunities
    opp_map: Dict[str, OpportunityCandidate] = {
        opp.id: opp for opp in opportunities_result.opportunities
    }
    valid_ids: Set[str] = set(opp_map.keys())

    # 2. Validate submitted domain assessment IDs
    domain_map: Dict[str, OpportunityDomainAssessmentInput] = {}
    if domain_assessments:
        for item in domain_assessments:
            if item.opportunity_id not in valid_ids:
                sorted_valid = sorted(list(valid_ids))
                raise ValueError(
                    f"Unknown opportunity_id '{item.opportunity_id}'. "
                    f"Submitted assessments must match opportunities detected from the provided event log. "
                    f"Valid IDs: {sorted_valid}"
                )
            if item.opportunity_id in domain_map:
                raise ValueError(
                    f"Duplicate domain assessment for opportunity_id '{item.opportunity_id}'. "
                    "Each opportunity candidate may only be assessed once per request."
                )
            domain_map[item.opportunity_id] = item

    # 3. Assess each opportunity deterministically
    assessments: List[OpportunityReadinessResult] = []
    ready_count = 0
    prereq_count = 0
    blocked_count = 0
    insufficient_count = 0
    total_discrepancies = 0

    for opp in opportunities_result.opportunities:
        domain_input = domain_map.get(opp.id)
        res = assess_single_opportunity_readiness(opp, domain_input)
        assessments.append(res)

        if res.overall_readiness_tier == OverallReadinessTier.READY_FOR_SPECIFICATION:
            ready_count += 1
        elif res.overall_readiness_tier == OverallReadinessTier.PREREQUISITES_REQUIRED:
            prereq_count += 1
        elif res.overall_readiness_tier == OverallReadinessTier.PROHIBITED_OR_BLOCKED:
            blocked_count += 1
        else:
            insufficient_count += 1

        total_discrepancies += len(res.discrepancies)

    summary = ReadinessSummary(
        evaluated_opportunities_count=len(assessments),
        ready_for_specification_count=ready_count,
        prerequisites_required_count=prereq_count,
        prohibited_or_blocked_count=blocked_count,
        insufficient_critical_evidence_count=insufficient_count,
        discrepancy_count=total_discrepancies,
    )

    return ReadinessAssessmentResponse(
        filename=filename,
        summary=summary,
        assessments=assessments,
    )
