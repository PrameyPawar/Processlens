# ProcessLens Portfolio Demo and Deployment Boundaries

## 1. Overview & Architecture

ProcessLens is designed as a lightweight, decoupled web application:
- **Backend:** Python FastAPI application serving deterministic analytics, problem detection, economics, prioritisation, evidence dossiers, and grounded explanations.
- **Frontend:** Single Page Application (SPA) built with React, Vite, and TypeScript.
- **Design Principles:**
  - CSV analysis uses in-memory request processing and deterministic pipelines. Authentication accounts, revoked sessions, and rate-limit state use SQLite when configured; production-like startup requires a durable `USER_STORE_DB_PATH`.
  - Explicit CORS protection preventing unauthorized cross-origin requests.
  - Safe error reporting without stack traces or sensitive credential leakage.
  - Automatic fallback to deterministic rule-based templates when external LLM access is absent or unconfigured.

---

## 2. Prerequisites

| Component | Minimum Version | Recommended | Notes |
|---|---|---|---|
| **Python** | 3.10+ | 3.11 or 3.12 | Standard CPython |
| **Node.js** | 18.0.0+ | 20.x LTS | Required for frontend build |
| **npm** | 9.0.0+ | 10.x | Node package manager |
| **Reverse Proxy** *(Optional for production)* | Nginx 1.20+ or Caddy 2.7+ | Caddy / Nginx | For SSL/TLS termination and unified domain routing |

---

## 3. Environment Variables & Authentication Configuration

### Backend Configuration (`backend/.env`)

Copy `backend/.env.example` to `backend/.env` (or configure via environment variables in your deployment target):

```ini
# Allowed origins for CORS (comma-separated list of origins)
# In production, set to your exact public frontend origin(s):
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,http://testserver

# Optional LLM Provider Configuration
# When LLM_API_KEY is omitted or blank, ProcessLens operates deterministically
# using deterministic rule-based templates. This does not mean an independent grounding audit ran; inspect `grounding_audit` in each response.
LLM_API_KEY=
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini
LLM_TIMEOUT_SECONDS=30.0

# -------------------------------------------------------------
# Authentication & Session Security (Phase 11.6)
# -------------------------------------------------------------
# Set explicit, stable secret values before deploying to staging or production; blank values only generate local per-process secrets.
AUTH_SECRET_KEY=

# Session lifespan in seconds (default: 28800 = 8 hours)
AUTH_TOKEN_EXPIRE_SECONDS=28800

# Set to true in production behind HTTPS to enforce the Secure cookie flag
AUTH_SECURE_COOKIE=false

# TRUSTED_PROXY_IPS=127.0.0.1  # Only set to the exact peer IP(s) of your reverse proxy.

# Deployment environment (development / test / staging / production)
ENVIRONMENT=development

# Initial Developer Administrator Account (Provisioned on server startup; change in production)
DEV_ADMIN_EMAIL=dev@processlens.internal
DEV_ADMIN_PASSWORD=

# Initial Evaluation Customer Account (Change or disable in production)
DEMO_CUSTOMER_EMAIL=customer@processlens.com
DEMO_CUSTOMER_PASSWORD=

# Required in staging/production; shared by all workers on one host.
USER_STORE_DB_PATH=/var/lib/processlens/auth.db
```

### Frontend Configuration (`frontend/.env` or `frontend/.env.production`)

Copy `frontend/.env.example` to `frontend/.env.production`:

```ini
# Backend API base URL
# Leave blank or omit when serving behind a reverse proxy (recommended),
# which routes /api/v1 and /health to the backend seamlessly.
# Set to an absolute URL if frontend and backend are hosted on distinct domains/ports:
# VITE_API_URL=https://api.processlens.example.com
VITE_API_URL=
```

---

## 3.1 Developer Account Provisioning & Security Controls

1. **No Public Developer Registration:** Public registration (`/api/v1/auth/register`) strictly sets `role: customer`. Users cannot choose or escalate their role.
2. **Server-Side Developer Provisioning:** Developer accounts are seeded from backend startup configuration (`DEV_ADMIN_EMAIL`, `DEV_ADMIN_PASSWORD`). No administrative CLI is implemented.
3. **Restricted Diagnostics:** The `/api/v1/dev/*` and `/dev/dashboard` routes require `role: developer`. Customers attempting access receive HTTP `403 Forbidden`.
4. **Role Guardrail:** Developer privileges do not grant access to customer analytics endpoints. `/api/v1/customer/workspace` enforces the customer role and returns identity-derived metadata only; it does not implement persistent tenant isolation.

---

## 3.2 Database Strategy & Multi-Tenant Migration Path

### Current Portfolio Demo State
- CSV content is handled in memory by the application request pipeline; analysis results are held in the browser application state. The app does not implement saved datasets or durable analysis history. This does not by itself establish a verified deletion guarantee for process memory, browser caches, reverse-proxy logs, crash dumps, or infrastructure telemetry.
- The `/api/v1/customer/workspace` response is identity-derived metadata. It is not a persisted workspace, tenant database, or cross-customer data-isolation system.
- Staging and production configuration requires `USER_STORE_DB_PATH`. Accounts, token revocations, and sliding-window rate limits are stored in SQLite. Use one durable local SQLite file shared by workers on the same host, with restrictive filesystem permissions and tested backups. All workers must use the same stable `AUTH_SECRET_KEY`. Multi-host deployments need a shared database/rate-limit design; a local SQLite file is not a multi-host coordination mechanism. Database backup, restore, and migration procedures have not yet been validated.
- This repository is a portfolio/demo candidate, not a production-ready service. Do not onboard real customer data until storage and tenant isolation, backup/restore, monitoring, recovery, and operational controls have been designed and validated.

### Production Multi-Tenant Persistence Architecture
For enterprise deployments requiring durable multi-tenant workspace persistence across reboots, the target architecture is documented below:
- **Engine:** PostgreSQL 15+ managed instance with SSL connections (`sslmode=verify-full`).
- **ORM / Migrations:** SQLAlchemy 2.0 with Alembic migration version control.
- **Relational Schema:**
  - `users` (id UUID PK, email VARCHAR UNIQUE, password_hash VARCHAR, role VARCHAR, created_at TIMESTAMPTZ)
  - `workspaces` (id UUID PK, owner_id UUID FK -> users.id, name VARCHAR, created_at TIMESTAMPTZ)
  - `workspace_members` (workspace_id UUID FK, user_id UUID FK, role VARCHAR, PRIMARY KEY (workspace_id, user_id))
  - `datasets` (id UUID PK, workspace_id UUID FK -> workspaces.id, filename VARCHAR, row_count INT, s3_uri VARCHAR, uploaded_at TIMESTAMPTZ)
  - `analyses` (id UUID PK, dataset_id UUID FK -> datasets.id, stage VARCHAR, result_json JSONB, created_at TIMESTAMPTZ)
- **Tenant Isolation Invariant:** All queries must filter by `workspace_id = current_user.workspace_id`. Row-Level Security (RLS) enabled on PostgreSQL tables.

---

## 3.3 Render Portfolio Demo Deployment

The repository includes a single-origin Docker deployment in `Dockerfile` and a Render Blueprint in `render.yaml`. The image builds the Vite frontend and serves it from FastAPI alongside the API, so browser routes and authenticated API calls use the same HTTPS origin.

For the free portfolio-demo setup, the SQLite account/session database is placed at `/tmp/processlens-auth.db`. Render free services use an ephemeral filesystem and may spin down after inactivity; account registrations and revoked-token/rate-limit state can reset after a restart or redeploy. Use synthetic or public sample data only. A persistent disk is a paid-service capability; do not change the database path to imply durable storage unless the service has an attached persistent disk.

To deploy: push the project to a GitHub repository you control, create a new Blueprint in Render from that repository, and select `render.yaml`. Render generates the signing key and seed passwords. Confirm the generated service origin matches `CORS_ORIGINS`; update it if the Render service name or custom domain changes. The developer seed password is secret and should not be disclosed. Customer visitors can create a customer account through the registration screen.

After the deploy is live, verify `/health`, open the root page, register a throwaway demo account, load the quickstart CSV, and exercise the workflow through the evidence dossier and exports. Check `/login` and `/dev/login` directly after a refresh to confirm SPA routing. This verifies the demo deployment path; it does not establish production readiness.

## 4. Local Startup (Development)

### Backend
From the repository root or `backend/` directory:
```bash
# In backend virtual environment:
pip install --require-hashes -r backend/requirements.lock
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

### Frontend
From the `frontend/` directory:
```bash
npm install
npm run dev
```
By default, Vite runs at `http://localhost:5173` and proxies `/api` and `/health` requests to `http://localhost:8000`.

---

## 5. Production Build & Startup

### Step A: Build Frontend Static Bundle
```bash
cd frontend
npm ci
npm run build
```
This produces optimized production assets in `frontend/dist/`.

### Step B: Run Production Backend
Install dependencies and run Uvicorn with production worker processes:
```bash
pip install --require-hashes -r backend/requirements.lock

# Run with Uvicorn (adjust workers based on CPU cores):
uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

### Step C: Production Hosting Topology

#### Option 1: Unified Reverse Proxy (Recommended)
Use Nginx or Caddy to serve the frontend static bundle and reverse-proxy API requests to Uvicorn. Terminate HTTPS at this proxy or an upstream load balancer; the example below is only an HTTP virtual host and must be paired with a TLS listener and HTTP-to-HTTPS redirect before deployment. This avoids cross-origin complexity entirely.

**Example Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name processlens.example.com;

    # Frontend static assets
    location / {
        root /var/www/processlens/frontend/dist;
        index index.html;
        try_files $uri $uri/ /index.html;
    }

    # Backend API and health check proxy
    location ~ ^/(api|health|docs|openapi.json) {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 15M;
    }
}
```

Configure `TRUSTED_PROXY_IPS` with the exact proxy peer address(es). Do not trust forwarded headers from arbitrary clients. Verify the proxy appends the observed client address to `X-Forwarded-For` and passes the correct external scheme.

#### Option 2: Split Domain / Static Host
If hosting frontend on a static CDN (Cloudflare Pages, Vercel, Netlify, AWS S3) and backend on a VM/container service:
1. Set `VITE_API_URL=https://api.processlens.example.com` before running `npm run build`.
2. Configure backend `CORS_ORIGINS=https://processlens.example.com`.
3. Set your server or proxy `client_max_body_size` to at least 15MB to allow the 10MB CSV upload limit.

---

## 6. Health Checks & Monitoring

The backend exposes a standard health endpoint:
```http
GET /health
```

**Expected Response (200 OK):**
```json
{
  "status": "ok",
  "service": "processlens-backend",
  "version": "0.1.0"
}
```

Monitor uptime and service readiness by pinging `/health` every 15–60 seconds.

---

## 7. Production Smoke Testing

Perform a live smoke test using `curl` and the quickstart sample dataset (`data/ProcessLens_Development_Data/samples/manufacturing_orders_quickstart.csv`):

### Authenticate as the demo customer
Set `DEMO_CUSTOMER_EMAIL` and `DEMO_CUSTOMER_PASSWORD` from the backend environment in your shell. Keep secrets out of shell scripts and source control.

```bash
AUTH_TOKEN=$(curl -fsS -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d "{\"email\":\"${DEMO_CUSTOMER_EMAIL}\",\"password\":\"${DEMO_CUSTOMER_PASSWORD}\"}" \
  | python -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
```

### 1. Verify Health
```bash
curl -f http://127.0.0.1:8000/health
```

### 2. Verify Ingestion & Validation
```bash
curl -f -X POST http://127.0.0.1:8000/api/v1/ingestion/upload \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@data/ProcessLens_Development_Data/samples/manufacturing_orders_quickstart.csv"
```

### 3. Verify Full Analytics Pipeline
```bash
curl -f -X POST http://127.0.0.1:8000/api/v1/analytics/process \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@data/ProcessLens_Development_Data/samples/manufacturing_orders_quickstart.csv"
```

### 4. Verify Prioritisation
```bash
curl -f -X POST http://127.0.0.1:8000/api/v1/prioritisation/rank \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@data/ProcessLens_Development_Data/samples/manufacturing_orders_quickstart.csv"
```

### 5. Verify Grounded Explanations (Deterministic Mode)
```bash
curl -f -X POST http://127.0.0.1:8000/api/v1/explanation/generate \
  -H "Authorization: Bearer ${AUTH_TOKEN}" \
  -F "file=@data/ProcessLens_Development_Data/samples/manufacturing_orders_quickstart.csv" \
  -F "enable_llm=false"
```

All requests must succeed with HTTP 200 and return valid JSON structures conforming to the API schema.

---

## 8. Security & Reliability Invariants

1. **Upload Size Limits:** Hard limit of 10 MB (`settings.MAX_FILE_SIZE_BYTES`). Larger uploads are rejected with HTTP 413 before in-memory processing.
2. **File Type Filtering:** Only files ending with `.csv` are accepted; unsupported extensions fail safely.
3. **No Credential Exposure:**
   - Stack traces are suppressed from error payloads.
   - LLM errors redact API keys, Bearer tokens, and sensitive headers via `sanitize_message()`.
4. **Deterministic Resilience:** When external LLM connectivity is absent or failing, the explanation pipeline falls back to deterministic template generation with `FALLBACK_APPLIED` and structured audit logs.
5. **No File Leakage:** CSV uploads are processed via in-memory bytes streams; no temporary files remain on disk.

---

## 9. Rollback & Troubleshooting

| Symptom | Probable Cause | Remediation |
|---|---|---|
| **CORS Error in Browser** (`No 'Access-Control-Allow-Origin' header present`) | Frontend origin is not listed in `CORS_ORIGINS`. | Add frontend URL to `CORS_ORIGINS` in backend environment and restart backend. |
| **413 Payload Too Large / Connection Dropped** | Reverse proxy max request body limit exceeded. | Set `client_max_body_size 15M;` in Nginx or equivalent in reverse proxy. |
| **500 Error on Ingestion** | Corrupt CSV file format or encoding issue. | Check upload file encoding (UTF-8 recommended) and header names. |
| **Frontend blank screen / 404 on refresh** | SPA history routing not handled by web server. | Configure web server fallback to `index.html` (e.g., `try_files $uri /index.html;`). |
| **Explanation generation returns fallback** | `LLM_API_KEY` missing, expired, or provider timeout. | Inspect `grounding_audit` and generated evidence references. Deterministic fallback behavior alone does not prove zero evidence loss or an independently verified grounding result. |

### Rollback Procedure
If a production issue occurs:
1. Revert to previous frontend `dist/` directory or static deployment build.
2. Restart Uvicorn workers: `systemctl restart processlens-backend` or restart process runner.
3. Verify `/health` responds with HTTP 200.


## 10. Readiness Gates

### Portfolio demonstration
A local demonstration with synthetic or public data is appropriate after the test suites and build pass. Label analytics as exploratory and show the dataset, exclusions, assumptions, and evidence links.

### Real business pilot or production
Not currently recommended. Before using customer data, complete and independently review: durable tenant-scoped storage and authorization, database migrations and tested backup/restore, password recovery and account operations, centralized audit logging and monitoring, deployment-specific resource/time limits, incident response, data retention/deletion controls, and business validation against customer-confirmed ground truth. A passing automated suite cannot establish those operational or commercial claims.

Current upload scope is CSV only, capped at 10 MB. XES import, multi-tenant saved workspaces, and durable analysis history are not implemented. No customer accuracy, ROI, or market-demand claim is established by this demo.
