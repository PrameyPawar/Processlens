# ProcessLens Architecture & Scope Decisions Log (`Docs/decisions.md`)

## Decision Record 001: Agent Operating Model & Character Persona Instantiation
* **Date:** 2026-10-09
* **Status:** Approved
* **Owner:** Product Lead / Orchestrator

### Context
To prevent feature drift, unverified metric calculations, and duplicated effort across subagents, ProcessLens requires a bounded agent operating model.

### Decision
1. Adopt the 8-agent role matrix defined in [AGENTS.md](file:///c:/processlens/AGENTS.md).
2. Instantiate [agentchar.md](file:///c:/processlens/agentchar.md) to define explicit behavioral characteristics, non-negotiables, and communication standards for all 8 agent roles:
   - **Product Lead / Orchestrator**
   - **Data & Domain Analyst**
   - **Backend & Ingestion Engineer**
   - **Process Analytics Engineer**
   - **Opportunity & Economics Analyst**
   - **Frontend / UX Engineer**
   - **QA / Reliability Engineer**
   - **AI / Explanation Engineer**
3. Strictly enforce the **Feature-Creep Gate** and **Deterministic Analytics Integrity** across all phases.

### Consequences
- All tasks must be assigned to specific roles with clear acceptance criteria.
- Analytics, readiness, and ROI must remain 100% deterministic (no LLM metric generation).
- AI layer remains disabled until Phase 10.
