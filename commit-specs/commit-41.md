# Commit 41 - `purchase-order-storage` - Rex

**Phase:** Demo data foundation
**Owner:** rex
**Depends on:** C40
**Estimated diff lines:** 280
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Persist purchase orders linking one internal buyer to one vendor.

---

## Semantic Fit Review

- **Atomic outcome:** One new authoritative procurement entity can be created and queried through the ORM.
- **Failure boundary:** Shipment linkage and lifecycle fields remain C42.
- **Budget rationale:** One model, one additive migration, one model export, and one focused integration test fit the four-file ceiling.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - backend/app/models/purchase_order.py
  - backend/alembic/versions/0003_purchase_order_storage.py
initial_context:
  - backend/app/models/user.py
  - backend/app/models/vendor.py
  - backend/app/models/__init__.py
  - backend/alembic/versions/0002_rag_storage_hardening.py
  - backend/tests/models/test_policy_storage.py
forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/services/
  - backend/seed.py
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/models/purchase_order.py` | add | Map the purchase_orders table and status constraint. |
| `backend/app/models/__init__.py` | edit | Export PurchaseOrder for metadata discovery. |
| `backend/alembic/versions/0003_purchase_order_storage.py` | add | Create and remove purchase_orders safely. |
| `backend/tests/models/test_purchase_order_storage.py` | add | Verify relationships, uniqueness, statuses, and downgrade. |

---

## Contract

Create `purchase_orders` with:

- UUID `id` primary key using `gen_random_uuid()`.
- Unique, non-null `order_number`.
- Non-null `vendor_id` referencing `vendors.id` with delete restricted.
- Non-null `buyer_id` referencing `users.id` with delete restricted.
- Non-null timezone-aware `ordered_at`.
- Non-null timezone-aware `requested_delivery_at`.
- Non-null `status` defaulting to `approved`.
- Status check allowing `draft`, `approved`, `fulfilled`, and `cancelled`.
- Non-null `created_at` defaulting to `now()`.

The ORM and migration must agree exactly. No API schemas or shipment foreign key are
introduced in this commit.

---

## Environment Prerequisites

- PostgreSQL has migrations through `0002_rag_storage_hardening`.
- Tests run through the C34 container command so `db:5432` resolves correctly.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/models/test_purchase_order_storage.py -q
```

---

## Focused Tests

- A valid purchase order persists with its vendor and buyer identifiers.
- Duplicate order numbers fail the database constraint.
- Invalid statuses fail the database constraint.
- Upgrade creates the table and downgrade removes it without modifying existing tables.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C46 demo data ready.

---

## Not In This Commit

- Shipment purchase-order linkage.
- Shipment lifecycle fields, events, seeding, APIs, and assistant behavior.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
