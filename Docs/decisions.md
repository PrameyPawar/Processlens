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
