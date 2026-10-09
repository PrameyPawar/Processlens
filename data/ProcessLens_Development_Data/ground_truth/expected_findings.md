# Expected Findings — Synthetic Data

These are expected tendencies, NOT rules to hard-code.

## Clean
- Inventory Check should be a major waiting-time contributor.
- Order Verification should be a high-frequency manual activity.
- Production should dominate absolute processing time.
- Some Quality Inspection cases should contain Rework.
- Standard flow should be the dominant variant.
- A small number of cases should be unusually slow.

## Rework
- Rework loops occur much more frequently.
- Affected cases should have longer cycle times.
- Rework should become a prominent improvement opportunity.

## Messy
Contains:
- missing case IDs
- missing activities
- missing timestamps
- missing resources
- duplicate events
- invalid timestamp strings
- unordered rows

ProcessLens must detect/report these issues and must NOT silently treat bad records as valid.

## Critical testing rule

Never hard-code:
`if activity == "Inventory Check": bottleneck`

Instead calculate metrics, impact and rankings so the expected pattern emerges from the data.
