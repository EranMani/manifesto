# Commit 87 - `update-rag-logistics-join` - Nova

**Phase:** Phase 3
**Owner:** nova
**Depends on:** C85
**Estimated diff lines:** 30
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

RAG logistics evidence gathering loads shipment products through the shipment_items join table instead of querying Product.shipment_id directly.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, the assistant's logistics evidence correctly retrieves products via the new data model. Independently testable with existing golden tests.
- **Failure boundary:** Only rag_logistics.py changes; no other service or route is affected.
- **Budget rationale:** One file, ~30 diff lines. Simple join rewrite.

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
  - backend/app/services/rag_logistics.py

initial_context:
  - commit-specs/commit-87.md
  - backend/app/services/rag_logistics.py
  - backend/app/models/shipment_item.py
  - backend/app/models/product.py

forbidden:
  - frontend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Replace Product.shipment_id query with join through ShipmentItem |

---

## Contract

### Current code (lines ~257-263):

```python
products = (
    await db.execute(
        select(Product)
        .where(Product.shipment_id == shipment.id)
        .order_by(Product.name, Product.id)
    )
).scalars().all()
```

### Replacement:

```python
from app.models.shipment_item import ShipmentItem

products_with_qty = (
    await db.execute(
        select(Product, ShipmentItem.quantity)
        .join(ShipmentItem, ShipmentItem.product_id == Product.id)
        .where(ShipmentItem.shipment_id == shipment.id)
        .order_by(Product.name, Product.id)
    )
).all()
```

Update the ProductEvidence construction to use the shipment_item quantity instead of product.quantity (since product.quantity is now the catalog/inventory quantity, not the per-shipment quantity):

```python
products=[
    ProductEvidence(
        id=product.id,
        name=product.name,
        description=product.description,
        quantity=item_qty,
        unit=product.unit,
    )
    for product, item_qty in products_with_qty
]
```

Add `from app.models.shipment_item import ShipmentItem` to imports.

---

## Environment Prerequisites

- Backend running via `docker compose up`
- Database at migration 0006 with seed data (C86)

---

## Verification Command

```powershell
python -c "from app.services.rag_logistics import gather_procurement_evidence; print('import ok')"
```

---

## Focused Tests

- Happy path: gather_procurement_evidence returns products with per-shipment quantities from shipment_items.
- Regression: ProductEvidence structure unchanged (id, name, description, quantity, unit).

---

## Done When

- [ ] rag_logistics.py loads products via ShipmentItem join.
- [ ] ProductEvidence uses per-shipment quantity from shipment_items, not catalog quantity.
- [ ] All Python imports resolve.

---

## Developer Test Checkpoint

- **Next milestone:** C88 — internal service change, not independently demonstrable.

---

## Not In This Commit

- Updating test_rag_logistics.py fixtures — future commit if golden tests break.
- Frontend changes — C88-C90.

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
