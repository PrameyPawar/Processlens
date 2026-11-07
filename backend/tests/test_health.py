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


def test_cors_allowed_origin(client):
    """Verify that requests from an allowed origin receive CORS headers."""
    response = client.get("/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert response.headers.get("access-control-allow-credentials") == "true"


def test_cors_disallowed_origin(client):
    """Verify that requests from an unapproved origin do not receive CORS allow origin header."""
    response = client.get("/health", headers={"Origin": "http://untrusted-domain.example.com"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_cors_preflight_allowed_origin(client):
    """Verify OPTIONS preflight request from allowed origin."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.status_code == 200
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
