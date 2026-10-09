# ProcessLens Architecture & Scope Decisions Log (`Docs/decisions.md`)

## Decision Record 001: Agent Operating Model & Character Persona Instantiation
* **Date:** 2026-10-09
* **Status:** Approved
* **Owner:** Product Lead / Orchestrator

### Context
To prevent feature drift, unverified metric calculations, and duplicated effort across subagents, ProcessLens requires a bounded agent operating model.

### Decision
1. Adopt the 8-agent role matrix defined in [AGENTS.md](file:///c:/processlens/AGENTS.md).
2. Instantiate [agentchar.md](file:///c:/processlens/agentchar.md) to define explicit behavioral characteristics, non-negotiables, and communication standards for all 8 agent roles.
3. Strictly enforce the **Feature-Creep Gate** and **Deterministic Analytics Integrity** across all phases.

### Consequences
- All tasks must be assigned to specific roles with clear acceptance criteria.
- Analytics, readiness, and ROI must remain 100% deterministic (no LLM metric generation).
- AI layer remains disabled until Phase 10.

---

## Decision Record 002: Phase 0 Scaffold & Phase 1 Ingestion & Data Quality Validation Engine
* **Date:** 2026-10-09
* **Status:** Implemented & Verified
* **Owner:** Product Lead / Orchestrator

### Context
Phase 1 requires a robust, non-destructive CSV ingestion engine that validates raw operational event data against the canonical schema without silently dropping bad rows.

### Decision
1. Build Python FastAPI backend scaffold (`backend/app/main.py`) with CORS support and `/health` status endpoint.
2. Implement line-by-line validation engine (`backend/app/services/validator.py`) with Pydantic output contract (`DataQualityReport`).
3. Enforce 10MB maximum file size limit and `.csv` extension checks.
4. Validate mandatory canonical fields (`case_id`, `activity`, `timestamp`), report invalid timestamps, missing values, and duplicate events with exact row indices.
5. Create React + Vite + TypeScript frontend (`frontend/`) with dark glassmorphism design tokens, live backend health status indicator, drag-and-drop CSV uploader, and Data Quality Report view.
6. Create automated pytest suite (`backend/tests`) verifying synthetic sample datasets (`quickstart.csv`, `clean.csv`, `messy.csv`).

### Consequences & Verification
- 100% of backend tests (`7/7 passed`).
- Frontend production bundle built cleanly without TypeScript or Vite errors.
- Raw invalid records are preserved and reported; zero silent deletions.
