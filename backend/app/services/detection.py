"""
Deterministic problem detection and operational signals domain service (Phase 4).
Consumes Phase 2 reconstruction and Phase 3 analytics results.
"""

import re
from typing import List, Dict, Any, Tuple
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import (
    FindingCategory,
    SignalLevel,
    SeverityLevel,
    EvidenceStrength,
    ReconciliationStatus,
    DetectionSummary,
    ProblemFinding,
    ProblemDetectionResult,
)


def slugify(text: str) -> str:
    """Creates a deterministic URL-safe snake_case identifier from arbitrary text."""
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "_", text).strip("_").lower()
    return cleaned or "unknown"


def evaluate_evidence_strength(sample_size: int) -> EvidenceStrength:
    """
    Evaluates finding-specific evidence strength based strictly on the evaluated sample size
    for that specific finding (e.g. transition executions, recurrence cases, or variant cases).
    Thresholds:
      - >= 30: HIGH
      - 10 to 29: MODERATE
      - < 10: LIMITED
    """
    if sample_size >= 30:
        return EvidenceStrength.HIGH
    elif sample_size >= 10:
        return EvidenceStrength.MODERATE
    else:
        return EvidenceStrength.LIMITED


def compute_percentile(sorted_values: List[float], p: float) -> float:
    """
    Deterministic linear interpolation percentile calculation.
    Rank formula: p * (n - 1)
    """
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if n == 1:
        return float(sorted_values[0])

    rank = p * (n - 1)
    lower_idx = int(rank)
    fraction = rank - lower_idx
    if lower_idx + 1 < n:
        return sorted_values[lower_idx] + fraction * (
            sorted_values[lower_idx + 1] - sorted_values[lower_idx]
        )
    return float(sorted_values[lower_idx])


def detect_process_problems(
    reconstruction: ProcessReconstructionResult,
    analytics: ProcessAnalyticsResult,
    duration_share_threshold_pct: float = 20.0,
    tolerance_percentage: float = 1.0,
) -> ProblemDetectionResult:
    """
    Detects deterministic process operational signals:
      1. Accounting integrity check (transition durations vs complete-case cycle time).
      2. Transition duration concentration (suppressed if reconciliation fails or cycle time is 0).
      3. Repeated activity / recurrence indicators.
      4. Cycle-time Tukey 1.5x IQR outliers.
      5. Rare process variant path variation.
      6. Data quality limitations (reconciliation discrepancies, zero cycle time, small samples).

    All metrics operate strictly on complete cases.
    Signal prominence is strictly separated from statistical evidence strength.
    """
    complete_cases = [c for c in reconstruction.cases if c.is_complete]
    n_complete = len(complete_cases)

    # 1. Cumulative Process Cycle Time across complete cases
    case_cycle_times: List[float] = []
    for c in complete_cases:
        if c.start_time and c.end_time:
            ct = max(0.0, (c.end_time - c.start_time).total_seconds())
        else:
            ct = 0.0
        case_cycle_times.append(ct)
    cumulative_cycle_time = sum(case_cycle_times)

    # 2. Total Transition Duration from complete-case transitions
    total_transition_duration = 0.0
    for t in analytics.transitions:
        dur = t.transition_count * t.duration_stats.mean_seconds
        total_transition_duration += dur

    # 3. Accounting Reconciliation Health Check
    discrepancy_seconds = abs(total_transition_duration - cumulative_cycle_time)
    if cumulative_cycle_time > 0.0:
        discrepancy_pct = (discrepancy_seconds / cumulative_cycle_time) * 100.0
        reconciled = discrepancy_pct <= tolerance_percentage
    else:
        if total_transition_duration == 0.0:
            discrepancy_pct = 0.0
            reconciled = True
        else:
            discrepancy_pct = 100.0
            reconciled = False

    duration_share_suppressed = (not reconciled) or (cumulative_cycle_time == 0.0)

    reconciliation_status = ReconciliationStatus(
        reconciled=reconciled,
        total_transition_duration_seconds=round(total_transition_duration, 2),
        cumulative_cycle_time_seconds=round(cumulative_cycle_time, 2),
        discrepancy_seconds=round(discrepancy_seconds, 2),
        discrepancy_percentage=round(discrepancy_pct, 6),
        tolerance_percentage=tolerance_percentage,
        duration_share_suppressed=duration_share_suppressed,
    )

    findings: List[ProblemFinding] = []

    # Rule A: Accounting Reconciliation Discrepancy
    if not reconciled:
        signal_level = (
            SignalLevel.HIGH
            if discrepancy_pct > 10.0
            else SignalLevel.MEDIUM
        )
        findings.append(
            ProblemFinding(
                id="finding_accounting_reconciliation_discrepancy",
                category=FindingCategory.DATA_QUALITY_LIMITATION,
                rule="ACCOUNTING_RECONCILIATION_DISCREPANCY",
                title="Transition Durations Do Not Reconcile With Process Cycle Time",
                signal_level=signal_level,
                severity=signal_level,
                evidence_strength=EvidenceStrength.HIGH,
                metrics={
                    "total_transition_duration_seconds": round(
                        total_transition_duration, 2
                    ),
                    "cumulative_cycle_time_seconds": round(
                        cumulative_cycle_time, 2
                    ),
                    "discrepancy_seconds": round(discrepancy_seconds, 2),
                    "discrepancy_percentage": round(discrepancy_pct, 4),
                    "tolerance_percentage": tolerance_percentage,
                },
                explanation=(
                    f"Total eligible transition duration ({total_transition_duration:.2f}s) differs from "
                    f"cumulative complete-case cycle time ({cumulative_cycle_time:.2f}s) by "
                    f"{discrepancy_seconds:.2f}s ({discrepancy_pct:.4f}%). Because this exceeds the "
                    f"{tolerance_percentage:.1f}% accounting integrity threshold, transition duration-share "
                    f"findings have been suppressed to prevent misleading attribution."
                ),
                limitations=[
                    "Reconciliation discrepancy indicates that recorded event intervals do not sum to total case spans, possibly due to unrecorded intermediate gaps, missing timestamps, or multi-threaded tracking.",
                    "Duration-share rankings are suppressed to avoid misleading attribution.",
                ],
            )
        )

    # Rule B: Zero Cycle Time Process
    if n_complete > 0 and cumulative_cycle_time == 0.0:
        findings.append(
            ProblemFinding(
                id="finding_zero_cycle_time_process",
                category=FindingCategory.DATA_QUALITY_LIMITATION,
                rule="ZERO_CYCLE_TIME_PROCESS",
                title="Process Has Zero Recorded Elapsed Cycle Time",
                signal_level=SignalLevel.INFO,
                severity=SignalLevel.INFO,
                evidence_strength=EvidenceStrength.HIGH,
                metrics={
                    "evaluated_cases_count": n_complete,
                    "cumulative_cycle_time_seconds": 0.0,
                },
                explanation=(
                    "All evaluated complete cases have a recorded cycle time of 0.0 seconds "
                    "(e.g., single-event cases or simultaneous timestamps). Transition duration-share "
                    "calculations are undefined and suppressed."
                ),
                limitations=[
                    "Source event data does not contain multi-milestone elapsed intervals."
                ],
            )
        )

    # Rule C: Small Sample Caution
    if 0 < n_complete < 10:
        findings.append(
            ProblemFinding(
                id="finding_small_sample_caution",
                category=FindingCategory.DATA_QUALITY_LIMITATION,
                rule="SMALL_SAMPLE_CAUTION",
                title="Limited Sample Size For Problem Detection",
                signal_level=SignalLevel.INFO,
                severity=SignalLevel.INFO,
                evidence_strength=EvidenceStrength.LIMITED,
                metrics={"evaluated_cases_count": n_complete},
                explanation=(
                    f"Only {n_complete} complete cases were evaluated. Statistical dispersion metrics, "
                    f"percentile calculations, and duration shares have high uncertainty with small sample sizes (<10 cases)."
                ),
                limitations=[
                    "All findings should be interpreted with extreme caution until a larger volume of complete cases is collected."
                ],
            )
        )

    # Rule D: Transition Duration Concentration (when verified and cycle time > 0)
    if not duration_share_suppressed and cumulative_cycle_time > 0.0:
        for t in analytics.transitions:
            dur = t.transition_count * t.duration_stats.mean_seconds
            share = (dur / cumulative_cycle_time) * 100.0
            if share >= duration_share_threshold_pct:
                m_tau = t.transition_count
                strength = evaluate_evidence_strength(m_tau)

                # Signal prominence is based strictly on concentration magnitude in data
                if share >= 40.0:
                    signal_level = SignalLevel.HIGH
                elif share >= 25.0:
                    signal_level = SignalLevel.MEDIUM
                else:
                    signal_level = SignalLevel.LOW

                slug = f"{slugify(t.source_activity)}_{slugify(t.target_activity)}"
                findings.append(
                    ProblemFinding(
                        id=f"finding_transition_{slug}",
                        category=FindingCategory.DURATION_CONCENTRATION,
                        rule="TRANSITION_DURATION_SHARE",
                        title=f"High Duration Concentration on {t.source_activity} to {t.target_activity}",
                        signal_level=signal_level,
                        severity=signal_level,
                        evidence_strength=strength,
                        metrics={
                            "source_activity": t.source_activity,
                            "target_activity": t.target_activity,
                            "transition_count": t.transition_count,
                            "case_count": t.case_count,
                            "mean_duration_seconds": round(
                                t.duration_stats.mean_seconds, 2
                            ),
                            "median_duration_seconds": round(
                                t.duration_stats.median_seconds, 2
                            ),
                            "p90_duration_seconds": round(
                                t.duration_stats.p90_seconds, 2
                            ),
                            "cumulative_transition_duration_seconds": round(
                                dur, 2
                            ),
                            "duration_share_percentage": round(share, 2),
                        },
                        explanation=(
                            f"Transition '{t.source_activity}' -> '{t.target_activity}' accounts for "
                            f"{share:.2f}% of cumulative complete-case cycle time across {t.transition_count} "
                            f"executions (mean elapsed duration {t.duration_stats.mean_seconds:.2f}s)."
                        ),
                        limitations=[
                            "Elapsed transition duration reflects chronological time between milestone recordings and does not distinguish active work from waiting time without explicit start/end lifecycle timestamps.",
                            "Duration concentration indicates where elapsed time accumulates; it does not independently prove an operational bottleneck, constraint, defect, or inefficiency without domain context.",
                        ],
                    )
                )

    # Rule E: Activity Recurrence (Repeated Activities)
    for r in analytics.rework:
        if r.rework_case_count > 0:
            strength = evaluate_evidence_strength(r.rework_case_count)

            # Signal prominence is based on prevalence of recurrence
            if r.rework_case_percentage >= 30.0:
                signal_level = SignalLevel.HIGH
            elif r.rework_case_percentage >= 15.0:
                signal_level = SignalLevel.MEDIUM
            else:
                signal_level = SignalLevel.LOW

            slug = slugify(r.activity)
            findings.append(
                ProblemFinding(
                    id=f"finding_recurrence_{slug}",
                    category=FindingCategory.REPETITION,
                    rule="ACTIVITY_RECURRENCE",
                    title=f"Repeated Execution of {r.activity}",
                    signal_level=signal_level,
                    severity=signal_level,
                    evidence_strength=strength,
                    metrics={
                        "activity": r.activity,
                        "recurrence_case_count": r.rework_case_count,
                        "recurrence_case_percentage": round(
                            r.rework_case_percentage, 2
                        ),
                        "recurrence_occurrences": r.rework_occurrences,
                        "duplicate_events_count": r.duplicate_events_count,
                        "potential_duplicate_events_count": r.potential_duplicate_events_count,
                        # Backward-compatibility aliases
                        "rework_case_count": r.rework_case_count,
                        "rework_case_percentage": round(
                            r.rework_case_percentage, 2
                        ),
                        "rework_occurrences": r.rework_occurrences,
                    },
                    explanation=(
                        f"Activity '{r.activity}' recurred at distinct timestamps in {r.rework_case_count} "
                        f"complete cases ({r.rework_case_percentage:.2f}%), with {r.rework_occurrences} "
                        f"total repeated occurrences beyond initial execution."
                    ),
                    limitations=[
                        "Repeated activities indicate re-execution patterns, which may represent intended operational rework, iterative review, or standard multi-step procedures.",
                        "Prevalent recurrence is an observation of process behavior, not independent proof of operational waste or process failure.",
                        f"Confirmed repeated source IDs ({r.duplicate_events_count}) and possible identity collisions ({r.potential_duplicate_events_count}) are tracked separately; ambiguous rows are not removed from analytics.",
                    ],
                )
            )

    # Rule F: Cycle-Time Outliers (Tukey 1.5x IQR Rule)
    if n_complete > 0:
        ct_sorted = sorted(case_cycle_times)
        q1 = compute_percentile(ct_sorted, 0.25)
        q3 = compute_percentile(ct_sorted, 0.75)
        iqr = q3 - q1

        if iqr == 0.0:
            strength = evaluate_evidence_strength(n_complete)
            findings.append(
                ProblemFinding(
                    id="finding_zero_variance_cycle_time",
                    category=FindingCategory.DATA_QUALITY_LIMITATION,
                    rule="ZERO_VARIANCE_CYCLE_TIME",
                    title="Zero Variance in Process Cycle Times",
                    signal_level=SignalLevel.INFO,
                    severity=SignalLevel.INFO,
                    evidence_strength=strength,
                    metrics={
                        "evaluated_cases_count": n_complete,
                        "q1_seconds": round(q1, 2),
                        "q3_seconds": round(q3, 2),
                        "iqr_seconds": 0.0,
                    },
                    explanation=(
                        f"All evaluated complete cases have identical cycle times ({q1:.2f}s, IQR = 0.0s). "
                        f"No statistical cycle-time outliers detected."
                    ),
                    limitations=[
                        "Cycle-time distribution has zero dispersion, rendering Tukey outlier fences non-applicable."
                    ],
                )
            )
        else:
            upper_fence = q3 + 1.5 * iqr
            outliers = []
            for c, ct in zip(complete_cases, case_cycle_times):
                if ct > upper_fence:
                    outliers.append((c.case_id, ct))

            if outliers:
                outlier_count = len(outliers)
                outlier_pct = (outlier_count / n_complete) * 100.0
                strength = evaluate_evidence_strength(n_complete)
                signal_level = (
                    SignalLevel.MEDIUM
                    if outlier_pct >= 5.0
                    else SignalLevel.LOW
                )

                findings.append(
                    ProblemFinding(
                        id="finding_cycle_time_outliers",
                        category=FindingCategory.CYCLE_TIME_OUTLIER,
                        rule="CYCLE_TIME_TUKEY_OUTLIER",
                        title="Cycle-Time Outliers Exceeding Statistical Upper Fence",
                        signal_level=signal_level,
                        severity=signal_level,
                        evidence_strength=strength,
                        metrics={
                            "evaluated_cases_count": n_complete,
                            "q1_seconds": round(q1, 2),
                            "q3_seconds": round(q3, 2),
                            "iqr_seconds": round(iqr, 2),
                            "upper_fence_seconds": round(upper_fence, 2),
                            "outlier_case_count": outlier_count,
                            "outlier_case_percentage": round(outlier_pct, 2),
                            "sample_outlier_case_ids": [
                                oid for oid, _ in outliers[:10]
                            ],
                        },
                        explanation=(
                            f"{outlier_count} complete cases ({outlier_pct:.2f}%) exceed the Tukey upper fence "
                            f"of {upper_fence:.2f}s (Q3 + 1.5*IQR)."
                        ),
                        limitations=[
                            "Tukey fence is a non-parametric statistical dispersion heuristic, not proof of operational defect or business impact.",
                            "Outlier cases may reflect valid process exceptions, complex customer orders, or intentional holding periods.",
                        ],
                    )
                )

    # Rule G: Rare Process Variants
    rare_variants = [v for v in reconstruction.variants if v.percentage < 2.0]
    if rare_variants:
        rare_case_count = sum(v.case_count for v in rare_variants)
        rare_case_pct = (
            (rare_case_count / n_complete * 100.0) if n_complete > 0 else 0.0
        )
        strength = evaluate_evidence_strength(rare_case_count)

        findings.append(
            ProblemFinding(
                id="finding_rare_process_variants",
                category=FindingCategory.PATH_VARIATION,
                rule="RARE_PROCESS_VARIANT",
                title="High Process Path Variation (Infrequent Variants)",
                signal_level=SignalLevel.LOW,
                severity=SignalLevel.LOW,
                evidence_strength=strength,
                metrics={
                    "rare_variant_count": len(rare_variants),
                    "rare_variant_frequency_threshold_percentage": 2.0,
                    "total_variant_count": len(reconstruction.variants),
                    "rare_case_count": rare_case_count,
                    "rare_case_percentage": round(rare_case_pct, 2),
                    "sample_rare_variant_ids": [
                        v.variant_id for v in rare_variants[:5]
                    ],
                },
                explanation=(
                    f"Identified {len(rare_variants)} rare process variants (<2.0% frequency) accounting for "
                    f"{rare_case_count} complete cases ({rare_case_pct:.2f}%)."
                ),
                limitations=[
                    "Infrequent variants may represent valid operational edge cases, customized paths, or data collection discrepancies.",
                    "Low frequency does not inherently indicate process failure or non-compliance.",
                ],
            )
        )

    # Deterministic Sorting of Findings by Signal Prominence
    signal_order = {
        SignalLevel.HIGH: 0,
        SignalLevel.MEDIUM: 1,
        SignalLevel.LOW: 2,
        SignalLevel.INFO: 3,
    }
    findings.sort(
        key=lambda f: (
            signal_order.get(f.signal_level, 99),
            f.category.value,
            f.id,
        )
    )

    high_cnt = sum(1 for f in findings if f.signal_level == SignalLevel.HIGH)
    med_cnt = sum(1 for f in findings if f.signal_level == SignalLevel.MEDIUM)
    low_cnt = sum(1 for f in findings if f.signal_level == SignalLevel.LOW)
    info_cnt = sum(1 for f in findings if f.signal_level == SignalLevel.INFO)

    summary = DetectionSummary(
        evaluated_cases_count=n_complete,
        total_findings_count=len(findings),
        high_signal_count=high_cnt,
        medium_signal_count=med_cnt,
        low_signal_count=low_cnt,
        info_signal_count=info_cnt,
        high_severity_count=high_cnt,
        medium_severity_count=med_cnt,
        low_severity_count=low_cnt,
        info_severity_count=info_cnt,
        reconciliation=reconciliation_status,
    )

    return ProblemDetectionResult(
        filename=analytics.filename, summary=summary, findings=findings
    )
