# Commit 15b — `fix-vendor-update` · Rex

**Phase:** 1E — Viktor Fix Wave
**Assignee:** Rex (Backend)
**Depends on:** C15a (fix-admin-update)
**Triggered by:** Viktor batch wave C11–C15, Finding 4 (BLOCK) + Finding 7 (WARN)

**No gate wave on this commit.**
**Sage conditional: no — no auth/secret/external API changes.**

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/vendors.py    # route to fix

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/admin.py
  - backend/app/api/v1/shipments.py
  - backend/app/api/v1/products.py
  - backend/app/schemas/

estimated_reads: 1
estimated_edits: 1   # vendors.py only
fits_single_agent: true
```

---

## What

Fix two issues in `vendors.py` found by Viktor batch wave:

1. **Finding 4 (BLOCK)** — `update_vendor` uses `if payload.X is not None` guards, which means clients can never clear optional fields back to NULL. Switch to `model_dump(exclude_unset=True)`.
2. **Finding 7 (WARN)** — `delete_vendor` has no guard for child shipments — deletion of a vendor with existing shipments either cascades silently or raises a 500. Add a 409 check.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/api/v1/vendors.py` | Fix `update_vendor` (exclude_unset); fix `delete_vendor` (409 guard) |

---

## Exact Changes

### `update_vendor` — replace field-by-field assignment

```python
# Replace the four `if payload.X is not None` lines with:
for field, value in payload.model_dump(exclude_unset=True).items():
    setattr(vendor, field, value)
await db.commit()
await db.refresh(vendor)
return vendor
```

### `delete_vendor` — add child-shipment guard

Add after the 404 check and before `await db.delete(vendor)`:

```python
from app.models.shipment import Shipment  # add to imports at top of file

# inside delete_vendor, after the 404 check:
child = await db.execute(select(Shipment).where(Shipment.vendor_id == vendor_id))
if child.scalars().first() is not None:
    raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vendor has existing shipments")
```

---

## Done When

- [ ] PUT `{"contact": null}` on a vendor clears `contact` to NULL in the DB
- [ ] PUT `{"name": "New Name"}` (without contact) does not touch `contact`
- [ ] DELETE on a vendor that has shipments returns 409
- [ ] DELETE on a vendor with no shipments succeeds with 204
