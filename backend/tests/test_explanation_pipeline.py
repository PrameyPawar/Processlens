"""
Test suite for ProcessLens Phase 10.5 Explanation API & Pipeline.
Verifies prompt assembly, candidate parsing, deterministic-only generation,
grounded LLM explanation generation, hallucination rejection, causal and guaranteed-savings
guardrails, unmonetized economic safeguards, provider failure resilience,
and FastAPI endpoint integration.

Zero live network calls are made.
"""

import io
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app, get_llm_provider
from app.core.config import settings
from app.schemas.evidence import (
    EpistemicType,
    EpistemicItem,
    EvidenceAuditResponse,
    EvidenceAuditSummary,
    EvidenceAuditManifest,
    OpportunityEvidenceDossier,
    CaseTraceExemplar,
)
from app.schemas.explanation import (
    ExplanationResponse,
    OpportunityExplanation,
    ExplanationSource,
    GroundingVerificationStatus,
    GroundingAudit,
)
from app.schemas.opportunity import OpportunityArchetype
from app.schemas.prioritisation import PortfolioCohort
from app.schemas.llm import (
    LLMGenerateRequest,
    LLMGenerateResponse,
    LLMUsage,
)
from app.services.llm_provider import (
    BaseLLMProvider,
    LLMTimeoutError,
    LLMNetworkError,
    LLMResponseError,
    LLMConfigurationError,
)
from app.services.explanation_prompt import (
    build_opportunity_prompt,
    parse_candidate_explanation,
)
from app.services.explanation_templates import (
    generate_opportunity_explanation,
    generate_deterministic_explanation_response,
)
from app.services.explanation_pipeline import run_explanation_pipeline


# ==============================================================================
# Test Fixtures & Mock Providers
# ==============================================================================

class MockLLMProvider(BaseLLMProvider):
    """
    Test provider allowing custom response payloads or exceptions.
    """
    def __init__(self, handler=None, model="mock-model"):
        self.handler = handler
        self.model = model

    def generate(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        if self.handler:
            return self.handler(request)
        return LLMGenerateResponse(
            content=json.dumps({
                "executive_summary": "Refined executive summary.",
                "operational_problem_narrative": "Refined problem narrative.",
                "economic_interpretation": "Refined economic interpretation.",
                "strategic_rationale": "Refined strategic rationale.",
                "key_assumptions_and_risks": ["Assumption 1"],
                "investigation_next_steps": ["Step 1"],
            }),
            model=self.model,
        )

    async def generate_async(self, request: LLMGenerateRequest) -> LLMGenerateResponse:
        return self.generate(request)


@pytest.fixture
def sample_dossier():
    return OpportunityEvidenceDossier(
        opportunity_id="OPP-DELAY-01",
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        portfolio_cohort=PortfolioCohort.IMMEDIATE_AUTOMATION_SPECIFICATION,
        rank_order=1,
        composite_priority_score=85.5,
        target_entity="Review -> Approval",
        exemplars=[
            CaseTraceExemplar(
                case_id="CASE_101",
                exemplar_metric_value=920.0,
                exemplar_metric_description="Transition duration (seconds)",
                total_case_duration_seconds=920.0,
                event_anchors=[],
                trace_summary="Slowest transition instance",
            )
        ],
        exemplar_selection_policy="DESCENDING_TRANSITION_DURATION",
        derivations=[],
        epistemic_ledger=[
            EpistemicItem(
                item_id="EPI-01",
                epistemic_type=EpistemicType.FACT,
                statement="Transition latency observed between Review and Approval with median duration 450.0s.",
                source_or_basis="OPS_SCORE_V1",
            ),
            EpistemicItem(
                item_id="EPI-02",
                epistemic_type=EpistemicType.ESTIMATE,
                statement="Projects 120.0 annual capacity hours released.",
                source_or_basis="LABOR_EFFORT_V1",
            ),
        ],
        boundary_limitations=["Observational process log correlation only"],
    )


@pytest.fixture
def sample_audit_response(sample_dossier):
    manifest = EvidenceAuditManifest(
        source_file_sha256="test-sha-256",
        source_filename="test.csv",
        source_file_size_bytes=1024,
        total_source_rows=50,
        complete_cases_count=10,
        reconciliation_status="RECONCILED",
        effective_prioritisation_weights={"IMPACT": 25.0},
        formula_version="v1.0",
        is_persisted_snapshot=False,
        notes="Test manifest notes",
    )
    summary = EvidenceAuditSummary(
        total_opportunities_evaluated=1,
        dossiers_emitted=1,
        filter_applied=None,
        cohort_distribution={"IMMEDIATE_AUTOMATION_SPECIFICATION": 1},
    )
    return EvidenceAuditResponse(manifest=manifest, summary=summary, dossiers=[sample_dossier])


# ==============================================================================
# Group 1: Prompt Assembly and Candidate Parsing
# ==============================================================================

class TestPromptAndParser:
    def test_build_opportunity_prompt_structure(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        messages = build_opportunity_prompt(sample_dossier, det_exp)

        assert len(messages) == 2
        assert messages[0].role.value == "system"
        assert messages[1].role.value == "user"

        # System message invariants
        assert "Ground Truth Invariant" in messages[0].content
        assert "No Causal Claims" in messages[0].content
        assert "No Guaranteed Savings" in messages[0].content

        # User message content
        user_body = json.loads(messages[1].content)
        assert user_body["opportunity_metadata"]["opportunity_id"] == "OPP-DELAY-01"
        assert user_body["opportunity_metadata"]["target_entity"] == "Review -> Approval"

    def test_parse_candidate_explanation_valid_json(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        valid_json = json.dumps({
            "executive_summary": "Executive summary of Review -> Approval.",
            "operational_problem_narrative": "Observed 450.0s latency in Review -> Approval.",
            "economic_interpretation": "120.0 hours released.",
            "strategic_rationale": "Ranked #1 in IMMEDIATE_AUTOMATION_SPECIFICATION.",
            "key_assumptions_and_risks": ["Assumption A"],
            "investigation_next_steps": ["Investigate Case CASE_101"],
        })

        candidate = parse_candidate_explanation(valid_json, det_exp)
        assert candidate.opportunity_id == "OPP-DELAY-01"
        assert candidate.archetype == OpportunityArchetype.DELAY_COMPRESSION
        assert candidate.rank_order == 1
        assert candidate.composite_priority_score == 85.5
        assert candidate.executive_summary == "Executive summary of Review -> Approval."
        assert candidate.key_assumptions_and_risks == det_exp.key_assumptions_and_risks
        assert candidate.investigation_next_steps == det_exp.investigation_next_steps

    def test_parse_candidate_explanation_strips_markdown_code_fences(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        fenced_json = """```json
        {
            "executive_summary": "Fenced executive summary.",
            "operational_problem_narrative": "Fenced problem narrative.",
            "economic_interpretation": "Fenced economic narrative.",
            "strategic_rationale": "Fenced strategic rationale.",
            "key_assumptions_and_risks": ["Fenced risk"],
            "investigation_next_steps": ["Fenced step"]
        }
        ```"""

        candidate = parse_candidate_explanation(fenced_json, det_exp)
        assert candidate.executive_summary == "Fenced executive summary."

    def test_parse_candidate_explanation_rejects_invalid_json(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        with pytest.raises(ValueError) as exc:
            parse_candidate_explanation("This is plain text, not JSON", det_exp)
        assert "not valid JSON" in str(exc.value)

    def test_parse_candidate_explanation_rejects_missing_required_fields(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        incomplete_json = json.dumps({
            "executive_summary": "Summary",
            # missing operational_problem_narrative
            "economic_interpretation": "Economics",
            "strategic_rationale": "Strategy",
            "key_assumptions_and_risks": [],
            "investigation_next_steps": [],
        })
        with pytest.raises(ValueError) as exc:
            parse_candidate_explanation(incomplete_json, det_exp)
        assert "operational_problem_narrative" in str(exc.value)

    def test_parse_candidate_explanation_metadata_cannot_be_overwritten(self, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        malicious_json = json.dumps({
            "opportunity_id": "TAMPERED_ID_999",
            "archetype": "RECURRENCE_REDUCTION",
            "portfolio_cohort": "BLOCKED_BY_BARRIERS",
            "rank_order": 999,
            "composite_priority_score": 9999.0,
            "target_entity": "Hacked Entity",
            "executive_summary": "Executive summary here.",
            "operational_problem_narrative": "Problem narrative here.",
            "economic_interpretation": "Economic narrative here.",
            "strategic_rationale": "Strategic narrative here.",
            "key_assumptions_and_risks": ["Assumption 1"],
            "investigation_next_steps": ["Step 1"],
        })
        candidate = parse_candidate_explanation(malicious_json, det_exp)
        # Structural fields must come exclusively from deterministic baseline
        assert candidate.opportunity_id == det_exp.opportunity_id
        assert candidate.archetype == det_exp.archetype
        assert candidate.portfolio_cohort == det_exp.portfolio_cohort
        assert candidate.rank_order == det_exp.rank_order
        assert candidate.composite_priority_score == det_exp.composite_priority_score
        assert candidate.target_entity == det_exp.target_entity
        assert candidate.key_assumptions_and_risks == det_exp.key_assumptions_and_risks
        assert candidate.investigation_next_steps == det_exp.investigation_next_steps


# ==============================================================================
# Group 2: Pipeline Core Execution & Grounding Guardrails
# ==============================================================================

class TestExplanationPipelineExecution:
    def test_deterministic_only_execution_preserves_not_evaluated(self, sample_audit_response):
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=False)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        assert resp.model_identifier is None
        assert len(resp.explanations) == 1

        exp = resp.explanations[0]
        assert exp.grounding_audit is not None
        assert exp.grounding_audit.status == GroundingVerificationStatus.NOT_EVALUATED
        assert exp.grounding_audit.discrepancies == []

    def test_unconfigured_provider_graceful_fallback(self, sample_audit_response, monkeypatch):
        monkeypatch.setattr("app.core.config.settings.LLM_API_KEY", None)

        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=None)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        assert resp.model_identifier is None
        assert len(resp.explanations) == 1

        exp = resp.explanations[0]
        assert exp.grounding_audit is not None
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Provider configuration error" in d for d in exp.grounding_audit.discrepancies)

    def test_valid_llm_grounded_output_accepted(self, sample_audit_response, sample_dossier):
        # Build LLM response matching exact dossier values
        det_exp = generate_opportunity_explanation(sample_dossier)
        mock_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=mock_output, model="gpt-4o-grounded"),
            model="gpt-4o-grounded",
        )

        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        assert resp.explanation_source == ExplanationSource.LLM_AUGMENTED
        assert resp.model_identifier == "gpt-4o-grounded"
        assert len(resp.explanations) == 1

        exp = resp.explanations[0]
        assert exp.grounding_audit is not None
        assert exp.grounding_audit.status == GroundingVerificationStatus.VERIFIED_GROUNDED
        assert exp.grounding_audit.discrepancies == []

    def test_hallucinated_number_rejected_and_fallback_applied(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        hallucinated_output = json.dumps({
            "executive_summary": "Latency is 999999.0s in Review -> Approval.",  # Hallucinated duration!
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=hallucinated_output, model="gpt-4o-hallucinating"),
            model="gpt-4o-hallucinating",
        )

        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        # Fallback applied: engine source is DETERMINISTIC_TEMPLATE because 0 opportunities were verified
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        assert resp.model_identifier is None

        exp = resp.explanations[0]
        assert exp.grounding_audit is not None
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Unsupported duration claim" in d for d in exp.grounding_audit.discrepancies)
        # Content returned is the clean deterministic baseline text, not the hallucinated text
        assert "999999.0s" not in exp.executive_summary

    def test_unsupported_entity_rejected_and_fallback_applied(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        hallucinated_entity_output = json.dumps({
            "executive_summary": "Latency observed in activity 'NonExistentActivity_XYZ'.",
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=hallucinated_entity_output, model="gpt-4o"),
        )

        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("NonExistentActivity_XYZ" in d for d in exp.grounding_audit.discrepancies)

    def test_causal_and_guaranteed_savings_claims_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        banned_output = json.dumps({
            "executive_summary": "This bottleneck definitively causes delay.",
            "operational_problem_narrative": "It provides guaranteed savings of $50,000.",
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=banned_output, model="gpt-4o"),
        )

        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        discrepancies_text = " ".join(exp.grounding_audit.discrepancies)
        assert "Causal assertion guardrail violation" in discrepancies_text
        assert "Economic guardrail violation" in discrepancies_text

    def test_provider_timeout_resilience(self, sample_audit_response):
        def timeout_handler(req):
            raise LLMTimeoutError("Socket timed out after 30.0 seconds")

        provider = MockLLMProvider(handler=timeout_handler)
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Socket timed out" in d for d in exp.grounding_audit.discrepancies)

    def test_provider_network_and_http_error_resilience(self, sample_audit_response):
        def http_err_handler(req):
            raise LLMResponseError("Provider returned HTTP 500: Internal error", status_code=500)

        provider = MockLLMProvider(handler=http_err_handler)
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)

        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("HTTP 500" in d for d in exp.grounding_audit.discrepancies)

    def test_smuggled_claims_in_list_fields_neutralized_by_deterministic_constraints(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        # Model attempts to inject ungrounded duration, phantom entity, and causal assertion via list fields
        smuggled_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": ["Latency measured at 88888.0s across the batch.", "Definitively causes failure."],
            "investigation_next_steps": ["Investigate activity 'Ghost_Activity_Phantom'."],
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=smuggled_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        exp = resp.explanations[0]
        # Strict deterministic constraints in parse_candidate_explanation drop all smuggled list items
        assert "88888.0s" not in " ".join(exp.key_assumptions_and_risks)
        assert "Ghost_Activity_Phantom" not in " ".join(exp.investigation_next_steps)
        assert "Definitively causes failure" not in " ".join(exp.key_assumptions_and_risks)
        assert exp.key_assumptions_and_risks == det_exp.key_assumptions_and_risks
        assert exp.investigation_next_steps == det_exp.investigation_next_steps

    def test_smuggled_unsupported_numeric_claim_in_prose_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        smuggled_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": "Observed 88888.0s latency in Review -> Approval.",  # Hallucinated duration in prose!
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=smuggled_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Unsupported duration claim" in d for d in exp.grounding_audit.discrepancies)
        assert "88888.0s" not in exp.operational_problem_narrative

    def test_smuggled_fabricated_entity_in_prose_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        smuggled_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": "Prioritize activity 'Ghost_Activity_Phantom' immediately.",  # Phantom entity in prose!
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=smuggled_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Ghost_Activity_Phantom" in d for d in exp.grounding_audit.discrepancies)

    def test_smuggled_causal_assertion_in_prose_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        smuggled_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": "This transition definitively causes delays downstream.",  # Causal claim in prose!
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=smuggled_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Causal assertion guardrail violation" in d for d in exp.grounding_audit.discrepancies)

    def test_smuggled_guaranteed_savings_in_prose_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        smuggled_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": "Automation will achieve guaranteed cash savings for the firm.",  # Banned claim in prose!
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=smuggled_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Economic guardrail violation" in d for d in exp.grounding_audit.discrepancies)

    def test_unmonetized_opportunity_hallucinated_currency_rejected(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        hallucinated_currency_output = json.dumps({
            "executive_summary": det_exp.executive_summary,
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": "This yields $45,000 in net annual benefit.",
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=hallucinated_currency_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Economic guardrail violation" in d for d in exp.grounding_audit.discrepancies)
        # Verify fallback preserves unknown/unmonetized economics rather than $0 or fabricated value
        assert "$45,000" not in exp.economic_interpretation
        assert "remain unknown and unmonetized" in exp.economic_interpretation

    def test_malformed_model_output_fallback_semantics(self, sample_audit_response):
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content="Not a JSON object {broken", model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        assert resp.explanation_source == ExplanationSource.DETERMINISTIC_TEMPLATE
        exp = resp.explanations[0]
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert any("Generation failed" in d for d in exp.grounding_audit.discrepancies)

    def test_rejected_llm_response_never_leaks_or_certifies_baseline(self, sample_audit_response, sample_dossier):
        det_exp = generate_opportunity_explanation(sample_dossier)
        hallucinated_output = json.dumps({
            "executive_summary": "SECRET_LEAK_12345: Latency measured at 999999.0s in Review -> Approval.",
            "operational_problem_narrative": det_exp.operational_problem_narrative,
            "economic_interpretation": det_exp.economic_interpretation,
            "strategic_rationale": det_exp.strategic_rationale,
            "key_assumptions_and_risks": det_exp.key_assumptions_and_risks,
            "investigation_next_steps": det_exp.investigation_next_steps,
        })
        provider = MockLLMProvider(
            handler=lambda req: LLMGenerateResponse(content=hallucinated_output, model="gpt-4o"),
        )
        resp = run_explanation_pipeline(sample_audit_response, enable_llm=True, provider=provider)
        exp = resp.explanations[0]
        # Must NOT falsely certify the baseline as VERIFIED_GROUNDED
        assert exp.grounding_audit.status == GroundingVerificationStatus.FALLBACK_APPLIED
        assert exp.grounding_audit.status != GroundingVerificationStatus.VERIFIED_GROUNDED
        # Must NOT leak untrusted text into output
        assert "SECRET_LEAK_12345" not in exp.executive_summary
        assert exp.executive_summary == det_exp.executive_summary


# ==============================================================================
# Group 3: FastAPI Endpoint Integration Tests
# ==============================================================================

class TestExplanationEndpointAPI:
    def test_empty_filename_rejected(self, client):
        boundary = "boundary789"
        body = (
            b"--" + boundary.encode() + b"\r\n"
            b'Content-Disposition: form-data; name="file"; filename=""\r\n'
            b"Content-Type: text/csv\r\n\r\n"
            b"case_id,activity,timestamp\r\n"
            b"--" + boundary.encode() + b"--\r\n"
        )
        headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
        response = client.post(f"{settings.API_V1_STR}/explanation/generate", content=body, headers=headers)
        assert response.status_code == 400
        assert "Filename cannot be empty" in response.json()["detail"]

    def test_unsupported_file_extension_rejected(self, client):
        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("data.txt", b"case_id,activity,timestamp\n", "text/plain")},
        )
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]

    def test_malformed_json_parameters_rejected(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data={"prioritisation_weights": "not-valid-json"},
        )
        assert response.status_code == 400
        assert "Invalid JSON" in response.json()["detail"]

    def test_unknown_opportunity_id_rejected(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data={"opportunity_id": "OPP-NONEXISTENT-999"},
        )
        assert response.status_code == 400
        assert "not found" in response.json()["detail"]

    def test_valid_deterministic_request_success(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data={"enable_llm": "false"},
        )
        assert response.status_code == 200
        data = response.json()

        assert data["explanation_source"] == "DETERMINISTIC_TEMPLATE"
        assert data["model_identifier"] is None
        assert "portfolio_summary" in data
        assert len(data["explanations"]) > 0

        # Grounding status is NOT_EVALUATED
        for exp in data["explanations"]:
            assert exp["grounding_audit"]["status"] == "NOT_EVALUATED"
            assert exp["grounding_audit"]["discrepancies"] == []

    def test_valid_llm_request_with_mock_provider_override(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        # Override FastAPI get_llm_provider dependency with our mock provider
        def mock_provider_dep():
            return MockLLMProvider()

        app.dependency_overrides[get_llm_provider] = mock_provider_dep
        try:
            response = client.post(
                f"{settings.API_V1_STR}/explanation/generate",
                files={"file": ("clean.csv", clean_bytes, "text/csv")},
                data={"enable_llm": "true"},
            )
            assert response.status_code == 200
            data = response.json()

            # When mock provider returns generic text, verifier catches discrepancy and applies fallback!
            # Returns HTTP 200 and FALLBACK_APPLIED without crashing
            for exp in data["explanations"]:
                assert exp["grounding_audit"]["status"] in ("VERIFIED_GROUNDED", "FALLBACK_APPLIED")
        finally:
            app.dependency_overrides.pop(get_llm_provider, None)

    def test_opportunity_id_filtering(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        # First query all to obtain an opportunity ID
        res_all = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data={"enable_llm": "false"},
        )
        assert res_all.status_code == 200
        all_exps = res_all.json()["explanations"]
        target_opp_id = all_exps[0]["opportunity_id"]

        # Filter by this opportunity ID
        res_filtered = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data={"enable_llm": "false", "opportunity_id": target_opp_id},
        )
        assert res_filtered.status_code == 200
        filtered_data = res_filtered.json()
        assert len(filtered_data["explanations"]) == 1
        assert filtered_data["explanations"][0]["opportunity_id"] == target_opp_id

    def test_file_size_limit_exceeded_rejected(self, client, monkeypatch):
        # Temporarily set max file size to 50 bytes for fast deterministic testing
        monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 50)
        oversized_content = b"case_id,activity,timestamp\n" * 10
        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("oversized.csv", oversized_content, "text/csv")},
        )
        assert response.status_code == 400
        assert "exceeds maximum allowed limit" in response.json()["detail"]

    def test_client_cannot_pass_fake_dossier_or_tamper_server_state(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        # Attempt to inject client-controlled dossier, rank, and verified status
        fake_payload = {
            "dossiers": json.dumps([{"opportunity_id": "FAKE_01", "rank_order": 1, "composite_priority_score": 100.0}]),
            "grounding_status": "VERIFIED_GROUNDED",
            "composite_priority_score": "99.9",
            "enable_llm": "false",
        }
        response = client.post(
            f"{settings.API_V1_STR}/explanation/generate",
            files={"file": ("clean.csv", clean_bytes, "text/csv")},
            data=fake_payload,
        )
        assert response.status_code == 200
        data = response.json()
        # Verify all emitted explanations have genuine server-derived opportunity IDs and NOT_EVALUATED status
        for exp in data["explanations"]:
            assert exp["opportunity_id"].startswith("opp_")
            assert exp["opportunity_id"] != "FAKE_01"
            assert exp["grounding_audit"]["status"] == "NOT_EVALUATED"

    def test_no_secret_or_prompt_leakage_in_error_fallback(self, client, sample_clean_path):
        with open(sample_clean_path, "rb") as f:
            clean_bytes = f.read()

        secret_token = "sk-proj-super-secret-key-that-must-never-leak"

        def secret_leaking_provider():
            def handler(req):
                raise LLMResponseError(f"HTTP 401 Unauthorized: Invalid key {secret_token}", status_code=401)
            return MockLLMProvider(handler=handler)

        app.dependency_overrides[get_llm_provider] = secret_leaking_provider
        try:
            response = client.post(
                f"{settings.API_V1_STR}/explanation/generate",
                files={"file": ("clean.csv", clean_bytes, "text/csv")},
                data={"enable_llm": "true"},
            )
            assert response.status_code == 200
            data = response.json()
            resp_str = json.dumps(data)
            assert secret_token not in resp_str
            assert "You are an executive communication assistant" not in resp_str
        finally:
            app.dependency_overrides.pop(get_llm_provider, None)
