# ProcessLens

ProcessLens is a portfolio decision-support demo that turns operational event-log CSV files into a process overview, timing and transition metrics, bottleneck and rework signals, ranked improvement opportunities, and evidence-linked explanations.

> **Status:** Portfolio/demo software. It is not a production service or validated business advisory product. Do not upload confidential or customer data. No customer accuracy, ROI, or market-demand claim has been established.

## What it demonstrates

- CSV ingestion, schema checks, and data-quality reporting.
- Case reconstruction and process variants.
- Cycle-time and activity-transition analysis.
- Bottleneck, rework, and opportunity detection with linked evidence.
- Transparent prioritisation and explanatory views.
- Developer/customer authentication flows for a local demo.
- React, TypeScript, and Vite frontend with a FastAPI backend.

## Architecture

- `frontend/`: React + TypeScript SPA built with Vite.
- `backend/`: FastAPI API and deterministic analytics pipeline.
- `data/ProcessLens_Development_Data/`: synthetic manufacturing event logs for controlled development.
- `processlens_independent_validation_bundle/`: separate synthetic returns event log and reference/ground-truth files for reproducible checks. The ground truth is included in this public repository, so this is not a blind benchmark after publication.
- `Docs/`: project, design, authentication, deployment, and newcomer documentation.

The current demo processes uploaded CSVs in request memory and keeps analysis state in the browser. It does not provide durable customer workspaces or proven cross-customer analytics isolation. See [deployment notes](Docs/deployment.md) for operational limits.

## Run locally (Windows PowerShell)

Prerequisites: Python 3.11+ and Node.js 20+ with npm.

```powershell
# Backend
cd backend
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.lock
Copy-Item .env.example .env
uvicorn app.main:app --reload --port 8000
```

In another terminal:

```powershell
cd frontend
npm ci
Copy-Item .env.example .env
npm run dev
```

Open the Vite URL shown in the frontend terminal (normally `http://localhost:5173`). Keep the backend running on port 8000. For demo credentials and account setup, see [authentication documentation](Docs/authentication.md); set local passwords in `backend/.env` and never commit that file.

## Build and test

```powershell
# Frontend production build
cd frontend
npm ci
npm run build

# Backend tests
cd ..\backend
python -m pytest
```

## Data and evaluation limits

The included development logs and independent returns bundle are synthetic, controlled test data. They can check behavior against planted patterns and reference calculations, but do not establish accuracy on a real company’s event logs. For the benchmark protocol and caveats, read `processlens_independent_validation_bundle/README.md` and `Docs/deployment.md`.

The app currently accepts CSV, with a documented 10 MB upload limit. Persistent analysis history, XES import, production-grade tenant storage/isolation, recovery operations, backup/restore, and full operational monitoring are not implemented or validated.

## Deployment

A Render blueprint is provided in `render.yaml`. The free demo configuration uses ephemeral storage and is unsuitable for real customer accounts or durable data. Review [deployment documentation](Docs/deployment.md) before deploying. Never put real credentials, API keys, or customer data into this repository or a public demo.

## License

No license is currently provided. Public visibility does not grant permission to reuse or redistribute the code.
