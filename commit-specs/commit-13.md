# Commit 13 — `shipment-routes` · Rex

**Phase:** 1D — Inventory Routes
**Assignee:** Rex (Backend)
**Depends on:** C12 (vendor-routes) — shipments reference vendors

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/main.py             # to register the router
  - backend/app/dependencies.py     # need require_role
  - backend/app/models/shipment.py  # need Shipment model fields
  - backend/app/models/vendor.py    # need Vendor FK reference

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/vendors.py   # done in C12, do not touch

estimated_reads: 4
estimated_edits: 3   # shipments.py (new), schemas/shipment.py (new), main.py (update)
fits_single_agent: true
```

---

## What

Implement shipment CRUD routes. Shipments belong to a vendor.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/shipments.py` | new | Full CRUD for shipments |
| `backend/app/schemas/shipment.py` | new | ShipmentRead, ShipmentCreate schemas |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register shipment router under `/api/v1/shipments` |

---

## Routes

```
GET    /api/v1/shipments              — list all shipments
GET    /api/v1/shipments/{id}         — get shipment by id
POST   /api/v1/shipments              — create shipment (requires vendor_id)
DELETE /api/v1/shipments/{id}         — delete shipment
```

All routes: `Depends(require_role("admin", "manager"))`.

---

## Done When

- [ ] `POST /api/v1/shipments` with a valid vendor_id creates a shipment
- [ ] `POST /api/v1/shipments` with an invalid vendor_id returns 404 or 422
- [ ] `GET /api/v1/shipments` returns list
- [ ] All routes appear in `/docs`
