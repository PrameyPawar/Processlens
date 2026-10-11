"""
Unit and integration tests for Phase 10 Explanation Schemas and Deterministic Template Engine.
Validates:
- Schema enforcement and rejection of extra attributes (extra="forbid").
- Deterministic generation for all five Phase 5 opportunity archetypes.
- Exact repeatable output across multiple executions.
- Proper handling of missing/unmonetized economic values (no silent zeros).
- Epistemic preservation (facts vs assumptions vs estimates vs decisions).
- Strict non-additive portfolio economics disclaimer.
- Regressions across all four development datasets (quickstart, clean, rework, messy).
- Empty dossier list handling.
"""

import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.schemas.opportunity import OpportunityArchetype
from app.schemas.prioritisation import PortfolioCohort
from app.schemas.evidence import (
    EpistemicType,
    EvidenceAuditResponse,
    OpportunityEvidenceDossier,
    CaseTraceExemplar,
    EventRowAnchor,
    MetricDerivationAudit,
    EpistemicItem,
    EvidenceAuditManifest,
)
from app.schemas.explanation import (
    ExplanationSource,
    GroundingVerificationStatus,
    GroundingAudit,
    OpportunityExplanation,
    PortfolioExecutiveSummary,
    ExplanationResponse,
)
from app.services.explanation_templates import (
    generate_opportunity_explanation,
    generate_portfolio_executive_summary,
    generate_deterministic_explanation_response,
)


# =============================================================================
# GROUP 1: Schema Validation and Rejection of Extra Fields
# =============================================================================

def test_group1_1_explanation_schema_strictness_rejects_extra():
    """Verify that schemas with extra='forbid' raise ValidationError on extra fields."""
    valid_grounding = {
        "status": GroundingVerificationStatus.VERIFIED_GROUNDED.value,
        "verified_numbers": ["10", "20.5"],
        "verified_entities": ["Activity A"],
        "discrepancies": [],
    }
    grounding = GroundingAudit(**valid_grounding)
    assert grounding.status == GroundingVerificationStatus.VERIFIED_GROUNDED

    with pytest.raises(ValidationError):
        GroundingAudit(**{**valid_grounding, "hallucinated_field": 123})

    valid_explanation = {
        "opportunity_id": "opp_test_1",
        "archetype": OpportunityArchetype.DELAY_COMPRESSION.value,
        "portfolio_cohort": PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION.value,
        "rank_order": 1,
        "composite_priority_score": 85.5,
        "target_entity": "ActA -> ActB",
        "executive_summary": "Exec summary text.",
        "operational_problem_narrative": "Problem narrative text.",
        "economic_interpretation": "Economic interpretation text.",
        "strategic_rationale": "Strategic rationale text.",
        "key_assumptions_and_risks": ["[ASSUMPTION] Test assumption"],
        "investigation_next_steps": ["Observe step."],
        "grounding_audit": valid_grounding,
    }
    exp = OpportunityExplanation(**valid_explanation)
    assert exp.opportunity_id == "opp_test_1"
    assert exp.grounding_audit is not None

    # Test optionality: grounding_audit defaults to None when omitted
    valid_explanation_no_audit = {k: v for k, v in valid_explanation.items() if k != "grounding_audit"}
    exp_no_audit = OpportunityExplanation(**valid_explanation_no_audit)
    assert exp_no_audit.grounding_audit is None

    with pytest.raises(ValidationError):
        OpportunityExplanation(**{**valid_explanation, "invented_attribute": "invalid"})


def test_group1_2_portfolio_summary_rejects_extra_fields():
    """Verify that PortfolioExecutiveSummary forbids extra fields."""
    valid_summary = {
        "overall_narrative": "Overall portfolio narrative.",
        "top_recommended_actions": ["Action 1"],
        "foundational_prerequisites": ["Prerequisite 1"],
        "portfolio_economics_caveat": "Non-additive caveat text.",
    }
    summary = PortfolioExecutiveSummary(**valid_summary)
    assert summary.overall_narrative == "Overall portfolio narrative."

    with pytest.raises(ValidationError):
        PortfolioExecutiveSummary(**{**valid_summary, "extra_metric": 999.0})


# =============================================================================
# GROUP 2: Archetype Coverage and Deterministic Wording
# =============================================================================

def _build_minimal_dossier(
    archetype: OpportunityArchetype,
    cohort: PortfolioCohort = PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,
    target_entity: str = "TestTarget",
    exemplars: list = None,
    derivations: list = None,
    epistemic_ledger: list = None,
) -> OpportunityEvidenceDossier:
    """Helper to construct a fully valid OpportunityEvidenceDossier for unit testing."""
    return OpportunityEvidenceDossier(
        opportunity_id=f"opp_{archetype.value.lower()}_test",
        archetype=archetype,
        portfolio_cohort=cohort,
        rank_order=1,
        composite_priority_score=75.0,
        target_entity=target_entity,
        exemplars=exemplars or [],
        exemplar_selection_policy="Deterministic test selection",
        derivations=derivations or [],
        epistemic_ledger=epistemic_ledger or [
            EpistemicItem(
                item_id="fact_1",
                epistemic_type=EpistemicType.FACT,
                statement="50 cases observed",
                source_or_basis="Log observation",
            ),
            EpistemicItem(
                item_id="assump_1",
                epistemic_type=EpistemicType.ASSUMPTION,
                statement="Hourly rate is $50.00",
                source_or_basis="User input",
            ),
            EpistemicItem(
                item_id="hyp_1",
                epistemic_type=EpistemicType.HYPOTHESIS,
                statement="Batching causes delay",
                source_or_basis="Analytical heuristic",
            ),
            EpistemicItem(
                item_id="est_1",
                epistemic_type=EpistemicType.ESTIMATE,
                statement="Annual capacity benefit is $25,000",
                source_or_basis="Capacity formula",
            ),
            EpistemicItem(
                item_id="dec_1",
                epistemic_type=EpistemicType.DECISION,
                statement="Assigned rank #1",
                source_or_basis="Precedence sort key",
            ),
        ],
        boundary_limitations=["Observation limited to sample duration."],
    )


def test_group2_1_delay_compression_explanation():
    """Verify DELAY_COMPRESSION explanation addresses milestone transition latency and exemplars."""
    exemplar = CaseTraceExemplar(
        case_id="CASE_001",
        exemplar_metric_value=450.5,
        exemplar_metric_description="Transition duration",
        total_case_duration_seconds=1200.0,
        event_anchors=[
            EventRowAnchor(
                row_index=1,
                csv_line_number=2,
                case_id="CASE_001",
                activity="Assembly",
                timestamp_raw="2026-01-01T10:00:00",
                role_in_evidence="TRANSITION_SOURCE",
            ),
            EventRowAnchor(
                row_index=2,
                csv_line_number=3,
                case_id="CASE_001",
                activity="Testing",
                timestamp_raw="2026-01-01T10:07:30",
                role_in_evidence="TRANSITION_TARGET",
            ),
        ],
        trace_summary="Sample trace summary",
    )
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        target_entity="Assembly -> Testing",
        exemplars=[exemplar],
    )
    exp = generate_opportunity_explanation(dossier)

    assert exp.archetype == OpportunityArchetype.DELAY_COMPRESSION
    assert "Assembly -> Testing" in exp.operational_problem_narrative
    assert "CASE_001" in exp.operational_problem_narrative
    assert "450.5" in exp.operational_problem_narrative or "450.50s" in exp.operational_problem_narrative
    assert "elapsed chronological time" in exp.operational_problem_narrative
    assert len(exp.investigation_next_steps) >= 3
    assert any("direct operational observation" in step.lower() for step in exp.investigation_next_steps)


def test_group2_2_recurrence_reduction_explanation():
    """Verify RECURRENCE_REDUCTION explanation addresses repeated activity loops."""
    exemplar = CaseTraceExemplar(
        case_id="CASE_002",
        exemplar_metric_value=3.0,
        exemplar_metric_description="Repeat count",
        total_case_duration_seconds=1800.0,
        event_anchors=[],
        trace_summary="Repeat trace summary",
    )
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.RECURRENCE_REDUCTION,
        target_entity="Rework Subassembly",
        exemplars=[exemplar],
    )
    exp = generate_opportunity_explanation(dossier)

    assert exp.archetype == OpportunityArchetype.RECURRENCE_REDUCTION
    assert "Rework Subassembly" in exp.operational_problem_narrative
    assert "CASE_002" in exp.operational_problem_narrative
    assert "3 times" in exp.operational_problem_narrative
    assert "operational rework" in exp.operational_problem_narrative.lower()
    assert any("reasons for rework" in step.lower() for step in exp.investigation_next_steps)


def test_group2_3_tail_variance_mitigation_explanation():
    """Verify TAIL_VARIANCE_MITIGATION explanation addresses statistical cycle-time outliers."""
    exemplar = CaseTraceExemplar(
        case_id="CASE_OUTLIER",
        exemplar_metric_value=8500.0,
        exemplar_metric_description="Extreme cycle time",
        total_case_duration_seconds=8500.0,
        event_anchors=[],
        trace_summary="Outlier trace",
    )
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
        target_entity="Cycle Time Distribution",
        exemplars=[exemplar],
    )
    exp = generate_opportunity_explanation(dossier)

    assert exp.archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION
    assert "CASE_OUTLIER" in exp.operational_problem_narrative
    assert "8500.00s" in exp.operational_problem_narrative
    assert "upper fence" in exp.operational_problem_narrative
    assert any("outlier case files" in step.lower() for step in exp.investigation_next_steps)


def test_group2_4_path_standardization_explanation():
    """Verify PATH_STANDARDIZATION explanation addresses rare variant pathways."""
    exemplar = CaseTraceExemplar(
        case_id="CASE_RARE",
        exemplar_metric_value=2400.0,
        exemplar_metric_description="Rare path duration",
        total_case_duration_seconds=2400.0,
        event_anchors=[],
        trace_summary="Rare trace",
    )
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.PATH_STANDARDIZATION,
        target_entity="Variant Routing",
        exemplars=[exemplar],
    )
    exp = generate_opportunity_explanation(dossier)

    assert exp.archetype == OpportunityArchetype.PATH_STANDARDIZATION
    assert "CASE_RARE" in exp.operational_problem_narrative
    assert "<2% frequency" in exp.operational_problem_narrative
    assert any("standard operating procedures" in step.lower() for step in exp.investigation_next_steps)


def test_group2_5_data_instrumentation_explanation():
    """Verify DATA_INSTRUMENTATION explanation addresses excluded rows and foundational tracking."""
    anchor = EventRowAnchor(
        row_index=15,
        csv_line_number=16,
        case_id="CASE_DEFECT",
        activity="UnparseableTimestamp",
        timestamp_raw="INVALID",
        role_in_evidence="EXCLUDED_DATA_ROW",
    )
    exemplar = CaseTraceExemplar(
        case_id="CASE_DEFECT",
        exemplar_metric_value=1.0,
        exemplar_metric_description="Excluded row",
        total_case_duration_seconds=None,
        event_anchors=[anchor],
        trace_summary="Excluded row 15",
    )
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
        cohort=PortfolioCohort.FOUNDATIONAL_DATA_QUALITY,
        target_entity="Timestamp Logging",
        exemplars=[exemplar],
    )
    exp = generate_opportunity_explanation(dossier)

    assert exp.archetype == OpportunityArchetype.DATA_INSTRUMENTATION
    assert "Row 15" in exp.operational_problem_narrative
    assert "CSV line 16" in exp.operational_problem_narrative
    assert "foundational data quality" in exp.strategic_rationale.lower()
    assert any("audit event ingestion extract pipelines" in step.lower() for step in exp.investigation_next_steps)


# =============================================================================
# GROUP 3: Determinism and Idempotence
# =============================================================================

def test_group3_1_deterministic_repeated_output_identity():
    """Verify that multiple executions produce bit-for-bit identical explanation outputs."""
    dossier = _build_minimal_dossier(archetype=OpportunityArchetype.DELAY_COMPRESSION)
    exp1 = generate_opportunity_explanation(dossier)
    exp2 = generate_opportunity_explanation(dossier)

    assert exp1.model_dump() == exp2.model_dump()


# =============================================================================
# GROUP 4: Missing and Null Economic Values
# =============================================================================

def test_group4_1_unmonetized_economics_handling():
    """Verify that opportunities without economic inputs do not fabricate $0.00 figures."""
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        cohort=PortfolioCohort.BUSINESS_CASE_VALIDATION,
        derivations=[],  # No CAPACITY_VAL_V1 derivation
    )
    exp = generate_opportunity_explanation(dossier)

    assert "Economic inputs were not supplied" in exp.economic_interpretation
    assert "remain unknown and unmonetized" in exp.economic_interpretation
    assert "$0" not in exp.economic_interpretation
    assert "$0.00" not in exp.economic_interpretation


def test_group4_2_monetized_economics_with_payback():
    """Verify that monetized opportunities report net benefit and payback correctly with caveats."""
    derivations = [
        MetricDerivationAudit(
            metric_id="LABOR_EFFORT_V1",
            formula_expression="sample_active_hours * R_raw",
            input_variables={},
            intermediate_values={},
            output_value=500.0,
            quantization_rule="Half-up",
            limitations_and_assumptions=[],
        ),
        MetricDerivationAudit(
            metric_id="CAPACITY_VAL_V1",
            formula_expression="gross - recurring",
            input_variables={
                "hourly_labor_rate": 60.0,
                "annual_recurring_cost": 5000.0,
            },
            intermediate_values={
                "gross_capacity_valuation": 30000.0,
                "net_annual_capacity_benefit": 25000.0,
            },
            output_value=25000.0,
            quantization_rule="Commercial half-up",
            limitations_and_assumptions=[],
        ),
        MetricDerivationAudit(
            metric_id="PAYBACK_PERIOD_V1",
            formula_expression="(cost / net) * 12",
            input_variables={
                "implementation_cost": 12500.0,
                "net_annual_capacity_benefit": 25000.0,
            },
            intermediate_values={},
            output_value=6.0,
            quantization_rule="round(x, 1)",
            limitations_and_assumptions=[],
        ),
    ]
    dossier = _build_minimal_dossier(
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        cohort=PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,
        derivations=derivations,
    )
    exp = generate_opportunity_explanation(dossier)

    assert "$30,000 in gross annual capacity value" in exp.economic_interpretation
    assert "$60.00/hr" in exp.economic_interpretation
    assert "500 annual active labor hours" in exp.economic_interpretation
    assert "$5,000 in annual recurring maintenance" in exp.economic_interpretation
    assert "$25,000" in exp.economic_interpretation
    assert "6.0 months" in exp.economic_interpretation
    assert "does not constitute guaranteed cash savings" in exp.economic_interpretation


# =============================================================================
# GROUP 5: Epistemic Distinctions and Portfolio Summary
# =============================================================================

def test_group5_1_epistemic_distinctions_in_assumptions():
    """Verify that key assumptions/risks explicitly distinguish ASSUMPTION, HYPOTHESIS, and ESTIMATE."""
    dossier = _build_minimal_dossier(archetype=OpportunityArchetype.DELAY_COMPRESSION)
    exp = generate_opportunity_explanation(dossier)

    prefixes = [item.split()[0] for item in exp.key_assumptions_and_risks]
    assert "[ASSUMPTION]" in prefixes
    assert "[HYPOTHESIS]" in prefixes
    assert "[ESTIMATE]" in prefixes
    assert "[LIMITATION]" in prefixes


def test_group5_2_portfolio_summary_non_additive_caveat():
    """Verify that PortfolioExecutiveSummary includes the mandatory non-additive capacity caveat."""
    dossier1 = _build_minimal_dossier(archetype=OpportunityArchetype.DELAY_COMPRESSION)
    dossier2 = _build_minimal_dossier(
        archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
        cohort=PortfolioCohort.FOUNDATIONAL_DATA_QUALITY,
    )

    summary = generate_portfolio_executive_summary([dossier1, dossier2])
    assert "non-additive" in summary.portfolio_economics_caveat.lower()
    assert "must not be summed" in summary.portfolio_economics_caveat.lower()
    assert len(summary.foundational_prerequisites) > 0
    assert "Prerequisite: Resolve data tracking defects" in summary.foundational_prerequisites[0]


def test_group5_3_empty_dossier_list_portfolio_summary():
    """Verify that an empty dossier list produces a restrained, non-crashing summary."""
    summary = generate_portfolio_executive_summary([])
    assert "No improvement opportunities were detected" in summary.overall_narrative
    assert len(summary.top_recommended_actions) > 0
    assert len(summary.foundational_prerequisites) > 0


# =============================================================================
# GROUP 6: End-to-End Regressions on All Four Synthetic Datasets
# =============================================================================

@pytest.mark.parametrize(
    "dataset_fixture",
    [
        "sample_quickstart_path",
        "sample_clean_path",
        "sample_rework_path",
        "sample_messy_path",
    ],
)
def test_group6_1_end_to_end_explanation_across_all_datasets(request, client: TestClient, dataset_fixture):
    """
    Test 6.1: Executes Phase 9 evidence audit endpoint on each synthetic dataset,
    then generates deterministic explanations from the resulting dossiers.
    Verifies 100% schema compliance, archetype handling, and portfolio summary.
    """
    sample_path = request.getfixturevalue(dataset_fixture)
    with open(sample_path, "rb") as f:
        audit_res = client.post("/api/v1/evidence/audit", files={"file": (sample_path.name, f, "text/csv")})
    assert audit_res.status_code == 200
    audit_data = audit_res.json()
    audit_response = EvidenceAuditResponse(**audit_data)

    explanation_res = generate_deterministic_explanation_response(audit_response, execution_duration_seconds=0.05)
    assert explanation_res.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
    assert explanation_res.manifest.source_filename == sample_path.name
    assert len(explanation_res.explanations) == len(audit_response.dossiers)

    # Check each individual explanation
    for exp in explanation_res.explanations:
        assert exp.opportunity_id != ""
        assert exp.target_entity != ""
        assert len(exp.executive_summary) > 20
        assert len(exp.operational_problem_narrative) > 20
        assert len(exp.economic_interpretation) > 20
        assert len(exp.strategic_rationale) > 20
        assert len(exp.investigation_next_steps) >= 2
        assert exp.grounding_audit is None, (
            "Deterministic template engine must not claim independent grounding verification has run"
        )

    # Check portfolio summary
    summary = explanation_res.portfolio_summary
    assert len(summary.overall_narrative) > 20
    assert len(summary.top_recommended_actions) > 0
    assert len(summary.foundational_prerequisites) > 0
    assert "must not be summed" in summary.portfolio_economics_caveat.lower()
