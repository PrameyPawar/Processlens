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

---

## Decision Record 003: Deterministic Process Reconstruction & Variant Derivation (Phase 2)
* **Date:** 2026-10-09
* **Status:** Implemented & Verified
* **Owner:** Process Analytics Engineer

### Context
Phase 2 requires converting raw event logs into chronologically ordered case traces and identifying process variants without using heuristics or nondeterministic LLM grouping.

### Decision
1. Implemented `backend/app/services/reconstruction.py` and `backend/app/schemas/reconstruction.py`.
2. Group events strictly by `case_id` and sort them chronologically by parsed timestamp.
3. Handle equal timestamps deterministically by breaking ties using the source file row position (`row_index`).
4. Preserve repeated activities within the sequence (do not collapse loops).
5. Identify process variants using the exact ordered sequence of activity names as the unique key (`tuple(activity_sequence)`).
6. Calculate variant percentages using `reconstructed_cases_count` (the count of valid, complete cases) as the explicit denominator.
7. Enforce strict data-quality exclusions:
   - Rows with missing `case_id` are excluded from all cases and reported in `missing_case_id_rows`.
   - Rows with missing `activity` or unparseable timestamps cannot form valid traces; they are excluded and their parent cases are flagged `is_complete=False` and excluded from variant statistics.
   - Duplicate events are preserved in the trace, flagged `is_duplicate=True`, and retained in the activity sequence.
8. Exposed `POST /api/v1/process/reconstruct` endpoint in FastAPI while keeping `POST /api/v1/ingestion/upload` intact and fully compatible.

### Consequences & Verification
- 21/21 backend tests passing (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`).
- 100% deterministic outputs across repeated runs on identical inputs.

---

## Decision Record 004: Deterministic Process Analytics Engine (Phase 3)
* **Date:** 2026-10-09
* **Status:** Implemented & Verified
* **Owner:** Process Analytics Engineer

### Context
Phase 3 requires computing operational process metrics (activity frequency, case cycle time, repeated-activity indicators, and step-to-step transition durations) strictly from reconstructed traces.

### Decision
1. Implemented typed Pydantic schemas in `backend/app/schemas/analytics.py` (`DurationStats`, `ReconstructionSummary`, `ActivityFrequency`, `ActivityRework`, `ActivityTransition`, `CycleTimeSummary`, `ProcessAnalyticsResult`).
2. Implemented deterministic analytics engine in `backend/app/services/analytics.py`:
   - **Population Consistency:** All analytics (frequency, rework, transitions, cycle times) operate strictly on complete cases (`is_complete = True`).
   - **Cycle Time Semantics:** Calculated as `end_time - start_time` for complete cases. Single-event cases evaluate to `0.0` seconds and are included in `evaluated_cases_count`.
   - **Transition Duration vs. Waiting/Processing Time:** Labeled elapsed duration between consecutive milestones strictly as `transition_duration`. Internal waiting time and processing time are explicitly not inferred without explicit start/end lifecycle event pairs.
   - **Repeated-Activity Indicators vs. Recording Duplicates:**
     - Duplicate events sharing identical `(case_id, activity, timestamp)` keys are tracked in `duplicate_events_count` and do NOT count as rework.
     - Distinct-timestamp occurrences within a case are tracked as `rework_case_count` and `rework_occurrences`. Documented neutrally as repeated-activity indicators, not proof of process failure.
   - **Deterministic p90 Percentile:** Calculated using linear interpolation between closest sorted ranks ($r = 0.90 \times (N - 1)$).
3. Exposed dedicated endpoint `POST /api/v1/analytics/process` in FastAPI while maintaining existing `/health`, `/ingestion/upload`, and `/process/reconstruct` endpoints.
4. Comprehensive test coverage in `backend/tests/test_analytics.py` including hand-calculated fixtures, zero-division safeguards, single-event cases, duplicate vs rework separation, and sample dataset integration tests.

### Consequences & Verification
- 32/32 backend tests passing across all suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`).
- Zero division-by-zero vulnerabilities on empty input files or datasets containing only incomplete cases.

---

## Decision Record 005: Reliability Hardening & Transition Integrity
* **Date:** 2026-10-09
* **Status:** Implemented & Verified
* **Owner:** Backend Reliability Engineer

### Context
QA audit revealed:
1. Duplicate events in traces created artificial `(A -> A)` self-transitions of duration `0.0s`.
2. Ingestion and reconstruction duplicate-key detection differed when timestamps had different textual formats representing identical datetime values.
3. The scope of `ActivityRework.duplicate_events_count` required explicit documentation regarding its complete-case population basis.
4. HTTP boundary failure modes (>10MB payload, empty filename, non-CSV extension) lacked regression coverage on reconstruction and analytics endpoints.

### Decision
1. **Transition Integrity:** Updated `calculate_process_analytics` to filter out `event.is_duplicate` records when computing transitions. Legitimate co-temporal transitions between distinct activities and genuine operational loops at distinct timestamps are strictly preserved.
2. **Duplicate Key Semantic Alignment:** Updated `validate_csv_content` in `validator.py` to use normalized parsed datetime strings when valid, achieving exact parity with `reconstruction.py`.
3. **Duplicate Scope Explicit Definition:** Documented that `ActivityRework.duplicate_events_count` evaluates complete cases only, adhering to the fundamental rule that all process analytics metrics are calculated strictly over the complete-case population.
4. **Boundary Failure Coverage:** Added regression tests covering non-CSV uploads, files exceeding 10MB limit, empty filename headers, and missing canonical columns across all API endpoints.

### Consequences & Verification
- Artificial 0.0s self-transitions eliminated from messy dataset and synthetic fixtures.
- Backward-compatibility preserved across all endpoints.

---

## Decision Record 006: Phase 4 Deterministic Problem and Bottleneck Detection
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Process Analytics Engineer & Product Lead

### Context
Phase 3 established deterministic process metrics (cycle times, frequencies, rework indicators, transitions) on complete cases. Phase 4 requires detecting operational inefficiencies and delays while strictly preventing unverified claims:
1. Transition duration shares cannot unconditionally claim to sum to 100% due to branching, rework loops, and potential gaps.
2. In cases where transition interval totals fail to reconcile with complete-case cycle times, duration shares must be suppressed rather than returning misleading percentages.
3. The 1% reconciliation tolerance serves solely as an accounting integrity check between event intervals and case spans; it does not independently prove that individual transitions are correctly attributed, non-overlapping, or active work.
4. Evidence strength cannot be inferred globally from overall case counts ($N \ge 30$), but must reflect finding-specific sample sizes (e.g. transition execution counts, recurrence case counts).
5. All terminology must remain strictly neutral: findings report measured operational variance, recurrence, and elapsed duration shares without asserting proven defects, root causes, savings, or automation feasibility.

### Decision
1. **Pydantic Schemas (`schemas/detection.py`):**
   - Defined enums `FindingCategory` (`BOTTLENECK`, `REPETITION`, `CYCLE_TIME_OUTLIER`, `PATH_VARIATION`, `DATA_QUALITY_LIMITATION`), `SeverityLevel` (`HIGH`, `MEDIUM`, `LOW`, `INFO`), and `EvidenceStrength` (`HIGH`, `MODERATE`, `LIMITED`).
   - Defined typed models `ReconciliationStatus`, `DetectionSummary`, `ProblemFinding`, and `ProblemDetectionResult`.
2. **Domain Service (`services/detection.py`):**
   - Implemented `detect_process_problems(reconstruction, analytics)` consuming typed Phase 2 and Phase 3 outputs without duplicate CSV parsing.
   - **Accounting Reconciliation Health Check:** Evaluates $\Delta = |\sum D_\tau - T_{\text{cumulative\_cycle}}| / T_{\text{cumulative\_cycle}}$. If discrepancy exceeds 1.0% or cycle time is 0.0s, transition duration-share findings are suppressed, and an explicit diagnostic finding (`ACCOUNTING_RECONCILIATION_DISCREPANCY` or `ZERO_CYCLE_TIME_PROCESS`) is emitted with measured accounting metrics.
   - **Finding-Specific Evidence Strength:** High ($\ge 30$), Moderate ($10-29$), Limited ($< 10$) based strictly on the finding's evaluated sample dimension ($M_\tau$ for transitions, recurrence case count, variant case count).
   - **Tukey 1.5x IQR Outlier Detection:** Applied to complete-case cycle times. If $\text{IQR} = 0.0\text{s}$, emits informative `ZERO_VARIANCE_CYCLE_TIME` finding rather than spurious outliers.
   - **Deterministic Sorting & IDs:** IDs generated via `slugify()`; findings stably sorted by severity (`HIGH` -> `MEDIUM` -> `LOW` -> `INFO`), category, and ID.
3. **API Contract (`POST /api/v1/problems/detect`):**
   - Added endpoint in `main.py` preserving all existing contracts and boundary validations (file size, extension, empty filename).
4. **Documentation of Limitations:** Explicitly documented that passing the 1% reconciliation check verifies arithmetic consistency only and does not prove active working time or non-overlapping transitions.

### Consequences & Verification
- 57/57 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`).
- Reconciliation check passes on all 4 development datasets with $< 0.0001\%$ numerical discrepancy.
- Rework loop detection verified on `rework.csv` (`Quality Inspection` in 253 cases).
- 18 rare variants verified on `messy.csv`.

---

## Decision Record 007: Phase 4 Semantic Correction & Signal Prominence Separation
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Process Analytics Engineer & Product Lead

### Context
Following review of Phase 4 (commit `8ae785d`), three semantic and classification alignments were required to adhere to the core principles of ProcessLens:
1. **Unsupported Bottleneck Classification:** Labeling elapsed-duration-share findings as `BOTTLENECK` constituted an unverified claim. Process logs record milestone timestamps, not active task execution versus queue time. A high share represents elapsed time concentration, not proven process constraint.
2. **Conflation of Signal Prominence and Evidence Strength:** Signal prominence (how large or concentrated a pattern is in data, e.g. 80% duration share or 33% recurrence) was previously combined with sample size thresholds (`m_tau >= 10`) under a "severity" label. Furthermore, labeling data patterns as "HIGH severity" falsely implied business impact or operational defect.
3. **Recurrence Terminology:** Metric keys such as `rework_case_count` and `rework_case_percentage` in finding metrics asserted operational "rework" rather than neutral activity recurrence.

### Decision
1. **Neutral Finding Category (`DURATION_CONCENTRATION`):** Replaced `BOTTLENECK` with `DURATION_CONCENTRATION` across schemas and domain service. `BOTTLENECK` is retained as an enum alias mapping to `DURATION_CONCENTRATION` for backward compatibility.
2. **Strict Separation of Signal Prominence and Evidence Strength:**
   - Introduced `SignalLevel` (`HIGH`, `MEDIUM`, `LOW`, `INFO`) reflecting pattern magnitude in observed data:
     - Duration share: $\ge 40\%$ (HIGH), $\ge 25\%$ (MEDIUM), $< 25\%$ (LOW).
     - Recurrence prevalence: $\ge 30\%$ (HIGH), $\ge 15\%$ (MEDIUM), $< 15\%$ (LOW).
     - Cycle-time outliers: $\ge 5\%$ (MEDIUM), $< 5\%$ (LOW).
   - Sample size checks (e.g. `m_tau >= 10`) are removed from signal level determination and reside exclusively in `evidence_strength` ($N \ge 30$ High, $10-29$ Moderate, $< 10$ Limited).
   - Schema field renamed to `signal_level`, with `severity` retained as an optional backward-compatible alias.
   - `DetectionSummary` exposes `high_signal_count`, `medium_signal_count`, etc., alongside `high_severity_count` backward-compatibility aliases.
3. **Neutral Recurrence Metric Keys:** Updated finding metrics dictionary to use `recurrence_case_count`, `recurrence_case_percentage`, and `recurrence_occurrences`. Retained `rework_case_count` aliases in the dictionary for transition compatibility.
4. **API Compatibility Implications:**
   - **Primary Schema Additions:** Clients reading `ProblemFinding` should consume `category == "DURATION_CONCENTRATION"`, `signal_level`, and `metrics["recurrence_case_count"]`.
   - **Deprecations with Zero-Breakage Aliases:** `category == "BOTTLENECK"` deserializes to `DURATION_CONCENTRATION`. `finding.severity` and `summary.high_severity_count` remain populated. Legacy consumers of `rework_case_count` in finding metrics continue to receive the key alongside `recurrence_case_count`.

### Consequences & Verification
- 59/59 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`).
- Orthogonality verified by `test_separation_of_signal_prominence_and_evidence_strength` (sample size $< 10$ with share $\ge 80\%$ yields `signal_level = HIGH` and `evidence_strength = LIMITED`).
- Neutral language verified across all findings (`test_neutral_terminology_and_no_unsupported_claims`).

---

## Decision Record 008: Phase 4 API Compatibility Audit, Deprecation Annotations & Serialization Verification
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Backend & Ingestion Engineer, Product Lead

### Context
Following the Phase 4 semantic correction (Decision Record 007, commit `0e41e81`), an API contract audit was conducted to verify serialization, OpenAPI schema emission, and backward compatibility for legacy clients while establishing canonical guidance for all new consumers.

Key compatibility questions audited:
1. Does `BOTTLENECK` serialize as its old string value `"BOTTLENECK"` or canonical `"DURATION_CONCENTRATION"`?
2. How does Python's `Enum` treat enum aliases versus distinct values in Pydantic v2 serialization and deserialization?
3. Are deprecated fields properly marked with `deprecated=True` in the generated OpenAPI 3.1 specification?
4. Do legacy incoming payloads (e.g. payloads with `category: "BOTTLENECK"`, `severity: "HIGH"`, or `rework_*` metric keys) validate without breaking?

### Audit Findings & Decisions
1. **Enum Representation & Serialization Behavior (`FindingCategory`):**
   - **Tested Behavior:** When defined as distinct enum members `DURATION_CONCENTRATION = "DURATION_CONCENTRATION"` and `BOTTLENECK = "BOTTLENECK"`, a finding explicitly created with `FindingCategory.BOTTLENECK` serializes strictly as `"BOTTLENECK"` in `model_dump_json()`. Live engine outputs generated by `detect_process_problems` strictly emit canonical `"DURATION_CONCENTRATION"`.
   - **Deserialization Safety:** Having `BOTTLENECK = "BOTTLENECK"` ensures `FindingCategory("BOTTLENECK")` or incoming JSON payloads with `"category": "BOTTLENECK"` succeed in Pydantic validation. (If defined as an alias `BOTTLENECK = "DURATION_CONCENTRATION"`, Python's `Enum` hides `"BOTTLENECK"` from valid values, causing `FindingCategory("BOTTLENECK")` to raise a `ValueError`.)
   - **Consumer Guidance:** `BOTTLENECK` is marked as deprecated in docstrings and schemas. All new consumers are instructed to consume and assert only `DURATION_CONCENTRATION`.
2. **OpenAPI Deprecation Metadata (`deprecated=True`):**
   - Configured `Field(..., deprecated=True)` on:
     - `ProblemFinding.severity`
     - `DetectionSummary.high_severity_count`, `medium_severity_count`, `low_severity_count`, `info_severity_count`
   - Verified that `app.openapi()` emits `"deprecated": true` directly into the generated OpenAPI 3.1 schema under `components.schemas.ProblemFinding.properties.severity` and `DetectionSummary.properties.*_severity_count`.
   - Pydantic v2 also emits runtime `DeprecationWarning` when accessing fields with `deprecated=True`.
3. **Neutral Recurrence vs Legacy `rework_*` Metrics:**
   - Canonical metrics in `ProblemFinding.metrics` are `recurrence_case_count`, `recurrence_case_percentage`, and `recurrence_occurrences`.
   - Legacy keys `rework_case_count`, `rework_case_percentage`, and `rework_occurrences` are dual-emitted for backward compatibility and marked as deprecated in schema descriptions. All new consumers must use `recurrence_*`.
4. **Preservation of Core Detection Logic:**
   - Zero changes made to detection thresholds, Tukey IQR outlier logic, accounting reconciliation tolerance (1.0%), or evidence strength thresholds.

### Consequences & Verification
- 63/63 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`).
- Added four targeted audit tests in `test_detection.py`:
  - `test_enum_values_and_legacy_compatibility`: Verifies enum string values, string conversion, and `SeverityLevel` alias.
  - `test_json_serialization_behavior_bottleneck_vs_duration_concentration`: Verifies that legacy instances serialize as `"BOTTLENECK"`, canonical instances serialize as `"DURATION_CONCENTRATION"`, and live engine outputs strictly emit canonical `"DURATION_CONCENTRATION"`.
  - `test_openapi_schema_generated_deprecation_metadata`: Verifies `deprecated=True` in generated OpenAPI JSON schema.
  - `test_backward_compatibility_incoming_payloads`: Verifies that payloads containing deprecated legacy fields deserialize cleanly without 422 errors.

---

## Decision Record 009: Phase 5 Deterministic Opportunity Detection, Evidence Traceability, and Operational Priority Scoring
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Opportunity & Economics Analyst (Lead), Product Lead

### Context
Phase 4 established deterministic problem detection, identifying operational patterns (`DURATION_CONCENTRATION`, `REPETITION`, `CYCLE_TIME_OUTLIER`, `PATH_VARIATION`, `DATA_QUALITY_LIMITATION`) without premature business-impact claims. Phase 5 requires converting these operational findings into structured, evidence-backed Opportunity Candidates while strictly adhering to the ProcessLens North Star:
1. **Derive from Verified Findings:** Every opportunity candidate must trace directly to at least one valid Phase 4 `ProblemFinding` ID.
2. **Explicit Distinction of Evidence Layers:** Distinguish observed facts, investigation hypotheses, and candidate interventions in the response.
3. **No Speculative Economics:** Event logs provide operational timestamps and activity names, not wages, licensing costs, or implementation hours. Financial ROI belongs to Phase 7.
4. **Transparent Provisional Priority Scoring:** Operational priority score $P = (S_{\text{coverage}} + S_{\text{concentration}}) \times W_{\text{evidence}}$ ($0$ to $100$), with a strict guardrail: `LIMITED` evidence ($<10$ cases) always assigns `TIER_4_EXPLORATORY` regardless of score.
5. **Data Quality Awareness:** When transition duration reconciliation fails, duration-share opportunities are suppressed, and a `DATA_INSTRUMENTATION` opportunity is generated instead.
6. **No Domain Hardcoding:** Zero hardcoded activity names or manufacturing rules. Opportunities emerge entirely from data-driven signals.

### Decisions
1. **Pydantic Schemas (`schemas/opportunity.py`):**
   - Enums: `OpportunityArchetype` (`DELAY_COMPRESSION`, `RECURRENCE_REDUCTION`, `TAIL_VARIANCE_MITIGATION`, `PATH_STANDARDIZATION`, `DATA_INSTRUMENTATION`), `InterventionCategory` (`PROCESS_SIMPLIFICATION`, `TASK_AUTOMATION_CANDIDATE`, `QUALITY_GATING`, `EXCEPTION_MANAGEMENT`, `DATA_INSTRUMENTATION`), and `PriorityTier` (`TIER_1_HIGH`, `TIER_2_MEDIUM`, `TIER_3_LOW`, `TIER_4_EXPLORATORY`).
   - Distinct metric percentage fields: `duration_share_percentage`, `recurrence_case_percentage`, `outlier_case_percentage`, and `variant_case_percentage` replace ambiguous generic shares.
   - Distinct evidence fields: `observed_facts`, `investigation_hypotheses`, `candidate_actions`, `candidate_interventions`, `rationale`, and `limitations`.
   - Models: `ScoreBreakdown`, `OpportunityCandidate`, `OpportunitySummary`, `OpportunityDetectionResult`.
2. **Domain Service (`services/opportunity.py`):**
   - Implemented `detect_improvement_opportunities(reconstruction, analytics, detection)` consuming typed outputs from Phases 2, 3, and 4.
   - Handled deduplication: multiple findings for the same target entity/archetype merge into a single candidate, combining source finding IDs while preserving the highest priority score and metrics.
   - Deterministic sorting: sorted by `(-operational_priority_score, -affected_case_count, target_entity, id)`.
3. **API Endpoint (`POST /api/v1/opportunities/detect`):**
   - Preserves all existing endpoint contracts (`/health`, `/ingestion/upload`, `/process/reconstruct`, `/analytics/process`, `/problems/detect`).
   - Validates CSV file extension, empty filename, and file size limit.
   - Executes end-to-end pipeline: Reconstruct $\to$ Analytics $\to$ Detect Problems $\to$ Detect Opportunities.
4. **Testing (`tests/test_opportunity.py`):**
   - 15 dedicated unit and integration tests covering priority score formulas, boundary conditions, score traceability, finding ID validation, deduplication, reconciliation suppression, missing metrics, and all 4 development datasets.

### Consequences & Verification
- 78/78 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`, `test_opportunity.py`).
- 0 regressions in existing Phase 1–4 contracts.
- End-to-end opportunity detection verified on all synthetic datasets (`quickstart.csv`, `clean.csv`, `rework.csv`, `messy.csv`).

---

## Decision Record 010: Phase 5 Semantic Validation & Neutral Intervention Classification
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Opportunity & Economics Analyst, Product Lead

### Context
Following initial Phase 5 opportunity implementation (commit `3687e66`), a semantic review identified two unwarranted inferences requiring immediate alignment with ProcessLens core principles:
1. **Premature Assignment of `TASK_AUTOMATION_CANDIDATE`:** Assigning task automation based solely on elapsed duration concentration was an unverified leap. Milestone logs capture elapsed chronological time; they do not reveal whether delay stems from manual effort, physical processing (e.g. curing, cooling), external suppliers, batching, or queueing.
2. **Clarification of Operational Priority Score Semantics:** The `operational_priority_score` measures and ranks data patterns for investigation. It does not establish that a pattern represents avoidable waste, nor does it imply business value or automation readiness.
3. **Mandatory Steps with High Duration:** A mandatory, highly valuable process step (e.g. `Fabrication -> Heat Treatment`) may accumulate substantial elapsed duration and rank highly in data coverage and concentration without being unnecessary, wasteful, or an automation candidate.

### Decisions
1. **Neutral Intervention Classification (`UNDETERMINED_INVESTIGATION`):**
   - Added `UNDETERMINED_INVESTIGATION` to `InterventionCategory`.
   - Replaced automatic assignment of `TASK_AUTOMATION_CANDIDATE` in `DELAY_COMPRESSION` and `RECURRENCE_REDUCTION` rules with `UNDETERMINED_INVESTIGATION`.
   - `TASK_AUTOMATION_CANDIDATE` remains a valid enum member for backward compatibility and future phases where automation suitability criteria are explicitly evaluated.
2. **Schema & Documentation Clarifications:**
   - Updated `ScoreBreakdown` and `OpportunityCandidate.operational_priority_score` docstrings and descriptions to state explicitly:
     *"Deterministic score (0.0 to 100.0) ranking measured operational patterns for investigation. It does NOT establish avoidability, business value, savings, ROI, or intervention readiness."*
3. **Neutral Phrasing & Strict Evidence Separation:**
   - Formulated balanced `candidate_actions` and `investigation_hypotheses` prompting process owners to investigate active work vs. idle waiting vs. physical constraints.
   - Preserved explicit limitations: high duration concentration does not prove that a step is unnecessary, avoidable, or suitable for automation. Implementation readiness is explicitly separated (deferred to Phase 6).
4. **Mandatory Transition Verification Test:**
   - Added `test_mandatory_transition_high_duration_ranks_high_without_automation_claim`: verifies that a mandatory physical step (`Fabrication -> Heat Treatment`) with 45% duration share ranks highly ($71.25$, `TIER_1_HIGH`), receives `UNDETERMINED_INVESTIGATION` (never `TASK_AUTOMATION_CANDIDATE`), and contains zero claims of waste, avoidability, or justified automation.
   - Exact hand-calculated arithmetic: Coverage = $50.0 \times (10 / 10) = 50.0$ points; Concentration = $50.0 \times (45.0 / 50.0) = 45.0$ points; Raw Score = $50.0 + 45.0 = 95.0$; Evidence Weight for $N=10$ cases (MODERATE) = $0.75$; Final Operational Priority Score = $\text{round}(95.0 \times 0.75, 2) = 71.25 \rightarrow \text{TIER\_1\_HIGH}$.

### Consequences & Verification
- 79/79 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`, `test_opportunity.py`).
- Zero regressions in existing API contracts.

---

## Decision Record 011: Phase 6 Automation Readiness Assessment Architecture and Categorical Gating Model
* **Date:** 2026-10-10
* **Status:** Implemented & Verified
* **Owner:** Opportunity & Economics Analyst (Lead), Product Lead, Backend Engineer

### Context
Phase 5 established deterministic opportunity detection where `operational_priority_score` ranks measured operational patterns solely for investigation. Operational delay and recurrence alone cannot determine whether an opportunity can or should be automated:
1. **Separation of Priority and Feasibility:** A mandatory step with 45% duration concentration (e.g. physical heat treatment or complex contract negotiation) may rank in Tier 1 for investigation without being suitable for software automation. Conversely, a routine 30-second data re-entry task may be 100% automation-ready.
2. **Limits of Event Log Visibility:** Event logs record timestamps and activity sequences. They cannot observe data payload structures (e.g. paper vs. API), target system architectures (e.g. REST API vs. Citrix), business rule codification (e.g. deterministic IF-THEN vs. subjective discretion), or statutory mandates.
3. **Flaws of Arbitrary Numeric Averaging:** A naive weighted average (e.g. $0.25 \times S_1 + \dots$) dangerously masks fatal blockers (e.g. high volume and digital inputs compensating for a life-safety hazard or illegal automated execution).
4. **Distinction Between Unknown and Prohibited:** Domain intake may be missing (`UNKNOWN`), empirical data may have small sample size (`INSUFFICIENT_EVIDENCE`), or an approach may face technical prerequisites (`PREREQUISITE_REQUIRED`) versus an established hard prohibition (`PROHIBITIVE_BARRIER`).

### Decisions
1. **Categorical Non-Compensatory Gating Model:**
   - Removed composite numeric readiness indexes.
   - Defined four overall readiness tiers evaluated in strict non-compensatory precedence:
     1. `PROHIBITED_OR_BLOCKED`: Established hard prohibition on the assessed approach.
     2. `INSUFFICIENT_CRITICAL_EVIDENCE`: Critical domain dimensions remain `UNKNOWN` or event-log sample is `LIMITED` ($N < 10$). Never silently impute favorable values.
     3. `PREREQUISITES_REQUIRED`: Feasible in principle, but technical/procedural prerequisites or human-in-the-loop controls are required.
     4. `READY_FOR_SPECIFICATION`: All six dimensions favorable.
2. **No Sample-Size Discounting on Domain Inputs:**
   - Domain assessments evaluate system interface availability, rule determinism, and data formats; they are not discounted by event-log case counts.
3. **Refined Barrier Semantics:**
   - `PROHIBITIVE_BARRIER` is strictly reserved for documented hard prohibitions (`PROHIBITED_BY_LAW`, `PROHIBITED_ACCESS`).
   - Work that is safety-critical, judgment-intensive, or uses restricted interfaces evaluates to `PREREQUISITE_REQUIRED` (e.g. human-in-the-loop review, desktop automation, Document AI), not categorical bans.
4. **Provisional Empirical Heuristics:**
   - Event-log volume and path consistency are documented as observed process characteristics, not proof of task automation suitability or business-rule stability.
5. **Contradictory Evidence Detection:**
   - When domain claims assert unattended execution but event logs show recurrence $\ge 20\%$ or cycle outliers $\ge 10\%$, a structured `ReadinessDiscrepancy` is emitted with HTTP 200, prompting review of intentional multi-pass review vs. defect rework. Legitimate recurrence is never assumed to be an operational defect.
6. **Keying by Stable `opportunity_id` & Validation:**
   - Domain assessments are submitted per opportunity keyed by stable `opportunity_id`.
   - Unknown opportunity IDs are rejected with HTTP 400 Bad Request listing valid IDs from the uploaded CSV.
   - Partial domain submissions are supported: submitted opportunities are evaluated with domain data; unassessed opportunities evaluate cleanly to `INSUFFICIENT_CRITICAL_EVIDENCE`.
7. **Clean Pipeline Service Reuse:**
   - The endpoint `POST /api/v1/readiness/assess` reuses existing ingestion, reconstruction, analytics, and problem/opportunity detection services without duplicating domain logic.
8. **Specification Readiness Boundary Guardrail:**
   - Explicitly disclaimed in documentation and response schemas that `READY_FOR_SPECIFICATION` signifies readiness for detailed solution design and stakeholder specification; it does **not** authorize production deployment.

### Consequences & Verification
- 95/95 backend tests passing across all test suites (`test_health.py`, `test_ingestion.py`, `test_reconstruction.py`, `test_analytics.py`, `test_detection.py`, `test_opportunity.py`, `test_readiness.py`).
- Added 16 dedicated readiness tests covering default unknown baseline, hard prohibitions, human-in-the-loop prerequisites, specification readiness, contradictory evidence, legitimate recurrence, invalid ID validation, malformed JSON, and regression across all four synthetic datasets.
- Zero regressions in Phases 1–5 contracts.

---

## Decision Record 012: Phase 7 Business Impact & Financial Economics Analysis Engine and Strategic Synthesis Architecture
* **Date:** 2026-10-11
* **Status:** Implemented & Verified
* **Owner:** Opportunity & Economics Analyst (Lead), Product Lead, QA Engineer

### Context
ProcessLens Phases 1–6 established deterministic process analytics, problem detection, opportunity prioritization (`operational_priority_score`), and automation readiness gating (`overall_readiness_tier`). Phase 7 introduces deterministic business-impact and financial-economics analysis to resolve the core product question: *What should this business fix or automate first, why, and what value could it create?*

To protect the product from unwarranted financial claims and ensure architectural consistency:
1. **Tri-Partite Independence:** Operational priority (observed pattern concentration), automation readiness (technical/governance feasibility), and financial economics (payback, capacity return) must remain independent dimensions.
2. **Epistemological Rigor:** Distinguish observed operational metrics (`MEASURED_IN_LOG`), domain intake hypotheses (`USER_PROVIDED`), and scenario-based extrapolations (`CALCULATED_ESTIMATE`). Chronological milestone duration must never be equated to active labor without explicit domain intake.
3. **Capacity Valuation vs. Realized Cash:** Liberated labor hours represent theoretical capacity reallocation; cash-flow ROI requires verified budgetary/payroll evidence and remains unavailable (`cash_roi_available = False`).
4. **Unrounded Downstream Precision:** Scaling ratios ($R_{\text{raw}}$) and intermediate estimates must preserve raw IEEE 754 precision; integer rounding exists solely at the presentation boundary via commercial half-up rounding ($\lfloor x + 0.5 \rfloor$).
5. **Annualization Hierarchy:** Precedence must govern zero eligible cases, volume overrides, short windows (<30 days), and calendar projections without compounding errors into payback or ROI.
6. **Authorization Guardrail:** No economic tier or readiness state authorizes production deployment. The strategic outcome `SPECIFY_AUTOMATION_SOLUTION` authorizes detailed functional design and requirements specification only.

### Decisions
1. **Pydantic Schemas (`backend/app/schemas/economics.py`):**
   - Implemented models: `OpportunityEconomicInput`, `ObservationWindowInfo`, `LaborEffortMetrics`, `CapacityValuationMetrics`, `CashFlowMetrics`, `StrategicSynthesis`, `OpportunityEconomicsResult`, `EconomicsSummary`, `EconomicsEvaluationResponse`.
   - Strictly enforced finite-number validation on all request fields (`allow_inf_nan=False`, rejecting `NaN`, `+Infinity`, `-Infinity` with HTTP 422).
2. **Domain Service (`backend/app/services/economics.py`):**
   - Implemented `extract_observation_window()` with strict 5-branch precedence: Root Gate ($N_{\text{sample}} = 0 \to$ Branch 5 degenerate), Override ($N_{\text{sample}} \ge 1 \to$ Branch 3 override), Missing Window (Branch 4), Zero-Duration Window (Branch 5), Short Window (<30 days $\to$ Branch 1 sample basis), Calendar Extrapolation ($\ge 30$ days $\to$ Branch 2).
   - Sample vs. Annual Separation: In Branch 1 (<30 days), $R_{\text{raw}} = \text{None}$, sample metrics are reported, and annual estimates/payback/ROI evaluate to `None` (`INSUFFICIENT_ECONOMIC_INPUTS`).
   - Archetype-specific labor formulas:
     - `DELAY_COMPRESSION`: Scales aggregate sample duration via $R_{\text{raw}}$ without $N \times N$ case-count multiplication.
     - `PATH_STANDARDIZATION`: Scales affected cases while preserving distinct variant count ($V_{\text{rare}}$) unscaled.
     - `RECURRENCE_REDUCTION`: Scales re-execution occurrences via $R_{\text{raw}}$.
     - `DATA_INSTRUMENTATION`: Non-labor archetype; suppresses labor/valuation and evaluates directly to `RESOLVE_DATA_INSTRUMENTATION`.
   - Implemented `classify_economic_tier()` with full upfront validation, contradiction detection ($\epsilon = 10^{-3}$), zero-cost handling ($C_{\text{impl}} = 0 \to \text{payback} = 0.0, \text{ROI} = \text{None}, \text{COMPELLING_RETURN}$), and restored 36-month moderate return boundary.
   - Enforced missing cost safeguards: `annual_recurring_cost = None` preserves gross capacity scenario while setting net benefit, payback, and ROI to `None` (`INSUFFICIENT_ECONOMIC_INPUTS`).
3. **Immutable 64-Cell Strategic Synthesis Matrix (`SYNTHESIS_DECISION_MAP`):**
   - Keys typed as `Tuple[PriorityTier, OverallReadinessTier, EconomicTier]`.
   - All 16 combinations with `PROHIBITED_OR_BLOCKED` evaluate strictly to blocked outcomes (`BLOCKED_HIGH_POTENTIAL`, `BLOCKED_LOW_PRIORITY`, `BLOCKED_UNKNOWN_ECONOMICS`, `BLOCKED_AND_UNECONOMICAL`).
   - High/Medium priority with `READY_FOR_SPECIFICATION` and `COMPELLING_RETURN` evaluates to `SPECIFY_AUTOMATION_SOLUTION`.
4. **API Endpoint (`POST /api/v1/economics/evaluate` in `backend/app/main.py`):**
   - Enforces 10 MB file size limit and sequential pipeline execution (Reconstruction $\to$ Analytics $\to$ Problems $\to$ Opportunities $\to$ Readiness $\to$ Economics).
5. **Comprehensive Test Suite (`backend/tests/test_economics.py`):**
   - 45 automated unit and integration tests across 10 groups covering canonical derivations, finite validation, classifier contradictions, missing vs zero costs, half-up rounding, archetype scaling, 5 annualization branches, DATA_INSTRUMENTATION bypass, 64-cell synthesis matrix, and all 4 development datasets.

### Consequences & Verification
- 141/141 backend tests passing across all 8 test suites (`test_health`, `test_ingestion`, `test_reconstruction`, `test_analytics`, `test_detection`, `test_opportunity`, `test_readiness`, `test_economics`).
- 0 regressions in existing Phase 1–6 contracts.
- Verified deterministic economics and synthesis across `quickstart.csv`, `clean.csv`, `rework.csv`, and `messy.csv`.

---

## Decision Record 013: Phase 8 Opportunity Prioritisation & Portfolio Action Roadmap Architecture
* **Date:** 2026-10-11
* **Status:** Implemented & Verified
* **Owner:** Senior Backend Engineer, Process Mining Specialist, QA Engineer

### Context
ProcessLens Phases 1–7 established deterministic process reconstruction, analytics, problem detection, opportunity identification, readiness gating, and financial economics synthesis. Phase 8 completes the decision-support engine by implementing the portfolio prioritisation and ranking system to answer the central product question: *What should this business fix or automate first, why, and what value could it create?*

To protect the roadmap from architectural drift, arbitrary scoring, and speculative ranking:
1. **Cohort-First Precedence:** Portfolio sequencing must partition candidates into mutually exclusive, exhaustive strategic cohorts before any within-cohort score evaluation. Precedence dictates portfolio tiering, not arbitrary point scoring.
2. **Deterministic Factor Scoring:** Six transparent factors (Impact, Readiness, Payback, Effort, Risk, Confidence) evaluate candidates on a 0–100 scale using bounded piecewise-linear schedules.
3. **Transparent Evidence Provenance:** Impact distinguishes scenario-based capacity extrapolations (`CALCULATED_CAPACITY_SCENARIO`) from unmonetized operational concentration (`OPERATIONAL_CONCENTRATION_BASELINE`). Capacity scenario values across distinct opportunities may overlap and must never be represented as additive portfolio savings.
4. **Dynamic Weight Redistribution:** Missing factors (e.g. unassessed economics or missing cost inputs) do not inject fabricated neutral midpoint scores. Available weights are dynamically rescaled to maintain the 100% total weight invariant. If no eligible factors exist, candidates evaluate strictly to `UNSCORED` with `composite_priority_score = None`.
5. **Exact Numeric Precision:** Intermediate factor values and composite scores are calculated using full IEEE 754 precision. Only the final composite score is quantized to 4 decimal places using `ROUND_HALF_EVEN` and normalized to positive zero (`math.copysign(1.0, val) == 1.0`). Score ties are determined solely by quantized score-bucket equality, followed by deterministic secondary tie-breakers.

### Decisions
1. **Pydantic Schemas (`backend/app/schemas/prioritisation.py`):**
   - Enums: `PortfolioCohort` (8 cohorts: `FOUNDATIONAL_DATA_QUALITY`, `IMMEDIATE_AUTOMATION_SPECIFICATION`, `GUARDRAILED_AUTOMATION`, `PROCESS_RESTRUCTURING`, `BUSINESS_CASE_VALIDATION`, `FEASIBILITY_INVESTIGATION`, `REVISE_OR_DEFERRED`, `BLOCKED_BY_BARRIERS`), `ImpactBasis`, `ScoringStatus`, `ConstraintStatus`.
   - Models: `PrioritisationWeights` (validating non-negative, finite weights summing to 100.0), `FactorBreakdown`, `PrioritisedOpportunity`, `PrioritisationSummary`, `PrioritisationResponse`.
2. **Domain Service (`backend/app/services/prioritisation.py`):**
   - Implemented `OUTCOME_TO_COHORT_MAP` mapping all 15 Phase 7 `StrategicDecisionOutcome` enum values exactly once to the 8 portfolio cohorts.
   - Implemented `evaluate_factors()` with deterministic scoring, dynamic weight redistribution, and explicit unscored state handling.
   - Implemented `make_sort_key()` with explicit `None` handling, correct zero values, and deterministic tie-breaking: `(cohort_precedence, scored_placement, -quantized_score, -net_annual_capacity_benefit, payback_period_months, -operational_priority_score, -sample_completed_cases, opportunity_id)`.
   - Implemented evidence-conditional `generate_primary_strength()` and `generate_primary_constraint()`, adhering strictly to observed facts and inter-cohort policies without inventing causal explanations.
   - Non-additive cumulative capacity benefit tracking with mandatory disclaimer.
3. **API Endpoint (`POST /api/v1/prioritisation/rank` in `backend/app/main.py`):**
   - Mounted at `/api/v1/prioritisation/rank`, accepting CSV uploads up to the 10 MB limit alongside optional JSON strings for prioritisation weights, economic inputs, and domain assessments.
   - Sequentially executes the full pipeline: Reconstruction $\to$ Analytics $\to$ Problems $\to$ Opportunities $\to$ Readiness $\to$ Economics $\to$ Prioritisation.
4. **Comprehensive Test Suite (`backend/tests/test_prioritisation.py`):**
   - 34 automated unit and integration tests across 9 groups covering:
     - Group 1: Decimal halfway rounding, boundary jitter, negative-zero normalization.
     - Group 2: Exhaustive mapping of all 15 Phase 7 outcomes and all 8 cohorts.
     - Group 3: Default and custom weights, sum-to-100 validation, rejection of non-finite/negative weights.
     - Group 4: End-to-end pipeline ranking on clean dataset with and without economic inputs.
     - Group 5: `DATA_INSTRUMENTATION` precedence (Cohort 1) and Cohort 1 $\to$ Cohort 2 boundary constraint.
     - Group 6: Full-precision accumulator divergence and neutral constraint fallbacks.
     - Group 7: Dynamic weight redistribution, deterministic score scaling (0-100), and zero-available-weight fallback to `UNSCORED`.
     - Group 8: Pipeline regressions on all four synthetic datasets (`quickstart.csv`, `clean.csv`, `rework.csv`, `messy.csv`).
     - Group 9: API boundary validation, unsupported file formats, malformed JSON payloads, 10 MB upload limit, empty filenames, unknown/duplicate opportunity IDs in economic and domain inputs.

### Consequences & Verification
- 175/175 backend tests passing across all test suites with 0 failures and 0 regressions.
- All Phase 1–7 contracts preserved.
- Verified deterministic ranking and roadmap generation.

---

## Decision Record 014: Phase 9 Evidence Audit, Traceability & Epistemic Ledger Architecture
* **Date:** 2026-10-11
* **Status:** Implemented & Verified
* **Owner:** Lead Process Mining Architect, Senior Backend Engineer, QA Engineer

### Context
ProcessLens Phases 1–8 established the complete deterministic pipeline from CSV ingestion through operational metrics, opportunity identification, readiness gating, financial economics, and portfolio prioritisation. However, for executive decision support to be trustworthy and defensible, every recommendation must be inspectable and auditable back to ground-truth operational events. Stakeholders must be able to trace *why* an opportunity was ranked where it was, inspect genuine source event rows, verify calculation derivations, and distinguish empirical facts from assumptions, estimates, hypotheses, and strategic decisions.

### Decisions
1. **Epistemic Classification Model (`EpistemicType` in `backend/app/schemas/evidence.py`):**
   - Strictly partitioned into five immutable categories:
     - `FACT`: Directly observed from ingested event logs (e.g., event counts, timestamps, variant frequencies, duration percentiles).
     - `ASSUMPTION`: Externally provided or defaulted domain parameters (e.g., hourly labor rates, implementation cost, recurring cost, baseline prioritisation weights).
     - `HYPOTHESIS`: Process improvement conjectures (e.g., opportunity archetype potential, estimated addressable percentage, time savings target).
     - `ESTIMATE`: Monetized and extrapolated projections computed from facts + assumptions (e.g., annual capacity hours released, gross/net capacity benefit, payback period).
     - `DECISION`: Strategic policy gates and portfolio tiering (e.g., readiness outcome, feasibility status, portfolio cohort placement, ranking position).
   - Enforced rule: No score, financial calculation, or policy outcome may be classified as `FACT`.
2. **Deterministic Source Anchoring Contract (`EventRowAnchor`, `CaseTraceExemplar`):**
   - Preserved canonical `row_index`: 1-based data-row index excluding the CSV header row.
   - Defined physical `csv_line_number = row_index + 1` corresponding 1:1 with the physical line on disk.
   - Exemplars are constrained to at most 3 cases per opportunity, selected via deterministic tie-breaking (e.g. descending transition duration, repetition count, cycle time) with secondary sort on `case_id`.
   - Never fabricates or synthesizes exemplars; if no relevant exemplar events exist (e.g., `DATA_INSTRUMENTATION` on clean data), an empty exemplar list is returned with an explicit limitation note.
3. **Archetype Exemplar Extraction (`backend/app/services/evidence.py`):**
   - `DELAY_COMPRESSION`: Exemplars anchor source rows performing the slowest transition between source and target activities.
   - `RECURRENCE_REDUCTION`: Exemplars anchor source rows executing duplicate/repeated instances of the target activity.
   - `TAIL_VARIANCE_MITIGATION`: Exemplars anchor full trace start and end rows for Tukey upper-fence cycle time outlier cases.
   - `PATH_STANDARDIZATION`: Exemplars anchor trace start and end rows for rare process variants (<2% frequency).
   - `DATA_INSTRUMENTATION`: Exemplars anchor raw data rows rejected by reconstruction validation; returns empty exemplar list when dataset has zero exclusions.
4. **Transparent Metric Derivations (`MetricDerivationAudit`):**
   - Audits actual formula inputs, intermediate quantities, calculation expressions, rounding conventions, and provenance for:
     - `OPS_SCORE_V1`: Operational priority score piecewise linear components.
     - `ANNUALIZATION_V1`: Observation window duration and extrapolation ratio.
     - `LABOR_EFFORT_V1`: Continuous delay hours vs discrete rework hours released.
     - `CAPACITY_VAL_V1`: Gross and net capacity value calculations and caveats.
     - `PAYBACK_PERIOD_V1`: Payback period in months with zero/negative benefit branching.
     - `WEIGHT_REDIST_V1`: Dynamic redistribution of weights for unscored factors.
     - `COMPOSITE_SCORE_V1`: Weighted average composite score scaled to 0–100.
5. **Cryptographic Manifest & Verification (`EvidenceAuditManifest`):**
   - Computes SHA-256 fingerprint of the uploaded CSV content.
   - Records file size in bytes, total rows, valid rows, excluded rows, cases count, and variants count.
   - Labels reconciliation status (`PERFECT` or `EXCLUSIONS_PRESENT`).
   - Tags active formula versions, effective factor weights, and explicitly declares `is_persisted_snapshot=False` to document in-memory execution.
6. **API Endpoint (`POST /api/v1/evidence/audit` in `backend/app/main.py`):**
   - Accepts multipart file upload (10 MB limit) with optional JSON overrides (`prioritisation_weights`, `economic_inputs`, `domain_assessments`, and `opportunity_id` filter).
   - Returns full dossier collection or exactly one filtered dossier; returns HTTP 400 for unknown opportunity ID or malformed payloads.
   - Fully backward-compatible; does not modify Phase 1–8 response models or route handlers.
7. **Comprehensive Test Suite (`backend/tests/test_evidence.py`):**
   - 28 unit and integration tests across 7 groups verifying:
     - Group 1: Source-row and CSV line number 1-based alignment with physical file lines.
     - Group 2: Exemplar extraction and relevance for all 5 archetypes, max-3 limits, deterministic tie-breaking, and empty exemplar handling.
     - Group 3: Derivation audits for operational scores, composite scores, and monetized economics.
     - Group 4: Strict epistemic ledger categorization and category boundaries.
     - Group 5: Full pipeline regressions across all 4 synthetic datasets (`quickstart.csv`, `clean.csv`, `rework.csv`, `messy.csv`).
     - Group 6: Exact opportunity ID filtering (single dossier match) and HTTP 400 for unknown IDs.
     - Group 7: File size limits, extension validation, empty filename rejection, SHA-256 digest integrity, manifest fields, malformed JSON rejection, and backward compatibility.

### Consequences & Verification
- 203/203 backend tests passing across all test suites (28 dedicated evidence tests + 175 baseline tests) with 0 failures and 0 regressions.
- Complete deterministic, auditable evidence trail established without persistence, external databases, or LLMs.
