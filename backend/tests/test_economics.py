"""
Comprehensive unit and integration test suite for Phase 7 Economics & Strategic Synthesis.
Tests derivation integrity, finite-number enforcement, economic tier classification,
5-branch annualization hierarchy, 64-cell synthesis matrix, and dataset regressions.
"""

import json
import math
import pytest
from fastapi.testclient import TestClient

from app.schemas.opportunity import PriorityTier, OpportunityArchetype
from app.schemas.readiness import OverallReadinessTier
from app.schemas.economics import (
    EconomicTier,
    StrategicDecisionOutcome,
    TimeBasis,
    AnnualisationMethod,
    OpportunityEconomicInput,
)
from app.services.reconstruction import reconstruct_process_from_csv
from app.services.economics import (
    classify_economic_tier,
    verify_internal_derivation_consistency,
    round_half_up,
    SYNTHESIS_DECISION_MAP,
    parse_economic_inputs_json,
    extract_observation_window,
)


# =============================================================================
# GROUP 1: Canonical Derivation & Positive Economics (API & Integration)
# =============================================================================

def test_group1_1_primary_input_pipeline_derivation(client: TestClient, sample_clean_path):
    """
    Test 1.1: Verify canonical primary input derivation on clean dataset (>=30 days window).
    """
    with open(sample_clean_path, "rb") as f:
        # First detect opportunities to obtain valid ID
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("clean.csv", f, "text/csv")})
    assert opp_res.status_code == 200
    opps = opp_res.json()["opportunities"]
    assert len(opps) > 0
    target_opp_id = opps[0]["id"]

    econ_inputs = [
        {
            "opportunity_id": target_opp_id,
            "hourly_labor_rate": 50.0,
            "active_labor_share_percentage": 25.0,
            "touch_labor_minutes_per_occurrence": 15.0,
            "addressable_efficiency_percentage": 20.0,
            "implementation_cost": 10000.0,
            "annual_recurring_cost": 2000.0,
        }
    ]

    with open(sample_clean_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("clean.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()
    assert data["filename"] == "clean.csv"

    # Find the evaluated opportunity
    eval_opp = next(o for o in data["opportunities"] if o["opportunity_id"] == target_opp_id)
    window = eval_opp["observation_window"]
    labor = eval_opp["labor_effort"]
    cap = eval_opp["capacity_valuation"]

    assert window["time_basis"] == TimeBasis.ANNUAL.value
    assert window["annualisation_ratio"] is not None
    assert labor["annual_active_labor_hours"] is not None
    assert labor["annual_addressable_labor_hours"] is not None

    expected_gross = labor["annual_addressable_labor_hours"] * 50.0
    assert abs(cap["gross_annual_capacity_value"] - expected_gross) < 1e-2

    expected_net = expected_gross - 2000.0
    assert abs(cap["net_annual_capacity_benefit"] - expected_net) < 1e-2

    if expected_net > 0:
        expected_payback = (10000.0 / expected_net) * 12.0
        assert abs(cap["payback_period_months"] - expected_payback) < 1e-2
        expected_roi = (((3.0 * expected_net) - 10000.0) / 10000.0) * 100.0
        assert abs(cap["three_year_capacity_roi_percentage"] - expected_roi) < 1e-2

        assert verify_internal_derivation_consistency(
            cap["gross_annual_capacity_value"],
            cap["annual_recurring_cost"],
            cap["net_annual_capacity_benefit"],
            cap["implementation_cost"],
            cap["payback_period_months"],
            cap["three_year_capacity_roi_percentage"],
        )


@pytest.mark.parametrize("field_name,bad_value", [
    ("hourly_labor_rate", float("nan")),
    ("hourly_labor_rate", float("inf")),
    ("hourly_labor_rate", float("-inf")),
    ("active_labor_share_percentage", float("nan")),
    ("touch_labor_minutes_per_occurrence", float("inf")),
    ("addressable_efficiency_percentage", float("nan")),
    ("implementation_cost", float("nan")),
    ("implementation_cost", float("inf")),
    ("annual_recurring_cost", float("nan")),
    ("annual_recurring_cost", float("-inf")),
])
def test_group1_2_boundary_finite_number_enforcement(client: TestClient, sample_clean_path, field_name, bad_value):
    """
    Test 1.2: Boundary finite number enforcement rejects NaN and Infinities.
    """
    # Direct Pydantic schema validation test
    with pytest.raises(Exception):
        OpportunityEconomicInput.model_validate({
            "opportunity_id": "opp_test",
            field_name: bad_value
        })


@pytest.mark.parametrize("bad_override", [-5, 0, 1.2, float("nan"), float("inf")])
def test_group1_3_positive_integer_override_validation(bad_override):
    """
    Test 1.3: Annual case volume override must be a strictly positive integer.
    """
    with pytest.raises(Exception):
        OpportunityEconomicInput.model_validate({
            "opportunity_id": "opp_test",
            "annual_case_volume_override": bad_override
        })


# =============================================================================
# GROUP 2: Internal Classifier Unit Tests (classify_economic_tier)
# =============================================================================

def test_group2_1_contradictory_finite_payback():
    """Test 2.1: Payback inconsistent with net benefit and implementation cost."""
    # B_net = 10,000, C_impl = 10,000 -> Expected payback = 12.0m. Supplied 6.0m is contradictory.
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=10000.0,
        payback_months=6.0,
        three_year_roi=200.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_2_contradictory_finite_three_year_roi():
    """Test 2.2: 3-Year ROI inconsistent with net benefit and implementation cost."""
    # B_net = 10,000, C_impl = 10,000, Payback = 12.0m -> Expected ROI = 200.0%. Supplied 500.0% is contradictory.
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=10000.0,
        payback_months=12.0,
        three_year_roi=500.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_3_negative_implementation_cost():
    """Test 2.3: Implementation cost cannot be negative."""
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=-5000.0,
        payback_months=6.0,
        three_year_roi=500.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_4_negative_payback():
    """Test 2.4: Payback period cannot be negative."""
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=5000.0,
        payback_months=-6.0,
        three_year_roi=500.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_5_zero_cost_with_contradictory_nonzero_payback():
    """Test 2.5: Zero cost project cannot have nonzero payback."""
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=0.0,
        payback_months=6.0,
        three_year_roi=None,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_6_zero_cost_with_defined_roi():
    """Test 2.6: Zero cost project has undefined ROI (division by zero avoided)."""
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=0.0,
        payback_months=0.0,
        three_year_roi=100.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_7_nonpositive_net_benefit_with_contradictory_payback():
    """Test 2.7: Nonpositive net benefit cannot have a finite payback."""
    tier = classify_economic_tier(
        net_benefit=-1000.0,
        implementation_cost=5000.0,
        payback_months=12.0,
        three_year_roi=None,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_8_missing_payback_when_benefit_and_cost_positive():
    """Test 2.8: Missing payback on positive benefit and cost evaluates to INSUFFICIENT."""
    tier = classify_economic_tier(
        net_benefit=10000.0,
        implementation_cost=5000.0,
        payback_months=None,
        three_year_roi=500.0,
    )
    assert tier == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_9_non_finite_arguments():
    """Test 2.9: Any NaN or Infinite argument evaluates to INSUFFICIENT."""
    assert classify_economic_tier(float("nan"), 5000.0, 6.0, 500.0) == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
    assert classify_economic_tier(10000.0, float("inf"), 6.0, 500.0) == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
    assert classify_economic_tier(10000.0, 5000.0, float("nan"), 500.0) == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS
    assert classify_economic_tier(10000.0, 5000.0, 6.0, float("inf")) == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS


def test_group2_10_restored_36_month_payback_boundaries():
    """Test 2.10: Threshold boundaries at 12m, 18m, 36m, and 36.012m."""
    # Payback <= 12m -> COMPELLING_RETURN
    assert classify_economic_tier(10000.0, 10000.0, 12.0, 200.0) == EconomicTier.COMPELLING_RETURN

    # 12m < Payback <= 36m -> MODERATE_RETURN
    assert classify_economic_tier(10000.0, 15000.0, 18.0, 100.0) == EconomicTier.MODERATE_RETURN
    assert classify_economic_tier(10000.0, 30000.0, 36.0, 0.0) == EconomicTier.MODERATE_RETURN

    # Payback > 36m -> MARGINAL_OR_UNECONOMICAL
    # 30010 / 10000 * 12 = 36.012m, ROI = ((30000 - 30010) / 30010) * 100 = -0.0333%
    roi = (((3.0 * 10000.0) - 30010.0) / 30010.0) * 100.0
    assert classify_economic_tier(10000.0, 30010.0, 36.012, roi) == EconomicTier.MARGINAL_OR_UNECONOMICAL


# =============================================================================
# GROUP 3: Input Precedence & Missing vs. Explicit-Zero Disambiguation
# =============================================================================

def test_group3_1_gross_capacity_available_with_missing_recurring_cost(client: TestClient, sample_clean_path):
    """
    Test 3.1: Gross capacity is available as labeled scenario, but missing recurring cost
    suppresses net benefit, payback, ROI, and evaluates to INSUFFICIENT_ECONOMIC_INPUTS.
    """
    with open(sample_clean_path, "rb") as f:
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("clean.csv", f, "text/csv")})
    opp_id = opp_res.json()["opportunities"][0]["id"]

    econ_inputs = [{
        "opportunity_id": opp_id,
        "hourly_labor_rate": 50.0,
        "active_labor_share_percentage": 25.0,
        "touch_labor_minutes_per_occurrence": 15.0,
        "addressable_efficiency_percentage": 20.0,
        "implementation_cost": 10000.0,
        "annual_recurring_cost": None,  # Missing
    }]

    with open(sample_clean_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("clean.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()
    eval_opp = next(o for o in data["opportunities"] if o["opportunity_id"] == opp_id)
    cap = eval_opp["capacity_valuation"]
    synth = eval_opp["synthesis"]

    assert cap["gross_annual_capacity_value"] is not None
    assert cap["annual_recurring_cost"] is None
    assert cap["net_annual_capacity_benefit"] is None
    assert cap["payback_period_months"] is None
    assert cap["three_year_capacity_roi_percentage"] is None
    assert cap["economic_tier"] == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS.value
    assert synth["strategic_decision"] != StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION.value


def test_group3_2_contrast_gross_capacity_available_with_explicit_zero_recurring_cost(client: TestClient, sample_clean_path):
    """
    Test 3.2: Contrast: Explicitly supplied zero recurring cost enables full derivation.
    """
    with open(sample_clean_path, "rb") as f:
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("clean.csv", f, "text/csv")})
    opp_id = opp_res.json()["opportunities"][0]["id"]

    econ_inputs = [{
        "opportunity_id": opp_id,
        "hourly_labor_rate": 50.0,
        "active_labor_share_percentage": 25.0,
        "touch_labor_minutes_per_occurrence": 15.0,
        "addressable_efficiency_percentage": 20.0,
        "implementation_cost": 10000.0,
        "annual_recurring_cost": 0.0,  # Explicitly zero
    }]

    with open(sample_clean_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("clean.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()
    eval_opp = next(o for o in data["opportunities"] if o["opportunity_id"] == opp_id)
    cap = eval_opp["capacity_valuation"]

    assert cap["gross_annual_capacity_value"] is not None
    assert cap["annual_recurring_cost"] == 0.0
    assert cap["net_annual_capacity_benefit"] == cap["gross_annual_capacity_value"]
    assert cap["payback_period_months"] is not None
    assert cap["three_year_capacity_roi_percentage"] is not None


def test_group3_3_missing_implementation_cost(client: TestClient, sample_clean_path):
    """Test 3.3: Missing implementation cost evaluates to INSUFFICIENT."""
    with open(sample_clean_path, "rb") as f:
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("clean.csv", f, "text/csv")})
    opp_id = opp_res.json()["opportunities"][0]["id"]

    econ_inputs = [{
        "opportunity_id": opp_id,
        "hourly_labor_rate": 50.0,
        "active_labor_share_percentage": 25.0,
        "touch_labor_minutes_per_occurrence": 15.0,
        "addressable_efficiency_percentage": 20.0,
        "implementation_cost": None,  # Missing
        "annual_recurring_cost": 2000.0,
    }]

    with open(sample_clean_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("clean.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    eval_opp = next(o for o in res.json()["opportunities"] if o["opportunity_id"] == opp_id)
    assert eval_opp["capacity_valuation"]["economic_tier"] == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS.value


def test_group3_4_zero_labor_rate_precedence():
    """Test 3.4: Zero labor rate with unknown recurring cost is INSUFFICIENT; with confirmed 0.0 is MARGINAL."""
    # (a) Unknown recurring cost -> INSUFFICIENT
    assert classify_economic_tier(None, 5000.0, None, None) == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS

    # (b) Confirmed 0 recurring cost -> net benefit = 0.0 -> MARGINAL
    assert classify_economic_tier(0.0, 5000.0, None, -100.0) == EconomicTier.MARGINAL_OR_UNECONOMICAL


# =============================================================================
# GROUP 4: Precision & Commercial Half-Up Rounding Verification
# =============================================================================

def test_group4_rounding_and_raw_precision():
    """Test 4.1 & 4.2: Commercial half-up rounding policy and precision."""
    assert round_half_up(0.4) == 0
    assert round_half_up(0.5) == 1
    assert round_half_up(2.49) == 2
    assert round_half_up(2.50) == 3
    assert round_half_up(2.51) == 3


# =============================================================================
# GROUP 5: Archetype Labor & Dimension Semantics
# =============================================================================

def test_group5_path_standardization_variant_count_unscaled(client: TestClient, sample_messy_path):
    """
    Test 5.2: In PATH_STANDARDIZATION, distinct rare variants count is a structural property
    and is strictly unscaled, while affected cases scale with volume.
    """
    econ_inputs = [{
        "opportunity_id": "opp_investigate_rare_path_variants",
        "hourly_labor_rate": 50.0,
        "touch_labor_minutes_per_occurrence": 10.0,
        "addressable_efficiency_percentage": 50.0,
        "annual_case_volume_override": 1304,  # Exactly 2x complete cases (652 * 2)
    }]

    with open(sample_messy_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("messy.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()
    rare_opp = next(o for o in data["opportunities"] if o["archetype"] == OpportunityArchetype.PATH_STANDARDIZATION.value)

    window = rare_opp["observation_window"]
    labor = rare_opp["labor_effort"]

    assert window["annualisation_ratio"] == 2.0
    # In messy.csv, sample distinct rare variants is 18
    assert labor["sample_distinct_rare_variants"] == 18
    # Annual occurrences remains unscaled 18
    assert labor["annual_occurrences"] == 18
    # Affected cases scale 2x
    assert labor["annual_affected_cases"] == labor["sample_affected_cases"] * 2


# =============================================================================
# GROUP 6: Annualization Branches & Override Precedence Tests
# =============================================================================

def test_group6_override_with_zero_duration_window():
    """
    Test 6.3: Override with zero-duration complete-case window.
    Synthetic CSV with 50 complete cases all having identical timestamps.
    """
    rows = ["case_id,activity,timestamp"]
    for i in range(1, 51):
        rows.append(f"case_{i},Task A,2026-01-01 00:00:00")
        rows.append(f"case_{i},Task B,2026-01-01 00:00:00")
    csv_content = "\n".join(rows).encode("utf-8")
    reconstruction = reconstruct_process_from_csv(csv_content, "zero_dur.csv")

    window = extract_observation_window(reconstruction, volume_override=50000)
    assert window.time_basis == TimeBasis.ANNUAL
    assert window.annualisation_method == AnnualisationMethod.EXPLICIT_OVERRIDE
    assert window.annualisation_ratio == 50000 / 50  # 1000.0
    assert window.evaluated_case_volume == 50000
    assert window.observation_duration_seconds == 0.0


def test_group6_zero_complete_cases_with_override():
    """
    Test 6.6: Zero complete cases with override suppresses annualization (Root Precedence).
    CSV where every row has missing activity -> 0 complete cases.
    """
    csv_content = "case_id,activity,timestamp\ncase_1,,2026-01-01 00:00:00\ncase_2,,2026-01-02 00:00:00".encode("utf-8")
    reconstruction = reconstruct_process_from_csv(csv_content, "empty_cases.csv")
    assert len([c for c in reconstruction.cases if c.is_complete]) == 0

    window = extract_observation_window(reconstruction, volume_override=50000)
    assert window.time_basis == TimeBasis.UNKNOWN
    assert window.annualisation_method == AnnualisationMethod.NONE
    assert window.annualisation_ratio is None
    assert window.evaluated_case_volume is None


def test_group6_zero_duration_window_without_override():
    """
    Test 6.7: Zero-duration complete-case window without override routes to Branch 5 (Degenerate).
    """
    rows = ["case_id,activity,timestamp"]
    for i in range(1, 11):
        rows.append(f"case_{i},Task A,2026-01-01 00:00:00")
        rows.append(f"case_{i},Task B,2026-01-01 00:00:00")
    csv_content = "\n".join(rows).encode("utf-8")
    reconstruction = reconstruct_process_from_csv(csv_content, "zero_dur.csv")

    window = extract_observation_window(reconstruction, volume_override=None)
    assert window.time_basis == TimeBasis.UNKNOWN
    assert window.annualisation_method == AnnualisationMethod.NONE
    assert window.annualisation_ratio is None
    assert window.evaluated_case_volume is None
    assert window.observation_duration_seconds == 0.0


def test_group6_api_override_precedence_on_dataset(client: TestClient, sample_quickstart_path):
    """
    Test 6.4: API integration test verifying explicit override precedence on real dataset.
    """
    with open(sample_quickstart_path, "rb") as f:
        opp_res = client.post("/api/v1/opportunities/detect", files={"file": ("quickstart.csv", f, "text/csv")})
    assert opp_res.status_code == 200
    opp_id = opp_res.json()["opportunities"][0]["id"]

    econ_inputs = [{"opportunity_id": opp_id, "annual_case_volume_override": 50000}]

    with open(sample_quickstart_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("quickstart.csv", f, "text/csv")},
            data={"economic_inputs": json.dumps(econ_inputs)},
        )
    assert res.status_code == 200
    data = res.json()
    window = data["opportunities"][0]["observation_window"]
    assert window["time_basis"] == TimeBasis.ANNUAL.value
    assert window["annualisation_method"] == AnnualisationMethod.EXPLICIT_OVERRIDE.value
    assert window["annualisation_ratio"] == 50000 / 100  # 500.0
    assert window["evaluated_case_volume"] == 50000


# =============================================================================
# GROUP 7: DATA_INSTRUMENTATION Decision Bypass
# =============================================================================

def test_group7_data_instrumentation_bypass(client: TestClient, sample_messy_path):
    """
    Test Group 7: Ingestion quality finding bypasses matrix to RESOLVE_DATA_INSTRUMENTATION.
    """
    with open(sample_messy_path, "rb") as f:
        res = client.post(
            "/api/v1/economics/evaluate",
            files={"file": ("messy.csv", f, "text/csv")},
        )
    assert res.status_code == 200
    data = res.json()
    inst_opps = [o for o in data["opportunities"] if o["archetype"] == OpportunityArchetype.DATA_INSTRUMENTATION.value]

    if inst_opps:
        inst_opp = inst_opps[0]
        synth = inst_opp["synthesis"]
        assert synth["strategic_decision"] == StrategicDecisionOutcome.RESOLVE_DATA_INSTRUMENTATION.value
        assert "Data instrumentation opportunity" in synth["decision_rationale"]
        assert inst_opp["capacity_valuation"]["economic_tier"] == EconomicTier.INSUFFICIENT_ECONOMIC_INPUTS.value
        assert inst_opp["labor_effort"]["sample_active_labor_hours"] is None


# =============================================================================
# GROUP 8: Tri-Partite Independence & Deployment Boundary Tests
# =============================================================================

def test_group8_1_compelling_economics_cannot_override_blocked_readiness():
    """
    Test 8.1: High priority, prohibited readiness, compelling return maps to BLOCKED_HIGH_POTENTIAL.
    """
    outcome = SYNTHESIS_DECISION_MAP[
        (PriorityTier.TIER_1_HIGH, OverallReadinessTier.PROHIBITED_OR_BLOCKED, EconomicTier.COMPELLING_RETURN)
    ]
    assert outcome == StrategicDecisionOutcome.BLOCKED_HIGH_POTENTIAL
    assert outcome != StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION


def test_group8_2_perfect_readiness_cannot_override_uneconomical_return():
    """
    Test 8.2: High priority, ready for specification, uneconomical return maps to REVISE_SCOPE_OR_RENEGOTIATE.
    """
    outcome = SYNTHESIS_DECISION_MAP[
        (PriorityTier.TIER_1_HIGH, OverallReadinessTier.READY_FOR_SPECIFICATION, EconomicTier.MARGINAL_OR_UNECONOMICAL)
    ]
    assert outcome == StrategicDecisionOutcome.REVISE_SCOPE_OR_RENEGOTIATE
    assert outcome != StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION


# =============================================================================
# GROUP 9: Uniform Blocked-Readiness Visibility & Full 64-Cell Mapping Table
# =============================================================================

def test_group9_1_uniform_blocked_readiness_visibility():
    """
    Test 9.1: All 16 combinations with PROHIBITED_OR_BLOCKED map strictly to BLOCKED_ outcomes.
    Zero blocked combinations evaluate to DEFER_OR_ARCHIVE or proceed outcomes.
    """
    for (priority, readiness, econ_tier), outcome in SYNTHESIS_DECISION_MAP.items():
        if readiness == OverallReadinessTier.PROHIBITED_OR_BLOCKED:
            assert outcome.value.startswith("BLOCKED_"), f"Failed for {priority}, {readiness}, {econ_tier}"
            assert outcome != StrategicDecisionOutcome.DEFER_OR_ARCHIVE
            assert outcome != StrategicDecisionOutcome.SPECIFY_AUTOMATION_SOLUTION
            assert outcome != StrategicDecisionOutcome.PROCEED_WITH_GUARDRAILS


def test_group9_2_full_64_cell_matrix_coverage():
    """
    Test 9.2: Assert all 64 possible combinations exist in SYNTHESIS_DECISION_MAP.
    """
    assert len(SYNTHESIS_DECISION_MAP) == 64
    for p in PriorityTier:
        for r in OverallReadinessTier:
            for e in EconomicTier:
                assert (p, r, e) in SYNTHESIS_DECISION_MAP


# =============================================================================
# GROUP 10: Verified Dataset Regressions
# =============================================================================

def test_group10_quickstart_regression(client: TestClient, sample_quickstart_path):
    with open(sample_quickstart_path, "rb") as f:
        res = client.post("/api/v1/economics/evaluate", files={"file": ("quickstart.csv", f, "text/csv")})
    assert res.status_code == 200
    assert res.json()["filename"] == "quickstart.csv"


def test_group10_clean_regression(client: TestClient, sample_clean_path):
    with open(sample_clean_path, "rb") as f:
        res = client.post("/api/v1/economics/evaluate", files={"file": ("clean.csv", f, "text/csv")})
    assert res.status_code == 200
    assert res.json()["filename"] == "clean.csv"


def test_group10_rework_regression(client: TestClient, sample_rework_path):
    with open(sample_rework_path, "rb") as f:
        res = client.post("/api/v1/economics/evaluate", files={"file": ("rework.csv", f, "text/csv")})
    assert res.status_code == 200
    assert res.json()["filename"] == "rework.csv"


def test_group10_messy_regression(client: TestClient, sample_messy_path):
    with open(sample_messy_path, "rb") as f:
        res = client.post("/api/v1/economics/evaluate", files={"file": ("messy.csv", f, "text/csv")})
    assert res.status_code == 200
    assert res.json()["filename"] == "messy.csv"
