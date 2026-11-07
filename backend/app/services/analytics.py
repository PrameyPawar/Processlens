"""
Process Analytics Service (Phase 3).
Calculates deterministic process metrics from reconstructed case traces:
- Population consistency (strictly over complete cases; incomplete cases excluded)
- Cycle time distributions (including single-event cases at 0.0s)
- Activity frequencies, case coverage, and repetition ratios
- Repeated-activity indicators (distinguishing genuine temporal recurrence from identical-timestamp duplicates)
- Confirmed repeated source-ID counts (strictly within complete cases, aligned with analytics population scope)
- Step-to-step transition durations (excluding confirmed repeated source IDs to prevent artificial 0.0s self-transitions,
  while preserving legitimate co-temporal transitions and genuine repeated-activity loops)
- Linear-interpolation p90 percentiles
"""

from typing import List, Dict, Any, Tuple
from collections import defaultdict
from app.schemas.reconstruction import ProcessReconstructionResult
from app.schemas.analytics import (
    DurationStats,
    ReconstructionSummary,
    ActivityFrequency,
    ActivityRework,
    ActivityTransition,
    CycleTimeSummary,
    ProcessAnalyticsResult
)

def compute_duration_stats(durations: List[float]) -> DurationStats:
    """
    Computes deterministic distribution metrics for duration values.
    Uses linear interpolation for the 90th percentile (p90).
    """
    if not durations:
        return DurationStats(
            mean_seconds=0.0,
            median_seconds=0.0,
            min_seconds=0.0,
            max_seconds=0.0,
            p90_seconds=0.0
        )

    n = len(durations)
    durations_sorted = sorted(durations)
    mean_val = sum(durations_sorted) / n

    # Median (50th percentile)
    if n % 2 == 1:
        median_val = float(durations_sorted[n // 2])
    else:
        median_val = (durations_sorted[n // 2 - 1] + durations_sorted[n // 2]) / 2.0

    min_val = float(durations_sorted[0])
    max_val = float(durations_sorted[-1])

    # p90 using linear interpolation between closest ranks
    if n == 1:
        p90_val = float(durations_sorted[0])
    else:
        rank = 0.90 * (n - 1)
        lower_idx = int(rank)
        fraction = rank - lower_idx
        if lower_idx + 1 < n:
            p90_val = durations_sorted[lower_idx] + fraction * (durations_sorted[lower_idx + 1] - durations_sorted[lower_idx])
        else:
            p90_val = float(durations_sorted[lower_idx])

    return DurationStats(
        mean_seconds=round(mean_val, 2),
        median_seconds=round(median_val, 2),
        min_seconds=round(min_val, 2),
        max_seconds=round(max_val, 2),
        p90_seconds=round(p90_val, 2)
    )

def calculate_process_analytics(reconstruction: ProcessReconstructionResult) -> ProcessAnalyticsResult:
    """
    Derives deterministic process metrics from reconstructed cases.
    All metrics operate strictly on complete cases.
    """
    complete_cases = [c for c in reconstruction.cases if c.is_complete]
    complete_cases_count = len(complete_cases)

    # 1. Cycle Time Distribution
    cycle_time_durations: List[float] = []
    for c in complete_cases:
        if c.start_time and c.end_time:
            ct = (c.end_time - c.start_time).total_seconds()
        else:
            ct = 0.0
        cycle_time_durations.append(max(0.0, ct))

    cycle_time_summary = CycleTimeSummary(
        evaluated_cases_count=complete_cases_count,
        duration_stats=compute_duration_stats(cycle_time_durations)
    )

    # 2. Activity Frequency & Coverage (strictly over complete cases)
    activity_total_counts: Dict[str, int] = defaultdict(int)
    activity_case_set: Dict[str, set] = defaultdict(set)
    activity_rework_cases: Dict[str, int] = defaultdict(int)
    activity_rework_occurrences: Dict[str, int] = defaultdict(int)
    activity_duplicate_counts: Dict[str, int] = defaultdict(int)
    activity_potential_duplicate_counts: Dict[str, int] = defaultdict(int)

    for c in complete_cases:
        case_activity_timestamps: Dict[str, set] = defaultdict(set)

        for event in c.events:
            act = event.activity
            activity_total_counts[act] += 1
            activity_case_set[act].add(c.case_id)
            case_activity_timestamps[act].add(event.timestamp_parsed)

            if event.is_duplicate:
                activity_duplicate_counts[act] += 1
            if event.is_potential_duplicate:
                activity_potential_duplicate_counts[act] += 1

        # Evaluate distinct-timestamp recurrences (genuine repetition)
        for act, timestamps in case_activity_timestamps.items():
            distinct_ts_count = len(timestamps)
            if distinct_ts_count >= 2:
                activity_rework_cases[act] += 1
                activity_rework_occurrences[act] += (distinct_ts_count - 1)

    all_activities = sorted(activity_total_counts.keys())

    frequency_list: List[ActivityFrequency] = []
    rework_list: List[ActivityRework] = []

    for act in all_activities:
        total_occ = activity_total_counts[act]
        case_cnt = len(activity_case_set[act])
        coverage_pct = round((case_cnt / complete_cases_count * 100.0), 2) if complete_cases_count > 0 else 0.0
        rep_ratio = round((total_occ / case_cnt), 2) if case_cnt > 0 else 0.0

        frequency_list.append(ActivityFrequency(
            activity=act,
            total_occurrences=total_occ,
            case_count=case_cnt,
            case_coverage_percentage=coverage_pct,
            repetition_ratio=rep_ratio
        ))

        rework_case_cnt = activity_rework_cases[act]
        rework_pct = round((rework_case_cnt / complete_cases_count * 100.0), 2) if complete_cases_count > 0 else 0.0

        rework_list.append(ActivityRework(
            activity=act,
            rework_case_count=rework_case_cnt,
            rework_case_percentage=rework_pct,
            rework_occurrences=activity_rework_occurrences[act],
            duplicate_events_count=activity_duplicate_counts[act],
            potential_duplicate_events_count=activity_potential_duplicate_counts[act],
        ))

    # Sort frequency by total_occurrences descending
    frequency_list.sort(key=lambda f: (-f.total_occurrences, f.activity))
    # Sort rework by rework_case_count descending
    rework_list.sort(key=lambda r: (-r.rework_case_count, -r.rework_occurrences, r.activity))

    # 3. Direct Transitions (consecutive steps in complete cases)
    # Exclude confirmed repeated source IDs from creating artificial 0.0s self-transitions,
    # while preserving transitions between distinct activities that share timestamps and genuine
    # repeated-activity loops at distinct timestamps.
    transition_durations: Dict[Tuple[str, str], List[float]] = defaultdict(list)
    transition_case_set: Dict[Tuple[str, str], set] = defaultdict(set)

    for c in complete_cases:
        non_duplicate_events = [e for e in c.events if not e.is_duplicate]
        for i in range(len(non_duplicate_events) - 1):
            src = non_duplicate_events[i].activity
            tgt = non_duplicate_events[i + 1].activity
            pair = (src, tgt)
            dur = (non_duplicate_events[i + 1].timestamp_parsed - non_duplicate_events[i].timestamp_parsed).total_seconds()
            dur = max(0.0, dur)
            transition_durations[pair].append(dur)
            transition_case_set[pair].add(c.case_id)

    transitions_list: List[ActivityTransition] = []
    sorted_pairs = sorted(
        transition_durations.keys(),
        key=lambda p: (-len(transition_durations[p]), p[0], p[1])
    )

    for src, tgt in sorted_pairs:
        durs = transition_durations[(src, tgt)]
        transitions_list.append(ActivityTransition(
            source_activity=src,
            target_activity=tgt,
            transition_count=len(durs),
            case_count=len(transition_case_set[(src, tgt)]),
            duration_stats=compute_duration_stats(durs)
        ))

    reconstruction_summary = ReconstructionSummary(
        total_source_rows=reconstruction.total_source_rows,
        eligible_event_count=reconstruction.eligible_event_count,
        total_cases_found=reconstruction.total_cases_found,
        complete_cases_count=reconstruction.complete_cases_count,
        incomplete_cases_count=reconstruction.incomplete_cases_count,
        variant_count=reconstruction.variant_count
    )

    return ProcessAnalyticsResult(
        filename=reconstruction.filename,
        reconstruction_summary=reconstruction_summary,
        cycle_time=cycle_time_summary,
        activity_frequency=frequency_list,
        rework=rework_list,
        transitions=transitions_list,
        variants=reconstruction.variants
    )
