"""
Test suite for Phase 5 Deterministic Opportunity Detection, Evidence Traceability,
and Operational Priority Scoring.
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems
from app.services.opportunity import (
    calculate_opportunity_score,
    detect_improvement_opportunities,
)
from app.schemas.detection import (
    ProblemDetectionResult,
    DetectionSummary,
    ProblemFinding,
    FindingCategory,
    SignalLevel,
    EvidenceStrength,
    ReconciliationStatus,
)
from app.schemas.opportunity import (
    OpportunityArchetype,
    InterventionCategory,
    PriorityTier,
    OpportunityCandidate,
    OpportunityDetectionResult,
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
# Unit Tests: Hand-Calculated Priority Scoring Formulas & Boundaries
# ---------------------------------------------------------------------------

def test_priority_score_hand_calculated_formulas():
    """
    Verifies the 50/50 coverage/concentration formula and evidence discounting
    against hand-calculated values.
    """
    # Case 1: High Coverage (80%), High Concentration (40%), High Evidence
    # Coverage: 50 * (80 / 100) = 40.0
    # Concentration: 50 * (40 / 50) = 40.0
    # Raw: 80.0, Weight: 1.0 -> Final: 80.0 -> TIER_1_HIGH
    score, tier, b = calculate_opportunity_score(
        OpportunityArchetype.DELAY_COMPRESSION,
        affected_case_percentage=80.0,
        concentration_metric_value=40.0,
        evidence_strength=EvidenceStrength.HIGH,
    )
    assert b.coverage_score == 40.0
    assert b.concentration_score == 40.0
    assert b.raw_score == 80.0
    assert b.evidence_weight == 1.0
    assert score == 80.0
    assert tier == PriorityTier.TIER_1_HIGH

    # Case 2: Same raw score (80.0) with MODERATE Evidence (weight 0.75)
    # Final: 80.0 * 0.75 = 60.0 -> TIER_1_HIGH (boundary test >= 60.0)
    score_mod, tier_mod, b_mod = calculate_opportunity_score(
        OpportunityArchetype.DELAY_COMPRESSION,
        affected_case_percentage=80.0,
        concentration_metric_value=40.0,
        evidence_strength=EvidenceStrength.MODERATE,
    )
    assert b_mod.evidence_weight == 0.75
    assert score_mod == 60.0
    assert tier_mod == PriorityTier.TIER_1_HIGH

    # Case 3: Same raw score (80.0) with LIMITED Evidence (weight 0.40)
    # Final: 80.0 * 0.40 = 32.0.
    # Guardrail check: Even though 32.0 is in TIER_3 range, LIMITED evidence
    # must strictly force assignment to TIER_4_EXPLORATORY!
    score_lim, tier_lim, b_lim = calculate_opportunity_score(
        OpportunityArchetype.DELAY_COMPRESSION,
        affected_case_percentage=80.0,
        concentration_metric_value=40.0,
        evidence_strength=EvidenceStrength.LIMITED,
    )
    assert b_lim.evidence_weight == 0.40
    assert score_lim == 32.0
    assert tier_lim == PriorityTier.TIER_4_EXPLORATORY


def test_priority_tier_score_boundaries():
    """
    Tests exact priority score boundaries:
      >= 60.0: TIER_1_HIGH
      40.0 to 59.99: TIER_2_MEDIUM
      20.0 to 39.99: TIER_3_LOW
      < 20.0: TIER_4_EXPLORATORY
    """
    # Tier 2 Boundary (e.g. 50.0)
    score_t2, tier_t2, _ = calculate_opportunity_score(
        OpportunityArchetype.RECURRENCE_REDUCTION,
        affected_case_percentage=50.0,
        concentration_metric_value=25.0,
        evidence_strength=EvidenceStrength.HIGH,
    )
    assert score_t2 == 50.0
    assert tier_t2 == PriorityTier.TIER_2_MEDIUM

    # Tier 3 Boundary (e.g. 30.0)
    score_t3, tier_t3, _ = calculate_opportunity_score(
        OpportunityArchetype.RECURRENCE_REDUCTION,
        affected_case_percentage=30.0,
        concentration_metric_value=15.0,
        evidence_strength=EvidenceStrength.HIGH,
    )
    assert score_t3 == 30.0
    assert tier_t3 == PriorityTier.TIER_3_LOW

    # Tier 4 Boundary (< 20.0)
    score_t4, tier_t4, _ = calculate_opportunity_score(
        OpportunityArchetype.PATH_STANDARDIZATION,
        affected_case_percentage=10.0,
        concentration_metric_value=5.0,
        evidence_strength=EvidenceStrength.HIGH,
    )
    assert score_t4 == 10.0
    assert tier_t4 == PriorityTier.TIER_4_EXPLORATORY


def test_score_component_traceability():
    """
    Verifies that every score component is traceable to the metrics used.
    """
    case_pct = 70.0
    share_pct = 35.0
    score, tier, breakdown = calculate_opportunity_score(
        OpportunityArchetype.DELAY_COMPRESSION,
        affected_case_percentage=case_pct,
        concentration_metric_value=share_pct,
        evidence_strength=EvidenceStrength.HIGH,
    )

    expected_coverage = round(50.0 * (case_pct / 100.0), 2)  # 35.0
    expected_concentration = round(50.0 * (share_pct / 50.0), 2)  # 35.0
    expected_raw = round(expected_coverage + expected_concentration, 2)  # 70.0
    expected_final = round(expected_raw * 1.0, 2)  # 70.0

    assert breakdown.coverage_score == expected_coverage
    assert breakdown.concentration_score == expected_concentration
    assert breakdown.raw_score == expected_raw
    assert breakdown.evidence_weight == 1.0
    assert breakdown.final_score == expected_final
    assert score == expected_final
    assert tier == PriorityTier.TIER_1_HIGH


# ---------------------------------------------------------------------------
# Unit Tests: Evidence Links, Deduplication & Edge Cases
# ---------------------------------------------------------------------------

def test_evidence_link_integrity_and_traceability():
    """
    Verifies that every generated opportunity candidate:
      1. Has at least one valid source finding ID.
      2. Every source finding ID matches an actual finding emitted by Phase 4.
      3. Contains distinct observed facts, investigation hypotheses, and candidate interventions.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    opps_result = detect_improvement_opportunities(recon, analytics, detection)

    finding_id_set = {f.id for f in detection.findings}

    assert len(opps_result.opportunities) > 0
    for opp in opps_result.opportunities:
        assert len(opp.source_finding_ids) >= 1
        for sf_id in opp.source_finding_ids:
            assert sf_id in finding_id_set, f"Opportunity {opp.id} has invalid source finding {sf_id}"

        # Distinct evidence elements
        assert len(opp.observed_facts) >= 1
        assert len(opp.investigation_hypotheses) >= 1
        assert len(opp.candidate_actions) >= 1
        assert len(opp.candidate_interventions) >= 1
        assert len(opp.limitations) >= 1
        assert opp.rationale != ""


def test_deterministic_ids_and_sorting_order():
    """
    Verifies that opportunities have deterministic IDs and are strictly ordered by:
      (-operational_priority_score, -affected_case_count, target_entity, id)
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    opps = result.opportunities
    for i in range(len(opps) - 1):
        curr = opps[i]
        nxt = opps[i + 1]

        # Check sorting criteria
        assert curr.operational_priority_score >= nxt.operational_priority_score
        if curr.operational_priority_score == nxt.operational_priority_score:
            assert curr.affected_case_count >= nxt.affected_case_count
            if curr.affected_case_count == nxt.affected_case_count:
                assert curr.target_entity <= nxt.target_entity


def test_deduplication_of_opportunities_sharing_target_entity():
    """
    Verifies that if multiple findings target the same archetype and entity,
    the opportunity service deduplicates them into a single candidate,
    unifies source finding IDs, and retains the highest priority score.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Step_A,2026-01-01 00:00:00\n"
        "C1,Step_B,2026-01-01 00:00:10\n"
    ).encode("utf-8")
    recon = reconstruct_process_from_csv(csv_content, "dedup.csv")
    analytics = calculate_process_analytics(recon)

    finding1 = ProblemFinding(
        id="finding_1",
        category=FindingCategory.DURATION_CONCENTRATION,
        rule="TRANSITION_DURATION_SHARE",
        title="Title 1",
        signal_level=SignalLevel.MEDIUM,
        evidence_strength=EvidenceStrength.HIGH,
        metrics={
            "source_activity": "Step_A",
            "target_activity": "Step_B",
            "transition_count": 1,
            "case_count": 1,
            "mean_duration_seconds": 10.0,
            "cumulative_transition_duration_seconds": 10.0,
            "duration_share_percentage": 25.0,
        },
        explanation="Exp 1",
        limitations=[],
    )
    finding2 = ProblemFinding(
        id="finding_2",
        category=FindingCategory.DURATION_CONCENTRATION,
        rule="TRANSITION_DURATION_SHARE",
        title="Title 2",
        signal_level=SignalLevel.HIGH,
        evidence_strength=EvidenceStrength.HIGH,
        metrics={
            "source_activity": "Step_A",
            "target_activity": "Step_B",
            "transition_count": 1,
            "case_count": 1,
            "mean_duration_seconds": 10.0,
            "cumulative_transition_duration_seconds": 10.0,
            "duration_share_percentage": 45.0,  # higher share -> higher score
        },
        explanation="Exp 2",
        limitations=[],
    )

    detection = ProblemDetectionResult(
        filename="dedup.csv",
        summary=DetectionSummary(
            evaluated_cases_count=1,
            total_findings_count=2,
            reconciliation=ReconciliationStatus(
                reconciled=True,
                total_transition_duration_seconds=10.0,
                cumulative_cycle_time_seconds=10.0,
                discrepancy_seconds=0.0,
                discrepancy_percentage=0.0,
                duration_share_suppressed=False,
            ),
        ),
        findings=[finding1, finding2],
    )

    opp_result = detect_improvement_opportunities(recon, analytics, detection)
    # Deduplicated to 1 opportunity for Step_A -> Step_B
    assert len(opp_result.opportunities) == 1
    opp = opp_result.opportunities[0]
    assert opp.id == "opp_delay_step_a_step_b"
    assert "finding_1" in opp.source_finding_ids
    assert "finding_2" in opp.source_finding_ids
    assert len(opp.source_finding_ids) == 2
    # Retained higher score from finding 2
    assert opp.duration_share_percentage == 45.0


def test_reconciliation_failure_suppression_and_data_instrumentation():
    """
    Verifies that when reconciliation fails:
      1. Duration concentration opportunities are suppressed.
      2. A DATA_INSTRUMENTATION opportunity is generated linking to the
         reconciliation discrepancy finding.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Step_A,2026-01-01 00:00:00\n"
        "C1,Step_B,2026-01-01 00:00:10\n"
    ).encode("utf-8")
    recon = reconstruct_process_from_csv(csv_content, "rec_fail.csv")
    analytics = calculate_process_analytics(recon)

    finding_rec = ProblemFinding(
        id="finding_accounting_reconciliation_discrepancy",
        category=FindingCategory.DATA_QUALITY_LIMITATION,
        rule="ACCOUNTING_RECONCILIATION_DISCREPANCY",
        title="Accounting Reconciliation Discrepancy",
        signal_level=SignalLevel.HIGH,
        evidence_strength=EvidenceStrength.HIGH,
        metrics={
            "discrepancy_seconds": 500.0,
            "discrepancy_percentage": 25.0,
            "tolerance_percentage": 1.0,
            "total_transition_duration_seconds": 2500.0,
            "cumulative_cycle_time_seconds": 2000.0,
        },
        explanation="Reconciliation failed",
        limitations=["Accounting mismatch"],
    )

    detection = ProblemDetectionResult(
        filename="rec_fail.csv",
        summary=DetectionSummary(
            evaluated_cases_count=1,
            total_findings_count=1,
            reconciliation=ReconciliationStatus(
                reconciled=False,
                total_transition_duration_seconds=2500.0,
                cumulative_cycle_time_seconds=2000.0,
                discrepancy_seconds=500.0,
                discrepancy_percentage=25.0,
                duration_share_suppressed=True,
            ),
        ),
        findings=[finding_rec],
    )

    opp_result = detect_improvement_opportunities(recon, analytics, detection)
    assert opp_result.summary.reconciliation_passed is False
    assert len(opp_result.opportunities) == 1

    opp = opp_result.opportunities[0]
    assert opp.archetype == OpportunityArchetype.DATA_INSTRUMENTATION
    assert opp.intervention_category == InterventionCategory.DATA_INSTRUMENTATION
    assert opp.source_finding_ids == ["finding_accounting_reconciliation_discrepancy"]
    assert opp.id == "opp_instrument_event_timestamps"
    assert "Reconciliation discrepancy" in opp.rationale


def test_empty_findings_and_zero_cases_robustness():
    """
    Verifies that zero cases or empty findings return clean, empty OpportunityDetectionResult
    without division-by-zero or crashes.
    """
    csv_content = "case_id,activity,timestamp\n".encode("utf-8")
    recon = reconstruct_process_from_csv(csv_content, "empty.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    result = detect_improvement_opportunities(recon, analytics, detection)
    assert result.summary.evaluated_cases_count == 0
    assert result.summary.total_opportunities_count == 0
    assert len(result.opportunities) == 0


def test_missing_metrics_resilience():
    """
    Verifies that findings with missing or None metric values fallback safely.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Step_A,2026-01-01 00:00:00\n"
    ).encode("utf-8")
    recon = reconstruct_process_from_csv(csv_content, "missing.csv")
    analytics = calculate_process_analytics(recon)

    incomplete_finding = ProblemFinding(
        id="finding_incomplete",
        category=FindingCategory.REPETITION,
        rule="ACTIVITY_RECURRENCE",
        title="Incomplete",
        signal_level=SignalLevel.LOW,
        evidence_strength=EvidenceStrength.LIMITED,
        metrics={},  # Completely empty metrics dict
        explanation="Exp",
        limitations=[],
    )
    detection = ProblemDetectionResult(
        filename="missing.csv",
        summary=DetectionSummary(
            evaluated_cases_count=1,
            total_findings_count=1,
            reconciliation=ReconciliationStatus(
                reconciled=True,
                total_transition_duration_seconds=0.0,
                cumulative_cycle_time_seconds=0.0,
                discrepancy_seconds=0.0,
                discrepancy_percentage=0.0,
                duration_share_suppressed=False,
            ),
        ),
        findings=[incomplete_finding],
    )

    result = detect_improvement_opportunities(recon, analytics, detection)
    assert len(result.opportunities) == 1
    opp = result.opportunities[0]
    assert opp.affected_case_count == 0
    assert opp.priority_tier == PriorityTier.TIER_4_EXPLORATORY


# ---------------------------------------------------------------------------
# Integration Tests: Four Development Datasets
# ---------------------------------------------------------------------------

def test_integration_quickstart_dataset():
    """
    Verifies opportunities generated on manufacturing_orders_quickstart.csv.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    assert result.summary.evaluated_cases_count == 100
    assert result.summary.reconciliation_passed is True
    assert result.summary.total_opportunities_count >= 1

    # Verify that the leading opportunity has valid score and tier
    top_opp = result.opportunities[0]
    assert top_opp.operational_priority_score > 0.0
    assert top_opp.priority_tier in (
        PriorityTier.TIER_1_HIGH,
        PriorityTier.TIER_2_MEDIUM,
        PriorityTier.TIER_3_LOW,
        PriorityTier.TIER_4_EXPLORATORY,
    )
    assert len(top_opp.source_finding_ids) >= 1


def test_integration_clean_dataset():
    """
    Verifies opportunities generated on manufacturing_orders_clean.csv (750 cases).
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_clean.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "clean.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    assert result.summary.evaluated_cases_count == 750
    assert result.summary.reconciliation_passed is True
    assert result.summary.total_opportunities_count >= 1

    # Check for duration compression opportunity
    delay_opps = [o for o in result.opportunities if o.archetype == OpportunityArchetype.DELAY_COMPRESSION]
    assert len(delay_opps) >= 1
    for d in delay_opps:
        assert d.duration_share_percentage is not None
        assert d.duration_share_percentage > 0.0


def test_integration_rework_dataset():
    """
    Verifies opportunities generated on manufacturing_orders_rework.csv (rework loops).
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_rework.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "rework.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    assert result.summary.evaluated_cases_count == 750
    rework_opps = [o for o in result.opportunities if o.archetype == OpportunityArchetype.RECURRENCE_REDUCTION]
    assert len(rework_opps) >= 1
    for r in rework_opps:
        assert r.recurrence_case_percentage is not None
        assert r.affected_case_count > 0


def test_integration_messy_dataset():
    """
    Verifies opportunities generated on manufacturing_orders_messy.csv.
    Messy dataset has invalid rows excluded, but complete cases should produce
    valid opportunities.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_messy.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "messy.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    assert result.summary.evaluated_cases_count == recon.complete_cases_count
    assert result.summary.total_opportunities_count >= 1

    # Check path standardization opportunity from rare variants
    path_opps = [o for o in result.opportunities if o.archetype == OpportunityArchetype.PATH_STANDARDIZATION]
    assert len(path_opps) >= 1
    for p in path_opps:
        assert p.variant_case_percentage is not None
        assert "rare" in p.title.lower() or "variant" in p.title.lower()


# ---------------------------------------------------------------------------
# API Endpoint Tests: POST /api/v1/opportunities/detect
# ---------------------------------------------------------------------------

def test_api_endpoint_opportunities_detect_success():
    """
    Tests POST /api/v1/opportunities/detect with quickstart CSV.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        files = {"file": ("quickstart.csv", f, "text/csv")}
        response = client.post("/api/v1/opportunities/detect", files=files)

    assert response.status_code == 200
    data = response.json()

    assert data["filename"] == "quickstart.csv"
    assert "summary" in data
    assert "opportunities" in data
    assert data["summary"]["evaluated_cases_count"] == 100
    assert len(data["opportunities"]) > 0

    first = data["opportunities"][0]
    assert "id" in first
    assert "title" in first
    assert "archetype" in first
    assert "intervention_category" in first
    assert "target_entity" in first
    assert "source_finding_ids" in first
    assert "operational_priority_score" in first
    assert "priority_tier" in first
    assert "score_breakdown" in first
    assert "observed_facts" in first
    assert "investigation_hypotheses" in first
    assert "candidate_actions" in first
    assert "candidate_interventions" in first
    assert "limitations" in first


def test_api_endpoint_validation_errors():
    """
    Tests input boundary validations on POST /api/v1/opportunities/detect:
    - Non-CSV file rejection
    - Empty filename rejection
    """
    # Non-CSV file
    files = {"file": ("data.json", b'{"key": "val"}', "application/json")}
    res = client.post("/api/v1/opportunities/detect", files=files)
    assert res.status_code == 400
    assert "Only CSV files" in res.json()["detail"]

    # Empty filename
    boundary = "boundary456"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    res = client.post("/api/v1/opportunities/detect", content=body, headers=headers)
    assert res.status_code == 400
    assert "Filename cannot be empty" in res.json()["detail"]


def test_mandatory_transition_high_duration_ranks_high_without_automation_claim():
    """
    Verifies that a common mandatory transition with high duration concentration:
      1. Ranks highly based on measured coverage and concentration (TIER_1_HIGH).
      2. Does NOT assign TASK_AUTOMATION_CANDIDATE (assigns neutral UNDETERMINED_INVESTIGATION).
      3. Does NOT claim the step is unnecessary, avoidable, or that automation is justified.
      4. Explicitly lists limitations distinguishing elapsed milestone duration from active labor
         and stating that implementation/automation readiness is evaluated separately.
    """
    # 10 complete cases of a 3-step mandatory process: Fabrication -> Heat Treatment -> Dispatch
    # Each case: Fabrication (0s) -> Heat Treatment (45s) -> Dispatch (100s). Cycle time = 100s.
    # Cumulative cycle time = 1000s across 10 cases.
    # Transition Fabrication -> Heat Treatment:
    #   count = 10, mean = 45s, total = 450s, share = 45.0%
    # Transition Heat Treatment -> Dispatch:
    #   count = 10, mean = 55s, total = 550s, share = 55.0%
    # Total transitions = 1000s -> exactly reconciles!
    rows = ["case_id,activity,timestamp"]
    for i in range(1, 11):
        rows.append(f"C{i:02d},Fabrication,2026-01-01 00:00:00")
        rows.append(f"C{i:02d},Heat Treatment,2026-01-01 00:00:45")
        rows.append(f"C{i:02d},Dispatch,2026-01-01 00:01:40")
    csv_content = "\n".join(rows).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "mandatory_cure.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)
    result = detect_improvement_opportunities(recon, analytics, detection)

    assert result.summary.evaluated_cases_count == 10
    assert result.summary.reconciliation_passed is True

    # Find the opportunity for Fabrication -> Heat Treatment
    opps = [o for o in result.opportunities if o.target_entity == "Fabrication -> Heat Treatment"]
    assert len(opps) == 1
    opp = opps[0]

    # Hand-calculated score verification:
    # Coverage: 10/10 cases (100%) -> 50.0 points
    # Concentration: 45.0% share -> 50 * (45.0 / 50.0) = 45.0 points
    # Raw score: 50.0 + 45.0 = 95.0
    # Evidence weight for N=10 cases (MODERATE): 0.75
    # Final score: round(95.0 * 0.75, 2) = 71.25
    assert opp.score_breakdown.coverage_score == 50.0
    assert opp.score_breakdown.concentration_score == 45.0
    assert opp.score_breakdown.raw_score == 95.0
    assert opp.score_breakdown.evidence_weight == 0.75
    assert opp.operational_priority_score == 71.25

    # 1. Measured pattern ranks highly in Tier 1
    assert opp.priority_tier == PriorityTier.TIER_1_HIGH

    # 2. Classified as neutral UNDETERMINED_INVESTIGATION, NOT TASK_AUTOMATION_CANDIDATE
    assert opp.intervention_category == InterventionCategory.UNDETERMINED_INVESTIGATION
    assert opp.intervention_category != InterventionCategory.TASK_AUTOMATION_CANDIDATE

    # 3. No unfounded claims that the step is unnecessary or automation is justified
    combined_text = (
        opp.rationale
        + " " + " ".join(opp.observed_facts)
        + " " + " ".join(opp.investigation_hypotheses)
    ).lower()
    assert "unnecessary" not in combined_text
    assert "defect" not in combined_text
    assert "automation is justified" not in combined_text

    # 4. Limitations explicitly state boundaries
    limitations_text = " ".join(opp.limitations)
    assert "does not establish that the transition is unnecessary, avoidable, or suitable for automation" in limitations_text
    assert "Implementation and automation readiness are evaluated separately" in limitations_text
