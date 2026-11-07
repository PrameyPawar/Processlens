"""
Pydantic schemas for Phase 9 Evidence Architecture and Audit Dossier.
Defines models for exact event row anchors, case trace exemplars,
reproducible formula derivations, epistemic ledgers, and audit response payloads.
"""

from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, ConfigDict, Field

from app.schemas.opportunity import OpportunityArchetype
from app.schemas.prioritisation import PortfolioCohort


class EpistemicType(str, Enum):
    """
    Epistemic classification of statements, metrics, and parameters in ProcessLens.
    Prevents confusing observed empirical data with assumptions, hypotheses, estimates, or decisions.
    """
    FACT = "FACT"
    ASSUMPTION = "ASSUMPTION"
    HYPOTHESIS = "HYPOTHESIS"
    ESTIMATE = "ESTIMATE"
    DECISION = "DECISION"


class EpistemicItem(BaseModel):
    """
    An individual ledger entry with strict epistemic classification and origin provenance.
    """
    model_config = ConfigDict(extra="forbid")

    item_id: str = Field(..., description="Unique identifier for this epistemic item")
    epistemic_type: EpistemicType = Field(..., description="Epistemic status: FACT, ASSUMPTION, HYPOTHESIS, ESTIMATE, DECISION")
    statement: str = Field(..., description="Content or assertion of the item")
    source_or_basis: str = Field(..., description="Specific operational data, formula, user input, or policy rule source")
    provenance_details: Optional[str] = Field(None, description="Detailed provenance context or parameters")


class EventRowAnchor(BaseModel):
    """
    Anchors an exemplar event back to the original source CSV file.
    Provides both 1-based data-row index and 1-based physical CSV line number (accounting for header row).
    """
    model_config = ConfigDict(extra="forbid")

    row_index: int = Field(..., description="1-based data-row index (Row 1 is first data row after CSV header)")
    csv_line_number: int = Field(..., description="1-based physical line number in source CSV file (Line 1 is header row, Line 2 is first data row)")
    case_id: Optional[str] = Field(None, description="Case identifier")
    activity: Optional[str] = Field(None, description="Activity name")
    timestamp_raw: Optional[str] = Field(None, description="Original raw timestamp from source record")
    resource: Optional[str] = Field(None, description="Resource or user recorded on event")
    source_event_id: Optional[str] = Field(None, description="Source-system event identifier when supplied")
    role_in_evidence: str = Field(..., description="Role in evidence (e.g. 'TRANSITION_SOURCE', 'TRANSITION_TARGET', 'REPEATED_ACTIVITY', 'TRACE_START', 'TRACE_END', 'EXCLUDED_DATA_ROW')")


class CaseTraceExemplar(BaseModel):
    """
    A concrete operational case trace demonstrating the opportunity pattern.
    Limited to a maximum of three exemplars per opportunity.
    """
    model_config = ConfigDict(extra="forbid")

    case_id: str = Field(..., description="Case identifier")
    exemplar_metric_value: float = Field(..., description="Measured quantitative value for this exemplar (e.g. seconds or count)")
    exemplar_metric_description: str = Field(..., description="Description of the exemplar metric value")
    total_case_duration_seconds: Optional[float] = Field(None, description="Total elapsed cycle time of the case in seconds")
    event_anchors: List[EventRowAnchor] = Field(default_factory=list, description="Specific anchored events demonstrating the pattern")
    trace_summary: str = Field(..., description="Human-readable summary of the exemplar trace")


class MetricDerivationAudit(BaseModel):
    """
    Step-by-step mathematical or algorithmic derivation of a calculated metric or score.
    """
    model_config = ConfigDict(extra="forbid")

    metric_id: str = Field(..., description="Canonical metric ID (e.g. OPS_SCORE_V1, COMPOSITE_SCORE_V1)")
    formula_expression: str = Field(..., description="Mathematical formula or decision rule expression")
    input_variables: Dict[str, Any] = Field(default_factory=dict, description="Input variable names and their provided or derived values")
    intermediate_values: Dict[str, Any] = Field(default_factory=dict, description="Intermediate steps or unquantized calculations")
    output_value: Any = Field(..., description="Final output value produced by the formula")
    quantization_rule: str = Field(..., description="Rounding, precision, or truncation rule applied")
    limitations_and_assumptions: List[str] = Field(default_factory=list, description="Assumptions or validity limits of the calculation")


class OpportunityEvidenceDossier(BaseModel):
    """
    Complete evidence dossier for an individual prioritised opportunity.
    Connects raw operational data to findings, derivations, economics, readiness, and roadmap decisions.
    """
    model_config = ConfigDict(extra="forbid")

    opportunity_id: str = Field(..., description="Unique opportunity identifier")
    archetype: OpportunityArchetype = Field(..., description="Operational archetype")
    portfolio_cohort: PortfolioCohort = Field(..., description="Assigned portfolio cohort from Phase 8")
    rank_order: int = Field(..., description="Deterministic rank position in portfolio roadmap")
    composite_priority_score: Optional[float] = Field(None, description="Quantized composite priority score (0-100) or None if unscored")
    target_entity: str = Field(..., description="Target process entity (transition, activity, variant, etc.)")
    exemplars: List[CaseTraceExemplar] = Field(default_factory=list, description="Up to 3 deterministic exemplar cases")
    exemplar_selection_policy: str = Field(..., description="Deterministic sorting and selection rule used for exemplars")
    derivations: List[MetricDerivationAudit] = Field(default_factory=list, description="Audit of key formula derivations for this opportunity")
    epistemic_ledger: List[EpistemicItem] = Field(default_factory=list, description="Epistemic categorization of all associated findings and parameters")
    boundary_limitations: List[str] = Field(default_factory=list, description="Explicit boundaries and disclaimers regarding evidence scope")


class EvidenceAuditManifest(BaseModel):
    """
    Cryptographic and parameter manifest verifying the input dataset and execution context.
    """
    model_config = ConfigDict(extra="forbid")

    source_file_sha256: str = Field(..., description="SHA-256 hexadecimal digest of uploaded CSV bytes")
    source_filename: str = Field(..., description="Original filename of uploaded CSV")
    source_file_size_bytes: int = Field(..., description="Uploaded CSV file size in bytes")
    total_source_rows: int = Field(..., description="Total rows in source CSV")
    complete_cases_count: int = Field(..., description="Total complete cases reconstructed")
    reconciliation_status: str = Field(..., description="Timestamp accounting reconciliation status: RECONCILED or DISCREPANCY_DETECTED")
    effective_prioritisation_weights: Dict[str, float] = Field(default_factory=dict, description="Weights applied in prioritisation")
    formula_version: str = Field(default="v1.0", description="Version of formula rules applied")
    is_persisted_snapshot: bool = Field(default=False, description="Flag indicating dossier is recomputed on-demand, not persisted")
    notes: str = Field(..., description="Operational context and methodology notice")


class EvidenceAuditSummary(BaseModel):
    """
    Summary counts and distribution across emitted dossiers.
    """
    model_config = ConfigDict(extra="forbid")

    total_opportunities_evaluated: int = Field(..., description="Total opportunities in full prioritised portfolio")
    dossiers_emitted: int = Field(..., description="Number of dossiers returned after optional filtering")
    filter_applied: Optional[str] = Field(None, description="Opportunity ID filter if applied, otherwise None")
    cohort_distribution: Dict[str, int] = Field(default_factory=dict, description="Count of opportunities per portfolio cohort")


class EvidenceAuditResponse(BaseModel):
    """
    Root response model for POST /api/v1/evidence/audit.
    """
    model_config = ConfigDict(extra="forbid")

    manifest: EvidenceAuditManifest
    summary: EvidenceAuditSummary
    dossiers: List[OpportunityEvidenceDossier] = Field(default_factory=list)
