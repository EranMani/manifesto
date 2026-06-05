# Commit 12 — `vendor-routes` · Rex

**Phase:** 1D — Inventory Routes
**Assignee:** Rex (Backend)
**Depends on:** C11 (admin-routes)

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/main.py            # to register the router
  - backend/app/dependencies.py    # need require_role
  - backend/app/models/vendor.py   # need Vendor model fields

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/admin.py    # done in C11, do not touch

estimated_reads: 3
estimated_edits: 3   # vendors.py (new), schemas/vendor.py (new), main.py (update)
fits_single_agent: true
```

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
