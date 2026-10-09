# ProcessLens Project Specification (`PROJECT.md`)

## 1. Project Summary

**Name:** ProcessLens  
**Category:** SME process intelligence and improvement/automation decision support.  
**MVP type:** Decision support, not autonomous execution.

**Product thesis:** Businesses may have operational data but lack a simple, evidence-backed way to decide which process improvements or automation opportunities should be addressed first. ProcessLens aims to turn event data into ranked opportunities with transparent evidence and business-impact estimates.

**Core question:** What should this business fix or automate first, why, and what value could it create?

**Core loop:** Discover → Quantify → Prioritise → Act  
**Core chain:** Operational Data → Evidence → Economics → Decision

## 2. Evidence Discipline and Current Status

The project is at the development-foundation stage. Synthetic development datasets have been created. The target segment and workflow remain hypotheses, not validated customer requirements.

Use these labels:
- **FACT:** supported by reliable source data or direct observation.
- **ASSUMPTION:** temporarily accepted but unverified.
- **HYPOTHESIS:** testable proposition.
- **DECISION:** deliberate project choice.
- **ESTIMATE:** calculated/approximated value with stated inputs and assumptions.

Current hypotheses:
- Target users may include SME owners and operations managers.
- Manufacturing operations are a candidate niche.
- Order-to-dispatch/order-to-delivery is a candidate workflow.
- CSV/Excel/event logs are practical initial inputs.
- Evidence-backed prioritisation is the intended differentiator.

Do not present these hypotheses as validated facts.

## 3. Problem Statement

Draft problem statement:

> Manufacturing SMEs may rely on fragmented operational data and manual analysis to understand their processes. Bottlenecks, repetitive work, rework, and delays can be difficult to quantify consistently. Managers may therefore struggle to determine which operational improvements or automation initiatives deserve attention first and what financial impact they could produce.

This is a hypothesis until validated with a defined customer segment and real operational context.

## 4. Candidate User and Workflow

**Candidate users:** SME owner, operations manager, process improvement lead, manufacturing/production manager.

**Candidate workflow:**

Order Received → Order Verification → Inventory Check → Production Planning → Production → Quality Inspection → Dispatch → Invoice

Rework and exception paths may occur. This workflow is used to generate development data; it is not assumed to fit every customer.

## 5. Positioning

Avoid generic positioning such as “AI-powered process mining” or “upload a CSV and AI finds bottlenecks.”

Intended positioning:

> ProcessLens helps businesses discover where operational time and effort are being lost, support findings with evidence, and prioritise what should be improved or automated first.

Potential differentiators, not yet proven:
1. Prioritisation of actions, not just process visualization.
2. Interpretable automation-readiness assessment.
3. Transparent business-impact calculations.
4. Evidence traceability from source events to recommendations.
5. SME-friendly file-based input.
6. Practical improvement/automation blueprint.

## 6. MVP Outcome

A user uploads an event-log file. ProcessLens validates it, reconstructs the process, calculates supported metrics, detects bottlenecks and opportunity candidates, estimates impact using transparent assumptions, ranks opportunities, and explains results with traceable evidence.

### MVP workflow
1. Upload CSV.
2. Map/validate required fields.
3. Inspect the data-quality report.
4. Reconstruct cases and activity sequences.
5. Calculate core metrics.
6. Detect bottlenecks.
7. Generate improvement/automation opportunities.
8. Assess automation readiness.
9. Estimate business impact where inputs support it.
10. Rank opportunities.
11. Inspect evidence and assumptions.
12. Explain verified results in human-readable language.
13. Present a proposed improvement/automation blueprint.
14. Let the user decide what to do next.

## 7. MVP Scope

### In scope

**Ingestion and validation**
- CSV first; Excel only if it does not materially delay the MVP.
- File type/size validation.
- Schema detection and column mapping.
- Required-field validation.
- Missing/invalid-value reporting.
- Duplicate-event detection.
- Dataset preview.
- No silent dropping of invalid records.

**Process reconstruction**
- Case/event grouping.
- Timestamp parsing and ordering.
- Activity sequences.
- Basic process variants and process graph.
- Preserve event-level evidence.

**Analytics**
- Cycle time.
- Activity frequency.
- Throughput.
- Waiting-time estimates where event semantics support them.
- Processing-time calculation only where start/end events or another defensible source support it.
- Rework/repeated-activity analysis.
- Variant frequency.

**Bottleneck/opportunity detection**
- Transparent rules and metrics.
- Ranked bottlenecks.
- Structured improvement and automation candidates.
- No activity-name-specific hard-coding.

**Automation readiness**
- Interpretable rule-based score.
- Factors may include repetition, rule-based nature, digital inputs, volume, exception rate, human judgment, and risk.
- Explain score contributions.

**Business impact and prioritisation**
- Labour hours/cost estimates only when inputs are available or explicitly supplied.
- Potential savings and payback labelled as estimates.
- Explicit assumptions and limitations.
- Transparent ranking factors.
- Keep impact, confidence, readiness, effort, and risk distinct.

**Evidence and explanation**
- Trace recommendations to relevant data and metrics.
- Add AI explanations only after deterministic outputs and evidence contracts are stable.
- AI is not the source of truth for metrics, scores, or ROI.

**UI**
- Upload and validation.
- Overview/process metrics.
- Process graph/variants.
- Bottlenecks and ranked opportunities.
- Opportunity details with evidence and assumptions.
- Basic report/export if time permits.

### Out of scope initially
- ERP integrations (SAP, Tally, etc.).
- Real-time streaming or continuous monitoring.
- RPA execution/deployment.
- Autonomous agents changing business systems.
- Digital twins and predictive simulation.
- Object-centric process mining.
- Multi-company SaaS architecture.
- Enterprise SSO and complex permissions.
- Mobile app.
- Generic AI chatbot as the main product.
- ML-based scoring before rules are validated.
- Complex forecasting.
- Full enterprise BI/dashboard builder.

## 8. Feature-Creep Rules

A feature is MVP-eligible only if it:
1. Supports Discover → Quantify → Prioritise → Act.
2. Is required for the core journey or its reliability.
3. Has an observable acceptance criterion.
4. Fits the delivery schedule.
5. Does not introduce disproportionate complexity.

Otherwise record it as Post-MVP. Do not build features merely because they are interesting or easy for an agent to generate.

## 9. Canonical Event-Log Contract

Internal processing must not depend on a specific source dataset.

### Required fields
| Field | Required | Meaning |
|---|---|---|
| `case_id` | Yes | Identifier for one process instance |
| `activity` | Yes | Activity/event name |
| `timestamp` | Yes | Event timestamp |

Optional fields: `resource`, `department`, `order_value`, `quantity`, `product_type`, `priority`, `event_type`, and later controlled source-specific attributes.

One row represents one event. Multiple rows can belong to one case. Repeated activities are valid. Events are ordered within each case by parsed timestamp, with invalid/missing values reported.

### Data-quality principles
- Distinguish invalid records from valid records.
- Report issue counts and examples.
- Do not silently delete or “repair” records.
- If partial processing is supported, report exactly what was excluded and why.
- Preserve uploaded-row provenance where feasible.

## 10. Synthetic Development Data

The current package is `ProcessLens_Development_Data.zip` and contains:
- `samples/manufacturing_orders_quickstart.csv` — 100 cases for rapid iteration.
- `samples/manufacturing_orders_clean.csv` — 750 cases for main analytical development.
- `samples/manufacturing_orders_rework.csv` — 750 cases with more rework loops.
- `samples/manufacturing_orders_messy.csv` — intentionally flawed data for validation.
- `schemas/canonical_event_log_schema.md` — schema reference.
- `ground_truth/expected_findings.md` — expected tendencies.

Expected tendencies:
- Inventory Check contributes substantial waiting time.
- Order Verification is frequent and manual.
- Production dominates absolute processing duration.
- Some cases contain rework.
- Rework-heavy data should show more rework loops and longer durations for affected cases.
- Messy data contains missing IDs/activities/timestamps/resources, duplicates, invalid timestamp strings, and unordered rows.

These are test expectations, not hard-coded rules. The engine must calculate results from the data.

**Limitation:** Synthetic data enables controlled testing; it does not establish real-world savings or validate the customer problem.

## 11. Technical Architecture

Recommended initial stack:
- Frontend: React + Vite + TypeScript.
- Backend/API: Python + FastAPI.
- Analytics: pandas and deterministic Python modules.
- Tests: pytest plus suitable frontend tests.
- Storage: local development storage initially.
- Database: defer until persistence is needed.
- AI: separate service layer, added after verified analytics/evidence contracts exist.
- Deployment: local-first; Docker/cloud deployment after the end-to-end MVP is stable.

Logical architecture:

Frontend → Backend API → ProcessLens Engine → Structured Analytical Result

AI explanation consumes verified findings and evidence; it does not replace the analytical engine.

Separate responsibilities:
- API: HTTP, uploads, request validation, response formatting.
- Ingestion: file reading.
- Validation: schema and quality checks.
- Reconstruction: cases, sequences, variants.
- Analytics: metrics.
- Opportunity: detection and ranking.
- Economics: transparent estimates.
- Evidence: traceability.
- AI: explanation.
- UI: presentation of results and assumptions.

Keep the MVP modular, not microservice-heavy.

## 12. Build Phases and Exit Gates

### Phase 0 — Development foundation
Repository, frontend/backend scaffold, environment config, README, Git workflow, health endpoint.
**Exit:** app runs locally and tests can run.

### Phase 1 — Ingestion and validation
CSV upload, field mapping, quality report, preview, error handling.
**Exit:** clean and messy samples produce correct understandable reports.

### Phase 2 — Process reconstruction
Case grouping, event ordering, sequences, variants, graph data.
**Exit:** small hand-verifiable event logs produce expected cases/sequences.

### Phase 3 — Process analytics
Implement documented metrics.
**Exit:** hand-calculated fixtures match outputs.

### Phase 4 — Bottleneck detection
Rank measurable delay/frequency/rework impacts.
**Exit:** findings emerge from calculations, not hard-coded activity names.

### Phase 5 — Opportunity detection
Convert evidence into structured candidates.
**Exit:** each candidate includes reason, metrics, evidence.

### Phase 6 — Automation readiness
Transparent rule-based score and factor explanations.
**Exit:** score is reproducible and interpretable.

### Phase 7 — Business impact / ROI
Explicit inputs, assumptions, costs, savings, payback where supportable.
**Exit:** each estimate traces to formulas and inputs.

### Phase 8 — Prioritisation
Rank opportunities using transparent factors.
**Exit:** user understands why the leading opportunity ranks first.

### Phase 9 — Evidence
Source records, metrics, formulas, assumptions, confidence.
**Exit:** recommendations are auditable at MVP level.

### Phase 10 — AI explanation
LLM explains structured verified results.
**Exit:** AI does not author authoritative metrics/scores and can state uncertainty.

### Phase 11 — Improvement/automation blueprint
Current state, problem, intervention, future state, technology category, human review.
**Exit:** proposed action is understandable.

### Phase 12 — Dashboard
Minimal workflow for upload, process, metrics, opportunities, evidence.
**Exit:** user can complete the flow without developer-only steps.

### Phase 13 — Testing
Clean, messy, rework, edge-case, regression tests.
**Exit:** supported-input behaviour is reproducible and robust.

### Phase 14 — Deployment
Secure configuration, logs, production build, hosting, basic monitoring.
**Exit:** MVP is accessible and demonstrable end-to-end.

### Phase 15 — Industry pilot
Use real company data with permission, validate findings with users, measure before/after.
**Exit:** a use case demonstrates measurable value or produces evidence to revise the thesis.

### Phase 16 — Productization
Consider integrations, multi-tenant architecture, permissions, monitoring, pricing, and support only after pilot validation.

## 13. First Implementation Milestone

Implement only:
1. Backend health endpoint.
2. CSV upload endpoint.
3. File type/size checks.
4. Required-column validation for `case_id`, `activity`, `timestamp`.
5. Missing/invalid timestamp handling.
6. Missing case/activity handling.
7. Duplicate-event reporting.
8. Dataset preview.
9. Structured data-quality response.
10. Automated tests using quickstart, clean, and messy samples.

Do not build analytics, AI, ROI, authentication, database, or cloud deployment in this first task.

### Definition of done
- Valid sample can be uploaded.
- Invalid data produces a useful quality report.
- Invalid records are not silently discarded.
- API behaviour is documented.
- Automated tests have been run and results reported.

## 14. Testing Philosophy

Use:
1. Unit tests with small hand-calculated cases and metrics.
2. Integration tests for upload → validation → structured response.
3. Dataset-level tests for quickstart, clean, rework, and messy files.

Use exact expected values where they can be calculated reliably; use ranges/order assertions for seeded tendencies. Never hard-code a named activity as a bottleneck to satisfy a test.

## 15. Metric and Business-Impact Integrity

- Event timestamps do not always reveal exact processing duration. Document when waiting/processing is a proxy.
- Define cycle time precisely, typically completion minus start for completed cases.
- Handle incomplete cases explicitly.
- Labour cost and savings require rates/effort assumptions; event logs alone rarely prove them.
- Automation readiness is not a guarantee of safety or economic value.
- Priority is a decision aid, not an autonomous investment decision.
- Keep impact, confidence, readiness, effort, and risk distinct.

## 16. Security and Privacy

- Never commit API keys or secrets.
- `.env.example` contains names/placeholders, not real values.
- Treat uploaded operational data as potentially confidential.
- Avoid logging raw records unless needed and approved.
- Enforce file-size limits and validate uploads.
- Keep uploads outside public static directories.
- Before industry pilots, agree on permission, retention, anonymisation, and access rules.
- Do not send confidential customer data to an external LLM without approval and appropriate safeguards.

## 17. Working with AI Coding Agents

- Read `AGENTS.md` and `PROJECT.md`.
- Work in small bounded tasks.
- Inspect before editing; do not overwrite files without review.
- Ask before expanding scope or adding major dependencies.
- Keep deterministic calculations separate from LLM explanations.
- Add and run tests.
- Report changed files, commands, results, assumptions, and limitations.
- Never claim success without verification.

Recommended initial task: Phase 0 scaffold plus Phase 1 CSV ingestion/validation, as described in Section 13.

## 18. Open Decisions

Resolve with evidence:
- Exact target SME segment.
- Exact initial industry/workflow.
- Whether Excel belongs in the first iteration or follows CSV.
- Lifecycle timestamp semantics versus one timestamp per event.
- Processing-time definition when start/end events are absent.
- Readiness and prioritisation formulas/weights.
- How labour and implementation costs are supplied.
- LLM provider/model and privacy controls.
- Deployment platform.
- Licensing, adaptation, and attribution for external datasets.

Do not silently make major product decisions while coding. Record proposals and seek approval if they change scope or data contracts.

## 19. Success Criteria

**Technical:** supported files validate; reconstruction/metrics are deterministic; bad data is handled transparently; findings have traceable evidence; tests verify calculations.

**User value:** non-technical user understands findings; top opportunity has a defensible reason; financial estimates expose assumptions; recommendations are actionable.

**Real-world validation:** only established after findings are reviewed against real operational context and a pilot measures outcomes.

## 20. Golden Rule

> Do not build features because they are impressive. Build features because they make the core decision better.

ProcessLens succeeds when it turns messy operational data into **Evidence → Economics → Prioritised Action**. The MVP proves the decision-support loop; a real-world pilot must prove whether that loop creates business value.
