# ProcessLens Authentication and Authorization Architecture

## 1. Overview & Security Principles

ProcessLens implements a **unified, server-enforced authentication and role-based access control (RBAC) architecture** providing two distinct user entry points:
- **Customer Portal:** `/login` (Operations leads, process engineers, business analysts)
- **Developer & Ops Console:** `/dev/login` (Internal engineering and DevOps diagnostics)

Both portals interface with the same backend identity engine (`/api/v1/auth/login`). Different URLs represent tailored presentation interfaces, **not** separate or duplicated authentication subsystems.

### Core Security Principles
1. **Server-Enforced Boundaries:** Client-side routing guards are purely visual convenience; authorization and role permissions are strictly validated on the FastAPI backend on every request.
2. **Standard Cryptography:** Password hashing uses OWASP-recommended **scrypt:32768:8:1** (via `werkzeug.security`), a memory-hard algorithm resistant to ASIC/GPU hardware brute-forcing.
3. **Cryptographically Signed Session Tokens:** Session tokens are HMAC-SHA256 signed using `itsdangerous.URLSafeTimedSerializer` with domain-specific salts and server-enforced expiration.
4. **Dual Transport Security:** Authentication tokens are delivered via **HttpOnly, SameSite=Lax** cookies for browser sessions and returned as Bearer tokens for API clients and automated tests.
5. **Brute-Force Throttling:** Sliding-window rate limiter restricts failed login attempts (5 attempts per 5 minutes per IP and email identifier) returning HTTP `429 Too Many Requests`.
6. **No User Enumeration:** Authentication and password-reset failure responses return generic messages ("Invalid email or password") to prevent email harvesting.
7. **Zero Plaintext Credentials in Logs:** Passwords and access tokens are strictly excluded from logs; security audit trails record masked emails (e.g. `d***@processlens.internal`) and client IP addresses only.

---

## 2. Role and Permission Model

| Role | Permitted Workspaces & Endpoints | Restricted Endpoints | Security Boundaries |
|---|---|---|---|
| **`customer`** | `/login`, `/`, Customer Operations Workspace (CSV Ingestion, Data Quality, Analytics, Problems, Opportunities, Explanations, Reports, `/api/v1/customer/workspace`) | `/api/v1/dev/*`, `/dev/dashboard` | **403 Forbidden** on any attempt to query developer telemetry, audit logs, or system internals. |
| **`developer`** | `/dev/login`, `/dev/dashboard`, `/api/v1/dev/status`, `/api/v1/dev/audit-events` | Customer analysis endpoints and `/api/v1/customer/workspace` | Explicit authentication required. Developer privileges do not permit access to customer uploads or analytics. |

---

## 3. Customer Data Handling and Isolation

- CSV analysis is handled through in-memory request processing; saved datasets and durable analysis history are not implemented. This is not a verified secure-erasure guarantee for process memory, browser caches, proxy logs, crash dumps, or infrastructure telemetry.
- Logout and dataset reset clear the corresponding frontend application state. This is not a certified secure-erasure mechanism.
- `/api/v1/customer/workspace` is role-gated and returns identity-derived metadata. It is not a persisted workspace, tenant database, or row-level isolation system.
- Analysis endpoints require the customer role; developer accounts cannot access customer analysis endpoints.
- Do not use the current build as a multi-tenant service for real customer records without a designed and independently reviewed storage/isolation layer and operational controls.

## 4. Environment Variables & Account Provisioning

### Backend Configuration (`backend/.env`)

Configure the following variables in production:

```ini
# Set a unique, stable signing key in every deployed environment; blank only for local development.
AUTH_SECRET_KEY=

# Session expiration lifespan (default: 28800 seconds = 8 hours)
AUTH_TOKEN_EXPIRE_SECONDS=28800

# Production startup requires true and valid HTTPS origins
AUTH_SECURE_COOKIE=true

TRUSTED_PROXY_IPS=  # Set only to the exact peer IP(s) of your reverse proxy; otherwise leave blank.

# Environment name (development / staging / production)
ENVIRONMENT=production

# Set these explicitly; production startup rejects blank or short passwords. Use distinct values.
# Initial Developer Administrator Account (Provisioned securely on server startup)
DEV_ADMIN_EMAIL=dev@processlens.internal
DEV_ADMIN_PASSWORD=

# Initial Demo Customer Account (For evaluation and smoke testing)
DEMO_CUSTOMER_EMAIL=customer@processlens.com
DEMO_CUSTOMER_PASSWORD=

# Allowed origins for CORS (comma-separated list of origins)
CORS_ORIGINS=https://app.processlens.example.com
```

### Security Hardening Mechanisms (Phase 11.8 Audit)
1. **Server-Side Token Revocation:** Every token contains a unique `jti` identifier. Upon logout (`POST /api/v1/auth/logout`), the token's `jti` is permanently revoked in `user_store`, preventing replay attacks even if an attacker obtained the raw Bearer string.
2. **CSRF Origin Verification:** All state-changing requests (`POST`, `PUT`, `DELETE`, `PATCH`) authenticated via HttpOnly cookies are strictly verified against `settings.CORS_ORIGINS`. Untrusted origins receive HTTP `403 Forbidden`.
3. **Durable SQLite Persistence:** When `USER_STORE_DB_PATH` is specified, user accounts and token revocations are persisted to a SQLite database with transactional uniqueness constraints, surviving process restarts.
4. **Honest Password Recovery:** Password-reset token generation and email delivery are not implemented. The endpoint returns HTTP `501 Not Implemented` even if SMTP settings are present; users must contact an administrator.
5. **Startup Configuration Gate:** In staging and production, the application requires explicitly configured strong secrets and seed passwords, secure cookies, and valid HTTPS-only CORS origins. Unknown environment names are rejected.

---

## 5. API Reference

### Authentication Endpoints
- `POST /api/v1/auth/login`: Authenticate customer or developer credentials. Returns Bearer token and sets HttpOnly session cookie.
- `POST /api/v1/auth/register`: Public customer registration. Enforces customer role server-side.
- `GET /api/v1/auth/me`: Retrieve currently authenticated user profile from session cookie or `Authorization: Bearer <token>`.
- `POST /api/v1/auth/logout`: Clears session cookie and invalidates server-side session token.
- `POST /api/v1/auth/forgot-password`: Rate-limited endpoint that returns 501 because password-reset token generation and email delivery are not implemented in this build.

### Customer Workspace Endpoints
- `GET /api/v1/customer/workspace`: Returns identity-derived workspace metadata. Protected by `require_customer_only`; this is not a persisted workspace. Developers receive `403 Forbidden`.

### Developer Diagnostic Endpoints
- `GET /api/v1/dev/status`: System uptime, FastAPI version, Python version, CORS origin count, and LLM configuration status. Protected by `require_developer`. Customers receive `403 Forbidden`.
- `GET /api/v1/dev/audit-events`: Sanitized recent operational and security events (logins, rate limits) with masked emails. Protected by `require_developer`. Customers receive `403 Forbidden`.

---

## 6. Current Deployment Boundary

This authentication design supports a portfolio demonstration. Password recovery, customer support/account administration, persistent tenant workspaces, and independently validated production operations are not implemented. The app is not ready for real customer data until the storage/isolation and operational gates in `Docs/deployment.md` are completed. Automated role tests do not prove deployment security.

## 7. Testing & Verification

Run the full automated test suites to verify authentication, RBAC, CSRF, and data isolation:

```bash
# Authentication & Security Audit Suite
python -m pytest backend/tests/test_auth.py backend/tests/test_security_audit.py -v

# Full Backend Suite
python -m pytest backend/tests -q

# Frontend Test Suite
cd frontend
npm test -- --run

# Production TypeScript Build
npm run build
```

