# Commit 14 — `product-routes` · Rex

**Phase:** 1D — Inventory Routes
**Assignee:** Rex (Backend)
**Depends on:** C13 (shipment-routes) — products reference shipments and categories

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/main.py              # to register the router
  - backend/app/dependencies.py      # need require_role, get_current_user
  - backend/app/models/product.py    # need Product model fields
  - backend/app/models/shipment.py   # need Shipment FK reference

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/shipments.py  # done in C13, do not touch

estimated_reads: 4
estimated_edits: 3   # products.py (new), schemas/product.py (new), main.py (update)
fits_single_agent: true
```

---

## What

Implement product CRUD routes. Products belong to a shipment and optionally a category.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/products.py` | new | Full CRUD for products |
| `backend/app/schemas/product.py` | new | ProductRead, ProductCreate schemas |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register product router under `/api/v1/products` |

---

## Routes

```
GET    /api/v1/products              — list all products
GET    /api/v1/products/{id}         — get product by id
POST   /api/v1/products              — create product
PUT    /api/v1/products/{id}         — update product
DELETE /api/v1/products/{id}         — delete product
```

All routes: `Depends(require_role("admin", "manager"))`.
`added_by` field is set from `current_user.id` — not from request body.

---

## Done When

- [ ] `POST /api/v1/products` with valid shipment_id creates a product
- [ ] `added_by` in DB is set to the authenticated user's id
- [ ] `GET /api/v1/products` returns list
- [ ] All routes appear in `/docs`

---

## Handoffs Out

→ Aria (C19): Dashboard table shows products. Fields available: name, description, quantity, unit, category_id, shipment_id, added_by, created_at.
