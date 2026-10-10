"""
Deterministic domain service for Process Improvement and Automation Opportunity Detection (Phase 5).
Transforms Phase 2 reconstruction, Phase 3 analytics, and Phase 4 problem findings into
structured, evidence-backed Opportunity Candidates with transparent priority rankings.
"""

from typing import List, Dict, Any, Tuple
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import ProcessAnalyticsResult
from app.schemas.detection import ProblemDetectionResult, FindingCategory, EvidenceStrength
from app.schemas.opportunity import (
    OpportunityArchetype,
    InterventionCategory,
    PriorityTier,
    ScoreBreakdown,
    OpportunityCandidate,
    OpportunitySummary,
    OpportunityDetectionResult,
)
from app.services.detection import slugify


def calculate_opportunity_score(
    archetype: OpportunityArchetype,
    affected_case_percentage: float,
    concentration_metric_value: float,
    evidence_strength: EvidenceStrength,
) -> Tuple[float, PriorityTier, ScoreBreakdown]:
    """
    Computes deterministic operational priority score (0.0 to 100.0) based on:
      1. Coverage Score (0.0 to 50.0): Extent of process population affected.
      2. Concentration Score (0.0 to 50.0): Archetype-specific operational magnitude.
      3. Evidence Weight: Sample size confidence discount factor.

    This score ranks measured operational patterns for investigation.
    It does NOT establish avoidability, business value, ROI, savings, or intervention readiness.
    """
    # 1. Coverage Score (0 to 50 points based on % of complete cases affected)
    bounded_case_pct = max(0.0, min(100.0, affected_case_percentage))
    coverage_score = round(50.0 * (bounded_case_pct / 100.0), 2)

    # 2. Concentration / Magnitude Score (0 to 50 points based on archetype metric)
    bounded_conc = max(0.0, concentration_metric_value)
    if archetype == OpportunityArchetype.DELAY_COMPRESSION:
        # 50 points when duration share reaches 50% or more
        concentration_score = round(50.0 * min(1.0, bounded_conc / 50.0), 2)
    elif archetype == OpportunityArchetype.RECURRENCE_REDUCTION:
        # 50 points when recurrence prevalence reaches 50% or more
        concentration_score = round(50.0 * min(1.0, bounded_conc / 50.0), 2)
    elif archetype == OpportunityArchetype.TAIL_VARIANCE_MITIGATION:
        # Outliers represent distribution tail; 50 points when outliers reach 20% of cases
        concentration_score = round(50.0 * min(1.0, bounded_conc / 20.0), 2)
    elif archetype == OpportunityArchetype.PATH_STANDARDIZATION:
        # 50 points when rare variants account for 50% or more of cases
        concentration_score = round(50.0 * min(1.0, bounded_conc / 50.0), 2)
    elif archetype == OpportunityArchetype.DATA_INSTRUMENTATION:
        # 50 points when accounting discrepancy reaches 10%
        concentration_score = round(50.0 * min(1.0, bounded_conc / 10.0), 2)
    else:
        concentration_score = round(50.0 * min(1.0, bounded_conc / 50.0), 2)

    raw_score = round(coverage_score + concentration_score, 2)

    # 3. Evidence Weight Discount Factor
    if evidence_strength == EvidenceStrength.HIGH:
        evidence_weight = 1.0
    elif evidence_strength == EvidenceStrength.MODERATE:
        evidence_weight = 0.75
    else:  # LIMITED
        evidence_weight = 0.40

    final_score = round(raw_score * evidence_weight, 2)

    # 4. Priority Tier Determination
    # Guardrail: LIMITED evidence always assigns TIER_4_EXPLORATORY regardless of score
    if evidence_strength == EvidenceStrength.LIMITED or final_score < 20.0:
        priority_tier = PriorityTier.TIER_4_EXPLORATORY
    elif final_score >= 60.0:
        priority_tier = PriorityTier.TIER_1_HIGH
    elif final_score >= 40.0:
        priority_tier = PriorityTier.TIER_2_MEDIUM
    else:
        priority_tier = PriorityTier.TIER_3_LOW

    breakdown = ScoreBreakdown(
        coverage_score=coverage_score,
        concentration_score=concentration_score,
        raw_score=raw_score,
        evidence_weight=evidence_weight,
        final_score=final_score,
    )

    return final_score, priority_tier, breakdown


def detect_improvement_opportunities(
    reconstruction: ProcessReconstructionResult,
    analytics: ProcessAnalyticsResult,
    detection: ProblemDetectionResult,
) -> OpportunityDetectionResult:
    """
    Deterministic domain service converting verified problem findings into structured,
    traceable Opportunity Candidates.
    """
    if hasattr(reconstruction, "complete_cases_count"):
        n_complete = reconstruction.complete_cases_count
    elif hasattr(analytics, "reconstruction_summary") and hasattr(analytics.reconstruction_summary, "complete_cases"):
        n_complete = analytics.reconstruction_summary.complete_cases
    else:
        n_complete = len([c for c in getattr(reconstruction, "cases", []) if getattr(c, "is_complete", True)])
    reconciliation_passed = detection.summary.reconciliation.reconciled

    candidates_map: Dict[Tuple[OpportunityArchetype, str], OpportunityCandidate] = {}

    for finding in detection.findings:
        # Rule 1: Delay Compression from Transition Duration Concentration
        if (
            finding.category in (FindingCategory.DURATION_CONCENTRATION, FindingCategory.BOTTLENECK)
            and finding.rule == "TRANSITION_DURATION_SHARE"
        ):
            source = str(finding.metrics.get("source_activity", "unknown"))
            target = str(finding.metrics.get("target_activity", "unknown"))
            t_count = int(finding.metrics.get("transition_count", 0))
            c_count = int(finding.metrics.get("case_count", 0))
            mean_sec = float(finding.metrics.get("mean_duration_seconds", 0.0))
            share = float(finding.metrics.get("duration_share_percentage", 0.0))
            cum_sec = float(finding.metrics.get("cumulative_transition_duration_seconds", 0.0))

            case_pct = round((c_count / n_complete) * 100.0, 2) if n_complete > 0 else 0.0
            score, tier, breakdown = calculate_opportunity_score(
                OpportunityArchetype.DELAY_COMPRESSION,
                case_pct,
                share,
                finding.evidence_strength,
            )

            target_entity = f"{source} -> {target}"
            opp_id = f"opp_delay_{slugify(source)}_{slugify(target)}"
            actions = [
                f"Investigate whether elapsed duration between '{source}' and '{target}' reflects active working time, queueing delay, physical processing, or external dependencies.",
                f"Evaluate candidate intervention levers (e.g. handoff streamlining, schedule coordination, or system integration if manual data re-entry is confirmed).",
            ]

            candidate = OpportunityCandidate(
                id=opp_id,
                title=f"Compress Elapsed Duration on {source} to {target}",
                archetype=OpportunityArchetype.DELAY_COMPRESSION,
                intervention_category=InterventionCategory.UNDETERMINED_INVESTIGATION,
                target_entity=target_entity,
                source_finding_ids=[finding.id],
                evidence_strength=finding.evidence_strength,
                affected_case_count=c_count,
                affected_case_percentage=case_pct,
                occurrence_count=t_count,
                cumulative_time_seconds=cum_sec,
                duration_share_percentage=share,
                observed_facts=[
                    f"Transition '{source}' -> '{target}' executed {t_count} times across {c_count} complete cases ({case_pct:.2f}%).",
                    f"Accounts for {share:.2f}% of cumulative complete-case cycle time with mean elapsed milestone duration of {mean_sec:.2f}s.",
                ],
                investigation_hypotheses=[
                    f"Determine whether elapsed duration between '{source}' and '{target}' reflects active working time, queueing delays, or external dependencies.",
                    f"Assess whether prerequisites for '{target}' can be initiated earlier or completed asynchronously.",
                ],
                candidate_actions=actions,
                candidate_interventions=actions,
                rationale=(
                    f"High elapsed duration concentration ({share:.2f}% of cumulative complete-case cycle time) identifies an operational pattern "
                    f"prioritised for investigation to evaluate potential cycle-time compression."
                ),
                limitations=[
                    "Milestone timestamps reflect chronological elapsed time between events and do not separate active labor from queueing, idle time, or physical processing.",
                    "High duration concentration is an operational observation; it does not establish that the transition is unnecessary, avoidable, or suitable for automation without workflow review.",
                    "Implementation and automation readiness are evaluated separately and are not determined from event logs alone.",
                ],
                operational_priority_score=score,
                priority_tier=tier,
                score_breakdown=breakdown,
            )
            _merge_or_add_candidate(candidates_map, candidate)

        # Rule 2: Recurrence Reduction from Repeated Activities
        elif (
            finding.category == FindingCategory.REPETITION
            and finding.rule == "ACTIVITY_RECURRENCE"
        ):
            activity = str(finding.metrics.get("activity", "unknown"))
            r_count = int(
                finding.metrics.get(
                    "recurrence_case_count",
                    finding.metrics.get("rework_case_count", 0),
                )
            )
            r_pct = float(
                finding.metrics.get(
                    "recurrence_case_percentage",
                    finding.metrics.get("rework_case_percentage", 0.0),
                )
            )
            r_occ = int(
                finding.metrics.get(
                    "recurrence_occurrences",
                    finding.metrics.get("rework_occurrences", 0),
                )
            )
            dup_count = int(finding.metrics.get("duplicate_events_count", 0))

            score, tier, breakdown = calculate_opportunity_score(
                OpportunityArchetype.RECURRENCE_REDUCTION,
                r_pct,
                r_pct,
                finding.evidence_strength,
            )

            opp_id = f"opp_recurrence_{slugify(activity)}"
            actions = [
                f"Investigate root causes of repeated executions for '{activity}' with process owners (e.g. specification changes, missing intake data, or intentional review iterations).",
                f"Evaluate candidate interventions such as upstream intake validation checklists, standardized templates, or quality review gating.",
            ]

            candidate = OpportunityCandidate(
                id=opp_id,
                title=f"Reduce Repetitions and Loopbacks on {activity}",
                archetype=OpportunityArchetype.RECURRENCE_REDUCTION,
                intervention_category=InterventionCategory.UNDETERMINED_INVESTIGATION,
                target_entity=activity,
                source_finding_ids=[finding.id],
                evidence_strength=finding.evidence_strength,
                affected_case_count=r_count,
                affected_case_percentage=r_pct,
                occurrence_count=r_occ,
                recurrence_case_percentage=r_pct,
                observed_facts=[
                    f"Activity '{activity}' repeated at distinct timestamps in {r_count} complete cases ({r_pct:.2f}%).",
                    f"Observed {r_occ} additional distinct executions beyond the initial execution (excluding {dup_count} identical-timestamp duplicates).",
                ],
                investigation_hypotheses=[
                    f"Investigate whether re-executions of '{activity}' are caused by upstream data defects, missing information, or normal multi-pass procedures.",
                    f"Examine whether cases requiring repeated '{activity}' experience extended overall cycle times.",
                ],
                candidate_actions=actions,
                candidate_interventions=actions,
                rationale=(
                    f"Prevalent activity recurrence ({r_pct:.2f}% of cases affected) prioritises this pattern for investigation "
                    f"to examine first-pass yield and recurring operational effort."
                ),
                limitations=[
                    "Repeated activities represent observed operational patterns; they do not distinguish intentional iterative reviews from operational failure without domain context.",
                    "Identical-timestamp duplicate records are excluded from recurrence counts.",
                    "Implementation and automation readiness are evaluated separately and are not determined from event logs alone.",
                ],
                operational_priority_score=score,
                priority_tier=tier,
                score_breakdown=breakdown,
            )
            _merge_or_add_candidate(candidates_map, candidate)

        # Rule 3: Tail Variance Mitigation from Cycle Time Outliers
        elif (
            finding.category == FindingCategory.CYCLE_TIME_OUTLIER
            and finding.rule == "CYCLE_TIME_OUTLIER_IQR"
        ):
            o_count = int(finding.metrics.get("outlier_case_count", 0))
            o_pct = float(finding.metrics.get("outlier_case_percentage", 0.0))
            thresh_sec = float(finding.metrics.get("outlier_threshold_seconds", 0.0))
            iqr_sec = float(finding.metrics.get("iqr_seconds", 0.0))
            max_sec = float(finding.metrics.get("max_cycle_time_seconds", 0.0))

            if o_count > 0:
                score, tier, breakdown = calculate_opportunity_score(
                    OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
                    o_pct,
                    o_pct,
                    finding.evidence_strength,
                )

                opp_id = "opp_mitigate_cycle_time_outliers"
                actions = [
                    "Implement proactive escalation triggers and SLA warning alerts for active cases nearing standard duration thresholds.",
                    "Establish standard operating procedures for triaging and expediting stalled or blocked cases.",
                ]

                candidate = OpportunityCandidate(
                    id=opp_id,
                    title="Mitigate Extreme Cycle-Time Outliers and Tail Latency",
                    archetype=OpportunityArchetype.TAIL_VARIANCE_MITIGATION,
                    intervention_category=InterventionCategory.EXCEPTION_MANAGEMENT,
                    target_entity="Cycle Time Tail Distribution",
                    source_finding_ids=[finding.id],
                    evidence_strength=finding.evidence_strength,
                    affected_case_count=o_count,
                    affected_case_percentage=o_pct,
                    occurrence_count=o_count,
                    outlier_case_percentage=o_pct,
                    observed_facts=[
                        f"{o_count} complete cases ({o_pct:.2f}%) exceeded the statistical outlier threshold of {thresh_sec:.2f}s.",
                        f"Interquartile range (IQR) is {iqr_sec:.2f}s with a maximum observed cycle time of {max_sec:.2f}s.",
                    ],
                    investigation_hypotheses=[
                        "Investigate whether outlier cases share specific resources, departments, custom order attributes, or external supply blockers.",
                        "Evaluate whether delayed cases encounter specific exception paths or severe waiting periods.",
                    ],
                    candidate_actions=actions,
                    candidate_interventions=actions,
                    rationale=(
                        f"Extreme cycle time variance ({o_pct:.2f}% statistical outliers) indicates an opportunity "
                        f"to protect service levels and stabilize turnaround times."
                    ),
                    limitations=[
                        "Tukey 1.5x IQR is a statistical heuristic; outlier cases may represent legitimate custom orders, specialized products, or planned holds rather than process failures.",
                    ],
                    operational_priority_score=score,
                    priority_tier=tier,
                    score_breakdown=breakdown,
                )
                _merge_or_add_candidate(candidates_map, candidate)

        # Rule 4: Path Standardization from Rare Variants
        elif (
            finding.category == FindingCategory.PATH_VARIATION
            and finding.rule in ("RARE_PROCESS_VARIANT", "RARE_PROCESS_VARIANTS")
        ):
            rare_cases = int(finding.metrics.get("rare_case_count", 0))
            rare_pct = float(finding.metrics.get("rare_case_percentage", 0.0))
            rare_vars = int(finding.metrics.get("rare_variant_count", 0))
            total_vars = int(finding.metrics.get("total_variant_count", finding.metrics.get("total_variants_count", 0)))
            thresh_cases = int(finding.metrics.get("rare_threshold_cases", 0))

            if rare_cases > 0:
                score, tier, breakdown = calculate_opportunity_score(
                    OpportunityArchetype.PATH_STANDARDIZATION,
                    rare_pct,
                    rare_pct,
                    finding.evidence_strength,
                )

                opp_id = "opp_investigate_rare_path_variants"
                actions = [
                    "Standardize workflow routing rules and consolidate ad-hoc variation into managed, supported workflows.",
                    "Clarify criteria for standard versus exception processing paths in operational guidelines.",
                ]

                candidate = OpportunityCandidate(
                    id=opp_id,
                    title="Investigate Rare Process Routing Variants",
                    archetype=OpportunityArchetype.PATH_STANDARDIZATION,
                    intervention_category=InterventionCategory.PROCESS_SIMPLIFICATION,
                    target_entity="Process Routing Variants",
                    source_finding_ids=[finding.id],
                    evidence_strength=finding.evidence_strength,
                    affected_case_count=rare_cases,
                    affected_case_percentage=rare_pct,
                    occurrence_count=rare_vars,
                    variant_case_percentage=rare_pct,
                    observed_facts=[
                        f"{rare_cases} complete cases ({rare_pct:.2f}%) executed across {rare_vars} rare variants (threshold <= {thresh_cases} cases).",
                        f"Dataset exhibits {total_vars} distinct variants across complete cases.",
                    ],
                    investigation_hypotheses=[
                        "Investigate whether uncommon execution paths represent legitimate product customization or undocumented operational workarounds.",
                        "Evaluate whether rare variants exhibit higher error rates, increased cycle times, or lower operational predictability.",
                    ],
                    candidate_actions=actions,
                    candidate_interventions=actions,
                    rationale=(
                        f"Process fragmentation across {rare_vars} rare variants indicates an opportunity "
                        f"to evaluate process standardization and simplify execution paths."
                    ),
                    limitations=[
                        "Rare paths are candidates for operational investigation, not confirmed process defects; variant diversity may be essential for customer customization.",
                    ],
                    operational_priority_score=score,
                    priority_tier=tier,
                    score_breakdown=breakdown,
                )
                _merge_or_add_candidate(candidates_map, candidate)

        # Rule 5: Data Instrumentation when Reconciliation Fails
        elif (
            finding.category == FindingCategory.DATA_QUALITY_LIMITATION
            and finding.rule == "ACCOUNTING_RECONCILIATION_DISCREPANCY"
        ):
            disc_pct = float(finding.metrics.get("discrepancy_percentage", 0.0))
            disc_sec = float(finding.metrics.get("discrepancy_seconds", 0.0))
            tot_trans = float(finding.metrics.get("total_transition_duration_seconds", 0.0))
            cum_ct = float(finding.metrics.get("cumulative_cycle_time_seconds", 0.0))

            score, tier, breakdown = calculate_opportunity_score(
                OpportunityArchetype.DATA_INSTRUMENTATION,
                100.0,
                disc_pct,
                EvidenceStrength.HIGH,
            )

            opp_id = "opp_instrument_event_timestamps"
            actions = [
                "Implement explicit lifecycle start and complete timestamps for operational activities.",
                "Calibrate clock synchronization and sequential event capture across logging systems.",
            ]

            candidate = OpportunityCandidate(
                id=opp_id,
                title="Improve Event Timestamp Instrumentation and Transition Accounting",
                archetype=OpportunityArchetype.DATA_INSTRUMENTATION,
                intervention_category=InterventionCategory.DATA_INSTRUMENTATION,
                target_entity="Event Log Instrumentation",
                source_finding_ids=[finding.id],
                evidence_strength=EvidenceStrength.HIGH,
                affected_case_count=n_complete,
                affected_case_percentage=100.0 if n_complete > 0 else 0.0,
                occurrence_count=1,
                observed_facts=[
                    f"Total transition durations ({tot_trans:.2f}s) failed to reconcile with cumulative cycle time ({cum_ct:.2f}s) by {disc_pct:.2f}% ({disc_sec:.2f}s discrepancy).",
                    "Duration concentration calculations were suppressed due to this accounting discrepancy.",
                ],
                investigation_hypotheses=[
                    "Investigate whether source systems log overlapping parallel events, uncaptured intermediate transitions, or asynchronous timestamps.",
                    "Audit event recording architecture to identify where time attribution between sequential steps is lost.",
                ],
                candidate_actions=actions,
                candidate_interventions=actions,
                rationale=(
                    f"Reconciliation discrepancy ({disc_pct:.2f}%) prevents reliable duration attribution. "
                    f"Data instrumentation is required before evaluating elapsed time improvements."
                ),
                limitations=[
                    "Duration concentration and delay compression opportunities are suppressed until transition interval accounting reconciles with case cycle times.",
                ],
                operational_priority_score=score,
                priority_tier=tier,
                score_breakdown=breakdown,
            )
            _merge_or_add_candidate(candidates_map, candidate)

    # Convert map to list and sort deterministically
    opportunities = list(candidates_map.values())
    opportunities.sort(
        key=lambda o: (
            -o.operational_priority_score,
            -o.affected_case_count,
            o.target_entity,
            o.id,
        )
    )

    # Compute tier counts
    tier_1 = sum(1 for o in opportunities if o.priority_tier == PriorityTier.TIER_1_HIGH)
    tier_2 = sum(1 for o in opportunities if o.priority_tier == PriorityTier.TIER_2_MEDIUM)
    tier_3 = sum(1 for o in opportunities if o.priority_tier == PriorityTier.TIER_3_LOW)
    tier_4 = sum(1 for o in opportunities if o.priority_tier == PriorityTier.TIER_4_EXPLORATORY)

    summary = OpportunitySummary(
        evaluated_cases_count=n_complete,
        total_opportunities_count=len(opportunities),
        tier_1_count=tier_1,
        tier_2_count=tier_2,
        tier_3_count=tier_3,
        tier_4_count=tier_4,
        reconciliation_passed=reconciliation_passed,
    )

    return OpportunityDetectionResult(
        filename=detection.filename,
        summary=summary,
        opportunities=opportunities,
    )


def _merge_or_add_candidate(
    candidates_map: Dict[Tuple[OpportunityArchetype, str], OpportunityCandidate],
    new_cand: OpportunityCandidate,
) -> None:
    """
    Deduplicates opportunities that target the same entity under the same archetype,
    merging their source finding IDs and supporting texts while retaining the maximum priority score.
    """
    key = (new_cand.archetype, new_cand.target_entity)
    if key not in candidates_map:
        candidates_map[key] = new_cand
        return

    existing = candidates_map[key]

    # Merge source finding IDs preserving uniqueness and sort order
    merged_findings = sorted(list(set(existing.source_finding_ids + new_cand.source_finding_ids)))

    # Merge list fields preserving order and uniqueness
    def _merge_unique_lists(a: List[str], b: List[str]) -> List[str]:
        seen = set()
        out = []
        for item in a + b:
            if item not in seen:
                seen.add(item)
                out.append(item)
        return out

    merged_facts = _merge_unique_lists(existing.observed_facts, new_cand.observed_facts)
    merged_hypotheses = _merge_unique_lists(existing.investigation_hypotheses, new_cand.investigation_hypotheses)
    merged_actions = _merge_unique_lists(existing.candidate_actions, new_cand.candidate_actions)
    merged_limitations = _merge_unique_lists(existing.limitations, new_cand.limitations)

    # Retain higher priority score
    if new_cand.operational_priority_score > existing.operational_priority_score:
        best_score = new_cand.operational_priority_score
        best_tier = new_cand.priority_tier
        best_breakdown = new_cand.score_breakdown
        existing.duration_share_percentage = new_cand.duration_share_percentage
        existing.recurrence_case_percentage = new_cand.recurrence_case_percentage
        existing.outlier_case_percentage = new_cand.outlier_case_percentage
        existing.variant_case_percentage = new_cand.variant_case_percentage
        existing.occurrence_count = new_cand.occurrence_count
        existing.cumulative_time_seconds = new_cand.cumulative_time_seconds
        existing.rationale = new_cand.rationale
    else:
        best_score = existing.operational_priority_score
        best_tier = existing.priority_tier
        best_breakdown = existing.score_breakdown

    # Update existing candidate in-place
    existing.source_finding_ids = merged_findings
    existing.observed_facts = merged_facts
    existing.investigation_hypotheses = merged_hypotheses
    existing.candidate_actions = merged_actions
    existing.candidate_interventions = merged_actions
    existing.limitations = merged_limitations
    existing.operational_priority_score = best_score
    existing.priority_tier = best_tier
    existing.score_breakdown = best_breakdown
