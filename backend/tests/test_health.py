"""
Unit tests for backend health check endpoint.
"""

def test_health_check_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "processlens-backend"
    assert "version" in data
