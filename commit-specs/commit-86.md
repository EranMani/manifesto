# Commit 86 - `shipment-items-api-and-seed` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C85
**Estimated diff lines:** 280
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The shipment creation endpoint accepts line items with quantities and deducts from product inventory using row-level locking. Seed data creates clients and uses shipment_items instead of direct product-to-shipment links.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, creating a shipment with items deducts inventory and seed data populates the new schema. Both are needed for the endpoint to be demonstrable.
- **Failure boundary:** Shipment create and seed are self-contained — failure does not affect product CRUD or client CRUD.
- **Budget rationale:** Two files. Shipment routes gain ~100 lines of item handling + inventory logic. Seed changes ~150 lines for client data and shipment_items. ~280 total.

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
  - backend/app/api/v1/shipments.py
  - backend/seed.py

initial_context:
  - commit-specs/commit-86.md
  - backend/app/api/v1/shipments.py
  - backend/app/schemas/shipment.py
  - backend/app/models/shipment_item.py
  - backend/app/models/product.py
  - backend/seed.py

forbidden:
  - frontend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/api/v1/shipments.py` | edit | Update create_shipment to accept items, validate stock, deduct inventory with FOR UPDATE locking |
| `backend/seed.py` | edit | Add client seed data, create shipment_items instead of products with shipment_id |

---

## Contract

### Shipment Create Endpoint (`backend/app/api/v1/shipments.py`)

Updated `create_shipment`:
1. Accept `ShipmentCreate` payload (now includes `items: list[ShipmentItemCreate]` and `client_id`).
2. Validate vendor exists (existing).
3. If `client_id` is provided, validate client exists. 404 if not found.
4. For each item in `payload.items`:
   a. Load the product row with `with_for_update()` (SELECT FOR UPDATE).
   b. If product not found, raise 404 with `"Product {product_id} not found"`.
   c. If `product.quantity < item.quantity`, raise 400 with `"Insufficient stock for product {product.name}: available {product.quantity}, requested {item.quantity}"`.
   d. Deduct: `product.quantity -= item.quantity`.
5. Create the Shipment (exclude `items` from model_dump: `payload.model_dump(exclude={"items"})`).
6. Create ShipmentItem records for each item.
7. Commit and return.

Imports to add: `ShipmentItem`, `ShipmentItemCreate`, `Product`, `Client`.

### Seed Data (`backend/seed.py`)

Add client data:
```python
CLIENTS = [
    {"name": "Acme Corp", "contact": "John Smith", "email": "orders@acme.example", "country": "United States", "badge_color": "#ef4444"},
    {"name": "Global Trade Ltd", "contact": "Maria Chen", "email": "procurement@globaltrade.example", "country": "Singapore", "badge_color": "#3b82f6"},
    {"name": "Nordic Supply AS", "contact": "Erik Larsen", "email": "supply@nordicsupply.example", "country": "Norway", "badge_color": "#22c55e"},
    {"name": "Pacific Rim Imports", "contact": "Yuki Tanaka", "email": "imports@pacificrim.example", "country": "Japan", "badge_color": "#f59e0b"},
    {"name": "Sahara Logistics", "contact": "Ahmed Hassan", "email": "ops@saharalogistics.example", "country": "Egypt", "badge_color": "#8b5cf6"},
]
```

Add `_ensure_client()` function following the `_ensure_vendor()` pattern.

In `seed()`:
- Create clients: `client_ids = [await _ensure_client(session, **c) for c in CLIENTS]`
- For each shipment, assign a client: `client_id=client_ids[index % len(client_ids)]`
- Pass `client_id` to `_ensure_shipment()`
- Replace `_add_product(session, shipment_id=...)` with `_add_shipment_item()` that creates ShipmentItem records instead.
- Keep products created without shipment_id (standalone catalog items with initial stock).

Update `_ensure_shipment()` to accept and store `client_id`.

Add `_add_shipment_item(session, *, shipment_id, product_id, quantity)` function.

Change product seeding: create products as catalog items first (without shipment_id), then create shipment_items linking them.

---

## Environment Prerequisites

- Backend running via `docker compose up`
- Database at migration 0006

---

## Verification Command

```powershell
python -c "from app.api.v1.shipments import create_shipment; print('endpoint ok')"
```

---

## Focused Tests

- Happy path: Shipment create with items deducts inventory correctly.
- Boundary path: Shipment create with insufficient stock returns 400.
- Boundary path: Shipment create with nonexistent product returns 404.
- Regression: Shipment list and get endpoints still work.
- Seed: seed.py runs without errors and creates clients + shipment_items.

---

## Done When

- [ ] Shipment create accepts items and deducts inventory with row locking.
- [ ] Insufficient stock returns 400 with descriptive message.
- [ ] Seed data creates clients and shipment_items.
- [ ] All Python imports resolve.

---

## Developer Test Checkpoint

- **Next milestone:** C88 — API works but frontend not yet updated.

---

## Not In This Commit

- RAG logistics update — C87.
- Frontend shipment form — C90.
- Inventory restoration on shipment cancellation — future commit if needed.

---

## Return Contract

The implementor's final message must begin with this concise human summary:

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```

After the human summary, include the structured telemetry JSON required by the
generated delegation brief. If the commit cannot finish within its budget, also
include the `SPLIT_REQUIRED` report.
