# Commit 15c — `fix-product-update` · Rex

**Phase:** 1E — Viktor Fix Wave
**Assignee:** Rex (Backend)
**Depends on:** C15b (fix-vendor-update)
**Triggered by:** Viktor batch wave C11–C15, Finding 5 (BLOCK) + Finding 6 (WARN)

**No gate wave on this commit.**
**Sage conditional: no — no auth/secret/external API changes.**

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/products.py      # route to fix
  - backend/app/schemas/product.py      # schema to extend (add ProductUpdate)
  - backend/app/api/v1/chat.py          # stub fix: conversation_id type

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/admin.py
  - backend/app/api/v1/vendors.py
  - backend/app/api/v1/shipments.py

estimated_reads: 3
estimated_edits: 3   # products.py, product.py (schema), chat.py
fits_single_agent: true
```

---

## What

Fix two issues found by Viktor batch wave:

1. **Finding 5 (BLOCK)** — `update_product` accepts `ProductCreate` which includes `shipment_id`. A PUT overwrites `shipment_id` with no FK re-validation. Create a `ProductUpdate` schema with only truly mutable fields; use `exclude_unset=True`.
2. **Finding 6 (WARN)** — `conversation_id: int` in stub routes contradicts the system-wide UUID string convention. Change to `str`.

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/schemas/product.py` | Add `ProductUpdate` class |
| `backend/app/api/v1/products.py` | Import `ProductUpdate`; change `update_product` signature and body |
| `backend/app/api/v1/chat.py` | Change `conversation_id: int` → `conversation_id: str` |

---

## Exact Changes

### `backend/app/schemas/product.py` — add ProductUpdate

Append after `ProductRead`:

```python
class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit: str | None = None
    category_id: str | None = None
```

### `backend/app/api/v1/products.py` — fix update_product

```python
# Add ProductUpdate to import:
from app.schemas.product import ProductCreate, ProductRead, ProductUpdate

# Replace update_product signature and body:
@router.put("/{product_id}", response_model=ProductRead)
async def update_product(
    product_id: str,
    payload: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_role("admin", "manager")),
):
    result = await db.execute(select(Product).where(Product.id == product_id))
    product = result.scalars().first()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Product not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(product, field, value)
    await db.commit()
    await db.refresh(product)
    return product
```

### `backend/app/api/v1/chat.py` — fix conversation_id type

```python
# Change both occurrences:
async def get_messages(conversation_id: str):   # was int
async def create_message(conversation_id: str):  # was int
```

---

## Done When

- [ ] `ProductUpdate` schema exists with 5 optional fields (name, description, quantity, unit, category_id)
- [ ] PUT on a product does not accept or overwrite `shipment_id`
- [ ] PUT `{"quantity": 10}` updates only quantity
- [ ] `conversation_id` path param in chat stubs is typed as `str`
