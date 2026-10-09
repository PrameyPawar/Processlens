# ProcessLens — Prerequisites & Feature Scope Control

## 1. Purpose

This document defines what must exist before ProcessLens development begins and, more importantly, what the MVP **will and will not contain**.

The purpose is to prevent feature creep and keep development focused on proving the core ProcessLens value proposition:

> **Take operational process data, identify where time and effort are being lost, quantify the business impact, and tell the user what should be improved or automated first.**

The MVP is not intended to be a complete enterprise process-mining, RPA, ERP, or autonomous-agent platform.

---

# 2. Scope-Control Principle

Every proposed feature must pass this question:

> **Does this feature materially improve ProcessLens's ability to identify, quantify, prioritise, and explain improvement or automation opportunities?**

If the answer is **no**, it does not belong in the MVP.

A feature may be:
- **MVP**
- **Post-MVP**
- **Future**
- **Rejected**

No feature should enter the MVP simply because it is technically interesting.

---

# 3. Product North Star

The MVP must answer one question exceptionally well:

> **What should this business fix or automate first, why, and what value could it create?**

The core product loop is:

**Discover → Quantify → Prioritise → Act**

And the technical value chain is:

**Operational Data → Evidence → Economics → Decision**

---

# 4. Prerequisites

## 4.1 Product Prerequisites

Before implementation, the following must be defined.

### Required

- [ ] Clear MVP problem statement
- [ ] Clear target user
- [ ] Initial industry/workflow hypothesis
- [ ] Defined input data format
- [ ] Defined required event-log fields
- [ ] Defined core analytical metrics
- [ ] Defined opportunity model
- [ ] Defined automation-readiness model
- [ ] Defined business-impact model
- [ ] Defined prioritisation model
- [ ] Defined evidence model
- [ ] Defined MVP success criteria

### Current working product assumption

ProcessLens initially focuses on operational workflows where activities can be represented as event sequences and where repetitive/manual work may create measurable inefficiency.

The exact industry and workflow remain hypotheses until validated with real-world users/data.

---

# 5. Data Prerequisites

The MVP should not attempt to solve every possible data format.

## 5.1 Minimum Event-Log Structure

The preferred input should contain at least:

| Field | Required | Purpose |
|---|---:|---|
| Case ID | Yes | Identifies an individual process instance |
| Activity | Yes | Identifies what happened |
| Timestamp | Yes | Determines event order and timing |
| Resource / Owner | Optional | Enables resource-level analysis |
| Additional business fields | Optional | Enables richer impact analysis |

Example:

```text
case_id,activity,timestamp,resource
1001,Order Received,2026-01-05 09:00,A
1001,Inventory Check,2026-01-05 09:15,B
1001,Production Planning,2026-01-05 11:00,C
1001,Production,2026-01-06 09:00,D
1001,Quality Inspection,2026-01-06 15:00,E
1001,Dispatch,2026-01-07 10:00,F
```

## 5.2 Data Quality Requirements

The MVP must handle:

- Missing required columns
- Missing timestamps
- Invalid timestamps
- Duplicate events
- Unordered events
- Missing case IDs
- Missing activity names
- Empty files
- Unsupported file formats

The system should report problems rather than silently producing misleading results.

---

# 6. Technical Prerequisites

## 6.1 Development Environment

Required:

- Git
- GitHub repository
- Local development environment
- Node.js / chosen frontend runtime
- Python / chosen analytics runtime
- Package manager
- Environment-variable management
- API development environment

## 6.2 Application Architecture

Minimum logical separation:

```text
Frontend
    ↓
Backend API
    ↓
Analytics / Process Engine
    ↓
Data Storage
```

The AI layer should sit above the deterministic analytics layer:

```text
Operational Data
      ↓
Deterministic Analytics
      ↓
Verified Results
      ↓
Evidence Layer
      ↓
LLM
      ↓
Explanation / Recommendation
```

---

# 7. MVP Feature Set

The MVP feature set is intentionally limited.

## Feature Group A — Data Upload

### MVP

- CSV upload
- Excel upload
- File size/type validation
- Dataset preview
- Schema detection
- Column mapping
- Required-field validation

### Not MVP

- ERP integrations
- SAP integration
- Tally integration
- Direct database connectors
- Real-time streaming
- Automated API ingestion
- Email ingestion
- WhatsApp ingestion

These may become future integrations.

---

# 8. Feature Group B — Data Quality

### MVP

- Missing-value detection
- Invalid timestamp detection
- Missing case/activity detection
- Duplicate event detection
- Basic data-quality score/report
- User-visible validation errors

### Not MVP

- Automated data cleansing pipelines
- Master-data management
- Advanced anomaly correction
- Automated schema learning across hundreds of systems

---

# 9. Feature Group C — Process Reconstruction

### MVP

- Case reconstruction
- Activity sequencing
- Timestamp ordering
- Process variants
- Basic process graph
- Case-level event history

### Not MVP

- Object-centric process mining
- Multi-process correlation
- Complex event-stream processing
- Enterprise process repository
- Full process conformance suite

---

# 10. Feature Group D — Process Analytics

### MVP Metrics

- Cycle time
- Waiting time
- Processing time
- Activity frequency
- Throughput
- Rework rate
- Variant frequency

### Optional MVP Metric

- Basic resource-level analysis when resource data exists

### Not MVP

- Advanced statistical process control
- Predictive process simulation
- Digital twins
- Complex forecasting
- Enterprise benchmarking

---

# 11. Feature Group E — Bottleneck Detection

### MVP

Identify and rank activities/transitions using measurable signals such as:

- Waiting time
- Processing time
- Frequency
- Rework
- Variation
- Volume

### Required output

Each bottleneck should contain:

```text
Bottleneck
├── Activity
├── Metric
├── Observed Value
├── Impact
├── Supporting Evidence
└── Confidence
```

### Not MVP

- Fully autonomous root-cause investigation across every business system
- Predictive bottleneck forecasting
- Autonomous process intervention

---

# 12. Feature Group F — Opportunity Detection

This is one of the most important MVP components.

### MVP

Convert analytical findings into structured opportunities based on:

- High manual effort
- High frequency
- Repetitive work
- Rule-based work
- High waiting/time impact
- High business impact
- Potential automation suitability

### Opportunity object

```text
Opportunity
├── Name
├── Process / Activity
├── Problem
├── Evidence
├── Frequency
├── Effort
├── Potential Impact
└── Opportunity Type
```

### Opportunity types

Initially keep this simple:

1. Process Improvement
2. Automation Candidate

Do not create dozens of opportunity categories in the MVP.

---

# 13. Feature Group G — Automation Readiness

### MVP

Generate an interpretable score from factors such as:

- Repetitiveness
- Rule-based nature
- Digital inputs
- Volume
- Exception rate
- Human judgment
- Risk

### Output

```text
Automation Readiness
├── Score
├── Rating
├── Positive Factors
├── Negative Factors
└── Explanation
```

### Important constraint

The score must be deterministic or rule-based in the MVP.

Do not allow an LLM to arbitrarily decide that an activity is "90% automatable."

---

# 14. Feature Group H — Business Impact & ROI

### MVP

Support transparent estimation of:

- Manual hours
- Labour cost
- Potential annual savings
- Implementation effort
- Estimated implementation cost
- Payback period

### Assumption handling

Every estimate should identify its source:

```text
Measured
Calculated
User Input
Assumption
Estimated
```

### Example

```text
Annual Manual Hours
        ↓
Estimated Labour Cost
        ↓
Potential Savings
        ↓
Implementation Cost
        ↓
Payback Period
```

### Not MVP

- Automated accounting integration
- Live financial systems
- Complex corporate financial modelling
- Tax calculations
- Full enterprise ROI modelling

---

# 15. Feature Group I — Opportunity Prioritisation

This is the central decision-support feature.

### MVP

Rank opportunities using a transparent scoring model based on factors such as:

- Business impact
- Automation readiness
- Implementation effort
- Payback
- Risk
- Confidence

### Output

```text
#1 Opportunity
#2 Opportunity
#3 Opportunity
...
```

The user should immediately understand:

> **Why is this #1?**

### Not MVP

- Machine-learning-based prioritisation
- Personalised optimisation algorithms
- Autonomous investment decisions

---

# 16. Feature Group J — Evidence Layer

### MVP

Every high-priority recommendation should have:

- Source dataset
- Relevant activity/cases
- Metrics
- Calculation logic
- Assumptions
- Confidence

### Evidence principle

> **Every important recommendation must be traceable back to data.**

### Not MVP

- Fully versioned enterprise data lineage
- Cross-system governance
- Enterprise audit management

---

# 17. Feature Group K — AI Explanation

### MVP

Use an LLM to:

- Explain findings
- Summarize the process
- Explain why an opportunity is important
- Explain priority
- Generate management-friendly recommendations
- Generate an improvement/automation explanation

### Architecture

```text
Verified Analytics
        ↓
Evidence
        ↓
LLM
        ↓
Explanation
```

### Hard boundary

The LLM must not be the source of truth for:

- Metrics
- Calculations
- ROI
- Savings
- Scores
- Evidence
- Process timing

---

# 18. Feature Group L — Improvement / Automation Blueprint

### MVP

For top opportunities, generate:

- Current state
- Problem
- Proposed intervention
- Future state
- Suggested technology category
- Human-in-the-loop requirement

### Example

```text
Current State
Manual invoice verification
        ↓
Problem
High volume + repetitive rules
        ↓
Intervention
Automated extraction + validation
        ↓
Future State
System processes normal cases
        ↓
Human
Reviews exceptions
```

### Not MVP

- Actual RPA deployment
- Autonomous workflow creation
- Automatic production changes
- Direct execution against customer systems

---

# 19. Feature Group M — Executive Output

### MVP

Generate a management-level report containing:

1. Process overview
2. Process health
3. Top bottlenecks
4. Top opportunities
5. Business impact
6. Automation readiness
7. Evidence
8. Recommended actions
9. Improvement / automation blueprint

### Not MVP

- Enterprise reporting suite
- Scheduled reporting
- Multi-department reporting
- Complex BI dashboards

---

# 20. Feature Group N — Dashboard

### MVP Screens

Keep the first interface small.

### 1. Upload

Upload and validate data.

### 2. Overview

Show:
- Process volume
- Cycle time
- Main bottlenecks
- Overall process health

### 3. Process

Show:
- Process graph
- Variants
- Core metrics

### 4. Opportunities

Show:
- Ranked opportunities
- Impact
- Readiness
- Priority

### 5. Opportunity Detail

Show:
- Evidence
- Calculations
- ROI
- Automation readiness
- Recommendation
- Blueprint

### 6. Report

Show/export the executive summary.

### Not MVP

- Complex multi-page enterprise dashboards
- Custom dashboard builders
- Drag-and-drop BI
- Advanced user customization

---

# 21. Features Explicitly Outside MVP

The following should be treated as **feature-creep traps**.

## Do NOT build initially

- Full ERP integration
- SAP integration
- Tally integration
- WhatsApp integration
- Email automation
- RPA deployment
- Autonomous agents
- Digital twins
- Predictive process simulation
- Object-centric process mining
- Real-time process monitoring
- Multi-company SaaS architecture
- Advanced role-based access control
- Enterprise SSO
- Mobile application
- Browser extension
- Custom workflow builder
- Marketplace
- Process benchmarking network
- AI chatbot as a standalone feature
- Complex forecasting
- ML-based opportunity discovery
- Automatic production-system changes

These can be reconsidered after MVP validation.

---

# 22. MVP Feature Priority

## Tier 1 — Absolutely Required

These define the product.

1. CSV/Excel upload
2. Schema detection / column mapping
3. Data validation
4. Case reconstruction
5. Process graph
6. Core process metrics
7. Bottleneck detection
8. Opportunity detection
9. Automation readiness
10. Business impact / ROI
11. Opportunity prioritisation
12. Evidence
13. AI explanation
14. Opportunity detail page

Without these, ProcessLens cannot prove its core thesis.

---

## Tier 2 — Required for a Usable MVP

1. Dashboard
2. Data-quality report
3. Process variants
4. Executive report
5. Automation / improvement blueprint
6. Basic authentication if deployment requires it
7. Error handling
8. Basic logging

---

## Tier 3 — Nice to Have

Only build these if Tier 1 and Tier 2 are complete and stable.

- Resource-level analytics
- Additional visualisations
- PDF export
- Additional process metrics
- More detailed filtering
- Dataset history

---

## Tier 4 — Post-MVP

- ERP integrations
- Real-time monitoring
- Advanced process mining
- Predictive analytics
- RPA integration
- Autonomous agents
- Multi-company SaaS
- Advanced permissions
- Continuous process monitoring

---

# 23. MVP Non-Goals

The MVP is **not** trying to:

- Replace an ERP
- Replace a process-mining enterprise platform
- Deploy automation itself
- Become an RPA platform
- Become a generic AI assistant
- Perform autonomous business decisions
- Solve every industry
- Support every data source
- Provide perfect ROI predictions

The MVP exists to prove:

> **ProcessLens can turn operational data into evidence-backed, financially understandable, prioritised improvement and automation opportunities.**

---

# 24. Feature Acceptance Gate

Before adding a new feature, ask:

### Question 1
Does it directly support:

**Discover → Quantify → Prioritise → Act?**

If no → **Do not add it.**

### Question 2
Does it help answer:

> What should the business fix or automate first?

If no → **Post-MVP.**

### Question 3
Can the MVP function without it?

If yes → **Strong candidate for Post-MVP.**

### Question 4
Does it introduce major architectural complexity?

If yes → **Defer unless essential.**

### Question 5
Can we validate its value with a real user?

If no → **Do not prioritize it.**

---

# 25. Feature-Creep Decision Matrix

| Feature | Core Value | Complexity | MVP? |
|---|---|---|---|
| CSV upload | High | Low | Yes |
| Excel upload | High | Low | Yes |
| Schema mapping | High | Medium | Yes |
| Process graph | High | Medium | Yes |
| Cycle-time analysis | High | Low | Yes |
| Bottleneck detection | High | Medium | Yes |
| Opportunity detection | Very High | Medium | Yes |
| Automation readiness | Very High | Medium | Yes |
| ROI estimation | Very High | Medium | Yes |
| Prioritisation | Very High | Medium | Yes |
| Evidence layer | Very High | Medium | Yes |
| AI explanation | High | Medium | Yes |
| ERP integration | Medium | High | No |
| RPA deployment | Medium | Very High | No |
| Real-time monitoring | Medium | High | No |
| Mobile app | Low | High | No |
| Autonomous agents | Low/Unproven | Very High | No |
| Digital twin | Low for MVP | Very High | No |
| Full enterprise IAM | Low initially | High | No |

---

# 26. MVP Definition of Done

ProcessLens MVP is considered complete only when this workflow works end-to-end:

```text
User
 ↓
Uploads Operational Dataset
 ↓
ProcessLens Validates Data
 ↓
ProcessLens Reconstructs Process
 ↓
ProcessLens Calculates Metrics
 ↓
ProcessLens Detects Bottlenecks
 ↓
ProcessLens Generates Opportunities
 ↓
ProcessLens Calculates Automation Readiness
 ↓
ProcessLens Estimates Business Impact
 ↓
ProcessLens Prioritises Opportunities
 ↓
ProcessLens Shows Evidence
 ↓
AI Explains Verified Findings
 ↓
ProcessLens Generates Improvement / Automation Blueprint
 ↓
User Makes a Decision
```

---

# 27. MVP Success Criteria

The MVP should be judged on product usefulness, not feature count.

### Functional

- [ ] User can upload supported operational data.
- [ ] Data can be validated.
- [ ] Process can be reconstructed.
- [ ] Metrics can be calculated.
- [ ] Bottlenecks can be identified.
- [ ] Opportunities can be generated.
- [ ] Opportunities can be scored.
- [ ] Business impact can be estimated.
- [ ] Opportunities can be ranked.
- [ ] Evidence can be inspected.
- [ ] AI can explain verified findings.
- [ ] A practical recommendation can be produced.

### Product

- [ ] A non-technical operations user can understand the result.
- [ ] The #1 opportunity has a clear reason for being #1.
- [ ] Financial estimates are transparent.
- [ ] Recommendations are traceable to data.
- [ ] The system does not depend on LLM hallucinations.
- [ ] The workflow can be demonstrated end-to-end.

---

# 28. Final Scope Boundary

The MVP should remain inside this box:

```text
┌─────────────────────────────────────────────────────────────┐
│                    PROCESSLENS MVP                          │
│                                                             │
│  DATA                                                       │
│   ↓                                                         │
│  PROCESS DISCOVERY                                          │
│   ↓                                                         │
│  ANALYTICS                                                  │
│   ↓                                                         │
│  BOTTLENECKS                                                │
│   ↓                                                         │
│  OPPORTUNITIES                                              │
│   ↓                                                         │
│  AUTOMATION READINESS                                       │
│   ↓                                                         │
│  BUSINESS IMPACT                                            │
│   ↓                                                         │
│  PRIORITISATION                                             │
│   ↓                                                         │
│  EVIDENCE                                                   │
│   ↓                                                         │
│  AI EXPLANATION                                             │
│   ↓                                                         │
│  IMPROVEMENT / AUTOMATION BLUEPRINT                         │
│   ↓                                                         │
│  DECISION                                                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Everything outside this box is presumed POST-MVP
unless it is required to make the core loop work.
```

---

# 29. Golden Rule

> **Do not build features because they are impressive. Build features because they make the core decision better.**

The MVP wins if it can reliably transform:

**Messy Operational Data**

into:

**Evidence → Economics → Prioritised Action**

That is the product.

