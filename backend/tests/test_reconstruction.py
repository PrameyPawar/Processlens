"""
Unit and integration tests for Phase 2: Process Reconstruction.

Tests cover:
1.  Multiple cases with known activity sequences.
2.  Events uploaded in unsorted timestamp order.
3.  Two cases sharing the same variant.
4.  Different activity orders producing different variants.
5.  Repeated activities within a case.
6.  Equal timestamps with deterministic tie handling.
7.  Missing case IDs, missing activities, and invalid timestamps.
8.  Duplicate events remaining traceable.
9.  Empty input and input with no reconstructable cases.
10. Variant counts and percentages using documented denominator.
11. Existing Phase 0 and Phase 1 tests continue to pass (run separately).
"""

from app.services.reconstructor import reconstruct_process


# ────────────────────────────────────────────────────────────────
# 1. Multiple cases with known activity sequences
# ────────────────────────────────────────────────────────────────

def test_multiple_cases_basic():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
        "C-02,X,2026-01-01 09:00:00\n"
        "C-02,Y,2026-01-01 10:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.source_event_count == 4
    assert result.eligible_event_count == 4
    assert result.excluded_event_count == 0
    assert result.case_count == 2

    cases_by_id = {c.case_id: c for c in result.cases}
    assert cases_by_id["C-01"].activity_sequence == ["A", "B"]
    assert cases_by_id["C-02"].activity_sequence == ["X", "Y"]


# ────────────────────────────────────────────────────────────────
# 2. Events in unsorted timestamp order
# ────────────────────────────────────────────────────────────────

def test_unsorted_timestamps_reordered():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,B,2026-01-01 12:00:00\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,C,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    case = result.cases[0]
    assert case.activity_sequence == ["A", "C", "B"]
    # Verify events are in chronological order
    assert case.events[0].activity == "A"
    assert case.events[1].activity == "C"
    assert case.events[2].activity == "B"


# ────────────────────────────────────────────────────────────────
# 3. Two cases sharing the same variant
# ────────────────────────────────────────────────────────────────

def test_shared_variant():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
        "C-02,A,2026-01-02 10:00:00\n"
        "C-02,B,2026-01-02 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.variant_count == 1
    variant = result.variants[0]
    assert variant.activity_sequence == ["A", "B"]
    assert variant.case_count == 2
    assert set(variant.case_ids) == {"C-01", "C-02"}
    assert variant.case_percentage == 100.0

    # Both cases should have the same variant_id
    assert result.cases[0].variant_id == result.cases[1].variant_id


# ────────────────────────────────────────────────────────────────
# 4. Different activity orders produce different variants
# ────────────────────────────────────────────────────────────────

def test_different_orders_different_variants():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
        "C-02,B,2026-01-01 10:00:00\n"
        "C-02,A,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.variant_count == 2
    assert result.cases[0].variant_id != result.cases[1].variant_id

    variant_seqs = {tuple(v.activity_sequence) for v in result.variants}
    assert ("A", "B") in variant_seqs
    assert ("B", "A") in variant_seqs


# ────────────────────────────────────────────────────────────────
# 5. Repeated activities within a case
# ────────────────────────────────────────────────────────────────

def test_repeated_activities_preserved():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
        "C-01,A,2026-01-01 12:00:00\n"
        "C-01,B,2026-01-01 13:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    case = result.cases[0]
    assert case.activity_sequence == ["A", "B", "A", "B"]
    assert case.event_count == 4


# ────────────────────────────────────────────────────────────────
# 6. Equal timestamps with deterministic tie handling
# ────────────────────────────────────────────────────────────────

def test_equal_timestamps_deterministic_order():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,Z,2026-01-01 10:00:00\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,M,2026-01-01 10:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    case = result.cases[0]
    # Tie-breaking by row_index preserves original CSV order
    assert case.activity_sequence == ["Z", "A", "M"]
    assert case.events[0].row_index == 1
    assert case.events[1].row_index == 2
    assert case.events[2].row_index == 3

    # Running again should produce the same result
    result2 = reconstruct_process(csv.encode(), "test.csv")
    assert result2.cases[0].activity_sequence == case.activity_sequence


# ────────────────────────────────────────────────────────────────
# 7. Missing case IDs, missing activities, invalid timestamps
# ────────────────────────────────────────────────────────────────

def test_exclusions_missing_case_id():
    csv = (
        "case_id,activity,timestamp\n"
        ",A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.source_event_count == 2
    assert result.excluded_event_count == 1
    assert result.eligible_event_count == 1
    assert result.exclusions.missing_case_id == 1
    assert result.exclusions.excluded_events[0].reason == "MISSING_CASE_ID"
    assert result.exclusions.excluded_events[0].row_index == 1
    assert result.case_count == 1


def test_exclusions_missing_activity():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.excluded_event_count == 1
    assert result.exclusions.missing_activity == 1
    assert result.exclusions.excluded_events[0].reason == "MISSING_ACTIVITY"


def test_exclusions_invalid_timestamp():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,not-a-date\n"
        "C-01,B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.excluded_event_count == 1
    assert result.exclusions.missing_or_invalid_timestamp == 1
    assert result.exclusions.excluded_events[0].reason == "MISSING_OR_INVALID_TIMESTAMP"


def test_exclusions_missing_timestamp():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,\n"
        "C-01,B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.excluded_event_count == 1
    assert result.exclusions.missing_or_invalid_timestamp == 1


def test_multiple_exclusion_types():
    csv = (
        "case_id,activity,timestamp\n"
        ",A,2026-01-01 10:00:00\n"       # missing case_id
        "C-01,,2026-01-01 11:00:00\n"     # missing activity
        "C-01,B,garbage\n"                # invalid timestamp
        "C-01,C,2026-01-01 12:00:00\n"    # valid
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.source_event_count == 4
    assert result.excluded_event_count == 3
    assert result.eligible_event_count == 1
    assert result.exclusions.missing_case_id == 1
    assert result.exclusions.missing_activity == 1
    assert result.exclusions.missing_or_invalid_timestamp == 1
    assert result.case_count == 1
    assert result.cases[0].activity_sequence == ["C"]


# ────────────────────────────────────────────────────────────────
# 8. Duplicate events remaining traceable
# ────────────────────────────────────────────────────────────────

def test_duplicate_events_included_and_flagged():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,A,2026-01-01 10:00:00\n"   # duplicate
        "C-01,B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.eligible_event_count == 3  # duplicates are eligible
    assert result.excluded_event_count == 0
    assert result.exclusions.duplicate_events_included == 1

    case = result.cases[0]
    assert case.event_count == 3
    assert case.activity_sequence == ["A", "A", "B"]
    assert case.has_quality_warnings is True
    assert len(case.quality_warnings) == 1
    assert case.quality_warnings[0].warning_type == "DUPLICATE_EVENT"
    assert case.quality_warnings[0].row_index == 2


# ────────────────────────────────────────────────────────────────
# 9. Empty input and input with no reconstructable cases
# ────────────────────────────────────────────────────────────────

def test_empty_csv_raises_error():
    import pytest
    with pytest.raises(ValueError, match="empty"):
        reconstruct_process(b"", "empty.csv")


def test_header_only_csv():
    csv = "case_id,activity,timestamp\n"
    result = reconstruct_process(csv.encode(), "empty.csv")

    assert result.source_event_count == 0
    assert result.case_count == 0
    assert result.variant_count == 0
    assert result.cases == []
    assert result.variants == []


def test_all_rows_excluded():
    csv = (
        "case_id,activity,timestamp\n"
        ",A,2026-01-01 10:00:00\n"
        ",B,2026-01-01 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.source_event_count == 2
    assert result.excluded_event_count == 2
    assert result.eligible_event_count == 0
    assert result.case_count == 0
    assert result.variant_count == 0


# ────────────────────────────────────────────────────────────────
# 10. Variant counts and percentages
# ────────────────────────────────────────────────────────────────

def test_variant_percentages():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-01,B,2026-01-01 11:00:00\n"
        "C-02,A,2026-01-02 10:00:00\n"
        "C-02,B,2026-01-02 11:00:00\n"
        "C-03,A,2026-01-03 10:00:00\n"
        "C-03,B,2026-01-03 11:00:00\n"
        "C-04,X,2026-01-04 10:00:00\n"
        "C-04,Y,2026-01-04 11:00:00\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    assert result.case_count == 4
    assert result.variant_count == 2

    # Variants sorted by case_count desc
    v1 = result.variants[0]
    v2 = result.variants[1]
    assert v1.case_count == 3
    assert v1.case_percentage == 75.0
    assert v1.activity_sequence == ["A", "B"]
    assert v2.case_count == 1
    assert v2.case_percentage == 25.0
    assert v2.activity_sequence == ["X", "Y"]

    # Verify denominator is case_count (4), not event_count (8)
    assert v1.case_percentage + v2.case_percentage == 100.0


def test_variant_ids_stable():
    csv = (
        "case_id,activity,timestamp\n"
        "C-01,A,2026-01-01 10:00:00\n"
        "C-02,B,2026-01-02 10:00:00\n"
    )
    r1 = reconstruct_process(csv.encode(), "test.csv")
    r2 = reconstruct_process(csv.encode(), "test.csv")

    assert r1.variants[0].variant_id == r2.variants[0].variant_id
    assert r1.variants[1].variant_id == r2.variants[1].variant_id


# ────────────────────────────────────────────────────────────────
# 11. Metadata and resource preservation
# ────────────────────────────────────────────────────────────────

def test_resource_and_metadata_preserved():
    csv = (
        "case_id,activity,timestamp,resource,department\n"
        "C-01,A,2026-01-01 10:00:00,Worker-1,Sales\n"
        "C-01,B,2026-01-01 11:00:00,Worker-2,Warehouse\n"
    )
    result = reconstruct_process(csv.encode(), "test.csv")

    case = result.cases[0]
    assert case.events[0].resource == "Worker-1"
    assert case.events[0].metadata.get("department") == "Sales"
    assert case.events[1].resource == "Worker-2"
    assert case.events[1].metadata.get("department") == "Warehouse"


# ────────────────────────────────────────────────────────────────
# Integration: API endpoint tests
# ────────────────────────────────────────────────────────────────

def test_reconstruct_endpoint_rejects_non_csv(client):
    files = {"file": ("test.txt", b"not csv", "text/plain")}
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 400


def test_reconstruct_endpoint_rejects_missing_columns(client):
    csv = "col_a,col_b\nval1,val2"
    files = {"file": ("test.csv", csv.encode(), "text/csv")}
    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 400
    assert "Missing required column" in response.json()["detail"]


def test_reconstruct_endpoint_quickstart(client, sample_quickstart_path):
    with open(sample_quickstart_path, "rb") as f:
        files = {"file": ("quickstart.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["source_event_count"] == 800
    assert data["excluded_event_count"] == 0
    assert data["case_count"] == 100
    assert data["variant_count"] >= 1
    # All events accounted for
    assert data["eligible_event_count"] == data["source_event_count"]
    # Standard flow should be the dominant variant
    dominant = data["variants"][0]
    assert dominant["case_count"] >= 50  # majority of cases
    assert dominant["case_percentage"] >= 50.0


def test_reconstruct_endpoint_clean(client, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        files = {"file": ("clean.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["excluded_event_count"] == 0
    assert data["case_count"] > 0
    assert data["variant_count"] >= 1
    # Verify all variant percentages sum to ~100
    total_pct = sum(v["case_percentage"] for v in data["variants"])
    assert abs(total_pct - 100.0) < 0.1


def test_reconstruct_endpoint_rework(client, sample_rework_path):
    with open(sample_rework_path, "rb") as f:
        files = {"file": ("rework.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["case_count"] > 0
    # Rework dataset should have more variants than clean dataset
    assert data["variant_count"] >= 2
    # At least one variant should contain repeated activities (rework loop)
    has_repeat = False
    for v in data["variants"]:
        seq = v["activity_sequence"]
        if len(seq) != len(set(seq)):
            has_repeat = True
            break
    assert has_repeat, "Rework dataset should contain at least one variant with repeated activities"


def test_reconstruct_endpoint_messy(client, sample_messy_path):
    with open(sample_messy_path, "rb") as f:
        files = {"file": ("messy.csv", f.read(), "text/csv")}

    response = client.post("/api/v1/process/reconstruct", files=files)
    assert response.status_code == 200
    data = response.json()

    # Messy dataset should have exclusions
    assert data["excluded_event_count"] > 0
    assert data["source_event_count"] == data["eligible_event_count"] + data["excluded_event_count"]
    # Should still reconstruct some valid cases
    assert data["case_count"] > 0

    # Exclusion reasons should be detailed
    excl = data["exclusions"]
    total_excl = excl["missing_case_id"] + excl["missing_activity"] + excl["missing_or_invalid_timestamp"]
    assert total_excl == data["excluded_event_count"]
    assert len(excl["excluded_events"]) == total_excl
