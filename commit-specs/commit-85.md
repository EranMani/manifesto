# Commit 85 - `product-catalog-refactor` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C84
**Estimated diff lines:** 150
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Products become a standalone inventory catalog: the shipment_id field is removed from the product model, schema, and creation endpoint. The shipment schema gains client_id and an items list for the new creation flow.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, creating a product no longer requires a shipment; shipment schemas accept client and item data. Independently testable via API calls.
- **Failure boundary:** Product CRUD and shipment schema are self-contained; the shipment create endpoint is updated separately in C86.
- **Budget rationale:** Four files, all small edits removing or adding fields. ~150 diff lines.

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
  - backend/app/models/product.py
  - backend/app/schemas/shipment.py

initial_context:
  - commit-specs/commit-85.md
  - backend/app/models/product.py
  - backend/app/schemas/product.py
  - backend/app/api/v1/products.py
  - backend/app/schemas/shipment.py

forbidden:
  - frontend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/models/product.py` | edit | Remove shipment_id column mapping (column stays in DB as nullable, unused) |
| `backend/app/schemas/product.py` | edit | Remove shipment_id from ProductBase/ProductCreate; remove from ProductRead |
| `backend/app/api/v1/products.py` | edit | Remove shipment existence check from create_product; remove Shipment import |
| `backend/app/schemas/shipment.py` | edit | Add client_id to ShipmentCreate/ShipmentRead; add ShipmentItemCreate schema |

---

## Contract

### Product Model (`backend/app/models/product.py`)

Remove the `shipment_id` mapped column entirely. The database column still exists (made nullable in C84) but the ORM no longer maps it.

### Product Schemas (`backend/app/schemas/product.py`)

- `ProductBase`: remove `shipment_id: str` field. Keep name, description, quantity, unit, category_id.
- `ProductCreate(ProductBase)`: no shipment_id.
- `ProductRead`: remove `shipment_id: str` field. Keep id, name, description, quantity, unit, category_id, added_by, created_at.
- `ProductUpdate`: unchanged.

### Product Routes (`backend/app/api/v1/products.py`)

- `create_product`: remove the shipment existence check (lines 43-45). Remove `from app.models.shipment import Shipment`.
- All other endpoints unchanged.

### Shipment Schemas (`backend/app/schemas/shipment.py`)

Add new schemas:

```python
class ShipmentItemCreate(BaseModel):
    product_id: str
    quantity: int

class ShipmentCreate(ShipmentBase):
    items: list[ShipmentItemCreate] = []
```

Add to `ShipmentBase`:
- `client_id: str | None = None`

Add to `ShipmentRead`:
- `client_id: str | None` (inherits from base)

---

## Environment Prerequisites

- Backend running via `docker compose up`
- Database at migration 0006

---

## Verification Command

```powershell
python -c "from app.schemas.product import ProductCreate; from app.schemas.shipment import ShipmentCreate, ShipmentItemCreate; print('schemas ok')"
```

---

## Focused Tests

- Happy path: ProductCreate no longer requires shipment_id; ShipmentCreate accepts items list and client_id.
- Boundary path: ProductCreate with only name field succeeds (minimal required fields).
- Regression: ProductRead still includes id, name, description, quantity, unit, category_id, added_by, created_at.

---

## Done When

- [ ] Product model has no shipment_id mapping.
- [ ] Product schemas have no shipment_id field.
- [ ] Product create endpoint does not validate shipment existence.
- [ ] Shipment schemas include client_id and ShipmentItemCreate.

---

## Developer Test Checkpoint

- **Next milestone:** C88 — schema changes are ready but the shipment create endpoint doesn't use them yet.

---

## Not In This Commit

- Shipment create endpoint update with items and inventory deduction — C86.
- Seed data update — C86.
- Frontend type updates — C88.

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
