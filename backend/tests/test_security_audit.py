"""
ProcessLens Phase 11.8: Comprehensive Authentication Security Audit & Hardening Test Suite.
Adversarial tests verifying endpoint authorization, token revocation, CSRF origin checks,
durable persistence across restarts, production configuration gates, and information leak prevention.
"""

import os
import time
import tempfile
import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings, Settings
from app.core.auth import create_auth_token
from app.services.user_store import UserStore, user_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_store_state():
    """Reset the global user store and rate limiter state before each test."""
    user_store.reset_for_tests()
    yield
    user_store.reset_for_tests()

# ==============================================================================
# 1. Full Endpoint Authorization & Policy Tests
# ==============================================================================

@pytest.mark.parametrize("route", [
    f"{settings.API_V1_STR}/ingestion/upload",
    f"{settings.API_V1_STR}/process/reconstruct",
    f"{settings.API_V1_STR}/analytics/process",
    f"{settings.API_V1_STR}/problems/detect",
    f"{settings.API_V1_STR}/opportunities/detect",
    f"{settings.API_V1_STR}/readiness/assess",
    f"{settings.API_V1_STR}/economics/evaluate",
    f"{settings.API_V1_STR}/prioritisation/rank",
    f"{settings.API_V1_STR}/evidence/audit",
    f"{settings.API_V1_STR}/explanation/generate",
])
def test_analysis_routes_reject_anonymous_uploads(route):
    """Customer analysis endpoints never accept anonymous uploads."""
    from app.core.dependencies import require_analysis_user
    override = app.dependency_overrides.pop(require_analysis_user, None)
    try:
        resp = client.post(
            route,
            files={"file": ("sample.csv", b"case_id,activity,timestamp\n1,A,2026-01-01T00:00:00Z\n", "text/csv")},
        )
        assert resp.status_code == 401, (route, resp.status_code, resp.text)
    finally:
        if override is not None:
            app.dependency_overrides[require_analysis_user] = override


def test_analysis_upload_over_limit_is_rejected(monkeypatch):
    """Upload handler rejects a customer upload larger than the configured file cap."""
    monkeypatch.setattr(settings, "MAX_FILE_SIZE_BYTES", 32)
    resp = client.post(
        f"{settings.API_V1_STR}/ingestion/upload",
        files={"file": ("large.csv", b"x" * 33, "text/csv")},
    )
    assert resp.status_code == 413


def test_forwarded_ip_header_is_not_trusted_by_default():
    """Client-supplied X-Forwarded-For cannot evade authentication throttling."""
    from starlette.requests import Request
    from app.api.v1.auth import get_client_ip
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/", "raw_path": b"/",
        "query_string": b"", "headers": [(b"x-forwarded-for", b"203.0.113.9")],
        "client": ("198.51.100.7", 12345), "server": ("testserver", 80),
    }
    assert get_client_ip(Request(scope)) == "198.51.100.7"


def test_health_endpoint_is_minimal_and_leak_free():
    """Public /health endpoint returns only minimal readiness telemetry without secrets or system internals."""
    resp = client.get("/health")
    assert resp.status_code == 200
    data = resp.json()
    assert set(data.keys()) == {"status", "service", "version"}
    assert data["status"] == "ok"
    assert "uptime" not in data
    assert "environment" not in data
    assert "python" not in data
    assert "secret" not in str(data).lower()

@pytest.mark.parametrize("route,method", [
    (f"{settings.API_V1_STR}/auth/me", "GET"),
    (f"{settings.API_V1_STR}/customer/workspace", "GET"),
    (f"{settings.API_V1_STR}/dev/status", "GET"),
    (f"{settings.API_V1_STR}/dev/audit-events", "GET"),
])
def test_protected_routes_reject_missing_credentials(route, method):
    """Every protected endpoint must return 401 Unauthorized when credentials are absent."""
    fresh_client = TestClient(app)
    resp = fresh_client.request(method, route)
    assert resp.status_code == 401
    assert "authentication required" in resp.json()["detail"].lower()

@pytest.mark.parametrize("route,method", [
    (f"{settings.API_V1_STR}/auth/me", "GET"),
    (f"{settings.API_V1_STR}/customer/workspace", "GET"),
    (f"{settings.API_V1_STR}/dev/status", "GET"),
    (f"{settings.API_V1_STR}/dev/audit-events", "GET"),
])
def test_protected_routes_reject_tampered_token(route, method):
    """Every protected endpoint must return 401 Unauthorized when token signature is tampered."""
    tampered = "eyJhbGciOiJIUzI1NiJ9.fake_tampered_payload.invalidsig"
    resp = client.request(method, route, headers={"Authorization": f"Bearer {tampered}"})
    assert resp.status_code == 401
    assert "invalid or tampered" in resp.json()["detail"].lower()

@pytest.mark.parametrize("route,method", [
    (f"{settings.API_V1_STR}/auth/me", "GET"),
    (f"{settings.API_V1_STR}/customer/workspace", "GET"),
    (f"{settings.API_V1_STR}/dev/status", "GET"),
    (f"{settings.API_V1_STR}/dev/audit-events", "GET"),
])
def test_protected_routes_reject_expired_token(route, method):
    """Every protected endpoint must return 401 Unauthorized when session token has expired."""
    payload = {"sub": "usr_cust_test", "email": "customer@processlens.com", "role": "customer", "name": "Test User"}
    # Generate token with negative max_age or simulate expiration
    token = create_auth_token(payload)
    
    # Mock decode_auth_token in dependencies module to simulate token expiry
    from app.core import dependencies
    original_decode = dependencies.decode_auth_token
    try:
        def raise_expired(*args, **kwargs):
            raise ValueError("Session token has expired. Please log in again.")
        dependencies.decode_auth_token = raise_expired
        resp = client.request(method, route, headers={"Authorization": f"Bearer {token}"})
        assert resp.status_code == 401
        assert "expired" in resp.json()["detail"].lower()
    finally:
        dependencies.decode_auth_token = original_decode


# ==============================================================================
# 2. Cross-Customer & Role Boundary Enforcement
# ==============================================================================

def test_customer_cannot_access_developer_endpoints():
    """Customer role calling developer diagnostics receives 403 Forbidden."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    cust_token = login_resp.json()["access_token"]
    
    # 1. Dev status
    resp_status = client.get(
        f"{settings.API_V1_STR}/dev/status",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert resp_status.status_code == 403
    assert "lacks required permissions" in resp_status.json()["detail"]

    # 2. Dev audit events
    resp_audit = client.get(
        f"{settings.API_V1_STR}/dev/audit-events",
        headers={"Authorization": f"Bearer {cust_token}"},
    )
    assert resp_audit.status_code == 403

def test_developer_cannot_access_customer_workspace():
    """Developer role calling customer private workspace receives 403 Forbidden to protect customer confidentiality."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEV_ADMIN_EMAIL, "password": settings.DEV_ADMIN_PASSWORD},
    )
    dev_token = login_resp.json()["access_token"]

    resp = client.get(
        f"{settings.API_V1_STR}/customer/workspace",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert resp.status_code == 403
    assert "lacks required permissions" in resp.json()["detail"]

# ==============================================================================
# 3. Server-Side Token Revocation & Invalidation
# ==============================================================================

def test_server_side_token_revocation_on_logout():
    """Revoked token cannot be reused even if retained in headers by an attacker."""
    # Step 1: Login
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    token = login_resp.json()["access_token"]

    # Step 2: Verify active session works
    me_resp = client.get(f"{settings.API_V1_STR}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200

    # Step 3: Logout
    logout_resp = client.post(f"{settings.API_V1_STR}/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert logout_resp.status_code == 200

    # Step 4: Token must be revoked immediately
    revoked_resp = client.get(f"{settings.API_V1_STR}/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert revoked_resp.status_code == 401
    assert "revoked" in revoked_resp.json()["detail"].lower()

# ==============================================================================
# 4. CSRF Protection for Cookie-Authenticated Mutating Requests
# ==============================================================================

def test_csrf_rejection_for_untrusted_cross_origin_cookie_requests():
    """State-changing requests using session cookies with untrusted Origin header must be rejected with 403."""
    # Obtain valid session cookie
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    token = login_resp.json()["access_token"]

    # Simulate malicious site making cookie-authenticated POST
    untrusted_resp = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        cookies={settings.AUTH_COOKIE_NAME: token},
        headers={"Origin": "https://malicious-attacker.com"},
    )
    assert untrusted_resp.status_code == 403
    assert "csrf" in untrusted_resp.json()["detail"].lower()

def test_csrf_permits_trusted_origin_cookie_requests():
    """State-changing requests with trusted origin succeed normally."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    token = login_resp.json()["access_token"]

    trusted_resp = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        cookies={settings.AUTH_COOKIE_NAME: token},
        headers={"Origin": "http://localhost:5173"},
    )
    assert trusted_resp.status_code == 200

def test_csrf_rejects_cookie_mutation_without_origin_or_referer():
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    token = login_resp.json()["access_token"]
    response = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        cookies={settings.AUTH_COOKIE_NAME: token},
    )
    assert response.status_code == 403

# ==============================================================================
# 5. Role Escalation & Account Registration Hardening
# ==============================================================================

def test_registration_strictly_enforces_customer_role():
    """Public registration ignores any submitted 'role' parameter and enforces customer role."""
    reg_resp = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "hacker.attempt@example.com",
            "name": "Hacker",
            "password": "Password2026!",
            "role": "developer",  # Malicious attempt to escalate role
        },
    )
    assert reg_resp.status_code == 201
    user_data = reg_resp.json()["user"]
    assert user_data["role"] == "customer"
    assert user_data["role"] != "developer"

def test_duplicate_registration_fails_cleanly():
    """Registering an existing email address returns a clear 400 error."""
    resp1 = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "unique.user@plant.co.uk", "name": "User One", "password": "Password2026!"},
    )
    assert resp1.status_code == 201

    resp2 = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={"email": "unique.user@plant.co.uk", "name": "User Duplicate", "password": "Password2026!"},
    )
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"].lower()

# ==============================================================================
# 6. Durable Storage Across Restarts & Transactions
# ==============================================================================

def test_sqlite_rate_limit_is_shared_between_store_instances():
    """SQLite-backed throttling is shared by app workers using the same database."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    try:
        store1 = UserStore(db_path=db_path)
        store2 = UserStore(db_path=db_path)
        for _ in range(5):
            assert store1.consume_rate_limit("login:203.0.113.25") is True
        assert store2.is_rate_limited("login:203.0.113.25") is True
        assert store2.consume_rate_limit("login:203.0.113.25") is False
        store2.reset_attempts("login:203.0.113.25")
        assert store1.consume_rate_limit("login:203.0.113.25") is True
    finally:
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass


def test_durable_sqlite_user_store_persistence():
    """Customer registration and token revocation persist across application restarts in durable storage."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()

    try:
        # 1. Instantiate UserStore with durable SQLite file
        store1 = UserStore(db_path=db_path)
        new_user = store1.create_customer_user(
            email="persisted.sme@factory.co.uk",
            name="Plant Director",
            password="DurablePassword2026!",
        )
        assert new_user.id is not None
        store1.revoke_token("tok_test_revoked_123")

        # 2. Simulate complete process restart by destroying store1 and creating store2 from same DB
        del store1
        store2 = UserStore(db_path=db_path)

        # 3. Verify user survived restart
        reloaded = store2.get_user_by_email("persisted.sme@factory.co.uk")
        assert reloaded is not None
        assert reloaded.name == "Plant Director"
        assert reloaded.role == "customer"
        assert store2.is_token_revoked("tok_test_revoked_123") is True

        # 4. Verify transactional duplicate constraint
        with pytest.raises(ValueError, match="already exists"):
            store2.create_customer_user("persisted.sme@factory.co.uk", "Duplicate", "AnotherPassword2026!")
    finally:
        import gc
        gc.collect()
        if os.path.exists(db_path):
            try:
                os.remove(db_path)
            except OSError:
                pass

def test_revocation_storage_failure_does_not_fail_open(monkeypatch):
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    db_path = tmp.name
    tmp.close()
    store = UserStore(db_path=db_path)
    def unavailable(*args, **kwargs):
        raise __import__("sqlite3").OperationalError("simulated unavailable database")
    monkeypatch.setattr("app.services.user_store.sqlite3.connect", unavailable)
    with pytest.raises(Exception, match="Session state storage is unavailable"):
        store.is_token_revoked("tok_unknown")
    with pytest.raises(Exception, match="Session state storage is unavailable"):
        store.revoke_token("tok_test")
    monkeypatch.undo()
    del store
    import gc
    gc.collect()
    os.remove(db_path)

def test_production_configuration_requires_durable_auth_store():
    prod = Settings()
    prod.ENVIRONMENT = "production"
    prod.AUTH_SECRET_KEY = "a-very-long-and-secure-random-64-character-string-for-prod-environment"
    prod.AUTH_SECURE_COOKIE = True
    prod.DEV_ADMIN_PASSWORD = "StrongDevPassword2026!#"
    prod.DEMO_CUSTOMER_PASSWORD = "StrongCustomerPassword2026!#"
    prod.CORS_ORIGINS = ["https://app.processlens.com"]
    prod.AUTH_SECRET_KEY_CONFIGURED = True
    prod.DEV_ADMIN_PASSWORD_CONFIGURED = True
    prod.DEMO_CUSTOMER_PASSWORD_CONFIGURED = True
    prod.USER_STORE_DB_PATH = None
    with pytest.raises(ValueError, match="USER_STORE_DB_PATH"):
        prod.validate_configuration()


# ==============================================================================
# 7. Production Startup Configuration Verification
# ==============================================================================

def test_production_startup_validation_rejects_insecure_defaults():
    """Settings.validate_configuration() must reject production deployment with insecure dev defaults."""
    bad_settings = Settings()
    bad_settings.ENVIRONMENT = "production"
    bad_settings.AUTH_SECRET_KEY = bad_settings.DEFAULT_DEV_SECRET
    bad_settings.AUTH_SECURE_COOKIE = False
    bad_settings.CORS_ORIGINS = ["*"]
    
    with pytest.raises(ValueError) as exc:
        bad_settings.validate_configuration()
    
    err_text = str(exc.value)
    assert "AUTH_SECRET_KEY must be changed" in err_text
    assert "AUTH_SECURE_COOKIE must be enabled" in err_text
    assert "CORS_ORIGINS cannot contain wildcard" in err_text

def test_production_startup_validation_accepts_hardened_settings():
    """Settings.validate_configuration() passes cleanly with hardened production configuration."""
    prod_settings = Settings()
    prod_settings.ENVIRONMENT = "production"
    prod_settings.AUTH_SECRET_KEY = "a-very-long-and-secure-random-64-character-string-for-prod-environment"
    prod_settings.AUTH_SECURE_COOKIE = True
    prod_settings.DEV_ADMIN_PASSWORD = "StrongDevPassword2026!#"
    prod_settings.DEMO_CUSTOMER_PASSWORD = "StrongCustomerPassword2026!#"
    prod_settings.CORS_ORIGINS = ["https://app.processlens.com"]
    prod_settings.USER_STORE_DB_PATH = "C:/var/lib/processlens/auth.db"
    prod_settings.AUTH_SECRET_KEY_CONFIGURED = True
    prod_settings.DEV_ADMIN_PASSWORD_CONFIGURED = True
    prod_settings.DEMO_CUSTOMER_PASSWORD_CONFIGURED = True
    
    # Should execute without raising ValueError
    prod_settings.validate_configuration()

# ==============================================================================
# 8. Password Recovery Honest Status
# ==============================================================================

def test_password_recovery_honest_unconfigured_status():
    """When delivery provider is unconfigured, endpoint returns 501 Not Implemented rather than simulating email dispatch."""
    settings.EMAIL_DELIVERY_ENABLED = False
    settings.SMTP_HOST = None

    resp = client.post(
        f"{settings.API_V1_STR}/auth/forgot-password",
        json={"email": "operator@factory.co.uk"},
    )
    assert resp.status_code == 501
    assert "not implemented" in resp.json()["detail"].lower()


def test_staging_configuration_rejects_development_defaults():
    staging = Settings()
    staging.ENVIRONMENT = "staging"
    staging.AUTH_SECRET_KEY = staging.DEFAULT_DEV_SECRET
    staging.AUTH_SECURE_COOKIE = False
    staging.CORS_ORIGINS = ["https://app.example.test"]
    with pytest.raises(ValueError, match="AUTH_SECRET_KEY must be changed"):
        staging.validate_configuration()


def test_unknown_environment_is_rejected():
    invalid = Settings()
    invalid.ENVIRONMENT = "prod"
    with pytest.raises(ValueError, match="ENVIRONMENT must be one of"):
        invalid.validate_configuration()


def test_default_authentication_material_is_randomized():
    generated = Settings()
    assert generated.AUTH_SECRET_KEY != generated.DEFAULT_DEV_SECRET
    assert generated.DEV_ADMIN_PASSWORD not in {"ProcessLensDev2026!", ""}
    assert generated.DEMO_CUSTOMER_PASSWORD not in {"ProcessLensCustomer2026!", ""}
    assert generated.DEV_ADMIN_PASSWORD != generated.DEMO_CUSTOMER_PASSWORD


def test_trusted_proxy_uses_proxy_appended_client_ip(monkeypatch):
    from starlette.requests import Request
    from app.api.v1.auth import get_client_ip
    monkeypatch.setattr(settings, "TRUSTED_PROXY_IPS", ["10.0.0.2"])
    scope = {
        "type": "http", "asgi": {"version": "3.0"}, "http_version": "1.1",
        "method": "POST", "scheme": "http", "path": "/", "raw_path": b"/",
        "query_string": b"", "headers": [(b"x-forwarded-for", b"192.0.2.99, 198.51.100.8")],
        "client": ("10.0.0.2", 12345), "server": ("testserver", 80),
    }
    assert get_client_ip(Request(scope)) == "198.51.100.8"
