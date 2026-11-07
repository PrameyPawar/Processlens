"""
Comprehensive test suite for ProcessLens authentication, role-based authorization,
rate limiting, session security, and customer/developer boundaries.
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings
from app.core.auth import create_auth_token
from app.services.user_store import user_store

client = TestClient(app)

@pytest.fixture(autouse=True)
def reset_user_store():
    """Reset user store and rate limiter state before each test."""
    user_store.reset_for_tests()
    yield
    user_store.reset_for_tests()

def test_customer_login_success():
    """Valid customer credentials return 200, JWT token, and session cookie."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "email": settings.DEMO_CUSTOMER_EMAIL,
            "password": settings.DEMO_CUSTOMER_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["role"] == "customer"
    assert data["user"]["email"] == settings.DEMO_CUSTOMER_EMAIL.lower()
    assert settings.AUTH_COOKIE_NAME in response.cookies

def test_developer_login_success():
    """Valid developer credentials return 200, JWT token, and session cookie."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "email": settings.DEV_ADMIN_EMAIL,
            "password": settings.DEV_ADMIN_PASSWORD,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["user"]["role"] == "developer"
    assert data["user"]["email"] == settings.DEV_ADMIN_EMAIL.lower()
    assert settings.AUTH_COOKIE_NAME in response.cookies

def test_login_invalid_password_returns_generic_401():
    """Invalid password returns generic 401 message."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "email": settings.DEMO_CUSTOMER_EMAIL,
            "password": "WrongPassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."

def test_login_nonexistent_email_returns_identical_generic_401():
    """Non-existent email returns exact same 401 message (no email enumeration)."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={
            "email": "ghost.user@doesnotexist.com",
            "password": "SomePassword123!",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid email or password."

def test_login_rate_limiting():
    """5 consecutive failed logins trigger 429 Too Many Requests."""
    target_email = "victim@processlens.com"
    for i in range(5):
        resp = client.post(
            f"{settings.API_V1_STR}/auth/login",
            json={"email": target_email, "password": f"bad_guess_{i}"},
        )
        assert resp.status_code == 401

    # 6th attempt should be blocked by rate limiter
    blocked_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": target_email, "password": "any_guess"},
    )
    assert blocked_resp.status_code == 429
    assert "Too many failed login attempts" in blocked_resp.json()["detail"]

def test_customer_registration_strictly_assigns_customer_role():
    """Public registration always assigns customer role and logs user in."""
    reg_response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": "new.customer@sme-plant.co.uk",
            "name": "Factory Ops Manager",
            "password": "SecurePassword2026!",
        },
    )
    assert reg_response.status_code == 201
    data = reg_response.json()
    assert data["user"]["role"] == "customer"
    assert data["user"]["name"] == "Factory Ops Manager"
    assert settings.AUTH_COOKIE_NAME in reg_response.cookies

def test_customer_registration_duplicate_email_fails():
    """Registering with an existing email returns 400 Bad Request."""
    response = client.post(
        f"{settings.API_V1_STR}/auth/register",
        json={
            "email": settings.DEMO_CUSTOMER_EMAIL,
            "name": "Impostor",
            "password": "Password12345!",
        },
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]

def test_auth_me_with_cookie_and_header():
    """GET /auth/me succeeds with either valid session cookie or Bearer header."""
    # Login as customer
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    token = login_resp.json()["access_token"]

    # 1. Test via Bearer Header
    header_client = TestClient(app)
    header_resp = header_client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert header_resp.status_code == 200
    assert header_resp.json()["email"] == settings.DEMO_CUSTOMER_EMAIL.lower()

    # 2. Test via Cookie
    cookie_client = TestClient(app)
    cookie_resp = cookie_client.get(
        f"{settings.API_V1_STR}/auth/me",
        cookies={settings.AUTH_COOKIE_NAME: token},
    )
    assert cookie_resp.status_code == 200
    assert cookie_resp.json()["email"] == settings.DEMO_CUSTOMER_EMAIL.lower()

def test_unauthenticated_access_to_protected_endpoints():
    """Unauthenticated calls to /dev/status and /customer/workspace return 401."""
    fresh_client = TestClient(app)
    resp_dev = fresh_client.get(f"{settings.API_V1_STR}/dev/status")
    assert resp_dev.status_code == 401

    resp_cust = fresh_client.get(f"{settings.API_V1_STR}/customer/workspace")
    assert resp_cust.status_code == 401

def test_customer_cannot_access_developer_endpoints():
    """Authenticated customer calling developer diagnostics receives 403 Forbidden."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    customer_token = login_resp.json()["access_token"]

    dev_attempt = client.get(
        f"{settings.API_V1_STR}/dev/status",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert dev_attempt.status_code == 403
    assert "lacks required permissions" in dev_attempt.json()["detail"]

    dev_audit_attempt = client.get(
        f"{settings.API_V1_STR}/dev/audit-events",
        headers={"Authorization": f"Bearer {customer_token}"},
    )
    assert dev_audit_attempt.status_code == 403

def test_developer_cannot_access_customer_private_workspace():
    """Authenticated developer calling customer workspace receives 403 Forbidden."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEV_ADMIN_EMAIL, "password": settings.DEV_ADMIN_PASSWORD},
    )
    dev_token = login_resp.json()["access_token"]

    cust_attempt = client.get(
        f"{settings.API_V1_STR}/customer/workspace",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert cust_attempt.status_code == 403
    assert "lacks required permissions" in cust_attempt.json()["detail"]

def test_customer_workspace_response_is_explicitly_identity_only():
    login = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    response = client.get(
        f"{settings.API_V1_STR}/customer/workspace",
        headers={"Authorization": f"Bearer {login.json()['access_token']}"},
    )
    assert response.status_code == 200
    assert response.json()["isolation_tier"] == "identity-only"
    assert response.json()["owner_id"] == login.json()["user"]["id"]

def test_developer_accesses_dev_status_and_audit_events():
    """Authenticated developer can view system status and sanitized audit events."""
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEV_ADMIN_EMAIL, "password": settings.DEV_ADMIN_PASSWORD},
    )
    dev_token = login_resp.json()["access_token"]

    status_resp = client.get(
        f"{settings.API_V1_STR}/dev/status",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["status"] == "ok"
    assert status_data["version"] == settings.VERSION
    assert "uptime_seconds" in status_data

    audit_resp = client.get(
        f"{settings.API_V1_STR}/dev/audit-events",
        headers={"Authorization": f"Bearer {dev_token}"},
    )
    assert audit_resp.status_code == 200
    events = audit_resp.json()["events"]
    assert isinstance(events, list)
    assert len(events) > 0
    # Confirm email is masked
    assert "@" in events[0]["email_masked"]
    assert "***" in events[0]["email_masked"]

def test_tampered_token_rejected():
    """Tampered token is rejected with 401 Unauthorized."""
    tampered_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.badpayload.signature"
    resp = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {tampered_token}"},
    )
    assert resp.status_code == 401

def test_logout_deletes_session_cookie_and_revokes_token():
    """Logout endpoint deletes the session cookie and revokes the session token server-side."""
    # 1. Login to get token
    login_resp = client.post(
        f"{settings.API_V1_STR}/auth/login",
        json={"email": settings.DEMO_CUSTOMER_EMAIL, "password": settings.DEMO_CUSTOMER_PASSWORD},
    )
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    # 2. Logout with token
    logout_resp = client.post(
        f"{settings.API_V1_STR}/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert logout_resp.status_code == 200
    assert logout_resp.cookies.get(settings.AUTH_COOKIE_NAME) is None or logout_resp.cookies.get(settings.AUTH_COOKIE_NAME) == '""'

    # 3. Attempting to use revoked token must now fail with 401
    reuse_resp = client.get(
        f"{settings.API_V1_STR}/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reuse_resp.status_code == 401
    assert "revoked" in reuse_resp.json()["detail"].lower()

def test_forgot_password_honest_unconfigured_state():
    """Forgot password returns honest 501 when email delivery provider is unconfigured."""
    settings.EMAIL_DELIVERY_ENABLED = False
    settings.SMTP_HOST = None
    resp = client.post(
        f"{settings.API_V1_STR}/auth/forgot-password",
        json={"email": "anyone@example.com"},
    )
    assert resp.status_code == 501
    assert "not implemented" in resp.json()["detail"].lower()

def test_forgot_password_generic_response_when_configured():
    """Configured SMTP alone must not make an unimplemented reset flow claim delivery."""
    settings.EMAIL_DELIVERY_ENABLED = True
    settings.SMTP_HOST = "smtp.mailprovider.internal"
    try:
        resp = client.post(
            f"{settings.API_V1_STR}/auth/forgot-password",
            json={"email": "anyone@example.com"},
        )
        assert resp.status_code == 501
        assert "not implemented" in resp.json()["detail"].lower()
    finally:
        settings.EMAIL_DELIVERY_ENABLED = False
        settings.SMTP_HOST = None

