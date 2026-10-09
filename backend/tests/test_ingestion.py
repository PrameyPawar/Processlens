"""
Integration and unit tests for CSV file ingestion and quality validation.
"""

import io
from app.core.config import settings
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

def test_upload_empty_filename_rejected(client):
    boundary = "boundary789"
    body = (
        b"--" + boundary.encode() + b"\r\n"
        b'Content-Disposition: form-data; name="file"; filename=""\r\n'
        b"Content-Type: text/csv\r\n\r\n"
        b"case_id,activity,timestamp\r\n"
        b"--" + boundary.encode() + b"--\r\n"
    )
    headers = {"Content-Type": f"multipart/form-data; boundary={boundary}"}
    response = client.post("/api/v1/ingestion/upload", content=body, headers=headers)
    assert response.status_code == 400
    assert "Filename cannot be empty" in response.json()["detail"]

def test_upload_exceeds_max_file_size(client):
    large_payload = b"case_id,activity,timestamp\n" + b"x" * (settings.MAX_FILE_SIZE_BYTES + 1)
    files = {"file": ("large.csv", large_payload, "text/csv")}
    response = client.post("/api/v1/ingestion/upload", files=files)
    assert response.status_code == 400
    assert "File size exceeds maximum allowed limit" in response.json()["detail"]

def test_upload_duplicate_key_normalized_timestamp():
    # Two events with same datetime but different textual representations
    raw_csv = (
        "case_id,activity,timestamp\n"
        "C-01,Inspect,2026-01-01 10:00:00\n"
        "C-01,Inspect,2026-01-01T10:00:00\n"
    )
    report = validate_csv_content(raw_csv.encode("utf-8"), "norm_test.csv")
    assert report.total_rows == 2
    assert report.summary.duplicate_event_count == 1
    assert report.invalid_rows == 1
