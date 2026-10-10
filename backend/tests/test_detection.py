"""
Unit and regression test suite for Phase 4: Deterministic Problem Detection and Operational Signals.
Covers:
- Hand-calculated duplicate interval preservation
- Repeated transitions and rework loop duration shares
- Incomplete cases and invalid event isolation
- Zero-duration cases (single event and co-temporal events)
- Zero-IQR cycle-time distributions
- Reconciliation discrepancy detection and duration-share suppression
- Small sample cautions and finding-specific evidence strength
- Separation of signal prominence from evidence strength
- Neutral terminology and rejection of unsupported bottleneck claims
- Deterministic IDs and signal prominence sorting
- API endpoint contracts and HTTP boundary validation
- Integration tests against all 4 development datasets
"""

import os
import io
import pytest
from datetime import datetime, timezone
from fastapi.testclient import TestClient

from app.main import app
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import (
    detect_process_problems,
    evaluate_evidence_strength,
    compute_percentile,
    slugify
)
from app.schemas.detection import (
    FindingCategory,
    SignalLevel,
    SeverityLevel,
    EvidenceStrength,
    ProblemFinding,
    ProblemDetectionResult
)
from app.schemas.reconstruction import ProcessReconstructionResult, CaseTrace, ReconstructedEvent
from app.schemas.analytics import ProcessAnalyticsResult, ReconstructionSummary, CycleTimeSummary, DurationStats, ActivityTransition, ActivityRework

client = TestClient(app)

DATA_DIR = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..",
        "..",
        "data",
        "ProcessLens_Development_Data",
        "samples"
    )
)


def test_hand_calculated_duplicate_interval_preservation():
    """
    Verifies duplicate events between distinct milestones:
    Case C1: A(t=10) -> A(t=10, dup) -> B(t=25).
    Reconstruction marks duplicate event; analytics forms 1 transition (A -> B) of duration 15s.
    Detection verifies cumulative cycle time = 15s, transition total = 15s,
    reconciliation passes, category is DURATION_CONCENTRATION, and A -> B has 100% duration share.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Order Verification,2026-01-01 00:00:10\n"
        "C1,Order Verification,2026-01-01 00:00:10\n"
        "C1,Inventory Check,2026-01-01 00:00:25\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "dup_interval.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    # 1 complete case, cycle time 15s
    assert detection.summary.evaluated_cases_count == 1
    assert detection.summary.reconciliation.reconciled is True
    assert detection.summary.reconciliation.cumulative_cycle_time_seconds == 15.0
    assert detection.summary.reconciliation.total_transition_duration_seconds == 15.0
    assert detection.summary.reconciliation.discrepancy_seconds == 0.0
    assert detection.summary.reconciliation.duration_share_suppressed is False

    # Neutral category is DURATION_CONCENTRATION, not BOTTLENECK
    trans_findings = [f for f in detection.findings if f.rule == "TRANSITION_DURATION_SHARE"]
    assert len(trans_findings) == 1
    assert trans_findings[0].category == FindingCategory.DURATION_CONCENTRATION
    assert trans_findings[0].metrics["duration_share_percentage"] == 100.0
    assert trans_findings[0].metrics["transition_count"] == 1

    # Signal prominence is HIGH (100% share), but evidence strength is LIMITED (1 execution)
    assert trans_findings[0].signal_level == SignalLevel.HIGH
    assert trans_findings[0].evidence_strength == EvidenceStrength.LIMITED


def test_repeated_transitions_rework_loop_shares():
    """
    Verifies repeated transitions (loops):
    Case C1: A(0) -> B(10) -> A(20) -> B(30). Cycle time = 30s.
    Transitions:
      - A -> B: count = 2, total = 20s (mean = 10s), share = 66.67%
      - B -> A: count = 1, total = 10s (mean = 10s), share = 33.33%
    Sum of shares = 100.0%. Reconciliation passes.
    Recurrence metrics use neutral terminology (recurrence_case_count).
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Step_A,2026-01-01 00:00:00\n"
        "C1,Step_B,2026-01-01 00:00:10\n"
        "C1,Step_A,2026-01-01 00:00:20\n"
        "C1,Step_B,2026-01-01 00:00:30\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "loop.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.reconciliation.reconciled is True
    assert detection.summary.reconciliation.cumulative_cycle_time_seconds == 30.0
    assert detection.summary.reconciliation.total_transition_duration_seconds == 30.0
    assert detection.summary.reconciliation.discrepancy_seconds == 0.0

    # Shares check with neutral DURATION_CONCENTRATION category
    trans_findings = {f.id: f for f in detection.findings if f.rule == "TRANSITION_DURATION_SHARE"}
    assert "finding_transition_step_a_step_b" in trans_findings
    assert "finding_transition_step_b_step_a" in trans_findings
    assert trans_findings["finding_transition_step_a_step_b"].category == FindingCategory.DURATION_CONCENTRATION
    assert trans_findings["finding_transition_step_a_step_b"].metrics["duration_share_percentage"] == 66.67
    assert trans_findings["finding_transition_step_b_step_a"].metrics["duration_share_percentage"] == 33.33

    # Neutral recurrence metrics
    recurr_findings = [f for f in detection.findings if f.rule == "ACTIVITY_RECURRENCE"]
    assert len(recurr_findings) == 2
    for rf in recurr_findings:
        assert rf.category == FindingCategory.REPETITION
        assert "recurrence_case_count" in rf.metrics
        assert "recurrence_case_percentage" in rf.metrics
        assert "recurrence_occurrences" in rf.metrics
        assert rf.metrics["recurrence_case_count"] == 1
        assert rf.metrics["recurrence_occurrences"] == 1


def test_incomplete_cases_isolation():
    """
    Verifies that incomplete cases and invalid records are isolated
    and do not contaminate detection metrics or cause reconciliation errors.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Order Verification,2026-01-01 00:00:00\n"
        "C1,Inventory Check,2026-01-01 00:00:20\n"
        "C2,Order Verification,2026-01-01 00:00:00\n"
        "C2,Inventory Check,INVALID_DATETIME\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "incomplete.csv")
    assert recon.complete_cases_count == 1
    assert recon.incomplete_cases_count == 1

    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.evaluated_cases_count == 1
    assert detection.summary.reconciliation.cumulative_cycle_time_seconds == 20.0
    assert detection.summary.reconciliation.total_transition_duration_seconds == 20.0
    assert detection.summary.reconciliation.reconciled is True


def test_zero_duration_single_event_cases():
    """
    Verifies single-event complete cases (cycle time 0.0s).
    Reconciliation passes (0 == 0), duration shares are suppressed,
    and ZERO_CYCLE_TIME_PROCESS finding is emitted.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Order Verification,2026-01-01 00:00:00\n"
        "C2,Order Verification,2026-01-01 00:00:00\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "single_event.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.evaluated_cases_count == 2
    assert detection.summary.reconciliation.cumulative_cycle_time_seconds == 0.0
    assert detection.summary.reconciliation.total_transition_duration_seconds == 0.0
    assert detection.summary.reconciliation.reconciled is True
    assert detection.summary.reconciliation.duration_share_suppressed is True

    # Check zero cycle time finding
    zero_findings = [f for f in detection.findings if f.rule == "ZERO_CYCLE_TIME_PROCESS"]
    assert len(zero_findings) == 1
    assert zero_findings[0].signal_level == SignalLevel.INFO


def test_simultaneous_events_zero_duration():
    """
    Verifies co-temporal distinct events (cycle time 0.0s, transition duration 0.0s).
    Duration shares are suppressed without division-by-zero errors.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,Step_A,2026-01-01 00:00:00\n"
        "C1,Step_B,2026-01-01 00:00:00\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "simultaneous.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.reconciliation.cumulative_cycle_time_seconds == 0.0
    assert detection.summary.reconciliation.duration_share_suppressed is True
    assert any(f.rule == "ZERO_CYCLE_TIME_PROCESS" for f in detection.findings)


def test_zero_iqr_cycle_time_distribution():
    """
    Verifies process where all cases have identical cycle times (IQR = 0.0s).
    Upper fence does not flag false positives; ZERO_VARIANCE_CYCLE_TIME finding emitted.
    """
    rows = ["case_id,activity,timestamp"]
    for i in range(10):
        cid = f"C{i}"
        rows.append(f"{cid},Start,2026-01-01 00:00:00")
        rows.append(f"{cid},End,2026-01-01 00:00:50")
    csv_content = "\n".join(rows).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "zero_iqr.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.evaluated_cases_count == 10
    outlier_findings = [f for f in detection.findings if f.rule == "CYCLE_TIME_TUKEY_OUTLIER"]
    assert len(outlier_findings) == 0

    zero_var_findings = [f for f in detection.findings if f.rule == "ZERO_VARIANCE_CYCLE_TIME"]
    assert len(zero_var_findings) == 1
    assert zero_var_findings[0].signal_level == SignalLevel.INFO
    assert zero_var_findings[0].metrics["iqr_seconds"] == 0.0


def test_reconciliation_discrepancy_suppresses_duration_shares():
    """
    Verifies that when transition totals do not reconcile with cycle time (> 1.0%),
    all TRANSITION_DURATION_SHARE findings are suppressed and an explicit
    ACCOUNTING_RECONCILIATION_DISCREPANCY finding is emitted.
    """
    dt1 = datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    dt2 = datetime(2026, 1, 1, 0, 1, 40, tzinfo=timezone.utc)  # 100 seconds
    cases = [
        CaseTrace(
            case_id="C1",
            events=[
                ReconstructedEvent(row_index=1, activity="A", timestamp_raw="", timestamp_parsed=dt1),
                ReconstructedEvent(row_index=2, activity="B", timestamp_raw="", timestamp_parsed=dt2),
            ],
            activity_sequence=["A", "B"],
            event_count=2,
            is_complete=True,
            start_time=dt1,
            end_time=dt2
        )
    ]
    recon = ProcessReconstructionResult(
        filename="mismatch.csv",
        total_source_rows=2,
        eligible_event_count=2,
        total_cases_found=1,
        complete_cases_count=1,
        incomplete_cases_count=0,
        variant_count=1,
        exclusions={"total_excluded_rows": 0, "missing_case_id_count": 0, "missing_activity_count": 0, "missing_or_invalid_timestamp_count": 0, "excluded_events": [], "incomplete_case_ids": []},
        variants=[],
        cases=cases
    )

    trans = [
        ActivityTransition(
            source_activity="A",
            target_activity="B",
            transition_count=1,
            case_count=1,
            duration_stats=DurationStats(
                mean_seconds=80.0,
                median_seconds=80.0,
                min_seconds=80.0,
                max_seconds=80.0,
                p90_seconds=80.0
            )
        )
    ]
    analytics = ProcessAnalyticsResult(
        filename="mismatch.csv",
        reconstruction_summary=ReconstructionSummary(
            total_source_rows=2, eligible_event_count=2, total_cases_found=1,
            complete_cases_count=1, incomplete_cases_count=0, variant_count=1
        ),
        cycle_time=CycleTimeSummary(
            evaluated_cases_count=1,
            duration_stats=DurationStats(
                mean_seconds=100.0, median_seconds=100.0, min_seconds=100.0, max_seconds=100.0, p90_seconds=100.0
            )
        ),
        activity_frequency=[],
        rework=[],
        transitions=trans
    )

    detection = detect_process_problems(recon, analytics)

    assert detection.summary.reconciliation.reconciled is False
    assert detection.summary.reconciliation.duration_share_suppressed is True
    assert detection.summary.reconciliation.discrepancy_seconds == 20.0
    assert detection.summary.reconciliation.discrepancy_percentage == 20.0

    # Assert duration share findings are strictly suppressed
    assert not any(f.rule == "TRANSITION_DURATION_SHARE" for f in detection.findings)

    # Assert diagnostic finding emitted
    discrepancy_findings = [f for f in detection.findings if f.rule == "ACCOUNTING_RECONCILIATION_DISCREPANCY"]
    assert len(discrepancy_findings) == 1
    assert discrepancy_findings[0].signal_level == SignalLevel.HIGH
    assert discrepancy_findings[0].evidence_strength == EvidenceStrength.HIGH


def test_small_sample_size_caution():
    """
    Verifies that datasets with fewer than 10 complete cases emit
    a SMALL_SAMPLE_CAUTION finding with LIMITED evidence strength.
    """
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,A,2026-01-01 00:00:00\n"
        "C1,B,2026-01-01 00:00:10\n"
        "C2,A,2026-01-01 00:00:00\n"
        "C2,B,2026-01-01 00:00:15\n"
        "C3,A,2026-01-01 00:00:00\n"
        "C3,B,2026-01-01 00:00:20\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "small.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    assert detection.summary.evaluated_cases_count == 3
    caution_findings = [f for f in detection.findings if f.rule == "SMALL_SAMPLE_CAUTION"]
    assert len(caution_findings) == 1
    assert caution_findings[0].evidence_strength == EvidenceStrength.LIMITED


def test_finding_specific_evidence_strength():
    """
    Verifies that evidence strength is evaluated based on the finding's
    specific sample size, not merely the global process size.
    """
    assert evaluate_evidence_strength(35) == EvidenceStrength.HIGH
    assert evaluate_evidence_strength(30) == EvidenceStrength.HIGH
    assert evaluate_evidence_strength(29) == EvidenceStrength.MODERATE
    assert evaluate_evidence_strength(10) == EvidenceStrength.MODERATE
    assert evaluate_evidence_strength(9) == EvidenceStrength.LIMITED
    assert evaluate_evidence_strength(1) == EvidenceStrength.LIMITED


def test_separation_of_signal_prominence_and_evidence_strength():
    """
    Verifies that signal prominence and evidence strength are strictly orthogonal:
    A high-concentration transition with few executions has HIGH signal prominence
    and LIMITED evidence strength. Sample size does not inflate or suppress signal prominence.
    """
    # 2 cases: A -> B takes 50s out of 60s total cycle time (83.33% share)
    csv_content = (
        "case_id,activity,timestamp\n"
        "C1,A,2026-01-01 00:00:00\n"
        "C1,B,2026-01-01 00:00:25\n"
        "C1,C,2026-01-01 00:00:30\n"
        "C2,A,2026-01-01 00:00:00\n"
        "C2,B,2026-01-01 00:00:25\n"
        "C2,C,2026-01-01 00:00:30\n"
    ).encode("utf-8")

    recon = reconstruct_process_from_csv(csv_content, "small_prominent.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    trans_ab = next((f for f in detection.findings if f.id == "finding_transition_a_b"), None)
    assert trans_ab is not None

    # High duration concentration (83.33% >= 40%) -> HIGH signal prominence
    assert trans_ab.signal_level == SignalLevel.HIGH

    # Only 2 executions (< 10) -> LIMITED evidence strength
    assert trans_ab.evidence_strength == EvidenceStrength.LIMITED

    # Asserts that high prominence does NOT falsely claim HIGH evidence strength
    assert trans_ab.signal_level != trans_ab.evidence_strength


def test_neutral_terminology_and_no_unsupported_claims():
    """
    Verifies that findings adhere to neutral operational language:
    - Category is DURATION_CONCENTRATION, not BOTTLENECK
    - Recurrence metrics use recurrence_case_count, not rework
    - No unverified claims of defects, waste, or bottlenecks
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_rework.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "rework.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    for finding in detection.findings:
        # Category must not be unverified "BOTTLENECK"
        assert finding.category.value != "BOTTLENECK" or finding.category == FindingCategory.DURATION_CONCENTRATION
        assert "bottleneck" not in finding.title.lower()
        assert "defect" not in finding.explanation.lower()
        assert "waste" not in finding.explanation.lower()
        assert "savings" not in finding.explanation.lower()
        assert "roi" not in finding.explanation.lower()


def test_deterministic_finding_ids_and_ordering():
    """
    Verifies deterministic finding IDs and stable sorting by signal prominence.
    """
    assert slugify("Production -> Quality Inspection") == "production_quality_inspection"
    assert slugify("Order Verification") == "order_verification"
    assert slugify("$$$Special---Chars!!!") == "special_chars"

    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)

    run1 = detect_process_problems(recon, analytics)
    run2 = detect_process_problems(recon, analytics)

    ids1 = [f.id for f in run1.findings]
    ids2 = [f.id for f in run2.findings]
    assert ids1 == ids2

    # Verify signal prominence sorting (HIGH -> MEDIUM -> LOW -> INFO)
    signals = [f.signal_level for f in run1.findings]
    signal_order = {SignalLevel.HIGH: 0, SignalLevel.MEDIUM: 1, SignalLevel.LOW: 2, SignalLevel.INFO: 3}
    order_ranks = [signal_order[s] for s in signals]
    assert order_ranks == sorted(order_ranks)


def test_api_endpoint_problems_detect():
    """
    Verifies POST /api/v1/problems/detect endpoint contracts and HTTP boundary validation.
    """
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    # Successful call
    response = client.post(
        "/api/v1/problems/detect",
        files={"file": ("manufacturing_orders_quickstart.csv", io.BytesIO(content), "text/csv")}
    )
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "findings" in data
    assert data["summary"]["evaluated_cases_count"] == 100
    assert data["summary"]["reconciliation"]["reconciled"] is True
    assert "high_signal_count" in data["summary"]

    # Empty filename
    boundary = "boundary789"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    resp_empty = client.post("/api/v1/problems/detect", content=body, headers=headers)
    assert resp_empty.status_code == 400
    assert "Filename cannot be empty" in resp_empty.json()["detail"]

    # Non-CSV file
    resp_bad_ext = client.post(
        "/api/v1/problems/detect",
        files={"file": ("data.json", io.BytesIO(b"{}"), "application/json")}
    )
    assert resp_bad_ext.status_code == 400
    assert "Unsupported file type" in resp_bad_ext.json()["detail"]

    # File size limit
    from app.core.config import settings
    large_payload = b"case_id,activity,timestamp\n" + b"x" * (settings.MAX_FILE_SIZE_BYTES + 1)
    resp_large = client.post(
        "/api/v1/problems/detect",
        files={"file": ("large.csv", large_payload, "text/csv")}
    )
    assert resp_large.status_code == 400
    assert "File size exceeds maximum allowed limit" in resp_large.json()["detail"]


def test_integration_four_development_datasets():
    """
    Comprehensive integration test on all four development datasets:
    - quickstart.csv (100 cases)
    - clean.csv (750 cases)
    - rework.csv (750 cases, recurrence loop on Quality Inspection)
    - messy.csv (750 cases, 652 complete, 18 rare variants)
    """
    datasets = [
        ("manufacturing_orders_quickstart.csv", 100, False, 0),
        ("manufacturing_orders_clean.csv", 750, False, 0),
        ("manufacturing_orders_rework.csv", 750, True, 0),
        ("manufacturing_orders_messy.csv", 652, False, 18),
    ]

    for fname, expected_complete, has_rework, expected_rare_variants in datasets:
        filepath = os.path.join(DATA_DIR, fname)
        assert os.path.exists(filepath), f"File {filepath} missing"

        with open(filepath, "rb") as f:
            content = f.read()

        recon = reconstruct_process_from_csv(content, fname)
        analytics = calculate_process_analytics(recon)
        detection = detect_process_problems(recon, analytics)

        assert detection.summary.evaluated_cases_count == expected_complete
        assert detection.summary.reconciliation.reconciled is True
        assert detection.summary.reconciliation.discrepancy_percentage < 0.01

        # Check duration concentration category
        trans_findings = [f for f in detection.findings if f.rule == "TRANSITION_DURATION_SHARE"]
        for tf in trans_findings:
            assert tf.category == FindingCategory.DURATION_CONCENTRATION

        # Check recurrence finding with neutral terminology
        recurr_findings = [f for f in detection.findings if f.rule == "ACTIVITY_RECURRENCE"]
        if has_rework:
            assert len(recurr_findings) >= 1
            quality_recurr = next((f for f in recurr_findings if "quality_inspection" in f.id), None)
            assert quality_recurr is not None
            assert quality_recurr.category == FindingCategory.REPETITION
            assert quality_recurr.metrics["recurrence_case_count"] == 253
            assert quality_recurr.metrics["recurrence_case_percentage"] == 33.73
            assert quality_recurr.metrics["recurrence_occurrences"] == 253
            assert quality_recurr.signal_level == SignalLevel.HIGH
            assert quality_recurr.evidence_strength == EvidenceStrength.HIGH
        else:
            assert len(recurr_findings) == 0

        # Check rare variant finding
        rare_findings = [f for f in detection.findings if f.rule == "RARE_PROCESS_VARIANT"]
        if expected_rare_variants > 0:
            assert len(rare_findings) == 1
            assert rare_findings[0].category == FindingCategory.PATH_VARIATION
            assert rare_findings[0].metrics["rare_variant_count"] == expected_rare_variants
        else:
            assert len(rare_findings) == 0


def test_enum_values_and_legacy_compatibility():
    """
    Verifies that FindingCategory retains canonical DURATION_CONCENTRATION
    and deprecated legacy BOTTLENECK with distinct string values.
    """
    assert FindingCategory.DURATION_CONCENTRATION.value == "DURATION_CONCENTRATION"
    assert FindingCategory.BOTTLENECK.value == "BOTTLENECK"

    # Both values deserialize correctly from raw strings
    assert FindingCategory("DURATION_CONCENTRATION") == FindingCategory.DURATION_CONCENTRATION
    assert FindingCategory("BOTTLENECK") == FindingCategory.BOTTLENECK

    # SeverityLevel is an alias for SignalLevel
    assert SeverityLevel is SignalLevel
    assert SeverityLevel.HIGH == SignalLevel.HIGH


def test_json_serialization_behavior_bottleneck_vs_duration_concentration():
    """
    Verifies JSON serialization behavior:
    1. A finding explicitly created with legacy BOTTLENECK serializes as its old value "BOTTLENECK".
    2. A finding created with canonical DURATION_CONCENTRATION serializes as "DURATION_CONCENTRATION".
    3. The live engine generates findings with canonical DURATION_CONCENTRATION only.
    """
    import json

    # Legacy finding serialization
    legacy_finding = ProblemFinding(
        id="legacy_1",
        category=FindingCategory.BOTTLENECK,
        rule="TRANSITION_DURATION_SHARE",
        title="Legacy Title",
        signal_level=SignalLevel.MEDIUM,
        severity=SignalLevel.MEDIUM,
        evidence_strength=EvidenceStrength.HIGH,
        explanation="Test explanation",
        limitations=[]
    )
    legacy_json = json.loads(legacy_finding.model_dump_json())
    assert legacy_json["category"] == "BOTTLENECK"
    assert legacy_json["severity"] == "MEDIUM"
    assert legacy_json["signal_level"] == "MEDIUM"

    # Canonical finding serialization
    canonical_finding = ProblemFinding(
        id="canonical_1",
        category=FindingCategory.DURATION_CONCENTRATION,
        rule="TRANSITION_DURATION_SHARE",
        title="Canonical Title",
        signal_level=SignalLevel.MEDIUM,
        severity=SignalLevel.MEDIUM,
        evidence_strength=EvidenceStrength.HIGH,
        explanation="Test explanation",
        limitations=[]
    )
    canonical_json = json.loads(canonical_finding.model_dump_json())
    assert canonical_json["category"] == "DURATION_CONCENTRATION"
    assert canonical_json["signal_level"] == "MEDIUM"

    # Live engine output verification on quickstart dataset
    filepath = os.path.join(DATA_DIR, "manufacturing_orders_quickstart.csv")
    with open(filepath, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    result = detect_process_problems(recon, analytics)

    result_json = json.loads(result.model_dump_json())
    for f in result_json["findings"]:
        if f["rule"] == "TRANSITION_DURATION_SHARE":
            # Engine strictly emits canonical DURATION_CONCENTRATION
            assert f["category"] == "DURATION_CONCENTRATION"
            assert f["category"] != "BOTTLENECK"


def test_openapi_schema_generated_deprecation_metadata():
    """
    Verifies that the generated OpenAPI schema includes deprecated=True
    metadata on legacy fields and enumerates both canonical and legacy categories.
    """
    openapi_schema = app.openapi()
    schemas = openapi_schema["components"]["schemas"]

    # ProblemFinding schema checks
    finding_schema = schemas["ProblemFinding"]
    assert "signal_level" in finding_schema["properties"]
    assert "severity" in finding_schema["properties"]
    assert finding_schema["properties"]["severity"].get("deprecated") is True

    # DetectionSummary schema checks
    summary_schema = schemas["DetectionSummary"]
    assert "high_signal_count" in summary_schema["properties"]
    assert "high_severity_count" in summary_schema["properties"]
    assert summary_schema["properties"]["high_severity_count"].get("deprecated") is True
    assert summary_schema["properties"]["medium_severity_count"].get("deprecated") is True
    assert summary_schema["properties"]["low_severity_count"].get("deprecated") is True
    assert summary_schema["properties"]["info_severity_count"].get("deprecated") is True

    # FindingCategory enum checks
    cat_schema = schemas["FindingCategory"]
    assert "DURATION_CONCENTRATION" in cat_schema["enum"]
    assert "BOTTLENECK" in cat_schema["enum"]


def test_backward_compatibility_incoming_payloads():
    """
    Verifies that incoming JSON payloads using deprecated legacy fields
    (category: BOTTLENECK, severity, rework_* metrics) validate cleanly.
    """
    legacy_payload = {
        "id": "finding_legacy_test",
        "category": "BOTTLENECK",
        "rule": "ACTIVITY_RECURRENCE",
        "title": "Legacy Finding",
        "signal_level": "HIGH",
        "severity": "HIGH",
        "evidence_strength": "MODERATE",
        "metrics": {
            "rework_case_count": 12,
            "rework_case_percentage": 24.0,
            "rework_occurrences": 15
        },
        "explanation": "Legacy test explanation",
        "limitations": []
    }

    finding = ProblemFinding.model_validate(legacy_payload)
    assert finding.category == FindingCategory.BOTTLENECK
    assert finding.severity == SignalLevel.HIGH
    assert finding.signal_level == SignalLevel.HIGH
    assert finding.metrics["rework_case_count"] == 12
