"""
Comprehensive test suite for Phase 6 Automation Readiness Assessment.
Tests categorical precedence, dimension-level evaluations, partial domain assessments,
established prohibitions, human-in-the-loop prerequisites, contradictory evidence,
legitimate repetition handling, invalid opportunity IDs, and deterministic behavior
across all four synthetic datasets.
"""

import os
import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems
from app.services.opportunity import detect_improvement_opportunities
from app.services.readiness import (
    parse_domain_assessments_json,
    assess_opportunities_readiness,
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
    ReadinessAssessmentResponse,
)

client = TestClient(app)

DATA_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "data",
        "ProcessLens_Development_Data",
        "samples",
    )
)


# ---------------------------------------------------------------------------
# Unit & Domain Service Tests
# ---------------------------------------------------------------------------

def test_readiness_default_unknown_without_domain_inputs():
    """
    Verifies that when an event log is analyzed without domain inputs:
      1. All opportunities evaluate to INSUFFICIENT_CRITICAL_EVIDENCE.
      2. Domain-dependent dimensions evaluate to UNKNOWN with DEFAULT_UNKNOWN provenance.
      3. Zero unverified claims of automation feasibility are made.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    result = assess_opportunities_readiness(opportunities, domain_assessments=None, filename="clean.csv")

    assert result.summary.evaluated_opportunities_count > 0
    assert result.summary.insufficient_critical_evidence_count == result.summary.evaluated_opportunities_count
    assert result.summary.ready_for_specification_count == 0
    assert result.summary.prohibited_or_blocked_count == 0

    for assessment in result.assessments:
        assert assessment.overall_readiness_tier == OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE
        assert assessment.digital_inputs_and_outputs.state == DimensionState.UNKNOWN
        assert assessment.digital_inputs_and_outputs.provenance == EvidenceProvenance.DEFAULT_UNKNOWN
        assert assessment.system_interface_accessibility.state == DimensionState.UNKNOWN
        assert assessment.system_interface_accessibility.provenance == EvidenceProvenance.DEFAULT_UNKNOWN
        assert assessment.safety_regulatory_and_governance.state == DimensionState.UNKNOWN
        assert len(assessment.source_finding_ids) >= 1
        assert any("does NOT authorize production deployment" in lim for lim in assessment.limitations)


def test_readiness_established_hard_prohibition_barrier():
    """
    Verifies that an established prohibition on automated execution:
      1. Strictly assigns PROHIBITED_OR_BLOCKED (Precedence 1).
      2. Overrides high volume (e.g. 750 cases) and 100% path standardization.
      3. Distinguishes hard prohibitions from mere technical difficulty.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    target_opp = opportunities.opportunities[0]

    domain_input = OpportunityDomainAssessmentInput(
        opportunity_id=target_opp.id,
        digital_data_format=DigitalDataFormat.STRUCTURED_DIGITAL,
        system_interface=SystemInterfaceType.PROHIBITED_ACCESS,  # Hard prohibition
        rule_determinism=RuleDeterminism.DETERMINISTIC_RULES,
        supervision_requirement=HumanSupervisionRequirement.UNATTENDED_FEASIBLE,
        governance_constraint=GovernanceConstraint.STANDARD_BUSINESS,
    )

    result = assess_opportunities_readiness(opportunities, [domain_input], "clean.csv")
    assessed = next(a for a in result.assessments if a.opportunity_id == target_opp.id)

    assert assessed.overall_readiness_tier == OverallReadinessTier.PROHIBITED_OR_BLOCKED
    assert assessed.system_interface_accessibility.state == DimensionState.PROHIBITIVE_BARRIER
    assert len(assessed.hard_blockers) >= 1
    assert "strictly prohibit automated interface access" in assessed.hard_blockers[0]


def test_readiness_human_in_the_loop_and_document_prerequisites():
    """
    Verifies that safety-critical work, discretionary judgment, or semi-structured documents:
      1. Do NOT cause PROHIBITED_OR_BLOCKED.
      2. Evaluate to PREREQUISITES_REQUIRED (Precedence 3).
      3. Actionable prerequisites and human-in-the-loop checkpoints are generated.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    target_opp = opportunities.opportunities[0]

    domain_input = OpportunityDomainAssessmentInput(
        opportunity_id=target_opp.id,
        digital_data_format=DigitalDataFormat.SEMI_STRUCTURED,  # PDF forms -> prerequisite
        system_interface=SystemInterfaceType.DIRECT_API_OR_DB,
        rule_determinism=RuleDeterminism.DETERMINISTIC_RULES,
        supervision_requirement=HumanSupervisionRequirement.HUMAN_IN_THE_LOOP,  # Human review -> prerequisite
        governance_constraint=GovernanceConstraint.REGULATED_AUDIT,  # Compliance audit -> prerequisite
    )

    result = assess_opportunities_readiness(opportunities, [domain_input], "clean.csv")
    assessed = next(a for a in result.assessments if a.opportunity_id == target_opp.id)

    assert assessed.overall_readiness_tier == OverallReadinessTier.PREREQUISITES_REQUIRED
    assert assessed.overall_readiness_tier != OverallReadinessTier.PROHIBITED_OR_BLOCKED
    assert len(assessed.prerequisites) >= 3
    assert any("OCR/Document AI" in p for p in assessed.prerequisites)
    assert any("human-in-the-loop" in p.lower() for p in assessed.prerequisites)
    assert any("audit logging" in p.lower() for p in assessed.prerequisites)


def test_readiness_ready_for_specification_and_guardrail():
    """
    Verifies that when all dimensions are favorable:
      1. Candidate evaluates to READY_FOR_SPECIFICATION (Precedence 4).
      2. Explicit guardrail is stated: specification readiness does not authorize production deployment.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    target_opp = opportunities.opportunities[0]

    domain_input = OpportunityDomainAssessmentInput(
        opportunity_id=target_opp.id,
        digital_data_format=DigitalDataFormat.STRUCTURED_DIGITAL,
        system_interface=SystemInterfaceType.DIRECT_API_OR_DB,
        rule_determinism=RuleDeterminism.DETERMINISTIC_RULES,
        supervision_requirement=HumanSupervisionRequirement.UNATTENDED_FEASIBLE,
        governance_constraint=GovernanceConstraint.STANDARD_BUSINESS,
    )

    result = assess_opportunities_readiness(opportunities, [domain_input], "clean.csv")
    assessed = next(a for a in result.assessments if a.opportunity_id == target_opp.id)

    assert assessed.overall_readiness_tier == OverallReadinessTier.READY_FOR_SPECIFICATION
    assert assessed.task_repeatability_and_rule_stability.state == DimensionState.FAVORABLE
    assert assessed.digital_inputs_and_outputs.state == DimensionState.FAVORABLE
    assert assessed.system_interface_accessibility.state == DimensionState.FAVORABLE
    assert assessed.exception_frequency_and_judgment.state == DimensionState.FAVORABLE
    assert assessed.safety_regulatory_and_governance.state == DimensionState.FAVORABLE
    assert assessed.evidence_completeness_and_uncertainty.state == DimensionState.FAVORABLE
    assert len(assessed.hard_blockers) == 0

    # Guardrail assertion
    guardrail_found = any(
        "does NOT authorize production deployment" in lim for lim in assessed.limitations
    )
    assert guardrail_found is True


def test_readiness_contradictory_evidence_detection():
    """
    Verifies that when a domain intake claims unattended feasibility, but empirical event data
    exhibits high repetition or variation:
      1. A ReadinessDiscrepancy is emitted.
      2. The dimension state is adjusted to PREREQUISITE_REQUIRED.
      3. Legitimate repetition is NOT automatically equated with defects.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_rework.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "rework.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    # Find the recurrence opportunity (e.g. Production recurrence)
    rec_opps = [o for o in opportunities.opportunities if "recurrence" in o.id.lower()]
    assert len(rec_opps) >= 1
    target_opp = rec_opps[0]

    domain_input = OpportunityDomainAssessmentInput(
        opportunity_id=target_opp.id,
        digital_data_format=DigitalDataFormat.STRUCTURED_DIGITAL,
        system_interface=SystemInterfaceType.DIRECT_API_OR_DB,
        rule_determinism=RuleDeterminism.DETERMINISTIC_RULES,
        supervision_requirement=HumanSupervisionRequirement.UNATTENDED_FEASIBLE,  # Claims unattended!
        governance_constraint=GovernanceConstraint.STANDARD_BUSINESS,
    )

    result = assess_opportunities_readiness(opportunities, [domain_input], "rework.csv")
    assessed = next(a for a in result.assessments if a.opportunity_id == target_opp.id)

    assert len(assessed.discrepancies) >= 1
    disc = assessed.discrepancies[0]
    assert disc.dimension == "exception_frequency_and_judgment"
    assert "unattended" in disc.domain_claim.lower()
    assert "recurrence" in disc.observed_event_evidence.lower()
    assert "multi-pass" in disc.reconciliation_guidance.lower()  # Guidance distinguishes review from defect!
    assert assessed.exception_frequency_and_judgment.state == DimensionState.PREREQUISITE_REQUIRED


def test_readiness_partial_domain_assessments():
    """
    Verifies support for partial domain assessments:
      Submitted opportunities are evaluated with domain data;
      Unassessed opportunities remain INSUFFICIENT_CRITICAL_EVIDENCE.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    assert len(opportunities.opportunities) >= 2
    submitted_opp = opportunities.opportunities[0]
    unassessed_opp = opportunities.opportunities[1]

    domain_input = OpportunityDomainAssessmentInput(
        opportunity_id=submitted_opp.id,
        digital_data_format=DigitalDataFormat.STRUCTURED_DIGITAL,
        system_interface=SystemInterfaceType.DIRECT_API_OR_DB,
        rule_determinism=RuleDeterminism.DETERMINISTIC_RULES,
        supervision_requirement=HumanSupervisionRequirement.UNATTENDED_FEASIBLE,
        governance_constraint=GovernanceConstraint.STANDARD_BUSINESS,
    )

    result = assess_opportunities_readiness(opportunities, [domain_input], "clean.csv")

    assessed_sub = next(a for a in result.assessments if a.opportunity_id == submitted_opp.id)
    assessed_un = next(a for a in result.assessments if a.opportunity_id == unassessed_opp.id)

    assert assessed_sub.overall_readiness_tier == OverallReadinessTier.READY_FOR_SPECIFICATION
    assert assessed_un.overall_readiness_tier == OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE
    assert result.summary.ready_for_specification_count == 1
    assert result.summary.insufficient_critical_evidence_count == len(opportunities.opportunities) - 1


def test_readiness_invalid_opportunity_id_rejected():
    """
    Verifies that submitting a domain assessment with an unknown opportunity_id raises ValueError.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opportunities = detect_improvement_opportunities(recon, analytics, detection)

    invalid_input = OpportunityDomainAssessmentInput(
        opportunity_id="opp_invalid_nonexistent_999",
        digital_data_format=DigitalDataFormat.STRUCTURED_DIGITAL,
    )

    with pytest.raises(ValueError) as excinfo:
        assess_opportunities_readiness(opportunities, [invalid_input], "clean.csv")

    assert "Unknown opportunity_id 'opp_invalid_nonexistent_999'" in str(excinfo.value)
    assert "Valid IDs:" in str(excinfo.value)


# ---------------------------------------------------------------------------
# API Endpoint Integration Tests: POST /api/v1/readiness/assess
# ---------------------------------------------------------------------------

def test_api_endpoint_readiness_assess_success_without_domain():
    """
    Tests POST /api/v1/readiness/assess with file only (no domain assessments).
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        files = {"file": ("clean.csv", f, "text/csv")}
        response = client.post("/api/v1/readiness/assess", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == "clean.csv"
    assert "summary" in data
    assert "assessments" in data
    assert data["summary"]["evaluated_opportunities_count"] > 0
    assert data["summary"]["insufficient_critical_evidence_count"] == data["summary"]["evaluated_opportunities_count"]


def test_api_endpoint_readiness_assess_success_with_domain():
    """
    Tests POST /api/v1/readiness/assess with file and valid domain_assessments JSON.
    """
    # 1. First get detected opportunities to grab a valid ID
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        files = {"file": ("clean.csv", f, "text/csv")}
        opp_res = client.post("/api/v1/opportunities/detect", files=files)
    assert opp_res.status_code == 200
    target_id = opp_res.json()["opportunities"][0]["id"]

    domain_payload = [
        {
            "opportunity_id": target_id,
            "digital_data_format": "STRUCTURED_DIGITAL",
            "system_interface": "DIRECT_API_OR_DB",
            "rule_determinism": "DETERMINISTIC_RULES",
            "supervision_requirement": "UNATTENDED_FEASIBLE",
            "governance_constraint": "STANDARD_BUSINESS",
        }
    ]

    with open(filepath, "rb") as f:
        files = {"file": ("clean.csv", f, "text/csv")}
        data_fields = {"domain_assessments": json.dumps(domain_payload)}
        response = client.post("/api/v1/readiness/assess", files=files, data=data_fields)

    assert response.status_code == 200
    data = response.json()
    assert data["summary"]["ready_for_specification_count"] == 1

    first = next(a for a in data["assessments"] if a["opportunity_id"] == target_id)
    assert first["overall_readiness_tier"] == "READY_FOR_SPECIFICATION"


def test_api_endpoint_readiness_invalid_opportunity_id():
    """
    Tests that submitting an unknown opportunity_id returns HTTP 400 Bad Request.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    domain_payload = [
        {
            "opportunity_id": "opp_fake_unknown_id",
            "digital_data_format": "STRUCTURED_DIGITAL",
        }
    ]

    with open(filepath, "rb") as f:
        files = {"file": ("clean.csv", f, "text/csv")}
        data_fields = {"domain_assessments": json.dumps(domain_payload)}
        response = client.post("/api/v1/readiness/assess", files=files, data=data_fields)

    assert response.status_code == 400
    assert "Unknown opportunity_id 'opp_fake_unknown_id'" in response.json()["detail"]


def test_api_endpoint_readiness_malformed_json():
    """
    Tests that malformed domain_assessments JSON returns HTTP 400 Bad Request.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        files = {"file": ("clean.csv", f, "text/csv")}
        data_fields = {"domain_assessments": "{not-valid-json}"}
        response = client.post("/api/v1/readiness/assess", files=files, data=data_fields)

    assert response.status_code == 400
    assert "Invalid JSON format" in response.json()["detail"]


def test_api_endpoint_readiness_validation_errors():
    """
    Tests standard input boundary validations on POST /api/v1/readiness/assess.
    """
    # Non-CSV
    files = {"file": ("data.json", b'{"key": "val"}', "application/json")}
    res = client.post("/api/v1/readiness/assess", files=files)
    assert res.status_code == 400
    assert "Only CSV files" in res.json()["detail"]

    # Empty filename
    boundary = "boundaryReadiness"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    res = client.post("/api/v1/readiness/assess", content=body, headers=headers)
    assert res.status_code == 400
    assert "Filename cannot be empty" in res.json()["detail"]


# ---------------------------------------------------------------------------
# Integration Across All 4 Development Datasets
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "filename",
    [
        "manufacturing_orders_quickstart.csv",
        "manufacturing_orders_clean.csv",
        "manufacturing_orders_rework.csv",
        "manufacturing_orders_messy.csv",
    ],
)
def test_readiness_regression_across_all_datasets(filename):
    """
    Verifies that POST /api/v1/readiness/assess runs cleanly and deterministically
    across all four development datasets with valid schema and source finding links.
    """
    filepath = os.path.join(DATA_DIR, filename)
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "text/csv")}
        response = client.post("/api/v1/readiness/assess", files=files)

    assert response.status_code == 200
    data = response.json()
    assert data["filename"] == filename
    assert data["summary"]["evaluated_opportunities_count"] >= 1

    for assessment in data["assessments"]:
        assert assessment["overall_readiness_tier"] in [
            "READY_FOR_SPECIFICATION",
            "PREREQUISITES_REQUIRED",
            "PROHIBITED_OR_BLOCKED",
            "INSUFFICIENT_CRITICAL_EVIDENCE",
        ]
        assert len(assessment["source_finding_ids"]) >= 1
        assert "limitations" in assessment
        assert len(assessment["limitations"]) >= 1
