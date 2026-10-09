# ProcessLens Development Data

## Files

- `samples/manufacturing_orders_quickstart.csv` — 100 cases, rapid development
- `samples/manufacturing_orders_clean.csv` — 750 cases, primary analytical development
- `samples/manufacturing_orders_rework.csv` — 750 cases, rework/variant testing
- `samples/manufacturing_orders_messy.csv` — 750 cases, data-quality testing
- `schemas/canonical_event_log_schema.md` — canonical data contract
- `ground_truth/expected_findings.md` — expected tendencies for validation

## Recommended order

1. Quickstart
2. Clean
3. Rework
4. Messy

Synthetic data is for controlled correctness testing. Later, real public event logs and eventually real industry data should be passed through the same canonical schema.
