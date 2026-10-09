"""
Tests for Process Analytics Engine (Phase 3).
Validates deterministic process metrics:
- Hand-calculated cycle time, activity frequency, rework, and transition durations
- Linear-interpolation p90 percentiles
- Single-event case cycle time handling (0.0s)
- Duplicate event separation vs. genuine temporal rework
- Exclusion of incomplete cases from analytic distributions
- Dedicated endpoint tests across all sample datasets
"""

import io
import pytest
from app.core.config import settings
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics, compute_duration_stats

def test_compute_duration_stats_known_distributions():
    # Empty distribution
    empty_stats = compute_duration_stats([])
    assert empty_stats.mean_seconds == 0.0
    assert empty_stats.median_seconds == 0.0
    assert empty_stats.min_seconds == 0.0
    assert empty_stats.max_seconds == 0.0
    assert empty_stats.p90_seconds == 0.0

    # Single value
    single_stats = compute_duration_stats([42.0])
    assert single_stats.mean_seconds == 42.0
    assert single_stats.median_seconds == 42.0
    assert single_stats.min_seconds == 42.0
    assert single_stats.max_seconds == 42.0
    assert single_stats.p90_seconds == 42.0

    # Hand-calculated 10-element vector [10, 20, 30, 40, 50, 60, 70, 80, 90, 100]
    # N = 10
    # Mean = 55.0
    # Median = (50 + 60) / 2 = 55.0
    # Min = 10.0, Max = 100.0
    # Linear p90: rank = 0.9 * (10 - 1) = 8.1 -> index 8 (90) + 0.1 * (100 - 90) = 91.0
    stats = compute_duration_stats([100.0, 10.0, 50.0, 20.0, 90.0, 30.0, 80.0, 40.0, 70.0, 60.0])
    assert stats.mean_seconds == 55.0
    assert stats.median_seconds == 55.0
    assert stats.min_seconds == 10.0
    assert stats.max_seconds == 100.0
    assert stats.p90_seconds == 91.0

def test_hand_calculated_multi_case_normal_workflow():
    # C1: Start -> Work -> End (total: 7200s, steps: 3600s, 3600s)
    # C2: Start -> Work -> End (total: 3600s, steps: 1800s, 1800s)
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Start,2026-01-01 10:00:00\n"
        "C1,Work,2026-01-01 11:00:00\n"
        "C1,End,2026-01-01 12:00:00\n"
        "C2,Start,2026-01-02 10:00:00\n"
        "C2,Work,2026-01-02 10:30:00\n"
        "C2,End,2026-01-02 11:00:00\n"
    )
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    analytics = calculate_process_analytics(reconstruction)

    # 1. Cycle Time
    # C1 = 7200s, C2 = 3600s -> Mean = 5400s, Median = 5400s, Min = 3600s, Max = 7200s
    # Linear p90: rank = 0.9 * (2 - 1) = 0.9 -> 3600 + 0.9 * (7200 - 3600) = 6840.0
    ct = analytics.cycle_time
    assert ct.evaluated_cases_count == 2
    assert ct.duration_stats.mean_seconds == 5400.0
    assert ct.duration_stats.median_seconds == 5400.0
    assert ct.duration_stats.min_seconds == 3600.0
    assert ct.duration_stats.max_seconds == 7200.0
    assert ct.duration_stats.p90_seconds == 6840.0

    # 2. Activity Frequency
    # Start: 2 occurrences, 2 cases, 100% coverage, rep ratio 1.0
    # Work: 2 occurrences, 2 cases, 100% coverage, rep ratio 1.0
    # End: 2 occurrences, 2 cases, 100% coverage, rep ratio 1.0
    freq_map = {f.activity: f for f in analytics.activity_frequency}
    assert len(freq_map) == 3
    for act in ["Start", "Work", "End"]:
        assert freq_map[act].total_occurrences == 2
        assert freq_map[act].case_count == 2
        assert freq_map[act].case_coverage_percentage == 100.0
        assert freq_map[act].repetition_ratio == 1.0

    # 3. Transitions
    # Start -> Work: count=2, case_count=2, durations=[3600s, 1800s] -> mean=2700s
    # Work -> End: count=2, case_count=2, durations=[3600s, 1800s] -> mean=2700s
    trans_map = {(t.source_activity, t.target_activity): t for t in analytics.transitions}
    assert ("Start", "Work") in trans_map
    assert ("Work", "End") in trans_map
    assert trans_map[("Start", "Work")].transition_count == 2
    assert trans_map[("Start", "Work")].duration_stats.mean_seconds == 2700.0

    # 4. Rework (no repeated activities)
    for r in analytics.rework:
        assert r.rework_case_count == 0
        assert r.rework_occurrences == 0
        assert r.duplicate_events_count == 0

def test_single_event_case_cycle_time_zero_and_evaluated():
    # Case C1 has 1 event. Complete cases = 1.
    # Cycle time must be 0.0s, evaluated_cases_count must be 1.
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,SingleStep,2026-01-01 10:00:00\n"
    )
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    analytics = calculate_process_analytics(reconstruction)

    assert analytics.cycle_time.evaluated_cases_count == 1
    assert analytics.cycle_time.duration_stats.mean_seconds == 0.0
    assert analytics.cycle_time.duration_stats.min_seconds == 0.0
    assert analytics.cycle_time.duration_stats.max_seconds == 0.0
    assert analytics.cycle_time.duration_stats.median_seconds == 0.0
    assert analytics.cycle_time.duration_stats.p90_seconds == 0.0

    # Activity frequency
    assert len(analytics.activity_frequency) == 1
    act = analytics.activity_frequency[0]
    assert act.activity == "SingleStep"
    assert act.total_occurrences == 1
    assert act.case_count == 1
    assert act.case_coverage_percentage == 100.0
    assert act.repetition_ratio == 1.0

    # Transitions should be empty
    assert len(analytics.transitions) == 0

def test_duplicate_events_vs_genuine_temporal_rework():
    # C1: Inspect at 10:00 and Inspect at 10:00 (identical timestamp -> duplicate, NOT rework)
    # C2: Inspect at 10:00, Fix at 11:00, Inspect at 12:00 (distinct timestamps -> genuine temporal repetition)
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Inspect,2026-01-01 10:00:00\n"
        "C1,Inspect,2026-01-01 10:00:00\n"
        "C2,Inspect,2026-01-02 10:00:00\n"
        "C2,Fix,2026-01-02 11:00:00\n"
        "C2,Inspect,2026-01-02 12:00:00\n"
    )
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    analytics = calculate_process_analytics(reconstruction)

    rework_map = {r.activity: r for r in analytics.rework}
    inspect_rework = rework_map["Inspect"]

    # In C1: 2 events with same timestamp -> duplicate_events_count = 1, but distinct timestamps = 1 -> no rework
    # In C2: 2 events with distinct timestamps (10:00, 12:00) -> rework_case_count = 1, rework_occurrences = 1
    # Total for Inspect:
    # rework_case_count = 1 (only C2)
    # rework_case_percentage = 50.0% (1 out of 2 complete cases)
    # rework_occurrences = 1
    # duplicate_events_count = 1 (from C1)
    assert inspect_rework.rework_case_count == 1
    assert inspect_rework.rework_case_percentage == 50.0
    assert inspect_rework.rework_occurrences == 1
    assert inspect_rework.duplicate_events_count == 1

    # Total occurrences of Inspect in frequency: 2 in C1 + 2 in C2 = 4
    freq_map = {f.activity: f for f in analytics.activity_frequency}
    assert freq_map["Inspect"].total_occurrences == 4
    assert freq_map["Inspect"].case_count == 2
    assert freq_map["Inspect"].repetition_ratio == 2.0

def test_incomplete_cases_excluded_from_analytics():
    # C1: complete (Start 10:00 -> End 12:00, duration 7200s)
    # C2: incomplete due to invalid timestamp row
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Start,2026-01-01 10:00:00\n"
        "C1,End,2026-01-01 12:00:00\n"
        "C2,Start,2026-01-02 10:00:00\n"
        "C2,End,not-a-timestamp\n"
    )
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert reconstruction.complete_cases_count == 1
    assert reconstruction.incomplete_cases_count == 1

    analytics = calculate_process_analytics(reconstruction)

    # Evaluated cases count must be 1 (only complete cases)
    assert analytics.cycle_time.evaluated_cases_count == 1
    assert analytics.cycle_time.duration_stats.mean_seconds == 7200.0

    # Activity coverage denominator must be complete_cases_count (1)
    freq_map = {f.activity: f for f in analytics.activity_frequency}
    # C2's valid Start event must NOT contribute to complete case activity frequencies
    assert freq_map["Start"].case_count == 1
    assert freq_map["Start"].total_occurrences == 1
    assert freq_map["Start"].case_coverage_percentage == 100.0

def test_empty_input_and_zero_complete_cases():
    csv_data = "case_id,activity,timestamp\n"
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    analytics = calculate_process_analytics(reconstruction)

    assert analytics.reconstruction_summary.total_source_rows == 0
    assert analytics.cycle_time.evaluated_cases_count == 0
    assert analytics.cycle_time.duration_stats.mean_seconds == 0.0
    assert len(analytics.activity_frequency) == 0
    assert len(analytics.rework) == 0
    assert len(analytics.transitions) == 0

def test_only_incomplete_cases_no_zero_division():
    # Only invalid rows -> complete_cases_count = 0
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Start,invalid-date\n"
    )
    reconstruction = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert reconstruction.complete_cases_count == 0
    assert reconstruction.incomplete_cases_count == 1

    analytics = calculate_process_analytics(reconstruction)
    assert analytics.cycle_time.evaluated_cases_count == 0
    assert analytics.cycle_time.duration_stats.mean_seconds == 0.0
    assert len(analytics.activity_frequency) == 0
    assert len(analytics.rework) == 0

def test_api_analytics_quickstart_dataset(client, sample_quickstart_path):
    with open(sample_quickstart_path, "rb") as f:
        files = {"file": ("manufacturing_orders_quickstart.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["filename"] == "manufacturing_orders_quickstart.csv"
    summary = data["reconstruction_summary"]
    assert summary["complete_cases_count"] == 100
    assert summary["incomplete_cases_count"] == 0

    # Cycle time checks
    ct = data["cycle_time"]
    assert ct["evaluated_cases_count"] == 100
    assert ct["duration_stats"]["mean_seconds"] > 0
    assert ct["duration_stats"]["p90_seconds"] >= ct["duration_stats"]["median_seconds"]

    # Activity frequency checks
    freq = data["activity_frequency"]
    assert len(freq) > 0
    for f_item in freq:
        assert f_item["case_count"] > 0
        assert f_item["total_occurrences"] >= f_item["case_count"]
        assert 0.0 <= f_item["case_coverage_percentage"] <= 100.0

    # Transitions
    transitions = data["transitions"]
    assert len(transitions) > 0
    for t_item in transitions:
        assert t_item["transition_count"] > 0
        assert t_item["duration_stats"]["min_seconds"] >= 0.0

def test_api_analytics_clean_dataset(client, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        files = {"file": ("manufacturing_orders_clean.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["reconstruction_summary"]["complete_cases_count"] > 0
    assert data["reconstruction_summary"]["incomplete_cases_count"] == 0
    assert data["cycle_time"]["evaluated_cases_count"] > 0

def test_api_analytics_rework_dataset(client, sample_rework_path):
    with open(sample_rework_path, "rb") as f:
        files = {"file": ("manufacturing_orders_rework.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 200
    data = response.json()

    # In rework dataset, rework indicators should identify repeated activities
    rework = data["rework"]
    rework_found = [r for r in rework if r["rework_case_count"] > 0]
    assert len(rework_found) > 0
    for r in rework_found:
        assert r["rework_occurrences"] > 0
        assert r["rework_case_percentage"] > 0.0

def test_api_analytics_messy_dataset(client, sample_messy_path):
    with open(sample_messy_path, "rb") as f:
        files = {"file": ("manufacturing_orders_messy.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 200
    data = response.json()

    summary = data["reconstruction_summary"]
    assert summary["incomplete_cases_count"] > 0
    # Complete cases evaluated count must equal summary complete_cases_count
    assert data["cycle_time"]["evaluated_cases_count"] == summary["complete_cases_count"]

def test_transitions_exclude_duplicate_events_and_preserve_equal_timestamps():
    # Case C1: Order Received at 10:00, Order Received duplicate at 10:00, Dispatch at 11:00
    # Duplicate event must NOT produce a 0.0s self-transition (Order Received -> Order Received)
    # Case C2: Start at 10:00, ParallelStep at 10:00, End at 11:00
    # Distinct co-temporal activities MUST produce a 0.0s transition (Start -> ParallelStep)
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Dispatch,2026-01-01 11:00:00\n"
        "C2,Start,2026-01-02 10:00:00\n"
        "C2,ParallelStep,2026-01-02 10:00:00\n"
        "C2,End,2026-01-02 11:00:00\n"
    )
    rec = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    ana = calculate_process_analytics(rec)

    trans_pairs = {(t.source_activity, t.target_activity): t for t in ana.transitions}

    # 1. Artificial duplicate self-transition must be absent
    assert ("Order Received", "Order Received") not in trans_pairs

    # 2. Transition from non-duplicate Order Received to Dispatch must exist with 3600s
    assert ("Order Received", "Dispatch") in trans_pairs
    assert trans_pairs[("Order Received", "Dispatch")].duration_stats.mean_seconds == 3600.0

    # 3. Legitimate co-temporal transition between different activities must be preserved
    assert ("Start", "ParallelStep") in trans_pairs
    assert trans_pairs[("Start", "ParallelStep")].duration_stats.mean_seconds == 0.0
    assert trans_pairs[("Start", "ParallelStep")].transition_count == 1

    # 4. Subsequent transition in C2 preserved
    assert ("ParallelStep", "End") in trans_pairs
    assert trans_pairs[("ParallelStep", "End")].duration_stats.mean_seconds == 3600.0

def test_transitions_preserve_genuine_repeated_activity_loops():
    # Case C1: Inspect at 10:00, Fix at 11:00, Inspect at 12:00 (loop back at distinct timestamp)
    # Case C2: Inspect at 10:00, Inspect at 11:00 (immediate operational repetition at distinct timestamp)
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Inspect,2026-01-01 10:00:00\n"
        "C1,Fix,2026-01-01 11:00:00\n"
        "C1,Inspect,2026-01-01 12:00:00\n"
        "C2,Inspect,2026-01-02 10:00:00\n"
        "C2,Inspect,2026-01-02 11:00:00\n"
    )
    rec = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    ana = calculate_process_analytics(rec)

    trans_pairs = {(t.source_activity, t.target_activity): t for t in ana.transitions}

    # C1 loop transitions
    assert ("Inspect", "Fix") in trans_pairs
    assert ("Fix", "Inspect") in trans_pairs

    # C2 immediate self-loop at distinct timestamps MUST be preserved
    assert ("Inspect", "Inspect") in trans_pairs
    assert trans_pairs[("Inspect", "Inspect")].duration_stats.mean_seconds == 3600.0
    assert trans_pairs[("Inspect", "Inspect")].transition_count == 1

def test_analytics_non_csv_rejected(client):
    files = {"file": ("test.txt", b"some text content", "text/plain")}
    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_analytics_missing_required_headers(client):
    csv_data = "case_id,timestamp\nC1,2026-01-01 10:00:00\n"
    files = {"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")}
    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 400
    assert "Missing required canonical column" in response.json()["detail"]

def test_analytics_empty_filename_rejected(client):
    boundary = "boundary456"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    response = client.post("/api/v1/analytics/process", content=body, headers=headers)
    assert response.status_code == 400
    assert "Filename cannot be empty" in response.json()["detail"]

def test_analytics_exceeds_max_file_size(client):
    large_payload = b"case_id,activity,timestamp\n" + b"x" * (settings.MAX_FILE_SIZE_BYTES + 1)
    files = {"file": ("large.csv", large_payload, "text/csv")}
    response = client.post("/api/v1/analytics/process", files=files)
    assert response.status_code == 400
    assert "File size exceeds maximum allowed limit" in response.json()["detail"]
