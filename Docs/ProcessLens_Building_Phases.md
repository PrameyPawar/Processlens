# ProcessLens — Product Building Phases

## 1. Purpose

This document defines the phased development roadmap for building ProcessLens from the initial development environment through MVP deployment and, later, real-world industry implementation and productization.

The build principle is:

> **Build the analytical engine first. Build the presentation layer around it.**

The core product question is:

> **What should this business fix or automate first, why, and what business value could it create?**

---

# Phase 0 — Development Foundation

### Goal
Establish the project and development environment.

### Work
- Finalize technology stack
- Create repository structure
- Set up frontend and backend
- Configure environment variables
- Set up database/storage
- Establish Git/GitHub workflow
- Define development conventions
- Establish basic CI/CD structure

### Exit Condition
The empty ProcessLens application runs locally and can be deployed.

---

# Phase 1 — Data Ingestion

### Goal
Get operational data into ProcessLens reliably.

### Work
- CSV upload
- Excel upload
- File validation
- Schema detection
- Column mapping
- Required-field identification
- Data preview
- Data-quality report
- Error handling

### Output

**Uploaded File → Validated Dataset**

### Exit Condition
A user can upload a realistic event-log dataset and ProcessLens can reliably interpret it.

---

# Phase 2 — Process Reconstruction

### Goal
Convert raw records into an actual business process.

### Work
- Case identification
- Activity identification
- Timestamp handling
- Event ordering
- Case reconstruction
- Process variants
- Process graph generation

### Output

**Event Log → Actual Process**

### Exit Condition
Given an event log, ProcessLens can reconstruct and visualize the underlying process.

---

# Phase 3 — Process Analytics Engine

### Goal
Quantify what is happening in the process.

### Core Metrics
- Cycle time
- Waiting time
- Processing time
- Activity frequency
- Throughput
- Rework rate
- Variant frequency
- Activity-level performance
- Resource-level metrics where available

### Output

**Process → Quantified Process**

### Exit Condition
Every important process observation comes from deterministic calculations.

---

# Phase 4 — Bottleneck & Problem Detection

### Goal
Find where the process is losing time and efficiency.

### Detection Areas
- Long waiting periods
- High processing times
- High-frequency activities
- Rework loops
- Repeated activities
- High-variation paths
- Resource concentration
- Other abnormal patterns

### Output

**Process Data → Ranked Problems**

### Exit Condition
ProcessLens can identify the most important operational problems without relying on an LLM.

---

# Phase 5 — Opportunity Detection

### Goal
Convert problems into improvement and automation opportunities.

### Evaluate
- Frequency
- Manual effort
- Repetitiveness
- Rule-based nature
- Exception rate
- Potential business impact

### Output

**Problem → Opportunity**

### Exit Condition
ProcessLens can generate structured opportunity candidates from analytical evidence.

---

# Phase 6 — Automation Readiness Engine

### Goal
Determine whether an opportunity is actually suitable for automation.

### Assessment Factors
- Repetitiveness
- Rule-based nature
- Digital inputs
- Volume
- Exception rate
- Human judgment
- Operational risk

### Output

**Automation Readiness Score**

The score should be interpretable rather than an opaque AI-generated number.

### Exit Condition
A user can understand why an opportunity received its automation-readiness score.

---

# Phase 7 — Business Impact & ROI Engine

### Goal
Translate operational problems into business economics.

### Calculate / Estimate
- Manual hours
- Labour cost
- Potential annual savings
- Implementation effort
- Estimated implementation cost
- Payback period
- Potential ROI

### Important Principle

Clearly distinguish:

**Measured → Calculated → Assumed → Estimated**

Every financial number should be traceable to its inputs and assumptions.

### Exit Condition
Every financial output can be explained and traced back to its underlying assumptions.

---

# Phase 8 — Opportunity Prioritisation

### Goal
Answer the core ProcessLens question:

> **What should I fix or automate first?**

### Prioritisation Factors
- Business impact
- Automation readiness
- Implementation effort
- Payback
- Risk
- Confidence

### Output

**Priority Score → Top Opportunities**

### Exit Condition
ProcessLens produces a defensible ranked list rather than a generic list of bottlenecks.

---

# Phase 9 — Evidence & Explainability

### Goal
Make every recommendation defensible.

Each opportunity should connect:

**Opportunity**
↓
**Source Activity**
↓
**Source Data**
↓
**Calculated Metrics**
↓
**Calculation Logic**
↓
**Business Impact**
↓
**Priority**

### Exit Condition
No major recommendation is a black box.

---

# Phase 10 — AI Intelligence Layer

### Goal
Make analytical output understandable and actionable.

### Architecture

**Deterministic Engine**
↓
**Verified Results**
↓
**LLM**
↓
**Explanation**

### AI Responsibilities
- Explain findings
- Summarize problems
- Explain priority
- Recommend actions
- Generate management-level language
- Create improvement/automation suggestions

### AI Restriction

The AI must not independently invent:
- Operational metrics
- ROI
- Savings
- Process times
- Scores
- Source evidence

### Exit Condition
AI adds interpretation without compromising analytical reliability.

---

# Phase 11 — Improvement / Automation Blueprint

### Goal
Turn a recommendation into an actionable future-state design.

### Blueprint Structure

**Current State**
→ **Problem**
→ **Intervention**
→ **Future State**
→ **Technology**
→ **Human-in-the-Loop**

### Exit Condition
A manager can understand what implementation could look like.

---

# Phase 12 — Product Dashboard

### Goal
Turn the analytical engines into a usable product.

### Core Screens
1. Dashboard
2. Data Upload
3. Data Quality
4. Process Overview
5. Process Map
6. Process Analytics
7. Bottlenecks
8. Opportunities
9. Opportunity Details
10. ROI / Business Impact
11. AI Explanation
12. Automation Blueprint
13. Report

### Exit Condition
A non-technical user can complete the entire ProcessLens workflow without developer intervention.

---

# Phase 13 — Testing & Validation

### Goal
Establish that the system actually works.

### Test Areas
- Clean datasets
- Missing data
- Duplicate events
- Incorrect timestamps
- Large datasets
- Multiple process variants
- Rework
- Edge cases
- Incorrect mappings
- Financial calculation accuracy
- Score consistency
- AI hallucination resistance

### Core Testing Principle

**Known Input → Expected Analytical Output**

### Exit Condition
Core calculations and recommendations are reproducible and reliable.

---

# Phase 14 — Deployment

### Goal
Make ProcessLens accessible outside the development environment.

### Work
- Production database
- Backend deployment
- Frontend deployment
- File storage
- Environment secrets
- Domain
- HTTPS
- Logging
- Monitoring
- Error tracking
- Basic security

### Exit Condition

> A user can open ProcessLens from the internet and use the MVP end-to-end.

---

# MVP COMPLETE

At the end of Phase 14, the MVP should demonstrate the complete core decision-support loop:

**Data Ingestion**
→ **Process Reconstruction**
→ **Process Analytics**
→ **Bottleneck Detection**
→ **Opportunity Detection**
→ **Automation Readiness**
→ **Business Impact**
→ **Prioritisation**
→ **Evidence**
→ **AI Explanation**
→ **Improvement / Automation Blueprint**
→ **Executive Output**

---

# Phase 15 — Real-World Industry Pilot

### Goal
Validate ProcessLens using real business operations.

### Pilot Workflow

**Real Company**
↓
**Real Operational Data**
↓
**ProcessLens Analysis**
↓
**Opportunity**
↓
**Business Validation**
↓
**Implement Improvement**
↓
**Implement Automation**
↓
**Measure Before vs After**
↓
**Actual Savings / Impact**
↓
**Customer Feedback**
↓
**ProcessLens Iteration**

### Exit Condition
At least one real-world use case demonstrates measurable operational or financial impact.

---

# Phase 16 — Productization

### Goal
Turn the validated MVP into a scalable product.

### Potential Capabilities
- Multi-company architecture
- Authentication
- Role-based access
- Organization/workspace model
- Recurring data ingestion
- ERP integrations
- API layer
- Continuous monitoring
- Benchmarking
- Process history
- Advanced analytics
- Automated reporting
- Collaboration
- Pricing model

### Exit Condition
ProcessLens can support multiple real businesses reliably and commercially.

---

# Complete Build Roadmap

```text
PHASE 0
Development Foundation
        ↓
PHASE 1
Data Ingestion
        ↓
PHASE 2
Process Reconstruction
        ↓
PHASE 3
Process Analytics
        ↓
PHASE 4
Bottleneck Detection
        ↓
PHASE 5
Opportunity Detection
        ↓
PHASE 6
Automation Readiness
        ↓
PHASE 7
Business Impact & ROI
        ↓
PHASE 8
Opportunity Prioritisation
        ↓
PHASE 9
Evidence & Explainability
        ↓
PHASE 10
AI Intelligence
        ↓
PHASE 11
Automation Blueprint
        ↓
PHASE 12
Product Dashboard
        ↓
PHASE 13
Testing & Validation
        ↓
PHASE 14
MVP Deployment
        ↓
========================
       MVP COMPLETE
========================
        ↓
PHASE 15
Industry Pilot
        ↓
PHASE 16
Productization
```

---

# Core Development Principle

Do not build the dashboard first.

The primary asset of ProcessLens is the analytical engine.

The system must first prove that it can take messy operational data and produce a defensible answer to:

> **What should this business fix or automate first?**

The UI should then make that intelligence understandable and actionable.
