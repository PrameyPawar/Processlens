# ProcessLens Canonical Event Log Schema

Minimum required fields:
- `case_id`: unique process/order instance
- `activity`: process activity
- `timestamp`: event timestamp

Optional enrichment:
- `resource`
- `department`
- `order_value`
- `quantity`
- `product_type`
- `priority`
- `event_type`

The engine must map external datasets into this canonical representation instead of depending on any one source dataset.

Primary synthetic activity vocabulary:
1. Order Received
2. Order Verification
3. Inventory Check
4. Production Planning
5. Production
6. Quality Inspection
7. Rework
8. Dispatch
9. Invoice

Repeated activities are valid and may indicate rework.
