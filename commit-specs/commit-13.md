# Commit 13 — `shipment-routes` · Rex

**Phase:** 1D — Inventory Routes
**Assignee:** Rex (Backend)
**Depends on:** C12 (vendor-routes) — shipments reference vendors

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
