"""
Comprehensive test suite for Phase 10.3 Grounding Verification and Anti-Hallucination Guardrails.
Tests:
- Group 1: Grounding passes for valid deterministic template explanations across all 5 archetypes.
- Group 2: Detection and rejection of unsupported numeric claims (currency, durations, counts, payback).
- Group 3: Detection and rejection of fabricated entities and case IDs.
- Group 4: Economic and causal guardrail enforcement (guaranteed savings, budget reductions, unproven causation).
- Group 5: Unmonetized economic substitution prevention (no silent $0 or fabricated monetary claims).
- Group 6: Metadata and structural identity alignment (mismatched ID, archetype, cohort, rank).
- Group 7: End-to-end dataset regressions across all four synthetic datasets (quickstart, clean, rework, messy).
- Group 8: Immutability and input preservation.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient

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
)
from app.schemas.explanation import (
    GroundingVerificationStatus,
    GroundingAudit,
    OpportunityExplanation,
)
from app.services.explanation_templates import generate_opportunity_explanation
from app.services.grounding import verify_opportunity_explanation


def _build_test_dossier(
    archetype: OpportunityArchetype = OpportunityArchetype.DELAY_COMPRESSION,
    cohort: PortfolioCohort = PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,
    target_entity: str = "Assembly -> Testing",
    exemplars: list = None,
    derivations: list = None,
    composite_score: float = 75.0,
) -> OpportunityEvidenceDossier:
    """Helper to build a rich, valid OpportunityEvidenceDossier for unit testing."""
    default_exemplar = CaseTraceExemplar(
        case_id="ORD_101",
        exemplar_metric_value=450.5,
        exemplar_metric_description="Elapsed transition duration",
        total_case_duration_seconds=1200.0,
        event_anchors=[
            EventRowAnchor(
                row_index=1,
                csv_line_number=2,
                case_id="ORD_101",
                activity="Assembly",
                timestamp_raw="2026-01-01T10:00:00",
                role_in_evidence="TRANSITION_SOURCE",
            ),
            EventRowAnchor(
                row_index=2,
                csv_line_number=3,
                case_id="ORD_101",
                activity="Testing",
                timestamp_raw="2026-01-01T10:07:30",
                role_in_evidence="TRANSITION_TARGET",
            ),
        ],
        trace_summary="Sample trace ORD_101",
    )

    default_derivations = [
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

    return OpportunityEvidenceDossier(
        opportunity_id="opp_grounding_test",
        archetype=archetype,
        portfolio_cohort=cohort,
        rank_order=1,
        composite_priority_score=composite_score,
        target_entity=target_entity,
        exemplars=exemplars if exemplars is not None else [default_exemplar],
        exemplar_selection_policy="Deterministic test selection",
        derivations=derivations if derivations is not None else default_derivations,
        epistemic_ledger=[
            EpistemicItem(
                item_id="fact_1",
                epistemic_type=EpistemicType.FACT,
                statement="50 complete cases observed",
                source_or_basis="Log observation",
            ),
            EpistemicItem(
                item_id="assump_1",
                epistemic_type=EpistemicType.ASSUMPTION,
                statement="Hourly rate is $60.00",
                source_or_basis="User input",
            ),
        ],
        boundary_limitations=["Observation limited to sample duration."],
    )


# =============================================================================
# GROUP 1: Valid Explanations Pass Grounding Verification
# =============================================================================

@pytest.mark.parametrize(
    "archetype,target_entity",
    [
        (OpportunityArchetype.DELAY_COMPRESSION, "Assembly -> Testing"),
        (OpportunityArchetype.RECURRENCE_REDUCTION, "Rework Subassembly"),
        (OpportunityArchetype.TAIL_VARIANCE_MITIGATION, "Cycle Time Tail"),
        (OpportunityArchetype.PATH_STANDARDIZATION, "Custom Path Route"),
        (OpportunityArchetype.DATA_INSTRUMENTATION, "Timestamp Logging"),
    ],
)
def test_group1_1_valid_deterministic_explanations_pass(archetype, target_entity):
    """Verify that correctly generated deterministic template explanations pass verification."""
    dossier = _build_test_dossier(archetype=archetype, target_entity=target_entity)
    explanation = generate_opportunity_explanation(dossier)

    audit = verify_opportunity_explanation(explanation, dossier)
    assert audit.status == GroundingVerificationStatus.VERIFIED_GROUNDED
    assert len(audit.discrepancies) == 0
    assert len(audit.verified_numbers) > 0
    assert len(audit.verified_entities) > 0


# =============================================================================
# GROUP 2: Numeric Claim Verification
# =============================================================================

def test_group2_1_detects_unsupported_currency_claim():
    """Verify that an invented or inflated currency figure is flagged as a discrepancy."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    # Tamper with economic interpretation by claiming $500,000 instead of $25,000
    tampered = explanation.model_copy(
        update={"economic_interpretation": explanation.economic_interpretation.replace("$25,000", "$500,000")}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("$500,000" in d for d in audit.discrepancies)


def test_group2_2_detects_unsupported_duration_claim():
    """Verify that an altered transition duration is flagged."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    # Tamper with narrative by replacing 450.50s with 9999.00s
    tampered = explanation.model_copy(
        update={"operational_problem_narrative": explanation.operational_problem_narrative.replace("450.50s", "9999.00s")}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("9999.00s" in d for d in audit.discrepancies)


def test_group2_3_detects_unsupported_payback_period():
    """Verify that an unsupported payback period is flagged."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    # Tamper with payback months (6.0 months -> 36.0 months)
    tampered = explanation.model_copy(
        update={"economic_interpretation": explanation.economic_interpretation.replace("6.0 months", "36.0 months")}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("36.0" in d for d in audit.discrepancies)


# =============================================================================
# GROUP 3: Entity Verification
# =============================================================================

def test_group3_1_detects_fabricated_case_reference():
    """Verify that mentioning a non-existent case ID is flagged as a discrepancy."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    # Inject fabricated case ORD_999
    tampered = explanation.model_copy(
        update={"operational_problem_narrative": explanation.operational_problem_narrative + " Case 'ORD_999' also showed delays."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("ORD_999" in d for d in audit.discrepancies)


def test_group3_2_detects_fabricated_process_activity():
    """Verify that mentioning an unobserved activity is flagged."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    # Inject fabricated activity 'InventoryDispatch'
    tampered = explanation.model_copy(
        update={"operational_problem_narrative": explanation.operational_problem_narrative + " Observed at activity 'InventoryDispatch'."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("InventoryDispatch" in d for d in audit.discrepancies)


# =============================================================================
# GROUP 4: Economic and Epistemic Guardrails
# =============================================================================

def test_group4_1_detects_guaranteed_savings_claim():
    """Verify that claiming guaranteed savings triggers an economic guardrail violation."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"economic_interpretation": "This solution provides guaranteed savings of $25,000 annually."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("guaranteed savings" in d.lower() for d in audit.discrepancies)


def test_group4_2_detects_unsupported_causal_assertion():
    """Verify that unproven causal claims (e.g. definitively causes) are flagged."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"operational_problem_narrative": explanation.operational_problem_narrative + " This delay definitively causes quality defects."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("definitively causes" in d.lower() for d in audit.discrepancies)


# =============================================================================
# GROUP 5: Unmonetized Economics Substitution
# =============================================================================

def test_group5_1_detects_zero_substitution_for_unmonetized_opportunity():
    """Verify that claiming $0.00 net benefit on unmonetized opportunities is flagged."""
    dossier = _build_test_dossier(derivations=[])  # Unmonetized
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"economic_interpretation": "Yields $0.00 in net annual capacity value with 0.0 months payback."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("unmonetized" in d.lower() for d in audit.discrepancies)


def test_group5_2_detects_fabricated_monetary_value_on_unmonetized_opportunity():
    """Verify that claiming non-zero monetary values on unmonetized opportunities is flagged."""
    dossier = _build_test_dossier(derivations=[])  # Unmonetized
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"economic_interpretation": "Projects $45,000 in net annual benefit."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("unmonetized" in d.lower() for d in audit.discrepancies)


# =============================================================================
# GROUP 6: Metadata & Identity Alignment
# =============================================================================

def test_group6_1_detects_mismatched_rank_and_score():
    """Verify that rank and composite score mismatches between explanation and dossier are detected."""
    dossier = _build_test_dossier(composite_score=75.0)
    explanation = generate_opportunity_explanation(dossier)

    # Tamper with rank order
    tampered_rank = explanation.model_copy(update={"rank_order": 5})
    audit_rank = verify_opportunity_explanation(tampered_rank, dossier)
    assert audit_rank.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("Rank order mismatch" in d for d in audit_rank.discrepancies)

    # Tamper with composite score
    tampered_score = explanation.model_copy(update={"composite_priority_score": 99.0})
    audit_score = verify_opportunity_explanation(tampered_score, dossier)
    assert audit_score.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("Composite priority score mismatch" in d for d in audit_score.discrepancies)


# =============================================================================
# GROUP 7: Regressions on All Four Synthetic Datasets
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
def test_group7_1_end_to_end_grounding_across_all_datasets(request, client: TestClient, dataset_fixture):
    """
    Test 7.1: Runs Phase 9 evidence audit on each dataset, generates deterministic
    explanations, and verifies that 100% of generated explanations pass grounding verification.
    """
    sample_path = request.getfixturevalue(dataset_fixture)
    with open(sample_path, "rb") as f:
        audit_res = client.post("/api/v1/evidence/audit", files={"file": (sample_path.name, f, "text/csv")})
    assert audit_res.status_code == 200
    audit_response = EvidenceAuditResponse(**audit_res.json())

    for dossier in audit_response.dossiers:
        explanation = generate_opportunity_explanation(dossier)
        audit = verify_opportunity_explanation(explanation, dossier)

        assert audit.status == GroundingVerificationStatus.VERIFIED_GROUNDED, (
            f"Grounding failed for opportunity '{dossier.opportunity_id}' in {sample_path.name}: {audit.discrepancies}"
        )
        assert len(audit.discrepancies) == 0
        assert len(audit.verified_numbers) > 0
        assert len(audit.verified_entities) > 0


# =============================================================================
# GROUP 8: Immutability and Input Preservation
# =============================================================================

def test_group8_1_verifier_does_not_mutate_inputs():
    """Verify that verify_opportunity_explanation does not modify explanation or dossier."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    exp_before = explanation.model_dump()
    dossier_before = dossier.model_dump()

    _ = verify_opportunity_explanation(explanation, dossier)

    assert explanation.model_dump() == exp_before
    assert dossier.model_dump() == dossier_before


# =============================================================================
# GROUP 9: Context-Aware Metric Compatibility & Advanced Guardrails
# =============================================================================

def test_group9_1_rejects_cross_metric_numeric_substitution():
    """
    Verify that an explanation cannot use a number from one metric type (e.g. duration 450.5s)
    as an unrelated metric (e.g. claiming $450.50 net annual benefit).
    """
    dossier = _build_test_dossier()  # Has duration 450.5s, but currencies are 60.0, 5000.0, 12500.0, 25000.0, 30000.0
    explanation = generate_opportunity_explanation(dossier)

    # Claim $450.50 net annual capacity benefit (using duration number as currency)
    tampered = explanation.model_copy(
        update={"economic_interpretation": explanation.economic_interpretation.replace("$25,000", "$450.50")}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("$450.50" in d for d in audit.discrepancies)


def test_group9_2_rejects_epistemic_inversion_of_estimates_to_facts():
    """Verify that claiming projected estimates or decisions as observed facts is rejected."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"executive_summary": explanation.executive_summary + " It is an observed fact that net annual capacity benefit is $25,000."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("epistemic integrity violation" in d.lower() for d in audit.discrepancies)


def test_group9_3_rejects_non_numeric_causal_assertions():
    """Verify that unsupported causal claims containing no numbers are rejected."""
    dossier = _build_test_dossier()
    explanation = generate_opportunity_explanation(dossier)

    tampered = explanation.model_copy(
        update={"operational_problem_narrative": explanation.operational_problem_narrative + " This transition delay causally leads to customer churn."}
    )

    audit = verify_opportunity_explanation(tampered, dossier)
    assert audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
    assert any("causally leads to" in d for d in audit.discrepancies)

