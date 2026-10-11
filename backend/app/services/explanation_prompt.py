"""
Prompt assembly and candidate response parsing for ProcessLens Phase 10.5.
Provides dedicated, testable functions for converting Phase 9 evidence dossiers
and deterministic template baselines into LLM chat prompts, and parsing
untrusted model completions into candidate OpportunityExplanation instances.

Prompt Design Principles:
- Operational evidence and deterministic findings are the sole source of analytical truth.
- The model is asked to improve executive readability and clarity only, not calculate metrics
  or infer causality.
- Minimum necessary evidence is included.
- Assembled prompts and provider secrets are never logged or returned in responses.
"""

import json
import re
from typing import List, Dict, Any, Optional

from app.schemas.evidence import OpportunityEvidenceDossier, EpistemicType
from app.schemas.explanation import OpportunityExplanation
from app.schemas.llm import LLMMessage, LLMRole


SYSTEM_PROMPT = """You are an executive communication assistant for ProcessLens, an operational process analysis system.
Your role is strictly to refine and improve the executive clarity, readability, and narrative flow of a process improvement opportunity explanation.

CRITICAL INSTRUCTIONS:
1. Ground Truth Invariant: The provided evidence dossier and baseline explanation are the ONLY source of analytical truth.
2. Do NOT Calculate: Never alter, compute, or fabricate any numbers, percentages, currencies, durations, or priority scores. Every number must match the provided baseline exactly.
3. No Causal Claims: Operational event logs show correlation, not proven causation. Never use phrases like 'definitively causes', 'conclusively proves', 'guarantees that', or 'direct cause of'.
4. No Guaranteed Savings: Capacity valuations are hypothetical labor reallocations, not cash savings. Never claim 'guaranteed savings', 'realized cash savings', or 'budget reductions'.
5. Missing Economics: If an opportunity is unmonetized or economic inputs are omitted, do not invent monetary figures or substitute $0.
6. Target Entities: Mention only the activities, transitions, and cases explicitly present in the provided evidence.
7. Output Format: Return ONLY a valid JSON object matching the requested schema with no extra text or markdown formatting.
"""


def build_opportunity_prompt(
    dossier: OpportunityEvidenceDossier,
    deterministic: OpportunityExplanation,
) -> List[LLMMessage]:
    """
    Constructs a minimal, structured prompt from a Phase 9 evidence dossier
    and its Phase 10.2 deterministic explanation baseline.
    """
    # Extract concise evidence facts from the epistemic ledger
    facts_summary: List[str] = []
    for item in dossier.epistemic_ledger:
        if item.epistemic_type == EpistemicType.FACT:
            facts_summary.append(f"- [FACT] {item.statement}")
        elif item.epistemic_type in (EpistemicType.ASSUMPTION, EpistemicType.ESTIMATE):
            facts_summary.append(f"- [{item.epistemic_type.value}] {item.statement}")

    # Extract exemplar traces
    exemplars_summary: List[str] = []
    for ex in dossier.exemplars:
        dur = f" (duration: {ex.total_case_duration_seconds:.1f}s)" if ex.total_case_duration_seconds is not None else ""
        exemplars_summary.append(
            f"- Case '{ex.case_id}': {ex.trace_summary}{dur}"
        )


    # Build prompt context
    user_content_dict: Dict[str, Any] = {
        "opportunity_metadata": {
            "opportunity_id": dossier.opportunity_id,
            "archetype": dossier.archetype.value,
            "portfolio_cohort": dossier.portfolio_cohort.value,
            "rank_order": dossier.rank_order,
            "target_entity": dossier.target_entity,
            "composite_priority_score": (
                round(dossier.composite_priority_score, 4)
                if dossier.composite_priority_score is not None
                else None
            ),
        },
        "verified_evidence_ledger": facts_summary[:10],
        "exemplars": exemplars_summary[:3],
        "baseline_draft_to_refine": {
            "executive_summary": deterministic.executive_summary,
            "operational_problem_narrative": deterministic.operational_problem_narrative,
            "economic_interpretation": deterministic.economic_interpretation,
            "strategic_rationale": deterministic.strategic_rationale,
            "key_assumptions_and_risks": deterministic.key_assumptions_and_risks,
            "investigation_next_steps": deterministic.investigation_next_steps,
        },
        "instructions": (
            "Refine the baseline draft for executive presentation. Maintain all exact numbers, "
            "caveats, assumptions, and entity names. Respond with a JSON object containing keys: "
            "'executive_summary', 'operational_problem_narrative', 'economic_interpretation', "
            "'strategic_rationale', 'key_assumptions_and_risks' (list of strings), and "
            "'investigation_next_steps' (list of strings)."
        ),
    }

    user_message_text = json.dumps(user_content_dict, indent=2)

    return [
        LLMMessage(role=LLMRole.SYSTEM, content=SYSTEM_PROMPT),
        LLMMessage(role=LLMRole.USER, content=user_message_text),
    ]


def parse_candidate_explanation(
    raw_content: str,
    deterministic: OpportunityExplanation,
) -> OpportunityExplanation:
    """
    Parses untrusted model text into a candidate OpportunityExplanation.
    Preserves all trusted structural fields from the deterministic baseline
    and extracts refined narrative fields from the model output.
    Raises ValueError on invalid JSON or missing required narrative fields.
    """
    cleaned = raw_content.strip()

    # Strip markdown code blocks if present (e.g. ```json ... ```)
    if cleaned.startswith("```"):
        match = re.search(r"```(?:json)?\s*(.*?)\s*```", cleaned, re.DOTALL)
        if match:
            cleaned = match.group(1).strip()
        else:
            cleaned = re.sub(r"^```[a-zA-Z]*\n?", "", cleaned)
            cleaned = re.sub(r"\n?```$", "", cleaned).strip()

    try:
        data = json.loads(cleaned)
    except Exception as exc:
        raise ValueError(f"Model output is not valid JSON: {exc}") from exc

    if not isinstance(data, dict):
        raise ValueError("Model output JSON is not an object.")

    # Validate required text fields
    required_text_fields = [
        "executive_summary",
        "operational_problem_narrative",
        "economic_interpretation",
        "strategic_rationale",
    ]
    for field in required_text_fields:
        val = data.get(field)
        if not isinstance(val, str) or not val.strip():
            raise ValueError(f"Model output missing non-empty string for field '{field}'.")

    # Optional list fields validation if supplied
    for list_field in ["key_assumptions_and_risks", "investigation_next_steps"]:
        if list_field in data:
            val = data[list_field]
            if not isinstance(val, list):
                raise ValueError(f"Model output field '{list_field}' must be a list of strings if provided.")
            for item in val:
                if not isinstance(item, str):
                    raise ValueError(f"Item in '{list_field}' must be a string, received {type(item).__name__}.")

    # Build untrusted candidate: structural fields and epistemic/governance lists
    # come strictly from deterministic baseline as strict deterministic constraints.
    # This prevents untrusted models from smuggling unsupported claims or hallucinations
    # into fields outside the four verified prose sections.
    return OpportunityExplanation(
        opportunity_id=deterministic.opportunity_id,
        archetype=deterministic.archetype,
        portfolio_cohort=deterministic.portfolio_cohort,
        rank_order=deterministic.rank_order,
        composite_priority_score=deterministic.composite_priority_score,
        target_entity=deterministic.target_entity,
        executive_summary=data["executive_summary"].strip(),
        operational_problem_narrative=data["operational_problem_narrative"].strip(),
        economic_interpretation=data["economic_interpretation"].strip(),
        strategic_rationale=data["strategic_rationale"].strip(),
        key_assumptions_and_risks=list(deterministic.key_assumptions_and_risks),
        investigation_next_steps=list(deterministic.investigation_next_steps),
        grounding_audit=None,
    )
