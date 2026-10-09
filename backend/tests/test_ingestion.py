"""
Integration and unit tests for CSV file ingestion and quality validation.
"""

import io
from app.services.validator import validate_csv_content

def test_upload_non_csv_rejected(client):
    files = {"file": ("test.txt", b"some text content", "text/plain")}
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]

def test_upload_missing_required_column(client):
    csv_data = "col1,col2\nval1,val2"
    files = {"file": ("test.csv", csv_data.encode("utf-8"), "text/csv")}
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 400
    assert "Missing required canonical column" in response.json()["detail"]

def test_validate_quickstart_sample(client, sample_quickstart_path):
    with open(sample_quickstart_path, "rb") as f:
        files = {"file": ("manufacturing_orders_quickstart.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["filename"] == "manufacturing_orders_quickstart.csv"
    assert data["total_rows"] == 800
    assert data["valid_rows"] == 800
    assert data["invalid_rows"] == 0
    assert len(data["preview"]) == 10
    assert data["preview"][0]["case_id"] == "ORD-00001"

def test_validate_clean_sample(client, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        files = {"file": ("manufacturing_orders_clean.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rows"] > 0
    assert data["invalid_rows"] == 0
    assert data["valid_rows"] == data["total_rows"]

def test_validate_messy_sample(client, sample_messy_path):
    with open(sample_messy_path, "rb") as f:
        files = {"file": ("manufacturing_orders_messy.csv", f.read(), "text/csv")}
    
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 200
    data = response.json()

    assert data["total_rows"] > 0
    assert data["invalid_rows"] > 0
    assert len(data["issues"]) > 0
    
    # Check that summary aggregates reported issues correctly
    summary = data["summary"]
    total_issues_in_summary = (
        summary["missing_case_id_count"] +
        summary["missing_activity_count"] +
        summary["missing_timestamp_count"] +
        summary["invalid_timestamp_count"] +
        summary["duplicate_event_count"]
    )
    assert total_issues_in_summary > 0

def test_direct_validator_unit_test():
    raw_csv = (
        "case_id,activity,timestamp\n"
        "C-01,Order Received,2026-01-01 10:00:00\n"
        ",Order Verification,2026-01-01 11:00:00\n"  # missing case_id
        "C-01,,2026-01-01 12:00:00\n"               # missing activity
        "C-01,Production,invalid_timestamp_str\n"     # invalid timestamp
        "C-01,Order Received,2026-01-01 10:00:00\n" # duplicate event
    )
    report = validate_csv_content(raw_csv.encode("utf-8"), "unit_test.csv")
    assert report.total_rows == 5
    assert report.valid_rows == 1
    assert report.invalid_rows == 4
    assert report.summary.missing_case_id_count == 1
    assert report.summary.missing_activity_count == 1
    assert report.summary.invalid_timestamp_count == 1
    assert report.summary.duplicate_event_count == 1
