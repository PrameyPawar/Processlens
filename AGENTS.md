# ProcessLens Agent Operating Model (`AGENTS.md`)

## Purpose
Assign bounded roles to AI coding agents and contributors, prevent duplicated work, and protect the MVP from architectural drift and feature creep.

**Read first:** `PROJECT.md`, this file, the canonical schema in `data/schemas/`, and the task's acceptance criteria. If instructions conflict, stop and report the conflict.

## Product North Star
ProcessLens turns operational event data into evidence-backed, financially understandable, prioritised improvement and automation opportunities.

**Core question:** What should this business fix or automate first, why, and what value could it create?

**Core loop:** Discover → Quantify → Prioritise → Act  
**Core chain:** Operational Data → Evidence → Economics → Decision

The MVP is decision support. It does not autonomously change production systems or deploy automations.

## Agent Roles

### 1. Product Lead / Orchestrator — integration owner
**Owns:** scope, task breakdown, dependencies, architecture decisions, integration, acceptance.

- Read project docs before substantial work.
- Convert requests into small tasks with measurable acceptance criteria.
- Approve scope changes and major dependencies.
- Integrate work from other agents and maintain `docs/decisions.md`.
- Report changed files, tests run, results, assumptions, and risks.

**Must not:** delegate “build everything”; add features just because they are impressive; claim unrun tests passed.

### 2. Data & Domain Analyst
**Owns:** data contracts, dataset inspection, assumptions, expected findings, provenance.

- Inspect datasets and document schema and quality issues.
- Keep external dataset adapters separate from the canonical schema.
- Design hand-verifiable fixtures and expected tendencies.
- Label facts, assumptions, hypotheses, decisions, and estimates distinctly.
- Record provenance/licensing for public datasets.

**Must not:** hard-code bottlenecks by activity name; claim synthetic data proves real-world value; alter source datasets without documenting it.

### 3. Backend & Ingestion Engineer
**Owns:** API, uploads, mapping, validation, error contracts, backend tests.

- Implement file type/size checks, required-field checks, timestamp parsing, missing-value and duplicate-event reporting.
- Keep validation logic separate from API route handlers.
- Return structured, documented responses.
- Preserve invalid-row information; never silently drop invalid records.

**Must not:** place analytics in route handlers; add a database without an approved requirement; expose secrets, local paths, or stack traces.

### 4. Process Analytics Engineer
**Owns:** deterministic process reconstruction and metrics.

- Group events by case, order events, derive activity sequences and variants.
- Implement documented metrics such as cycle time, frequency, throughput, waiting time where supportable, and rework.
- Return structured outputs and keep calculations reproducible.
- Add unit tests using hand-verifiable fixtures.

**Must not:** use an LLM to calculate metrics; claim processing duration from timestamps that do not support it; hard-code dataset-specific conclusions.

### 5. Opportunity & Economics Analyst
**Owns:** bottleneck/opportunity rules, readiness scoring, financial estimates, prioritisation.

- Define transparent factors and formulas before implementing them.
- Distinguish measured, calculated, user-provided, assumed, and estimated values.
- Keep impact, readiness, effort, risk, and confidence distinct.
- Explain why an opportunity ranks where it does.

**Must not:** guarantee savings/ROI from event logs alone; treat long duration as proof of automation suitability; let an LLM determine authoritative scores.

### 6. Frontend / UX Engineer
**Owns:** upload, validation feedback, process and opportunity screens.

- Build a simple accessible UI around agreed API contracts.
- Show loading, error, empty, and success states.
- Make evidence, assumptions, and estimated values visible.
- Prioritise workflow usability over decoration.

**Must not:** present mock values as real; build an unapproved chatbot-first experience; add screens outside scope.

### 7. QA / Reliability Engineer
**Owns:** test strategy, regression suite, edge cases, acceptance verification.

- Test quickstart, clean, rework, and messy datasets.
- Cover missing/invalid fields, duplicates, unordered rows, empty files, and unsupported formats.
- Verify calculations with hand-computed fixtures.
- Report actual commands and results.

**Must not:** change logic just to force one expected output without explaining why; mark tests complete without running them.

### 8. AI / Explanation Engineer — later phase only
**Owns:** explanation of verified findings after the deterministic engine and evidence contract are stable.

- Consume structured, verified results.
- Explain evidence, assumptions, rankings, and recommendations.
- Express uncertainty and insufficient evidence.
- Test for unsupported claims and hallucination resistance.

**Must not:** calculate authoritative metrics, ROI, savings, readiness or priority scores; invent evidence; implement before deterministic outputs are stable.

## Phase-to-Agent Assignment

| Phase | Lead | Supporting roles |
|---|---|---|
| 0 Foundation | Product Lead | Backend, Frontend, QA |
| 1 Ingestion | Backend | Data Analyst, QA |
| 2 Reconstruction | Analytics | Data Analyst, QA |
| 3 Metrics | Analytics | Data Analyst, QA |
| 4 Bottlenecks | Opportunity Analyst | Analytics, QA |
| 5 Opportunities | Opportunity Analyst | Analytics, Product Lead |
| 6 Readiness | Opportunity Analyst | Data Analyst, QA |
| 7 Economics | Opportunity Analyst | Product Lead, QA |
| 8 Prioritisation | Opportunity Analyst | Analytics, Product Lead |
| 9 Evidence | Analytics | Backend, QA |
| 10 AI Explanation | AI Engineer | Product Lead, QA |
| 11 Blueprint | Product Lead | Opportunity Analyst, AI Engineer |
| 12 Dashboard | Frontend | Backend, Product Lead |
| 13 Testing | QA | All roles |
| 14 Deployment | Product Lead / DevOps-capable agent | Backend, Frontend, QA |
| 15 Industry Pilot | Product Lead / Domain Analyst | Analytics, Opportunity Analyst |
| 16 Productization | Product Lead | Roles as needed |

## Delegation Template
Every delegated task must state:
- Objective
- Context/files to read
- Allowed files/modules to modify
- Explicit non-goals
- Interface/output contract
- Tests required
- Acceptance criteria
- Files changed and commands run

```text
Task:
Objective:
Read first:
Allowed changes:
Do not change:
Interface / output contract:
Tests:
Acceptance criteria:
Report back with:
```

## Parallel Work Rules
Parallelize only bounded tasks with stable interfaces.

**Good:** independent dataset inspection, metric-spec review, tests for an agreed contract.  
**Bad:** multiple agents editing the same files; UI work before API contracts are agreed; ROI before formulas are approved; AI before evidence outputs are stable.

The orchestrator owns integration and resolves conflicting interfaces before implementation continues.

## Rules for All Agents
- Inspect existing code before editing.
- Make the smallest change that satisfies the task.
- Do not add dependencies without justification.
- Do not reorganize modules opportunistically.
- Keep business logic deterministic and testable.
- Separate API, domain logic, data access, and UI.
- Add tests for new calculations and bug fixes.
- Never commit secrets.
- Document assumptions, limitations, and data provenance.
- Do not treat synthetic results as evidence of real customer value.
- Do not hard-code dataset-specific answers.
- Never claim tests passed unless run.

## Feature-Creep Gate
Before adding a feature, ask:
1. Does it improve Discover → Quantify → Prioritise → Act?
2. Does it help answer “what should the business fix or automate first?”
3. Is it required for the end-to-end MVP?
4. Can the MVP work without it?
5. What complexity and validation burden does it add?

If not essential, defer it unless the Product Lead explicitly approves an exception.

## Definition of Done
- Matches approved scope.
- Tests added or reason for omission stated.
- Relevant tests run and results reported.
- Errors and limitations documented.
- Dependent interfaces documented.
- No unrelated features/files changed.
