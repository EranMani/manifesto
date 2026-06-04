# Commit 12 — `vendor-routes` · Rex

**Phase:** 1D — Inventory Routes
**Assignee:** Rex (Backend)
**Depends on:** C11 (admin-routes)

---

## What

Implement vendor CRUD routes. Requires `manager` or `admin` role.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/vendors.py` | new | Full CRUD for vendors |
| `backend/app/schemas/vendor.py` | new | VendorRead, VendorCreate, VendorUpdate schemas |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register vendor router under `/api/v1/vendors` |

---

## Routes

```
GET    /api/v1/vendors          — list all vendors
GET    /api/v1/vendors/{id}     — get vendor by id
POST   /api/v1/vendors          — create vendor
PUT    /api/v1/vendors/{id}     — update vendor
DELETE /api/v1/vendors/{id}     — delete vendor
```

All routes: `Depends(require_role("admin", "manager"))`.

---

## Done When

- [ ] `GET /api/v1/vendors` with manager token returns `[]`
- [ ] `GET /api/v1/vendors` with no token returns 401
- [ ] `POST /api/v1/vendors` creates and returns a vendor
- [ ] `GET /api/v1/vendors/{id}` returns 404 for unknown id
- [ ] All routes appear in `/docs`
