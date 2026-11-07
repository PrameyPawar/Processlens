# ProcessLens: A Newcomer’s Guide

**Who this is for:** someone seeing ProcessLens for the first time, with no process-mining or software background.  
**What this guide covers:** the product idea, the data it needs, how an analysis runs, every main screen and control, what the numbers mean, and how to explain the project honestly.

---

## 1. ProcessLens in one minute

ProcessLens is a portfolio-stage decision-support application. It takes a CSV event log—one row per recorded business event—and summarizes how cases moved through a process. It looks for long elapsed intervals, repeated activities, unusual paths, and other patterns. It then ranks possible improvement investigations and shows evidence behind each one.

Imagine a business fulfilling customer orders. A single order is a **case**. “Order Received,” “Inventory Check,” and “Dispatch” are **activities**. Each activity record has a time. Put the records for one order in time order and you have its **trace**. Put many traces together and ProcessLens can compare how often each step occurs, how long cases take, and which sequences are common.

The product’s intended question is: **“Where might work be getting stuck, what evidence supports that, and what should the team investigate first?”** It does not execute changes in a business system, prove that a delay is waste, or promise savings. ProcessLens is a decision aid, not an autonomous operations agent.

## 2. What problem it is trying to solve

Many businesses have operational records but no easy way to see the full path an order, return, ticket, or request took. A spreadsheet can show individual timestamps; it is harder to compare thousands of cases and notice that one handoff repeatedly has a long gap, or that some cases loop back through the same activity.

ProcessLens tries to make that evidence easier to inspect and prioritize. Its current target user and initial manufacturing/order workflows are **product hypotheses**, not validated market findings. The current implementation is best presented as a working portfolio prototype.

### What it is not

- It is not a general-purpose ERP, workflow engine, or robotic process automation (RPA) tool.
- It does not connect to SAP or other business systems in real time.
- It does not tell a business that a particular delay is avoidable without operational context.
- A high ranking is not proof of ROI, automation suitability, or a guaranteed result.
- A green “valid” data check means the rows match the required structure; it does not prove the event log captured every real-world event.

## 3. The minimum data concepts

A CSV needs three required columns:

| Field | Plain-language meaning | Example |
|---|---|---|
| `case_id` | Which process instance this row belongs to | `ORD-00042` |
| `activity` | What happened | `Inventory Check` |
| `timestamp` | When it happened | `2026-03-04 10:30:00` |

One row is one recorded event. Many rows usually belong to one case. Optional columns such as `resource`, `department`, `order_value`, `quantity`, `priority`, or `event_id` can add context. An optional source event ID can help distinguish two legitimate events that happen to share the same case, activity, and time.

Example:

```csv
case_id,activity,timestamp,resource
ORD-00042,Order Received,2026-03-04 08:00:00,Sales-01
ORD-00042,Inventory Check,2026-03-04 10:30:00,Warehouse-02
ORD-00042,Dispatch,2026-03-05 09:15:00,Warehouse-02
```

This records a three-event trace. The gap from 08:00 to 10:30 is **elapsed time between recorded milestones**. It is not automatically 2.5 hours of employee work: it may include a queue, a night, a pause, or delayed recording.

### Important terms

- **Event:** one activity record at one timestamp.
- **Case:** one instance of the process, such as one order or ticket.
- **Trace:** the ordered events for one case.
- **Variant:** a distinct activity sequence. `Received → Check → Dispatch` is a different variant from `Received → Check → Rework → Dispatch`.
- **Cycle time:** elapsed time between the first and last recorded events in a case.
- **Transition:** two neighboring events in a case trace. Its duration is the elapsed time between their timestamps.
- **Rework / recurrence:** the same activity appears more than once at distinct timestamps in a case. That can be rework, a normal multi-pass procedure, or another business convention; the log alone cannot decide which.
- **Complete case:** a case whose usable rows pass required validation. Incomplete cases are reported but excluded from complete-case comparisons such as variant percentages.
- **Evidence strength / confidence:** a sample-size or data-support indicator in the current scoring model. It is not a calibrated probability that the finding is true.

## 4. How an analysis runs

After a customer session uploads a CSV, the browser sends it to the FastAPI backend. The frontend holds the returned analysis in its application state. The backend processes the file as an upload request and does not provide saved datasets or saved analysis history.

The visible workflow is:

1. **Upload and validate.** Check file type, size, headers, required fields, timestamps, malformed rows, and duplicate identity. The UI’s sample action is labelled **Load Quickstart Log**.
2. **Reconstruct cases.** Group events by `case_id`, parse timestamps, and sort each trace by time. Row order is used as a stable tie-break when times match.
3. **Calculate metrics.** Summarize cycle time, activity frequency, transitions, variants, and repeated activity for the eligible population.
4. **Detect findings.** Apply deterministic rules for delay concentration, cycle-time outliers, repeated activity, rare variants, and data-quality signals.
5. **Create opportunity candidates.** Translate findings into possible improvement investigations, such as reducing a long transition or investigating recurrence.
6. **Assess readiness and economics.** Use known event data plus separately supplied or missing domain/financial inputs. Missing inputs should remain “unknown,” not be silently treated as zero.
7. **Rank candidates.** Apply transparent scoring and constraints to produce an investigation order.
8. **Generate explanations and evidence.** Produce a deterministic explanation baseline and an evidence dossier that points to source rows, calculations, assumptions, and limitations.

The same file is uploaded to several API endpoints as each part of the pipeline runs. The main endpoint code is in `backend/app/main.py`; the calculations live under `backend/app/services/`.

### Deterministic versus AI-generated language

“Deterministic” means the same input and settings are intended to produce the same calculations and rule outputs. It does not mean the rules perfectly represent every company’s process. By default, the UI requests explanations with `enable_llm=false`, so narrative comes from deterministic templates. An optional LLM provider exists, but model text is treated as untrusted and checked against deterministic evidence; failed checks fall back to the template. Neither the LLM nor its prose is the source of metrics, ranking scores, or ROI.

## 5. Public website: what a visitor sees

The marketing page is shown to an unauthenticated visitor at `/`. Its navbar contains:

- **Product:** scrolls to the preview area.
- **How It Works:** scrolls to the four-stage pipeline description.
- **Use Cases:** scrolls to example industries/workflows.
- **Trust & Evidence:** scrolls to the evidence and limitations section.
- **Sign In:** opens `/login`.
- **Explore Product:** scrolls to the preview.
- On a narrow screen, a hamburger button opens the mobile navigation; Escape closes it.

The page content runs top to bottom:

1. **Hero:** “Find the friction. Fix what matters.” states the product pitch. The button scrolls to the preview. The small evidence/transparent-prioritization/no-invented-metrics phrases are positioning statements, not independent product certification.
2. **Product preview:** an interactive-looking sample dashboard with tabs for a spotlight, bottlenecks, and evidence. It is illustrative, hard-coded preview content—not an analysis of the visitor’s data and not a live connection to the backend. Treat its numbers as sample-demo content.
3. **Operational problem cards:** describes bottlenecks, signals, and prioritization at a high level.
4. **How it works:** introduces bringing data, reconstructing the process, surfacing findings, and prioritizing with evidence.
5. **Evidence showcase:** demonstrates the distinction between observed facts, assumptions, and unknowns.
6. **Use cases:** presents candidate areas such as manufacturing, procurement/order-to-cash, service delivery, and automation discovery. These are examples, not proven customer deployments.
7. **Trust section:** describes deterministic metrics, data-quality checks, epistemic labels, and transient analysis. The current tenant-storage limitations still apply; see Section 11.
8. **Final call to action and footer:** leads to sign-in, the sample preview, and the developer console link.

The marketing page is implemented in `frontend/src/components/marketing/`. Navigation is mostly smooth in-page scrolling; it is not a multi-page content-management system.

## 6. Sign-in and account roles

### Customer sign-in (`/login`)

This is the entry to the analysis workspace. A customer account signs in with email and password. “Create Account” registers a customer-role account. The “Forgot password?” control explains that recovery is unavailable in this portfolio demo; no reset email service is implemented.

### Developer sign-in (`/dev/login`)

This is a separate presentation route for an internally provisioned developer role. Public registration cannot request developer privileges. The account is configured by the server environment. The developer dashboard is protected by backend role checks; hiding a frontend button alone is not the security boundary.

### Session and sign-out

The app restores a session when it opens. The workspace header shows the signed-in email and role. **Sign Out** clears the current UI analysis state and logs out the session. This clears app state; it is not certified forensic deletion from browser memory, server memory, proxy logs, or backups.

## 7. The authenticated workspace: each main UI area

### Workspace header

- **ProcessLens logo:** returns to the workspace home.
- **Dataset pill:** shows the active CSV name.
- **Percent-valid badge:** opens the data-quality audit. The percentage reflects schema-valid rows, not the percentage of real business events captured.
- **Upload Another Dataset:** starts a new analysis and clears the previous result state.
- **Health indicator:** checks whether the backend health endpoint responds; it is a basic service check, not a complete readiness or security certification.
- **Theme toggle:** switches the visual theme.
- **Email and role badge:** shows the current identity (`CLIENT` or `DEV`).
- **Dev Console:** shown for developer sessions and opens diagnostic telemetry.
- **Sign Out:** logs out and resets the visible analysis state.

### Workflow navigation

The navigation bar contains **Overview**, **Process Explorer**, **Findings**, **Opportunities**, **Evidence & Explanations**, and **Reports**. **Data Quality Audit** appears while that audit is the current view. Steps become available as their analysis results are ready. A small completion marker means that step’s result is available in this run.

### Upload screen

The drop zone accepts a `.csv` file by browse or drag-and-drop. The current UI and backend limit uploads to 10 MB. **Load Quickstart Log** uses the bundled manufacturing example so a newcomer can run the workflow without preparing a file. During processing, the panel shows an in-progress state. An invalid extension, oversized file, malformed CSV, or missing required columns produces an error instead of continuing silently.

### Data Quality Audit

This is the first report and is worth reading before trusting any later chart.

- **Total Source Rows:** number of parsed CSV records.
- **Valid Events:** rows meeting structural requirements.
- **Invalid Rows:** rows with errors that can prevent a valid trace; examples include missing IDs, invalid timestamps, or malformed extra fields.
- **Confirmed Duplicate IDs:** repeated source event IDs within the same case.
- **Possible Duplicate Matches:** same operational tuple where available IDs do not let the system confirm whether the events are the same record.
- **Quality Breakdown:** shows rule counts and downstream impact.
- **Flagged Issues:** shows row-level diagnostics and their severity.
- **Data Preview:** displays an initial sample of the parsed rows.

A warning-only possible duplicate does not make the row structurally invalid or automatically remove it. The safe interpretation is “review this ambiguity,” not “the app proved this event is a duplicate.”

### Overview dashboard

This is the executive summary after a run:

- **Cases Analysed:** complete traces used in core comparisons.
- **Valid Event Rate:** structural CSV validity.
- **Median Cycle Time:** middle case duration (half of measured cases are at or below it, half at or above it).
- **P90 Cycle Time:** 90th percentile; a way to see the slower tail of cases.
- **Operational Findings:** number of generated signals and high-severity count.
- **Prioritised Opportunities:** number of candidates in the current roadmap.
- **Recommended Next Investigation:** a spotlight on the top-ranked candidate, its cohort, priority, readiness, and evidence confidence.
- **Economics notice:** shows if monetary calculations have inputs. When wage/cost inputs are missing, ROI remains unknown.
- **Visual charts:** cycle-time distribution, opportunity dimensions, activity frequency, and transition duration.
- **Inspect Evidence Dossier:** opens traceable source-row evidence for the spotlight opportunity.

The dashboard’s “top” opportunity means first under the implemented score and policy. It does not mean a human has approved it or that it will deliver the highest realized savings.

### Process Explorer

This view explains the observed process patterns. Its tabs are:

- **Visual Analytics:** cycle-time percentile chart, transition-duration chart, and activity-frequency chart.
- **Step Transitions:** table of adjacent activity pairs, how often they occur, case coverage, mean/median elapsed gap, and p90.
- **Activity Frequencies:** count and case coverage per activity. The search box filters the table; Clear removes the search text.
- **Process Variants:** groups complete cases by their exact activity sequence and shows frequency/percentage. A variant is a path pattern, not necessarily a good or bad path.
- **Rework & Repetition:** shows activity repeats at distinct timestamps and tracks duplicate identity separately.

Cycle time and transition duration are milestone-to-milestone elapsed time. Without start/end activity instrumentation or a defensible business rule, these values are not labor touch time, queue time, or time that can necessarily be saved.

### Findings

The findings view lists statistical or rule-based patterns produced from the event log. A card can include category/title, severity or signal level, evidence strength, measured values, affected population, observed facts, limitations, and cases/row examples. Read the limitations alongside the highlighted result.

A “finding” is a measured pattern under the app’s rules. For example, a long transition is an observation; “the department is inefficient” is a causal claim and needs other evidence. The app cannot infer why the gap occurred from timestamps alone.

### Opportunities and Roadmap

This view converts findings into candidate investigations and orders them under a scoring policy.

- Summary tiles show candidate count, top candidate, portfolio cohort allocation, and capacity valuation (when sufficient inputs exist).
- Search filters by text.
- **Cohort** filters by strategic disposition.
- **Archetype** filters by opportunity type (for example delay compression, recurrence reduction, tail variance, or path standardization).
- **Sort** allows ranking by default order, operational priority, readiness, impact, or evidence confidence.
- **Toggle chart** shows or hides the comparison chart.
- Each opportunity card shows rank, target, evidence/constraint summary, operational priority, readiness, impact potential, confidence, labor/economic fields, and decision/roadmap details.
- **Inspect Evidence Dossier & Row Anchors** opens the supporting trace bundle.

The scores answer different questions. **Operational priority** ranks observed patterns for investigation. **Automation readiness** estimates whether an intervention might be suitable based on explicit dimensions. **Impact potential** describes modeled improvement potential. **Evidence confidence** expresses how much support the event data provides. None is a probability of success or a financial guarantee. A missing value should remain unknown; it is not zero.

### Evidence & Explanations

The briefing summarizes recommended next actions and foundational prerequisites. Each opportunity explanation may include:

- **Executive Summary:** short statement of the candidate and measured signal.
- **Operational Problem Narrative:** describes the observed pattern.
- **Economic Interpretation:** explains modeled values and missing inputs.
- **Strategic Roadmap Rationale:** explains why the candidate ranks where it does.
- **Key Assumptions, Hypotheses & Boundaries:** separates facts from things to validate.
- **Recommended Operational Next Steps:** suggested investigation work.

Check the displayed explanation source and grounding status. In the default workflow, explanations are deterministic templates. If optional LLM text is configured and requested, the backend checks it against the trusted deterministic dossier and falls back to the template when verification fails.

### Reports

The report view assembles a printable executive briefing from the current analysis, including summary, findings, ranked actions, assumptions and supporting context. Use **Print / Save as PDF**, **Export Opportunities (CSV)**, or **Export Transitions (CSV)**. A report is a snapshot of the current in-memory run; this build does not provide durable report history or a shared customer workspace.

### Evidence Dossier modal

The dossier is the “show your work” view behind a candidate. It includes a source-file hash and file/run manifest where available, then tabs for:

- **Row Anchors:** original data row and CSV line, case, activity, raw timestamp, resource, and each anchor’s role (such as transition source/target or trace start/end). Source event IDs are retained in the evidence payload when available, though the current anchor table does not display that column.
- **Case Exemplars:** example cases chosen under a stated deterministic selection policy and the trace events that demonstrate the pattern.
- **Epistemic Ledger:** statements labelled FACT, ASSUMPTION, HYPOTHESIS, ESTIMATE, or DECISION, with their source or basis.
- **Formula Derivations:** formulas, input variables, intermediate values, output values, rounding rules, and limitations.

A SHA-256 hash helps identify the exact uploaded byte content; it does not validate the source data or prove the business interpretation. Row anchors let a reviewer locate source records. They do not prove causality.

### Developer Console

The developer dashboard is a restricted diagnostics view. It presents service/runtime information and recent sanitized security/operational audit events (for example login and rate-limit activity). It is not a customer analytics area, and developer role does not mean access to a customer’s uploaded data. UI access restrictions are backed by API authorization checks.

## 8. How to give a good 3-minute demo

1. Start both backend and frontend using the project’s local startup instructions in `Docs/deployment.md`.
2. Open the site. Explain the hero and the difference between the static product-preview section and an actual analysis.
3. Sign into the locally configured customer demo account; do not put credentials in this guide or a public repository.
4. Select **Load Quickstart Log**. Explain the three required columns before clicking through the results.
5. Start with **Data Quality Audit**. Show what is valid and any warnings. Explain why structurally valid does not mean complete business telemetry.
6. Open **Process Explorer**. Explain cases, traces, cycle time, transitions, and variants with one example.
7. Open **Findings**. Describe one result as a measured pattern; avoid claiming its cause is known.
8. Open **Opportunities**. Explain rank vs readiness vs confidence, then inspect one dossier.
9. In the dossier, show a row anchor, an epistemic label, and a formula. Explain what additional business evidence is needed.
10. End with the limitations: this build is a portfolio demo, not a production multi-tenant service or proven ROI product.

A useful short narrative is: **“ProcessLens helps a team inspect event-log evidence and choose what to investigate first. It measures elapsed patterns; the business still validates causes, feasibility, and value.”**

## 9. What a technically curious newcomer should inspect

| Question | Start here |
|---|---|
| Which pages/routes exist? | `frontend/src/App.tsx` |
| How the upload flow is sequenced? | `frontend/src/App.tsx` and `frontend/src/services/api.ts` |
| Where each visual screen is built? | `frontend/src/components/` |
| Which fields the frontend expects? | `frontend/src/types/api.ts` |
| Which API endpoints are exposed? | `backend/app/main.py`, `backend/app/api/v1/` |
| How CSV rows are checked? | `backend/app/services/validator.py` |
| How cases and variants are built? | `backend/app/services/reconstruction.py` |
| How metrics and findings are derived? | `backend/app/services/analytics.py`, `detection.py` |
| How candidates are made and ranked? | `opportunity.py`, `readiness.py`, `economics.py`, `prioritisation.py` |
| How evidence and explanations are assembled? | `evidence.py`, `explanation_pipeline.py`, `grounding.py`, `explanation_templates.py` |
| What the project intends and excludes? | `PROJECT.md` |
| What current deployment boundaries are known? | `Docs/deployment.md` and `Docs/authentication.md` |

## 10. Product and analytics caveats

1. **Elapsed time is not active time.** A time gap between events can contain work, waiting, weekends, missing events, or late logging.
2. **A correlation or outlier is not a cause.** ProcessLens sees event records; it does not know staffing, policy, seasonality, or operational exceptions unless supplied separately.
3. **Incomplete cases affect population size.** Always note the complete-case count and the exclusions.
4. **Source IDs matter.** Repeated IDs within a case can be confirmed as duplicates under the project rule. Matching timestamps without IDs are ambiguous and retained.
5. **Economics needs inputs.** Wages, implementation costs, addressable labor, and adoption assumptions cannot be fabricated from timestamps.
6. **Ranking is a policy choice.** It reflects the current formula and weights. It should support human review, not replace it.
7. **The preview is illustrative.** Marketing preview values are prebuilt demo content and must not be represented as results from an uploaded customer dataset.
8. **No validated market or customer outcome claim.** The project specification describes the audience and candidate workflow as hypotheses.

## 11. Current project boundaries

The current application accepts CSV files up to 10 MB. The customer workspace endpoint returns identity-derived metadata, not a durable tenant workspace. Password recovery, saved datasets, multi-tenant persisted analytics, XES import, database backup/restore validation, and production incident operations are not implemented or validated. The application is suitable for a controlled portfolio demonstration with synthetic or public data, not onboarding real customer data without further engineering and independent review.

The local account setup, server environment, and developer seeding instructions are maintained in `Docs/authentication.md` and `Docs/deployment.md`. Use those files rather than sharing account secrets.

## 12. Glossary

| Term | Meaning |
|---|---|
| API | A defined way for the frontend to ask the backend for analysis or account operations. |
| Backend | Server-side code that validates CSVs, computes metrics, enforces auth, and returns structured results. |
| Frontend | Browser interface built with React and TypeScript. |
| FastAPI | Python web framework serving the ProcessLens API. |
| HTTP status | A response code describing request outcome; for example 200 success, 401 unauthenticated, 403 forbidden, 413 too large. |
| In-memory | Held temporarily while a process or browser session runs, rather than saved as a dataset history. It is not the same as certified secure erasure. |
| LLM | Large language model; optional for narrative only, not the authoritative calculator. |
| P90 | 90th percentile: 90% of measured values are at or below it; the remaining 10% are above it. |
| RBAC | Role-based access control: permissions tied to roles such as customer or developer. |
| RPA | Robotic process automation: software that carries out repetitive user-interface or system tasks. |
| Schema | The names and expected shape of data columns. |
| Tenant isolation | Ensuring one customer cannot see or alter another customer’s stored data. A fully persisted multi-tenant data model is not implemented here. |

---

**Source of truth:** this guide describes the current code and is paired with `PROJECT.md`, `Docs/authentication.md`, and `Docs/deployment.md`. If marketing text, a sample preview, or an old report conflicts with current code, verify the specific behavior before making claims.
