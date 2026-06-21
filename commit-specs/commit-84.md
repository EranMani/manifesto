# Commit 84 - `shipment-refactor-migration` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C83
**Estimated diff lines:** 280
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Alembic migration creates the clients table, shipment_items join table, and adds client_id to shipments. Existing product-to-shipment relationships are migrated to shipment_items. The products.shipment_id column is made nullable but not dropped.

---

## Semantic Fit Review

- **Atomic outcome:** After running the migration, all three new structures exist and existing data is preserved in the new format.
- **Failure boundary:** Migration is self-contained with a full downgrade path. Failure here does not corrupt existing tables.
- **Budget rationale:** Four files: migration file (largest), ShipmentItem model, Shipment edit, __init__.py edit. ~280 diff lines.

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
  - backend/alembic/versions/0006_client_shipment_items_refactor.py
  - backend/app/models/shipment_item.py

initial_context:
  - commit-specs/commit-84.md
  - backend/app/models/client.py
  - backend/app/models/shipment.py
  - backend/app/models/product.py
  - backend/alembic/versions/0005_shipment_event_storage.py

forbidden:
  - frontend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/alembic/versions/0006_client_shipment_items_refactor.py` | add | Migration: create clients table, shipment_items table, add client_id to shipments, make shipment_id nullable on products, migrate data |
| `backend/app/models/shipment_item.py` | add | ShipmentItem SQLAlchemy model (shipment_id FK, product_id FK, quantity) |
| `backend/app/models/shipment.py` | edit | Add client_id foreign key column (nullable) |
| `backend/app/models/__init__.py` | edit | Add Client and ShipmentItem to imports and __all__ |

---

## Contract

### Migration (`0006_client_shipment_items_refactor.py`)

Revision chain: `0005_shipment_event_storage` → `0006_client_shipment_items_refactor`

**upgrade():**
1. Create `clients` table: id (UUID PK), name (String NOT NULL), contact (String nullable), email (String nullable), country (String nullable), badge_color (String NOT NULL DEFAULT '#6366f1'), created_at (DateTime TZ DEFAULT now())
2. Create `shipment_items` table: id (UUID PK DEFAULT gen_random_uuid()), shipment_id (UUID FK → shipments.id ON DELETE CASCADE, NOT NULL), product_id (UUID FK → products.id ON DELETE CASCADE, NOT NULL), quantity (Integer NOT NULL DEFAULT 0), created_at (DateTime TZ DEFAULT now())
3. Add `client_id` column to `shipments`: UUID FK → clients.id ON DELETE SET NULL, nullable
4. Data migration: INSERT INTO shipment_items (shipment_id, product_id, quantity) SELECT shipment_id, id, quantity FROM products WHERE shipment_id IS NOT NULL
5. Make `products.shipment_id` nullable (ALTER COLUMN SET NULL) — do NOT drop the column

**downgrade():**
1. Make `products.shipment_id` NOT NULL (after restoring data)
2. Data migration: UPDATE products SET shipment_id = si.shipment_id FROM shipment_items si WHERE si.product_id = products.id
3. Drop `client_id` from `shipments`
4. Drop `shipment_items` table
5. Drop `clients` table

### ShipmentItem Model (`backend/app/models/shipment_item.py`)

- `id`: UUID PK, server_default gen_random_uuid()
- `shipment_id`: UUID FK → shipments.id ON DELETE CASCADE, not null
- `product_id`: UUID FK → products.id ON DELETE CASCADE, not null
- `quantity`: Integer, not null, default 0
- `created_at`: DateTime(timezone=True), server_default now()
- Table name: `shipment_items`

### Shipment Model edit

Add: `client_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)`

### models/__init__.py edit

Add `from app.models.client import Client` and `from app.models.shipment_item import ShipmentItem` to imports. Add both to `__all__`.

---

## Environment Prerequisites

- Backend running via `docker compose up`
- Database at migration 0005

---

## Verification Command

```powershell
python -c "from app.models.shipment_item import ShipmentItem; from app.models.shipment import Shipment; from app.models.client import Client; print('models ok')"
```

---

## Focused Tests

- Happy path: All new models import correctly; migration script has valid upgrade/downgrade.
- Boundary path: Data migration preserves existing product-shipment relationships in shipment_items.
- Regression: Existing shipment and product model fields remain intact.

---

## Done When

- [ ] Migration file creates clients, shipment_items tables and adds client_id to shipments.
- [ ] ShipmentItem model exists with correct FKs.
- [ ] Shipment model has client_id column.
- [ ] Client and ShipmentItem are registered in models/__init__.py.
- [ ] All Python imports resolve.

---

## Developer Test Checkpoint

- **Next milestone:** C88 — database schema is ready but API/seed data not yet updated to use the new structures.

---

## Not In This Commit

- Dropping products.shipment_id column — deferred cleanup. Column is nullable and unused after C85.
- Updating product schemas/routes — C85.
- Updating shipment create endpoint — C86.
- Seed data updates — C86.

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
