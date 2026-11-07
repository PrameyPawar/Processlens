# ProcessLens Independent Validation Dataset

**Domain:** E-commerce returns and refunds. This synthetic holdout is independent of the previous manufacturing-order datasets.

## Files
- `processlens_independent_returns_holdout.csv` — blind event log to upload into ProcessLens; it contains no ground-truth label column.
- `processlens_returns_ground_truth_labels.csv` — expected case labels; keep separate until the blind run is complete.
- `processlens_returns_expected_results.json` — reference metrics and planted patterns.
- `processlens_returns_transition_reference.csv` — reference event-to-event transition durations.

## Blind evaluation procedure
1. Upload only the event log.
2. Save ProcessLens outputs before opening the ground-truth files.
3. Compare detected bottlenecks, rework cases, case counts, cycle-time statistics, and transition durations.
4. Align cycle-time boundaries, percentile method, and rework handling before comparing metrics.

## Ground truth
- Primary planted bottleneck: `Refund Review -> Refund Approved`, which has the highest mean transition duration due to a deliberately delayed subset.
- Delayed review cases: `RET-0031`–`RET-0070` (40 cases).
- Severe tail-delay cases: `RET-0101`–`RET-0110` (10 cases).
- Inspection rework cases: `RET-0081`–`RET-0090` (10 cases).
- Expected: 120 cases, complete sequences, no intentionally invalid rows, no intentionally duplicated events.

This is controlled synthetic data for testing known patterns, not proof of real-world accuracy.
