"""
Tests for Process Reconstruction and Variant Derivation (Phase 2).
Covers deterministic sorting, variant derivation, structured data quality exclusions,
tie-breaking, duplicate handling, and sample datasets.
"""

import io
import pytest
from app.core.config import settings
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
    assert res.complete_cases_count == 2
    assert res.incomplete_cases_count == 0
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
    assert res.complete_cases_count == 1
    assert res.incomplete_cases_count == 0
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

def test_extra_csv_cells_exclude_the_row_and_mark_case_incomplete():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Start,2026-01-01 10:00:00,unexpected\n"
        "C1,End,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process_from_csv(csv_data.encode("utf-8"), "malformed.csv")
    case = result.cases[0]
    assert result.total_source_rows == 2
    assert result.eligible_event_count == 1
    assert result.complete_cases_count == 0
    assert case.is_complete is False
    assert case.excluded_events[0].issue_type == "MALFORMED_ROW"
    assert case.excluded_events[0].raw_values["__extra_columns__"] == ["unexpected"]

def test_structured_exclusions_and_incomplete_cases():
    csv_data = (
        "case_id,activity,timestamp,resource\n"
        ",Activity1,2026-01-01 10:00:00,R1\n"               # row 1: missing case_id
        "C_Good,Activity1,2026-01-01 10:00:00,R2\n"         # row 2: valid in C_Good
        "C_Bad,Activity1,2026-01-01 10:00:00,R3\n"          # row 3: valid in C_Bad
        "C_Bad,,2026-01-01 11:00:00,R4\n"                   # row 4: missing activity
        "C_Bad2,Activity1,not_a_timestamp,R5\n"             # row 5: invalid timestamp
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    
    # Exclusions counts
    assert res.exclusions.total_excluded_rows == 3
    assert res.exclusions.missing_case_id_count == 1
    assert res.exclusions.missing_activity_count == 1
    assert res.exclusions.missing_or_invalid_timestamp_count == 1
    
    # Structured excluded event records
    ex_events = res.exclusions.excluded_events
    assert len(ex_events) == 3
    
    # Check row 1: missing case_id
    ex_row1 = next(e for e in ex_events if e.row_index == 1)
    assert ex_row1.issue_type == "MISSING_CASE_ID"
    assert ex_row1.case_id is None
    assert ex_row1.raw_values["activity"] == "Activity1"
    
    # Check row 4: missing activity
    ex_row4 = next(e for e in ex_events if e.row_index == 4)
    assert ex_row4.issue_type == "MISSING_ACTIVITY"
    assert ex_row4.case_id == "C_Bad"
    assert ex_row4.raw_values["case_id"] == "C_Bad"
    
    # Check row 5: invalid timestamp
    ex_row5 = next(e for e in ex_events if e.row_index == 5)
    assert ex_row5.issue_type == "INVALID_TIMESTAMP"
    assert ex_row5.case_id == "C_Bad2"
    assert ex_row5.raw_values["timestamp"] == "not_a_timestamp"

    # Case-level completeness and isolation from variants
    assert res.complete_cases_count == 1
    assert res.incomplete_cases_count == 2
    assert "C_Bad" in res.exclusions.incomplete_case_ids
    assert "C_Bad2" in res.exclusions.incomplete_case_ids

    # C_Bad trace inspection
    c_bad_trace = next(c for c in res.cases if c.case_id == "C_Bad")
    assert c_bad_trace.is_complete is False
    assert len(c_bad_trace.events) == 1  # only valid event retained
    assert len(c_bad_trace.excluded_events) == 1
    assert c_bad_trace.excluded_events[0].issue_type == "MISSING_ACTIVITY"

    # Ensure incomplete cases are NOT in variant statistics
    all_variant_cases = [cid for v in res.variants for cid in v.case_ids]
    assert all_variant_cases == ["C_Good"]
    assert "C_Bad" not in all_variant_cases
    assert "C_Bad2" not in all_variant_cases

def test_duplicate_events_preserved_and_flagged():
    csv_data = (
        "case_id,activity,timestamp\n"
        "C1,Order Received,2026-01-01 10:00:00\n"
        "C1,Order Received,2026-01-01 10:00:00\n"  # duplicate row
    )
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "test.csv")
    trace = res.cases[0]
    assert len(trace.events) == 2
    assert trace.events[0].is_duplicate is False
    assert trace.events[1].is_duplicate is False
    assert trace.events[1].is_potential_duplicate is True
    # Sequence retains repeated activity
    assert trace.activity_sequence == ["Order Received", "Order Received"]

def test_distinct_source_event_ids_preserve_same_timestamp_events():
    csv_data = (
        "source_event_id,case_id,activity,timestamp\n"
        "evt-1,C1,Inspect,2026-01-01 10:00:00\n"
        "evt-2,C1,Inspect,2026-01-01 10:00:00\n"
    )
    result = reconstruct_process_from_csv(csv_data.encode("utf-8"), "same_timestamp_distinct_ids.csv")
    events = result.cases[0].events
    assert [event.source_event_id for event in events] == ["evt-1", "evt-2"]
    assert all(not event.is_duplicate for event in events)
    assert all(not event.is_potential_duplicate for event in events)

def test_repeated_source_event_id_is_flagged_and_preserved():
    csv_data = (
        "eventID,case_id,activity,timestamp\n"
        "evt-1,C1,Inspect,2026-01-01 10:00:00\n"
        "evt-1,C1,Inspect,2026-01-01 10:00:00\n"
    )
    result = reconstruct_process_from_csv(csv_data.encode("utf-8"), "repeated_source_id.csv")
    events = result.cases[0].events
    assert len(events) == 2
    assert [event.is_duplicate for event in events] == [False, True]
    assert result.cases[0].is_complete

def test_duplicate_event_ids_are_scoped_to_case():
    csv_data = (
        "event_id,case_id,activity,timestamp\n"
        "evt-1,C1,Start,2026-01-01 10:00:00\n"
        "evt-1,C2,Start,2026-01-01 10:00:00\n"
    )
    result = reconstruct_process_from_csv(csv_data.encode("utf-8"), "case_scoped_ids.csv")
    assert all(not event.is_duplicate for case in result.cases for event in case.events)

def test_empty_input_and_no_cases():
    csv_data = "case_id,activity,timestamp\n"
    res = reconstruct_process_from_csv(csv_data.encode("utf-8"), "empty.csv")
    assert res.total_source_rows == 0
    assert res.eligible_event_count == 0
    assert res.total_cases_found == 0
    assert res.complete_cases_count == 0
    assert res.incomplete_cases_count == 0
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
    assert res.complete_cases_count == 4
    assert res.incomplete_cases_count == 0
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
    assert data["complete_cases_count"] == 100
    assert data["incomplete_cases_count"] == 0
    assert data["exclusions"]["total_excluded_rows"] == 0
    assert len(data["variants"]) > 0

def test_reconstruct_clean_dataset(client, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        files = {"file": ("manufacturing_orders_clean.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_source_rows"] > 0
    assert data["complete_cases_count"] > 0
    assert data["incomplete_cases_count"] == 0
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

    assert data["complete_cases_count"] > 0
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
    assert len(exclusions["excluded_events"]) == exclusions["total_excluded_rows"]
    assert data["incomplete_cases_count"] > 0

def test_reconstruct_non_csv_rejected(client):
    files = {"file": ("test.txt", b"some text content", "text/plain")}
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_reconstruct_missing_required_headers(client):
    csv_data = "case_id,timestamp\nC1,2026-01-01 10:00:00\n"
    files = {"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")}
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 400
    assert "Missing required canonical column" in response.json()["detail"]

def test_reconstruct_empty_filename_rejected(client):
    boundary = "boundary123"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    response = client.post("/api/v1/process/reconstruct", content=body, headers=headers)
    assert response.status_code == 400
    assert "Filename cannot be empty" in response.json()["detail"]

def test_reconstruct_exceeds_max_file_size(client):
    large_payload = b"case_id,activity,timestamp\n" + b"x" * (settings.MAX_FILE_SIZE_BYTES + 1)
    files = {"file": ("large.csv", large_payload, "text/csv")}
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 413
    assert "File size exceeds maximum allowed limit" in response.json()["detail"]
