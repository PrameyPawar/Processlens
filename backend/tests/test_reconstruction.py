"""
Tests for Process Reconstruction and Variant Derivation (Phase 2).
Covers deterministic sorting, variant derivation, data quality policy exclusions,
tie-breaking, duplicate handling, and sample datasets.
"""

import io
import pytest
from app.services.reconstruction import reconstruct_process_from_csv

def test_multiple_cases_known_sequences():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Check Inventory,2026-01-01 11:00:00\n"
        "C1,Dispatch,2026-01-01 12:00:00\n"
        "C2,Order Received,2026-01-02 09:00:00\n"
        "C2,Check Inventory,2026-01-02 10:00:00\n"
        "C2,Dispatch,2026-01-02 11:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert res.total_cases_found == 2
    assert res.reconstructed_cases_count == 2
    assert res.variant_count == 1
    assert res.variants[0].activity_sequence == ["Order Received", "Check Inventory", "Dispatch"]
    assert res.variants[0].case_count == 2
    assert res.variants[0].percentage == 100.0

def test_unsorted_timestamp_order():
    # Events uploaded out of chronological order
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Dispatch,2026-01-01 14:00:00\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Check Inventory,2026-01-01 12:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert res.reconstructed_cases_count == 1
    trace = res.cases[0]
    # Must be sorted chronologically regardless of upload order
    assert trace.activity_sequence == ["Order Received", "Check Inventory", "Dispatch"]
    assert [e.activity for e in trace.events] == ["Order Received", "Check Inventory", "Dispatch"]

def test_two_cases_sharing_same_variant():
    # Two cases with different timestamps and resources must share the same variant
    csv_data = (
        "case_id,activity,timestamp,resource\n"
        "C1,Start,2026-01-01 10:00:00,Alice\n"
        "C1,End,2026-01-01 11:00:00,Bob\n"
        "C2,Start,2026-02-01 08:00:00,Charlie\n"
        "C2,End,2026-02-01 09:00:00,David\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert res.variant_count == 1
    assert res.variants[0].case_count == 2
    assert sorted(res.variants[0].case_ids) == ["C1", "C2"]
    assert res.variants[0].percentage == 100.0

def test_different_activity_orders_produce_different_variants():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,A,2026-01-01 10:00:00\n"
        "C1,B,2026-01-01 11:00:00\n"
        "C2,B,2026-01-01 10:00:00\n"
        "C2,A,2026-01-01 11:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert res.variant_count == 2
    seqs = [v.activity_sequence for v in res.variants]
    assert ["A", "B"] in seqs
    assert ["B", "A"] in seqs
    assert res.variants[0].case_count == 1
    assert res.variants[1].case_count == 1
    assert res.variants[0].percentage == 50.0
    assert res.variants[1].percentage == 50.0

def test_repeated_activities_not_collapsed():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Inspect,2026-01-01 10:00:00\n"
        "C1,Rework,2026-01-01 11:00:00\n"
        "C1,Inspect,2026-01-01 12:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    trace = res.cases[0]
    assert trace.activity_sequence == ["Inspect", "Rework", "Inspect"]
    assert len(trace.events) == 3
    assert res.variants[0].activity_sequence == ["Inspect", "Rework", "Inspect"]

def test_equal_timestamps_deterministic_tie_breaking():
    # Two events with identical timestamps; sort must break ties by row_index stably
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,FirstUploaded,2026-01-01 10:00:00\n"
        "C1,SecondUploaded,2026-01-01 10:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    trace = res.cases[0]
    assert trace.activity_sequence == ["FirstUploaded", "SecondUploaded"]
    assert trace.events[0].row_index < trace.events[1].row_index

def test_exclusions_and_incomplete_cases():
    csv_data = (
        "case_id,activity,timestamp\n"
        ",Activity1,2026-01-01 10:00:00\n"           # row 1: missing case_id
        "C_Good,Activity1,2026-01-01 10:00:00\n"     # row 2: valid
        "C_Bad,Activity1,2026-01-01 10:00:00\n"      # row 3: valid event in C_Bad
        "C_Bad,,2026-01-01 11:00:00\n"               # row 4: missing activity
        "C_Bad2,Activity1,not_a_timestamp\n"         # row 5: invalid timestamp
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert 1 in res.exclusions.missing_case_id_rows
    assert 4 in res.exclusions.missing_activity_rows
    assert 5 in res.exclusions.missing_or_invalid_timestamp_rows
    assert res.exclusions.total_excluded_rows == 3

    # C_Bad and C_Bad2 should be flagged incomplete
    assert "C_Bad" in res.exclusions.incomplete_case_ids
    assert "C_Bad2" in res.exclusions.incomplete_case_ids
    assert res.reconstructed_cases_count == 1
    assert res.variants[0].case_ids == ["C_Good"]

def test_duplicate_events_preserved_and_flagged():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Order Received,2026-01-01 10:00:00\n" # duplicate row
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    trace = res.cases[0]
    assert len(trace.events) == 2
    assert trace.events[0].is_duplicate is False
    assert trace.events[1].is_duplicate is True
    # Sequence retains repeated activity
    assert trace.activity_sequence == ["Order Received", "Order Received"]

def test_empty_input_and_no_cases():
    csv_data = "case_id,activity,timestamp\n"
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "empty.csv")
    assert res.total_source_rows == 0
    assert res.eligible_event_count == 0
    assert res.total_cases_found == 0
    assert res.reconstructed_cases_count == 0
    assert res.variant_count == 0
    assert res.variants == []

def test_variant_percentages_documented_denominator():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,A,2026-01-01 10:00:00\n"
        "C2,A,2026-01-01 10:00:00\n"
        "C3,A,2026-01-01 10:00:00\n"
        "C4,B,2026-01-01 10:00:00\n"
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    assert res.reconstructed_cases_count == 4
    assert res.variant_count == 2
    # 3 cases for A = 75.0%
    assert res.variants[0].activity_sequence == ["A"]
    assert res.variants[0].case_count == 3
    assert res.variants[0].percentage == 75.0
    # 1 case for B = 25.0%
    assert res.variants[1].activity_sequence == ["B"]
    assert res.variants[1].case_count == 1
    assert res.variants[1].percentage == 25.0
    # Sum of percentages equals 100.0%
    total_pct = sum(v.percentage for v in res.variants)
    assert total_pct == 100.0

def test_reconstruct_quickstart_dataset(client, sample_quickstart_path):
    with open(sample_quickstart_path, "rb") as f:
        files = {"file": ("manufacturing_orders_quickstart.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_source_rows"] == 800
    assert data["eligible_event_count"] == 800
    assert data["total_cases_found"] == 100
    assert data["reconstructed_cases_count"] == 100
    assert data["exclusions"]["total_excluded_rows"] == 0
    assert len(data["variants"]) > 0

def test_reconstruct_clean_dataset(client, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        files = {"file": ("manufacturing_orders_clean.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_source_rows"] > 0
    assert data["reconstructed_cases_count"] > 0
    # Dominant variant should have highest case count
    dominant = data["variants"][0]
    assert dominant["case_count"] > 0
    assert dominant["percentage"] > 0

def test_reconstruct_rework_dataset(client, sample_rework_path):
    with open(sample_rework_path, "rb") as f:
        files = {"file": ("manufacturing_orders_rework.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["reconstructed_cases_count"] > 0
    # Rework should produce multiple distinct variants
    rework_variants = [v for v in data["variants"] if "Rework" in v["activity_sequence"]]
    assert len(rework_variants) > 0

def test_reconstruct_messy_dataset(client, sample_messy_path):
    with open(sample_messy_path, "rb") as f:
        files = {"file": ("manufacturing_orders_messy.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    # Messy dataset must report exclusions and incomplete cases
    exclusions = data["exclusions"]
    assert exclusions["total_excluded_rows"] > 0
    assert len(exclusions["incomplete_case_ids"]) > 0
