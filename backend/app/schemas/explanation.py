"""
Pydantic schemas for Phase 10 Explanation Layer.
Defines models for structured executive explanations, portfolio executive summaries,
grounding verification audits, and explanation response payloads.
"""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.opportunity import OpportunityArchetype
from app.schemas.prioritisation import PortfolioCohort
from app.schemas.evidence import EvidenceAuditManifest


class ExplanationSource(str, Enum):
    """
    Source mechanism that produced the explanation.
    """
    DETERMINISTIC_TEMPLATE = "DETERMINISTIC_TEMPLATE"
    LLM_AUGMENTED = "LLM_AUGMENTED"


class GroundingVerificationStatus(str, Enum):
    """
    Verification status of generated explanation against underlying evidence dossier.
    """
    NOT_EVALUATED = "NOT_EVALUATED"
    VERIFIED_GROUNDED = "VERIFIED_GROUNDED"
    FALLBACK_APPLIED = "FALLBACK_APPLIED"


class GroundingAudit(BaseModel):
    """
    Audit record verifying that all numerical claims, entities, and citations
    in the explanation are grounded directly in the deterministic evidence dossier.
    """
    model_config = ConfigDict(extra="forbid")

    status: GroundingVerificationStatus = Field(..., description="Grounding status: NOT_EVALUATED, VERIFIED_GROUNDED, or FALLBACK_APPLIED")
    verified_numbers: List[str] = Field(default_factory=list, description="List of numerical values verified against the evidence dossier")
    verified_entities: List[str] = Field(default_factory=list, description="List of activities, transitions, or variants verified against the dossier")
    discrepancies: List[str] = Field(default_factory=list, description="Any detected ungrounded claims or discrepancies")


class OpportunityExplanation(BaseModel):
    """
    Executive-ready, non-technical operational explanation for an individual prioritised opportunity.
    Directly grounded in the corresponding Phase 9 OpportunityEvidenceDossier.
    """
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str = Field(..., description="Unique opportunity identifier")
    archetype: OpportunityArchetype = Field(..., description="Operational archetype")
    portfolio_cohort: PortfolioCohort = Field(..., description="Assigned portfolio cohort from Phase 8")
    rank_order: int = Field(..., description="Deterministic rank position in portfolio roadmap")
    composite_priority_score: Optional[float] = Field(None, description="Quantized composite priority score (0-100) or None if unscored")
    target_entity: str = Field(..., description="Target process entity (transition, activity, variant, etc.)")
    executive_summary: str = Field(..., description="High-level 2-3 sentence overview suitable for operational leadership")
    operational_problem_narrative: str = Field(..., description="Concrete description of what was observed, referencing real traces and durations")
    economic_interpretation: str = Field(..., description="Explanation of labor hours, capacity valuation, and cost assumptions with explicit caveats")
    strategic_rationale: str = Field(..., description="Why this opportunity sits in its assigned portfolio cohort and ranking position")
    key_assumptions_and_risks: List[str] = Field(default_factory=list, description="Explicit assumptions, hypotheses, estimates, and data limitations")
    investigation_next_steps: List[str] = Field(default_factory=list, description="Recommended human operational investigation actions before automation")
    grounding_audit: Optional[GroundingAudit] = Field(None, description="Independent grounding verification record; None when no external verifier has run")


class PortfolioExecutiveSummary(BaseModel):
    """
    High-level executive briefing across the entire prioritised opportunity portfolio.
    """
    model_config = ConfigDict(extra="forbid")

    overall_narrative: str = Field(..., description="Executive narrative synthesizing total candidates, cohorts, and roadmap sequence")
    top_recommended_actions: List[str] = Field(default_factory=list, description="Top actionable recommendations based on cohort precedence")
    foundational_prerequisites: List[str] = Field(default_factory=list, description="Prerequisite data quality or governance improvements required before automating")
    portfolio_economics_caveat: str = Field(..., description="Explicit disclaimer regarding non-additive capacity figures and financial boundaries")


class ExplanationResponse(BaseModel):
    """
    Response model aggregating portfolio executive summary, opportunity explanations,
    source metadata, and cryptographic evidence manifest.
    """
    model_config = ConfigDict(extra="forbid")

    manifest: EvidenceAuditManifest = Field(..., description="Cryptographic evidence manifest from Phase 9")
    portfolio_summary: PortfolioExecutiveSummary = Field(..., description="Portfolio-level executive briefing")
    explanations: List[OpportunityExplanation] = Field(default_factory=list, description="List of per-opportunity executive explanations")
    explanation_source: ExplanationSource = Field(..., description="Engine source: DETERMINISTIC_TEMPLATE or LLM_AUGMENTED")
    model_identifier: Optional[str] = Field(None, description="Identifier of the model used if LLM_AUGMENTED, otherwise None")
    execution_duration_seconds: float = Field(..., description="Execution duration in seconds")
