"""
Pydantic schemas for Phase 6 Automation Readiness Assessment.
Defines typed models for multi-dimensional readiness evaluation, domain intakes,
discrepancy flags, and categorical readiness outcomes.
"""

from enum import Enum
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

from app.schemas.opportunity import OpportunityArchetype


class DimensionState(str, Enum):
    """Evaluation state of an individual readiness dimension."""
    FAVORABLE = "FAVORABLE"                          # Characteristics directly support straightforward automation
    PREREQUISITE_REQUIRED = "PREREQUISITE_REQUIRED"  # Feasible with documented prerequisites or human-in-the-loop controls
    PROHIBITIVE_BARRIER = "PROHIBITIVE_BARRIER"      # Established hard prohibition on the assessed automation approach
    UNKNOWN = "UNKNOWN"                              # Domain intake has not been supplied
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"  # Event log sample size is inadequate for empirical heuristics


class OverallReadinessTier(str, Enum):
    """
    Categorical readiness conclusion evaluated in strict non-compensatory precedence:
    1. PROHIBITED_OR_BLOCKED
    2. INSUFFICIENT_CRITICAL_EVIDENCE
    3. PREREQUISITES_REQUIRED
    4. READY_FOR_SPECIFICATION
    """
    PROHIBITED_OR_BLOCKED = "PROHIBITED_OR_BLOCKED"
    INSUFFICIENT_CRITICAL_EVIDENCE = "INSUFFICIENT_CRITICAL_EVIDENCE"
    PREREQUISITES_REQUIRED = "PREREQUISITES_REQUIRED"
    READY_FOR_SPECIFICATION = "READY_FOR_SPECIFICATION"


class EvidenceProvenance(str, Enum):
    """Source of truth for dimension evidence."""
    LOG_MEASURED = "LOG_MEASURED"             # Derived deterministically from event log
    DOMAIN_INPUT = "DOMAIN_INPUT"             # Provided via structured user/domain intake
    COMPUTED_SYNTHESIS = "COMPUTED_SYNTHESIS" # Evaluated across both log and domain evidence
    DEFAULT_UNKNOWN = "DEFAULT_UNKNOWN"       # Unassessed default awaiting domain intake


class DigitalDataFormat(str, Enum):
    """Format and digital structure of task inputs and handoff payloads."""
    STRUCTURED_DIGITAL = "STRUCTURED_DIGITAL"       # Database records, API payloads, EDI, structured JSON/XML
    SEMI_STRUCTURED = "SEMI_STRUCTURED"             # Standard PDFs, structured email text requiring extraction
    UNSTRUCTURED_OR_PAPER = "UNSTRUCTURED_OR_PAPER" # Paper forms, physical mail, phone intake, freehand notes
    UNKNOWN = "UNKNOWN"


class SystemInterfaceType(str, Enum):
    """Accessibility of target system interfaces for integration."""
    DIRECT_API_OR_DB = "DIRECT_API_OR_DB"           # Documented REST/SOAP API or direct database hook
    ACCESSIBLE_GUI = "ACCESSIBLE_GUI"               # Standard web/desktop UI accessible for automation
    RESTRICTED_OR_AIRGAPPED = "RESTRICTED_OR_AIRGAPPED" # Citrix/terminal emulator without API or air-gapped system
    PROHIBITED_ACCESS = "PROHIBITED_ACCESS"         # Legal/contractual terms strictly forbid automated interface access
    UNKNOWN = "UNKNOWN"


class RuleDeterminism(str, Enum):
    """Degree of codification and stability of business rules governing the task."""
    DETERMINISTIC_RULES = "DETERMINISTIC_RULES"     # Clear, documented IF-THEN rules; negligible ambiguity
    MIXED_RULES = "MIXED_RULES"                     # Documented rules with frequent edge-case interpretations
    DISCRETIONARY = "DISCRETIONARY"                 # Subjective judgment, aesthetic taste, or commercial negotiation
    UNKNOWN = "UNKNOWN"


class HumanSupervisionRequirement(str, Enum):
    """Level of human discretion and supervision mandated for the task."""
    UNATTENDED_FEASIBLE = "UNATTENDED_FEASIBLE"     # Routine verification suitable for straight-through automation
    HUMAN_IN_THE_LOOP = "HUMAN_IN_THE_LOOP"         # Requires human validation, approval gate, or second review
    EXCLUSIVELY_HUMAN = "EXCLUSIVELY_HUMAN"         # Mandated human relationship, counseling, or executive discretion
    UNKNOWN = "UNKNOWN"


class GovernanceConstraint(str, Enum):
    """Regulatory, safety, and legal compliance constraints."""
    STANDARD_BUSINESS = "STANDARD_BUSINESS"         # Standard business procedures; normal audit trail
    REGULATED_AUDIT = "REGULATED_AUDIT"             # Regulated (e.g. FDA, SOX, HIPAA); formal audit trail required
    PROHIBITED_BY_LAW = "PROHIBITED_BY_LAW"         # Statutory or regulatory mandate prohibiting automated execution
    UNKNOWN = "UNKNOWN"


class OpportunityDomainAssessmentInput(BaseModel):
    """Domain intake submitted for a specific opportunity candidate."""
    opportunity_id: str = Field(
        ...,
        description="Target OpportunityCandidate.id generated from the CSV (must match an existing opportunity)"
    )
    digital_data_format: DigitalDataFormat = Field(
        default=DigitalDataFormat.UNKNOWN,
        description="Format of input/output data payloads"
    )
    system_interface: SystemInterfaceType = Field(
        default=SystemInterfaceType.UNKNOWN,
        description="Interface accessibility of target applications"
    )
    rule_determinism: RuleDeterminism = Field(
        default=RuleDeterminism.UNKNOWN,
        description="Stability and codification of business rules"
    )
    supervision_requirement: HumanSupervisionRequirement = Field(
        default=HumanSupervisionRequirement.UNKNOWN,
        description="Human supervision and discretionary judgment required"
    )
    governance_constraint: GovernanceConstraint = Field(
        default=GovernanceConstraint.UNKNOWN,
        description="Safety, legal, and regulatory compliance constraints"
    )
    domain_notes: Optional[str] = Field(
        default=None,
        description="Optional operational notes or caveats from process owners"
    )


class ReadinessDiscrepancy(BaseModel):
    """Flagged contradiction between domain claims and empirical log patterns."""
    dimension: str = Field(
        ...,
        description="Readiness dimension where discrepancy was identified"
    )
    domain_claim: str = Field(
        ...,
        description="Assertion made in the domain intake"
    )
    observed_event_evidence: str = Field(
        ...,
        description="Empirical observation measured in the event log"
    )
    reconciliation_guidance: str = Field(
        ...,
        description="Investigation guidance for process owners to resolve the contradiction"
    )


class DimensionDetail(BaseModel):
    """Detailed evaluation of an individual readiness dimension."""
    dimension_name: str = Field(
        ...,
        description="Name of the evaluated dimension"
    )
    state: DimensionState = Field(
        ...,
        description="Assessed state: FAVORABLE, PREREQUISITE_REQUIRED, PROHIBITIVE_BARRIER, UNKNOWN, INSUFFICIENT_EVIDENCE"
    )
    provenance: EvidenceProvenance = Field(
        ...,
        description="Information source: LOG_MEASURED, DOMAIN_INPUT, COMPUTED_SYNTHESIS, DEFAULT_UNKNOWN"
    )
    observed_facts: List[str] = Field(
        default_factory=list,
        description="Empirical facts or confirmed domain assertions supporting this dimension"
    )
    assumptions: List[str] = Field(
        default_factory=list,
        description="Stated assumptions or unverified domain premises"
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Technical or procedural prerequisites required prior to automation specification"
    )
    blockers: List[str] = Field(
        default_factory=list,
        description="Established prohibitions or barriers preventing automation"
    )


class OpportunityReadinessResult(BaseModel):
    """Complete readiness evaluation for a specific opportunity candidate."""
    opportunity_id: str = Field(
        ...,
        description="Identifier of the assessed OpportunityCandidate"
    )
    target_entity: str = Field(
        ...,
        description="Target process entity (transition or activity)"
    )
    archetype: OpportunityArchetype = Field(
        ...,
        description="Opportunity archetype"
    )
    source_finding_ids: List[str] = Field(
        ...,
        description="Traceable Phase 4 ProblemFinding IDs underpinning this opportunity"
    )
    overall_readiness_tier: OverallReadinessTier = Field(
        ...,
        description="Categorical readiness outcome following strict precedence"
    )

    # Six Core Dimensions
    task_repeatability_and_rule_stability: DimensionDetail = Field(
        ...,
        description="Repeatability observed in event log and business rule determinism"
    )
    digital_inputs_and_outputs: DimensionDetail = Field(
        ...,
        description="Structure and digitization of input and handoff data"
    )
    system_interface_accessibility: DimensionDetail = Field(
        ...,
        description="Integration access and technical interface availability"
    )
    exception_frequency_and_judgment: DimensionDetail = Field(
        ...,
        description="Observed empirical variation and required human discretionary judgment"
    )
    safety_regulatory_and_governance: DimensionDetail = Field(
        ...,
        description="Legal mandates, physical safety, and compliance audit controls"
    )
    evidence_completeness_and_uncertainty: DimensionDetail = Field(
        ...,
        description="Coverage of required domain evidence and empirical sample adequacy"
    )

    discrepancies: List[ReadinessDiscrepancy] = Field(
        default_factory=list,
        description="Flagged contradictions between domain assertions and empirical event logs"
    )
    hard_blockers: List[str] = Field(
        default_factory=list,
        description="Established prohibitions preventing the assessed automation approach"
    )
    prerequisites: List[str] = Field(
        default_factory=list,
        description="Actionable technical or process prerequisites required prior to automation"
    )
    limitations: List[str] = Field(
        default_factory=list,
        description="Strict disclaimers and scope boundaries"
    )


class ReadinessSummary(BaseModel):
    """Aggregate summary counts of evaluated opportunities."""
    evaluated_opportunities_count: int = Field(
        ...,
        description="Total opportunity candidates evaluated"
    )
    ready_for_specification_count: int = Field(
        0,
        description="Opportunities meeting all criteria for detailed technical specification"
    )
    prerequisites_required_count: int = Field(
        0,
        description="Opportunities feasible once prerequisites or human-in-the-loop controls are resolved"
    )
    prohibited_or_blocked_count: int = Field(
        0,
        description="Opportunities with established hard prohibitions on automated execution"
    )
    insufficient_critical_evidence_count: int = Field(
        0,
        description="Opportunities lacking required domain intake or adequate empirical observations"
    )
    discrepancy_count: int = Field(
        0,
        description="Total flagged contradictions between domain claims and empirical log metrics"
    )


class ReadinessAssessmentResponse(BaseModel):
    """Top-level response payload for POST /api/v1/readiness/assess."""
    filename: str = Field(
        ...,
        description="Name of the analyzed CSV event log file"
    )
    summary: ReadinessSummary = Field(
        ...,
        description="Aggregate summary of readiness outcomes"
    )
    assessments: List[OpportunityReadinessResult] = Field(
        ...,
        description="List of detailed readiness assessments for each opportunity candidate"
    )
