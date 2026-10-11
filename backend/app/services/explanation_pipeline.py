"""
Explanation generation pipeline orchestrator for ProcessLens Phase 10.5.
Connects Phase 9 evidence dossiers, Phase 10.2 deterministic templates,
Phase 10.4 LLM provider adapters, and Phase 10.3 grounding verification.

Operational Trust Boundaries:
- Step 1: Builds verified deterministic explanation baseline.
- Step 2: If LLM is requested and configured, assembles prompt and invokes provider.
- Step 3: All model output is treated as untrusted and passed to Phase 10.3 verifier.
- Step 4: Output is accepted as LLM_AUGMENTED ONLY if verifier returns VERIFIED_GROUNDED.
- Step 5: On any verification failure, provider timeout, network error, or configuration defect,
          the deterministic template is returned with FALLBACK_APPLIED and structured reasons.
- Step 6: When LLM generation is not evaluated, status remains truthfully NOT_EVALUATED.
"""

import time
from typing import Optional, List, Dict

from app.schemas.evidence import EvidenceAuditResponse
from app.schemas.explanation import (
    ExplanationResponse,
    OpportunityExplanation,
    ExplanationSource,
    GroundingVerificationStatus,
    GroundingAudit,
)
from app.schemas.llm import LLMGenerateRequest
from app.services.explanation_templates import (
    generate_deterministic_explanation_response,
)
from app.services.explanation_prompt import (
    build_opportunity_prompt,
    parse_candidate_explanation,
)
from app.services.grounding import verify_opportunity_explanation
from app.services.llm_provider import (
    BaseLLMProvider,
    OpenAICompatibleProvider,
    LLMProviderError,
    LLMConfigurationError,
    sanitize_message,
)


def run_explanation_pipeline(
    audit_response: EvidenceAuditResponse,
    enable_llm: bool = False,
    provider: Optional[BaseLLMProvider] = None,
) -> ExplanationResponse:
    """
    Executes the explanation generation pipeline across all opportunity dossiers.
    Guarantees deterministic fallback on any error, timeout, or grounding defect.
    """
    start_time = time.perf_counter()

    # Step 1: Build authoritative deterministic baseline response
    deterministic_resp = generate_deterministic_explanation_response(audit_response)

    # If LLM generation is not requested, preserve NOT_EVALUATED grounding status
    if not enable_llm:
        not_evaluated_explanations: List[OpportunityExplanation] = []
        for det_exp in deterministic_resp.explanations:
            exp_copy = det_exp.model_copy()
            exp_copy.grounding_audit = GroundingAudit(
                status=GroundingVerificationStatus.NOT_EVALUATED,
                verified_numbers=[],
                verified_entities=[],
                discrepancies=[],
            )
            not_evaluated_explanations.append(exp_copy)

        elapsed = round(time.perf_counter() - start_time, 4)
        return ExplanationResponse(
            manifest=deterministic_resp.manifest,
            portfolio_summary=deterministic_resp.portfolio_summary,
            explanations=not_evaluated_explanations,
            explanation_source=ExplanationSource.DETERMINISTIC_TEMPLATE,
            model_identifier=None,
            execution_duration_seconds=elapsed,
        )

    # Step 2: Resolve LLM provider if LLM generation is enabled
    resolved_provider: Optional[BaseLLMProvider] = provider
    if resolved_provider is None:
        try:
            resolved_provider = OpenAICompatibleProvider()
        except LLMConfigurationError as cfg_err:
            # Provider credentials or settings missing: graceful fallback to deterministic
            clean_err = sanitize_message(str(cfg_err))
            fallback_explanations: List[OpportunityExplanation] = []
            for det_exp in deterministic_resp.explanations:
                exp_copy = det_exp.model_copy()
                exp_copy.grounding_audit = GroundingAudit(
                    status=GroundingVerificationStatus.FALLBACK_APPLIED,
                    verified_numbers=[],
                    verified_entities=[],
                    discrepancies=[f"Provider configuration error: {clean_err}. Deterministic fallback applied."],
                )
                fallback_explanations.append(exp_copy)

            elapsed = round(time.perf_counter() - start_time, 4)
            return ExplanationResponse(
                manifest=deterministic_resp.manifest,
                portfolio_summary=deterministic_resp.portfolio_summary,
                explanations=fallback_explanations,
                explanation_source=ExplanationSource.DETERMINISTIC_TEMPLATE,
                model_identifier=None,
                execution_duration_seconds=elapsed,
            )

    # Step 3: Process each opportunity through the verification gate
    dossier_by_id = {d.opportunity_id: d for d in audit_response.dossiers}
    final_explanations: List[OpportunityExplanation] = []
    llm_verified_count = 0

    for det_exp in deterministic_resp.explanations:
        dossier = dossier_by_id.get(det_exp.opportunity_id)
        if dossier is None:
            # Defensive guard: preserve deterministic explanation if dossier missing
            final_explanations.append(det_exp)
            continue

        try:
            # 3.1 Build bounded prompt
            messages = build_opportunity_prompt(dossier, det_exp)

            # 3.2 Invoke provider
            req = LLMGenerateRequest(messages=messages, temperature=0.0)
            llm_resp = resolved_provider.generate(req)

            # 3.3 Parse candidate explanation (structural fields preserved from baseline)
            candidate = parse_candidate_explanation(llm_resp.content, det_exp)

            # 3.4 Verify grounding deterministically
            audit = verify_opportunity_explanation(candidate, dossier)

            if audit.status == GroundingVerificationStatus.VERIFIED_GROUNDED:
                # Acceptance gate passed
                candidate.grounding_audit = audit
                final_explanations.append(candidate)
                llm_verified_count += 1
            else:
                # Grounding failed: apply deterministic fallback with verifier discrepancies
                fallback = det_exp.model_copy()
                fallback.grounding_audit = audit
                final_explanations.append(fallback)

        except (LLMProviderError, ValueError, Exception) as exc:
            # Provider failure, malformed JSON, or unexpected error: graceful fallback
            clean_exc = sanitize_message(str(exc))
            fallback = det_exp.model_copy()
            fallback.grounding_audit = GroundingAudit(
                status=GroundingVerificationStatus.FALLBACK_APPLIED,
                verified_numbers=[],
                verified_entities=[],
                discrepancies=[f"Generation failed: {clean_exc}. Deterministic fallback applied."],
            )
            final_explanations.append(fallback)

    # Step 4: Determine source classification
    resolved_model_name = getattr(resolved_provider, "model", None)
    if llm_verified_count > 0:
        source = ExplanationSource.LLM_AUGMENTED
        model_id = str(resolved_model_name) if resolved_model_name else "llm-provider"
    else:
        source = ExplanationSource.DETERMINISTIC_TEMPLATE
        model_id = None

    elapsed = round(time.perf_counter() - start_time, 4)
    return ExplanationResponse(
        manifest=deterministic_resp.manifest,
        portfolio_summary=deterministic_resp.portfolio_summary,
        explanations=final_explanations,
        explanation_source=source,
        model_identifier=model_id,
        execution_duration_seconds=elapsed,
    )
