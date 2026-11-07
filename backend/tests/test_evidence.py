"""
Comprehensive unit and integration test suite for Phase 9 Evidence Architecture and Audit Dossiers.
Tests:
- Group 1: Exact source-row semantics and physical CSV line anchoring (csv_line_number == row_index + 1).
- Group 2: Deterministic exemplar selection, relevance, tie-breaking, and archetype coverage (<= 3 exemplars).
- Group 3: Formula derivations, inputs, intermediate values, and mathematical accuracy.
- Group 4: Epistemic classification rules (FACT, ASSUMPTION, HYPOTHESIS, ESTIMATE, DECISION).
- Group 5: End-to-end audit regressions across all four synthetic datasets (quickstart, clean, rework, messy).
- Group 6: Opportunity ID filtering and unknown-ID validation (HTTP 400).
- Group 7: API boundary validation, unsupported formats, empty filenames, 10MB limit, and SHA-256 verification.
"""

import hashlib
import json
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from app.schemas.evidence import (
    EpistemicType,
    EvidenceAuditResponse,
)
from app.schemas.opportunity import OpportunityArchetype


# =============================================================================
# GROUP 1: Source-Row Semantics and CSV Line Number Anchoring
# =============================================================================

def test_group1_1_source_row_and_csv_line_number_consistency(client: TestClient, sample_quickstart_path):
    """
    Test 1.1: Verify that every event row anchor satisfies the exact invariant:
    csv_line_number == row_index + 1 (accounting for CSV header).
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()
    response = EvidenceAuditResponse(**data)

    anchors_checked = 0
    for dossier in response.dossiers:
        for ex in dossier.exemplars:
            for anchor in ex.event_anchors:
                anchors_checked += 1
                assert anchor.row_index >= 1, "row_index must be a 1-based data row index"
                assert anchor.csv_line_number == anchor.row_index + 1, (
                    f"Physical CSV line number ({anchor.csv_line_number}) must equal row_index + 1 ({anchor.row_index + 1})"
                )
    assert anchors_checked > 0, "At least one anchor must be verified"


def test_group1_2_physical_csv_line_content_verification(client: TestClient, sample_quickstart_path):
    """
    Test 1.2: Cross-reference physical lines from the actual CSV file on disk
    against the anchored row_index and csv_line_number values.
    """
    with open(sample_quickstart_path, "r", encoding="utf-8") as f:
        csv_lines = f.readlines()

    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for dossier in data["dossiers"]:
        for ex in dossier["exemplars"]:
            for anchor in ex["event_anchors"]:
                line_idx = anchor["csv_line_number"] - 1  # 0-indexed in Python list
                assert 0 <= line_idx < len(csv_lines), f"Line {line_idx} out of range"
                raw_line = csv_lines[line_idx]

                if anchor["case_id"]:
                    assert anchor["case_id"] in raw_line, (
                        f"Expected case_id '{anchor['case_id']}' in CSV line {anchor['csv_line_number']}: {raw_line}"
                    )
                if anchor["activity"]:
                    assert anchor["activity"] in raw_line, (
                        f"Expected activity '{anchor['activity']}' in CSV line {anchor['csv_line_number']}: {raw_line}"
                    )


# =============================================================================
# GROUP 2: Exemplar Selection, Relevance & Archetype Coverage
# =============================================================================

def test_group2_1_delay_compression_exemplar_relevance(client: TestClient, sample_quickstart_path):
    """
    Test 2.1: DELAY_COMPRESSION exemplars contain actual source and target events
    matching candidate target entity.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    delay_dossiers = [
        d for d in data["dossiers"] if d["archetype"] == OpportunityArchetype.DELAY_COMPRESSION.value
    ]
    assert len(delay_dossiers) > 0

    for d in delay_dossiers:
        target = d["target_entity"]
        assert " -> " in target
        src_act, tgt_act = target.split(" -> ", 1)

        assert 1 <= len(d["exemplars"]) <= 3
        for ex in d["exemplars"]:
            roles = [a["role_in_evidence"] for a in ex["event_anchors"]]
            assert "TRANSITION_SOURCE" in roles
            assert "TRANSITION_TARGET" in roles

            src_anchors = [a for a in ex["event_anchors"] if a["role_in_evidence"] == "TRANSITION_SOURCE"]
            tgt_anchors = [a for a in ex["event_anchors"] if a["role_in_evidence"] == "TRANSITION_TARGET"]
            assert src_anchors[0]["activity"] == src_act
            assert tgt_anchors[0]["activity"] == tgt_act


def test_group2_2_recurrence_reduction_exemplar_relevance(client: TestClient, sample_rework_path):
    """
    Test 2.2: RECURRENCE_REDUCTION exemplars contain the repeated activity
    executed at least twice at distinct timestamps.
    """
    with open(sample_rework_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("rework.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    rec_dossiers = [
        d for d in data["dossiers"] if d["archetype"] == OpportunityArchetype.RECURRENCE_REDUCTION.value
    ]
    assert len(rec_dossiers) > 0

    for d in rec_dossiers:
        act = d["target_entity"]
        assert 1 <= len(d["exemplars"]) <= 3
        for ex in d["exemplars"]:
            rep_anchors = [a for a in ex["event_anchors"] if a["role_in_evidence"] == "REPEATED_ACTIVITY"]
            assert len(rep_anchors) >= 2
            for a in rep_anchors:
                assert a["activity"] == act


def test_group2_3_max_three_exemplars_contract(client: TestClient, sample_clean_path):
    """
    Test 2.3: In all emitted dossiers, the exemplar list never exceeds 3 cases.
    """
    with open(sample_clean_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("clean.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for d in data["dossiers"]:
        assert len(d["exemplars"]) <= 3


def test_group2_4_deterministic_exemplar_tie_breaking(client: TestClient, sample_quickstart_path):
    """
    Test 2.4: Repeated executions produce identical exemplars in identical order.
    """
    with open(sample_quickstart_path, "rb") as f:
        res1 = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    with open(sample_quickstart_path, "rb") as f:
        res2 = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})

    assert res1.status_code == 200
    assert res2.status_code == 200
    assert res1.json() == res2.json()


def test_group2_5_path_standardization_exemplar_relevance(client: TestClient, sample_messy_path):
    """
    Test 2.5: PATH_STANDARDIZATION exemplars on messy dataset contain trace start
    and end events matching rare variant cases.
    """
    with open(sample_messy_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("messy.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    path_dossiers = [
        d for d in data["dossiers"] if d["archetype"] == OpportunityArchetype.PATH_STANDARDIZATION.value
    ]
    assert len(path_dossiers) > 0

    for d in path_dossiers:
        assert 1 <= len(d["exemplars"]) <= 3
        for ex in d["exemplars"]:
            roles = [a["role_in_evidence"] for a in ex["event_anchors"]]
            assert "TRACE_START" in roles
            assert "TRACE_END" in roles
            assert ex["exemplar_metric_value"] > 0.0


def test_group2_6_tail_variance_mitigation_exemplar_extraction(sample_quickstart_path):
    """
    Test 2.6: TAIL_VARIANCE_MITIGATION exemplar extraction correctly identifies
    cases exceeding cycle-time upper fence threshold.
    """
    from app.services.reconstruction import reconstruct_process_from_csv
    from app.services.analytics import calculate_process_analytics
    from app.services.detection import detect_process_problems
    from app.services.evidence import extract_exemplars_for_opportunity
    from app.schemas.prioritisation import PrioritisedOpportunity, PortfolioCohort, ScoringStatus, FactorBreakdown, ImpactBasis
    from app.schemas.opportunity import OpportunityCandidate, ScoreBreakdown, PriorityTier, InterventionCategory
    from app.schemas.detection import EvidenceStrength
    from app.schemas.readiness import OverallReadinessTier
    from app.schemas.economics import OpportunityEconomicsResult, ObservationWindowInfo, LaborEffortMetrics, CapacityValuationMetrics, CashFlowMetrics, StrategicSynthesis, EconomicTier, StrategicDecisionOutcome, MetricProvenance, TimeBasis, AnnualisationMethod

    with open(sample_quickstart_path, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    candidate = OpportunityCandidate(
        id="opp_tail_var_test",
        title="Mitigate Extreme Cycle-Time Outliers",
        archetype=OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
        intervention_category=InterventionCategory.EXCEPTION_MANAGEMENT,
        target_entity="Cycle Time Tail Distribution",
        source_finding_ids=["finding_cycle_time_outliers"],
        evidence_strength=EvidenceStrength.HIGH,
        affected_case_count=5,
        affected_case_percentage=5.0,
        occurrence_count=5,
        rationale="Test rationale for outlier mitigation",
        operational_priority_score=45.0,
        priority_tier=PriorityTier.TIER_2_MEDIUM,
        score_breakdown=ScoreBreakdown(
            coverage_score=20.0,
            concentration_score=25.0,
            raw_score=45.0,
            evidence_weight=1.0,
            final_score=45.0,
        ),
    )

    prioritised_opp = PrioritisedOpportunity(
        rank_order=1,
        opportunity_id="opp_tail_var_test",
        archetype=OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
        portfolio_cohort=PortfolioCohort.GUARDRAILED_AUTOMATION,
        scoring_status=ScoringStatus.SCORED,
        composite_priority_score=50.0,
        factors=FactorBreakdown(
            impact_score=50.0,
            impact_basis=ImpactBasis.OPERATIONAL_CONCENTRATION_BASELINE,
            impact_provenance=MetricProvenance.MEASURED_IN_LOG,
            confidence_score=75.0,
        ),
        economics=OpportunityEconomicsResult(
            opportunity_id="opp_tail_var_test",
            archetype=OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
            observation_window=ObservationWindowInfo(
                time_basis=TimeBasis.ANNUAL,
                annualisation_method=AnnualisationMethod.CALENDAR_EXTRAPOLATION,
                sample_completed_cases=recon.complete_cases_count,
                volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            labor_effort=LaborEffortMetrics(
                sample_affected_cases=5,
                affected_cases_provenance=MetricProvenance.MEASURED_IN_LOG,
                labor_metrics_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            capacity_valuation=CapacityValuationMetrics(
                hourly_labor_rate_provenance=MetricProvenance.USER_PROVIDED,
                annual_recurring_cost_provenance=MetricProvenance.USER_PROVIDED,
                implementation_cost_provenance=MetricProvenance.USER_PROVIDED,
                economic_tier=EconomicTier.MODERATE_RETURN,
            ),
            cash_flow=CashFlowMetrics(),
            synthesis=StrategicSynthesis(
                operational_priority=PriorityTier.TIER_2_MEDIUM,
                overall_readiness=OverallReadinessTier.READY_FOR_SPECIFICATION,
                economic_tier=EconomicTier.MODERATE_RETURN,
                strategic_decision=StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS,
                decision_rationale="Test",
            ),
        ),
        operational_priority_score=45.0,
        primary_strength="Cycle time tail latency",
    )

    exemplars, policy, caveats = extract_exemplars_for_opportunity(
        opp=prioritised_opp,
        candidate=candidate,
        reconstruction=recon,
        analytics=analytics,
        detection=detection,
    )
    assert "upper fence" in policy
    assert len(exemplars) <= 3
    if exemplars:
        assert exemplars[0].exemplar_metric_value > 0.0


def test_group2_7_data_instrumentation_exemplar_extraction(sample_messy_path):
    """
    Test 2.7: DATA_INSTRUMENTATION exemplar extraction anchors to excluded rows.
    """
    from app.services.reconstruction import reconstruct_process_from_csv
    from app.services.analytics import calculate_process_analytics
    from app.services.detection import detect_process_problems
    from app.services.evidence import extract_exemplars_for_opportunity
    from app.schemas.prioritisation import PrioritisedOpportunity, PortfolioCohort, ScoringStatus, FactorBreakdown, ImpactBasis
    from app.schemas.opportunity import OpportunityCandidate, ScoreBreakdown, PriorityTier, InterventionCategory
    from app.schemas.detection import EvidenceStrength
    from app.schemas.readiness import OverallReadinessTier
    from app.schemas.economics import OpportunityEconomicsResult, ObservationWindowInfo, LaborEffortMetrics, CapacityValuationMetrics, CashFlowMetrics, StrategicSynthesis, EconomicTier, StrategicDecisionOutcome, MetricProvenance, TimeBasis, AnnualisationMethod

    with open(sample_messy_path, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "messy.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    candidate = OpportunityCandidate(
        id="opp_data_inst_test",
        title="Improve Event Timestamp Instrumentation",
        archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
        intervention_category=InterventionCategory.DATA_INSTRUMENTATION,
        target_entity="Event Log Instrumentation",
        source_finding_ids=["finding_reconciliation_discrepancy"],
        evidence_strength=EvidenceStrength.HIGH,
        affected_case_count=10,
        affected_case_percentage=10.0,
        occurrence_count=1,
        rationale="Test rationale for data instrumentation",
        operational_priority_score=60.0,
        priority_tier=PriorityTier.TIER_1_HIGH,
        score_breakdown=ScoreBreakdown(
            coverage_score=50.0,
            concentration_score=10.0,
            raw_score=60.0,
            evidence_weight=1.0,
            final_score=60.0,
        ),
    )

    prioritised_opp = PrioritisedOpportunity(
        rank_order=1,
        opportunity_id="opp_data_inst_test",
        archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
        portfolio_cohort=PortfolioCohort.FOUNDATIONAL_DATA_QUALITY,
        scoring_status=ScoringStatus.SCORED,
        composite_priority_score=70.0,
        factors=FactorBreakdown(
            impact_score=70.0,
            impact_basis=ImpactBasis.OPERATIONAL_CONCENTRATION_BASELINE,
            impact_provenance=MetricProvenance.MEASURED_IN_LOG,
            confidence_score=90.0,
        ),
        economics=OpportunityEconomicsResult(
            opportunity_id="opp_data_inst_test",
            archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
            observation_window=ObservationWindowInfo(
                time_basis=TimeBasis.ANNUAL,
                annualisation_method=AnnualisationMethod.CALENDAR_EXTRAPOLATION,
                sample_completed_cases=recon.complete_cases_count,
                volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            labor_effort=LaborEffortMetrics(
                sample_affected_cases=10,
                affected_cases_provenance=MetricProvenance.MEASURED_IN_LOG,
                labor_metrics_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            capacity_valuation=CapacityValuationMetrics(
                hourly_labor_rate_provenance=MetricProvenance.USER_PROVIDED,
                annual_recurring_cost_provenance=MetricProvenance.USER_PROVIDED,
                implementation_cost_provenance=MetricProvenance.USER_PROVIDED,
                economic_tier=EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS,
            ),
            cash_flow=CashFlowMetrics(),
            synthesis=StrategicSynthesis(
                operational_priority=PriorityTier.TIER_1_HIGH,
                overall_readiness=OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE,
                economic_tier=EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS,
                strategic_decision=StrategicDecisionOutcome.RESOLVE_DATA_INSTRUMENTATION,
                decision_rationale="Test",
            ),
        ),
        operational_priority_score=60.0,
        primary_strength="Data quality foundation",
    )

    exemplars, policy, caveats = extract_exemplars_for_opportunity(
        opp=prioritised_opp,
        candidate=candidate,
        reconstruction=recon,
        analytics=analytics,
        detection=detection,
    )
    assert "excluded from reconstruction" in policy
    assert len(exemplars) <= 3
    if exemplars:
        assert exemplars[0].event_anchors[0].role_in_evidence == "EXCLUDED_DATA_ROW"


def test_group2_8_empty_exemplars_when_no_match(sample_quickstart_path):
    """
    Test 2.8: When no cases match an archetype, an empty exemplar list is returned
    with an explicit boundary limitation rather than substituting unrelated cases.
    """
    from app.services.reconstruction import reconstruct_process_from_csv
    from app.services.analytics import calculate_process_analytics
    from app.services.detection import detect_process_problems
    from app.services.evidence import extract_exemplars_for_opportunity
    from app.schemas.prioritisation import PrioritisedOpportunity, PortfolioCohort, ScoringStatus, FactorBreakdown, ImpactBasis
    from app.schemas.opportunity import OpportunityCandidate, ScoreBreakdown, PriorityTier, InterventionCategory
    from app.schemas.detection import EvidenceStrength
    from app.schemas.readiness import OverallReadinessTier
    from app.schemas.economics import OpportunityEconomicsResult, ObservationWindowInfo, LaborEffortMetrics, CapacityValuationMetrics, CashFlowMetrics, StrategicSynthesis, EconomicTier, StrategicDecisionOutcome, MetricProvenance, TimeBasis, AnnualisationMethod

    with open(sample_quickstart_path, "rb") as f:
        content = f.read()

    recon = reconstruct_process_from_csv(content, "quickstart.csv")
    analytics = calculate_process_analytics(recon)
    detection = detect_process_problems(recon, analytics)

    candidate = OpportunityCandidate(
        id="opp_nonexistent_transition",
        title="Nonexistent Transition",
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        intervention_category=InterventionCategory.UNDETERMINED_INVESTIGATION,
        target_entity="NonexistentActivityA -> NonexistentActivityB",
        source_finding_ids=["finding_nonexistent"],
        evidence_strength=EvidenceStrength.LIMITED,
        affected_case_count=0,
        affected_case_percentage=0.0,
        occurrence_count=0,
        rationale="Test non-existent opportunity",
        operational_priority_score=10.0,
        priority_tier=PriorityTier.TIER_4_EXPLORATORY,
        score_breakdown=ScoreBreakdown(
            coverage_score=0.0,
            concentration_score=10.0,
            raw_score=10.0,
            evidence_weight=1.0,
            final_score=10.0,
        ),
    )

    prioritised_opp = PrioritisedOpportunity(
        rank_order=99,
        opportunity_id="opp_nonexistent_transition",
        archetype=OpportunityArchetype.DELAY_COMPRESSION,
        portfolio_cohort=PortfolioCohort.REVISE_OR_DEFERRED,
        scoring_status=ScoringStatus.SCORED,
        composite_priority_score=10.0,
        factors=FactorBreakdown(
            impact_score=10.0,
            impact_basis=ImpactBasis.OPERATIONAL_CONCENTRATION_BASELINE,
            impact_provenance=MetricProvenance.MEASURED_IN_LOG,
            confidence_score=10.0,
        ),
        economics=OpportunityEconomicsResult(
            opportunity_id="opp_nonexistent_transition",
            archetype=OpportunityArchetype.DELAY_COMPRESSION,
            observation_window=ObservationWindowInfo(
                time_basis=TimeBasis.ANNUAL,
                annualisation_method=AnnualisationMethod.CALENDAR_EXTRAPOLATION,
                sample_completed_cases=recon.complete_cases_count,
                volume_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            labor_effort=LaborEffortMetrics(
                sample_affected_cases=0,
                affected_cases_provenance=MetricProvenance.MEASURED_IN_LOG,
                labor_metrics_provenance=MetricProvenance.MEASURED_IN_LOG,
            ),
            capacity_valuation=CapacityValuationMetrics(
                hourly_labor_rate_provenance=MetricProvenance.USER_PROVIDED,
                annual_recurring_cost_provenance=MetricProvenance.USER_PROVIDED,
                implementation_cost_provenance=MetricProvenance.USER_PROVIDED,
                economic_tier=EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS,
            ),
            cash_flow=CashFlowMetrics(),
            synthesis=StrategicSynthesis(
                operational_priority=PriorityTier.TIER_4_EXPLORATORY,
                overall_readiness=OverallReadinessTier.INSUFFICIENT_CRITICAL_EVIDENCE,
                economic_tier=EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS,
                strategic_decision=StrategicDecisionOutcome.DEFER_OR_ARCHIVE,
                decision_rationale="Test",
            ),
        ),
        operational_priority_score=10.0,
        primary_strength="None",
    )

    exemplars, policy, caveats = extract_exemplars_for_opportunity(
        opp=prioritised_opp,
        candidate=candidate,
        reconstruction=recon,
        analytics=analytics,
        detection=detection,
    )
    assert exemplars == []
    assert any("No complete cases matched" in c for c in caveats)


# =============================================================================
# GROUP 3: Formula Derivations & Reproducibility
# =============================================================================

def test_group3_1_operational_priority_score_derivation(client: TestClient, sample_quickstart_path):
    """
    Test 3.1: OPS_SCORE_V1 derivation contains coverage, concentration, and evidence weight.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for d in data["dossiers"]:
        derivs = {drv["metric_id"]: drv for drv in d["derivations"]}
        assert "OPS_SCORE_V1" in derivs
        ops_drv = derivs["OPS_SCORE_V1"]
        assert "coverage_score" in ops_drv["input_variables"]
        assert "concentration_score" in ops_drv["input_variables"]
        assert "evidence_weight" in ops_drv["input_variables"]
        assert ops_drv["output_value"] is not None


def test_group3_2_composite_score_derivation(client: TestClient, sample_quickstart_path):
    """
    Test 3.2: COMPOSITE_SCORE_V1 derivation reflects weighted factor synthesis.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for d in data["dossiers"]:
        derivs = {drv["metric_id"]: drv for drv in d["derivations"]}
        assert "COMPOSITE_SCORE_V1" in derivs
        comp_drv = derivs["COMPOSITE_SCORE_V1"]
        assert "effective_weights" in comp_drv["input_variables"]
        assert comp_drv["output_value"] == d["composite_priority_score"]


def test_group3_3_monetized_economics_derivations(client: TestClient, sample_quickstart_path):
    """
    Test 3.3: When economic inputs are supplied, annualization, labor effort,
    capacity valuation, and payback derivations are produced.
    """
    # Detect opportunities first
    with open(sample_quickstart_path, "rb") as f:
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("quickstart.csv", f, "text/csv")})
    assert opp_res.status_code == 200
    opp_id = opp_res.json()["opportunities"][0]["id"]

    econ_inputs = [{
        "opportunity_id": opp_id,
        "hourly_labor_rate": 65.0,
        "implementation_cost": 15000.0,
        "annual_recurring_cost": 2000.0,
        "touch_labor_minutes_per_occurrence": 12.0,
        "addressable_efficiency_percentage": 75.0,
    }]

    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()

    dossier = next(d for d in data["dossiers"] if d["opportunity_id"] == opp_id)
    metric_ids = [drv["metric_id"] for drv in dossier["derivations"]]
    assert "ANNUALIZATION_V1" in metric_ids
    assert "LABOR_EFFORT_V1" in metric_ids
    assert "CAPACITY_VAL_V1" in metric_ids
    assert "PAYBACK_PERIOD_V1" in metric_ids


# =============================================================================
# GROUP 4: Epistemic Classification Rules
# =============================================================================

def test_group4_1_epistemic_categories_present(client: TestClient, sample_quickstart_path):
    """
    Test 4.1: Every dossier contains entries for FACT, ASSUMPTION, HYPOTHESIS,
    ESTIMATE, and DECISION.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for d in data["dossiers"]:
        ledger = d["epistemic_ledger"]
        types = {item["epistemic_type"] for item in ledger}
        assert EpistemicType.FACT.value in types
        assert EpistemicType.ASSUMPTION.value in types
        assert EpistemicType.HYPOTHESIS.value in types
        assert EpistemicType.ESTIMATE.value in types
        assert EpistemicType.DECISION.value in types


def test_group4_2_epistemic_classification_boundaries(client: TestClient, sample_quickstart_path):
    """
    Test 4.2: Ensure facts are strictly observed logs, assumptions are parameters,
    hypotheses are investigation questions, estimates are models, and decisions are policies.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    for d in data["dossiers"]:
        for item in d["epistemic_ledger"]:
            if item["epistemic_type"] == EpistemicType.FACT.value:
                assert "reconstruction" in item["source_or_basis"].lower() or "accounting" in item["source_or_basis"].lower()
            elif item["epistemic_type"] == EpistemicType.ASSUMPTION.value:
                assert "default" in item["source_or_basis"].lower() or "input" in item["source_or_basis"].lower() or "weight" in item["source_or_basis"].lower()
            elif item["epistemic_type"] == EpistemicType.HYPOTHESIS.value:
                assert "heuristic" in item["source_or_basis"].lower() or "hypothesis" in item["source_or_basis"].lower() or "classification" in item["source_or_basis"].lower()
            elif item["epistemic_type"] == EpistemicType.ESTIMATE.value:
                assert "formula" in item["source_or_basis"].lower() or "scenario" in item["source_or_basis"].lower() or "synthesis" in item["source_or_basis"].lower()
            elif item["epistemic_type"] == EpistemicType.DECISION.value:
                assert "policy" in item["source_or_basis"].lower() or "matrix" in item["source_or_basis"].lower() or "sort key" in item["source_or_basis"].lower()


# =============================================================================
# GROUP 5: Regressions Across All Four Synthetic Datasets
# =============================================================================

@pytest.mark.parametrize(
    "dataset_fixture",
    [
        "sample_quickstart_path",
        "sample_clean_path",
        "sample_rework_path",
        "sample_messy_path",
    ],
)
def test_group5_1_pipeline_regression_across_all_datasets(request, client: TestClient, dataset_fixture):
    """
    Test 5.1: Verifies evidence audit endpoint executes cleanly across all four
    development datasets, generating valid dossiers and manifests.
    """
    sample_path = request.getfixturevalue(dataset_fixture)
    with open(sample_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": (sample_path.name, f, "text/csv")})
    assert res.status_code == 200
    data = res.json()

    manifest = data["manifest"]
    assert manifest["source_filename"] == sample_path.name
    assert manifest["total_source_rows"] > 0
    assert manifest["is_persisted_snapshot"] is False

    summary = data["summary"]
    assert summary["total_opportunities_evaluated"] == len(data["dossiers"])
    assert summary["dossiers_emitted"] == len(data["dossiers"])


# =============================================================================
# GROUP 6: Opportunity Filtering & Validation
# =============================================================================

def test_group6_1_opportunity_id_filtering_success(client: TestClient, sample_quickstart_path):
    """
    Test 6.1: When opportunity_id parameter is provided, exactly one dossier is emitted.
    """
    with open(sample_quickstart_path, "rb") as f:
        full_res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert full_res.status_code == 200
    first_opp_id = full_res.json()["dossiers"][0]["opportunity_id"]

    with open(sample_quickstart_path, "rb") as f:
        filtered_res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"opportunity_id": first_opp_id},
        )
    assert filtered_res.status_code == 200
    data = filtered_res.json()
    assert data["summary"]["dossiers_emitted"] == 1
    assert data["summary"]["filter_applied"] == first_opp_id
    assert len(data["dossiers"]) == 1
    assert data["dossiers"][0]["opportunity_id"] == first_opp_id


def test_group6_2_unknown_opportunity_id_returns_http_400(client: TestClient, sample_quickstart_path):
    """
    Test 6.2: Filtering by an unknown opportunity ID raises HTTP 400 listing valid IDs.
    """
    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"opportunity_id": "nonexistent_opp_123"},
        )
    assert res.status_code == 400
    assert "nonexistent_opp_123" in res.json()["detail"]
    assert "Valid IDs are" in res.json()["detail"]


# =============================================================================
# GROUP 7: API Boundary Validation & Integrity
# =============================================================================

def test_group7_1_invalid_file_extension(client: TestClient):
    """
    Test 7.1: Non-CSV file extension is rejected with HTTP 400.
    """
    res = client.post(
        "/api/v1/evidence/audit",
        files={"file": ("test.txt", b"some,content\n1,2", "text/plain")},
    )
    assert res.status_code == 400
    assert "Unsupported file type" in res.json()["detail"]


def test_group7_2_upload_exceeds_10mb_limit(client: TestClient):
    """
    Test 7.2: Uploads exceeding 10 MB limit are rejected with HTTP 400.
    """
    large_payload = b"A" * (10 * 1024 * 1024 + 1)
    res = client.post(
        "/api/v1/evidence/audit",
        files={"file": ("large.csv", large_payload, "text/csv")},
    )
    assert res.status_code == 413
    assert "File size exceeds maximum allowed limit" in res.json()["detail"]


def test_group7_3_empty_filename_rejected(client: TestClient):
    """
    Test 7.3: Upload with empty filename is rejected at framework level with HTTP 422.
    """
    res = client.post(
        "/api/v1/evidence/audit",
        files={"file": ("", b"case_id,activity,timestamp\n", "text/csv")},
    )
    assert res.status_code == 422


def test_group7_4_sha256_cryptographic_digest(client: TestClient, sample_quickstart_path):
    """
    Test 7.4: Manifest SHA-256 matches hashlib computation on uploaded bytes.
    """
    with open(sample_quickstart_path, "rb") as f:
        content = f.read()
    expected_sha = hashlib.sha256(content).hexdigest()

    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    assert res.json()["manifest"]["source_file_sha256"] == expected_sha


def test_group7_5_manifest_fields_reconciliation_and_file_size(client: TestClient, sample_quickstart_path):
    """
    Test 7.5: Manifest accurately includes file size in bytes and reconciliation status.
    """
    with open(sample_quickstart_path, "rb") as f:
        content = f.read()
    expected_len = len(content)

    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/evidence/audit", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    manifest = res.json()["manifest"]
    assert manifest["source_file_size_bytes"] == expected_len
    assert manifest["reconciliation_status"] in ("RECONCILED", "DISCREPANCY_DETECTED")
    assert manifest["is_persisted_snapshot"] is False


def test_group7_6_malformed_optional_json_inputs(client: TestClient, sample_quickstart_path):
    """
    Test 7.6: Syntactically malformed JSON in optional fields returns HTTP 400.
    """
    # Malformed weights
    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"prioritisation_weights": "not-a-json"},
        )
    assert res.status_code == 400

    # Malformed economics
    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"economic_inputs": "{bad:json}"},
        )
    assert res.status_code == 400

    # Malformed domain
    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/evidence/audit",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"domain_assessments": "[incomplete"},
        )
    assert res.status_code == 400


def test_group7_7_backward_compatibility_earlier_endpoints(client: TestClient, sample_quickstart_path):
    """
    Test 7.7: Verify that existing Phase 1-8 endpoints remain completely intact and functional.
    """
    # 1. Health
    h_res = client.get("/health")
    assert h_res.status_code == 200

    # 2. Ingestion
    with open(sample_quickstart_path, "rb") as f:
        v_res = client.post("/api/v1/ingestion/upload", files={"file": ("quickstart.csv", f, "text/csv")})
    assert v_res.status_code == 200

    # 3. Prioritisation
    with open(sample_quickstart_path, "rb") as f:
        p_res = client.post("/api/v1/prioritisation/rank", files={"file": ("quickstart.csv", f, "text/csv")})
    assert p_res.status_code == 200
    assert "ranked_opportunities" in p_res.json()

