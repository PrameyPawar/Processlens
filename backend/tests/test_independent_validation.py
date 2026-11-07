"""Regression benchmark against the separately labeled synthetic returns holdout."""
import csv
import json
from pathlib import Path

from app.services.reconstruction import reconstruct_process_from_csv
from app.services.analytics import calculate_process_analytics
from app.services.detection import detect_process_problems

ROOT = Path(__file__).resolve().parents[2]
BUNDLE = ROOT / "processlens_independent_validation_bundle"


def _rows(path):
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def test_independent_returns_holdout_metrics_and_rework_labels():
    source = (BUNDLE / "processlens_independent_returns_holdout.csv").read_bytes()
    reference = json.loads((BUNDLE / "processlens_returns_expected_results.json").read_text(encoding="utf-8"))
    reconstruction = reconstruct_process_from_csv(source, "processlens_independent_returns_holdout.csv")
    analytics = calculate_process_analytics(reconstruction)
    findings = detect_process_problems(reconstruction, analytics)

    assert reconstruction.total_source_rows == reference["event_count"]
    assert reconstruction.total_cases_found == reference["case_count"]
    assert reconstruction.complete_cases_count == reference["expected_complete_cases"]
    assert reconstruction.incomplete_cases_count == 0
    assert reconstruction.variant_count == 2

    cycle = analytics.cycle_time.duration_stats
    assert cycle.min_seconds / 3600 == reference["reference_cycle_time_hours"]["min"]
    assert cycle.median_seconds / 3600 == reference["reference_cycle_time_hours"]["median"]
    assert round(cycle.mean_seconds / 3600, 4) == reference["reference_cycle_time_hours"]["mean"]
    assert cycle.p90_seconds / 3600 == reference["reference_cycle_time_hours"]["p90"]
    assert cycle.max_seconds / 3600 == reference["reference_cycle_time_hours"]["max"]

    actual = {(f"{t.source_activity} -> {t.target_activity}"): t for t in analytics.transitions}
    assert set(actual) == {row["transition"] for row in reference["reference_transition_durations_hours"]}
    for expected in reference["reference_transition_durations_hours"]:
        metric = actual[expected["transition"]]
        stats = metric.duration_stats
        assert metric.transition_count == expected["count"]
        assert round(stats.mean_seconds / 3600, 4) == expected["mean_hours"]
        assert stats.median_seconds / 3600 == expected["median_hours"]
        assert stats.max_seconds / 3600 == expected["max_hours"]

    labels = {row["case_id"]: row for row in _rows(BUNDLE / "processlens_returns_ground_truth_labels.csv")}
    inspected = {case.case_id for case in reconstruction.cases
                 if sum(event.activity == "Item Inspected" for event in case.events) > 1}
    expected_rework = {case_id for case_id, row in labels.items()
                       if row["expected_inspection_rework"].lower() == "true"}
    assert inspected == expected_rework
    tp = len(inspected & expected_rework)
    fp = len(inspected - expected_rework)
    fn = len(expected_rework - inspected)
    assert (tp, fp, fn) == (10, 0, 0)
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    assert precision == recall == 1.0

    primary = max(analytics.transitions, key=lambda item: item.duration_stats.mean_seconds)
    assert f"{primary.source_activity} -> {primary.target_activity}" == "Refund Review -> Refund Approved"
    assert findings.summary.evaluated_cases_count == reference["case_count"]

