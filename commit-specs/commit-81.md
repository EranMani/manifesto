# Commit 81 - `product-detail-form` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C80
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Managers and admins can create new products (with shipment selection) and view/edit
existing products via `/products/new` and `/products/:id`.

---

## Semantic Fit Review

- **Atomic outcome:** The create and edit forms are one independently testable result —
  both use the same form component and share the same validation logic. A user can
  complete the full product CRUD lifecycle after this commit.
- **Failure boundary:** If the form fails, the list page (C80) still works — users can
  still view and delete products. The form is additive.
- **Budget rationale:** One new file plus one edit, all in Aria's domain. The form
  follows standard React patterns (controlled inputs, fetch-on-mount for shipment
  dropdown, submit handler calling the API client from C80).

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
  - frontend/src/pages/ProductDetail.tsx

initial_context:
  - commit-specs/commit-81.md
  - frontend/src/pages/ProductDetail.tsx
  - frontend/src/App.tsx
  - frontend/src/api/products.ts
  - backend/app/schemas/product.py

forbidden:
  - backend/app/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/ProductDetail.tsx` | add | Combined create/edit form with shipment dropdown, field validation, and save/cancel |
| `frontend/src/App.tsx` | edit | Add `/products/new` and `/products/:id` routes under manager+admin ProtectedRoute |

---

## Contract

### Detail/Form Page (`frontend/src/pages/ProductDetail.tsx`)

**Create mode** (route: `/products/new`):
- No `id` param in URL → create mode.
- Form fields: Name (required), Description (optional), Quantity (required, default 0),
  Unit (optional), Shipment (required dropdown), Category ID (optional).
- Shipment dropdown populated via `listShipments()` from `api/products.ts` (C80).
- If no shipments exist, show a message and disable form submission.
- On submit: calls `createProduct(data)` → navigates to `/products` on success.
- On error: shows inline error message, does not navigate.

**Edit mode** (route: `/products/:id`):
- `id` param present → edit mode.
- Fetches product via `getProduct(id)` on mount, pre-fills form fields.
- Same form fields as create mode, except Shipment is read-only (cannot change
  `shipment_id` after creation — `ProductUpdate` schema does not include it).
- On submit: calls `updateProduct(id, data)` → navigates to `/products` on success.
- On error: shows inline error message, does not navigate.

**Shared behavior**:
- "Cancel" button navigates back to `/products`.
- Loading state while fetching product or shipments.
- 404 handling: if `getProduct(id)` returns 404, show "Product not found" with
  a link back to the list.

### Routing (`frontend/src/App.tsx`)

- Add `/products/new` and `/products/:id` inside the existing
  `ProtectedRoute allowedRoles={['manager', 'admin']}` block.
- `/products/new` must appear before `/products/:id` in the route order to avoid
  the `:id` param matching "new".

---

## Environment Prerequisites

- Frontend dev server running (`npm run dev` in `frontend/`)
- Backend API running with seeded data (`docker compose up -d`)
- At least one shipment must exist in the database for the create form dropdown
- A manager or admin user account for testing

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Create happy path: navigate to `/products/new`, fill form, select shipment, submit →
  redirects to `/products`, new product appears in list.
- Create validation: submit with empty name → form does not submit (HTML required).
- Create no-shipments: when no shipments exist, form shows message and submit is disabled.
- Edit happy path: navigate to `/products/:id`, form pre-filled, change name, submit →
  redirects to `/products`, name updated in list.
- Edit 404: navigate to `/products/nonexistent-id` → shows "Product not found".
- Cancel: clicking Cancel from create or edit navigates back to `/products`.
- Manual browser check: visually verify forms render correctly, shipment dropdown
  populates, and save/cancel flows work.

---

## Done When

- [ ] `frontend/src/pages/ProductDetail.tsx` renders create form at `/products/new`.
- [ ] Create form has a working shipment dropdown populated from the API.
- [ ] Create form submits to `createProduct()` and redirects on success.
- [ ] Edit form at `/products/:id` pre-fills from `getProduct()`.
- [ ] Edit form submits to `updateProduct()` and redirects on success.
- [ ] Routes `/products/new` and `/products/:id` are accessible to manager and admin.
- [ ] `tsc --noEmit` passes with zero type errors.
- [ ] Manual browser verification confirms both forms work correctly.

---

## Developer Test Checkpoint

- **Ready now:** Full product CRUD management — list, create, edit, delete.
- **How to test:** Run `docker compose up -d` and `npm run dev` in `frontend/`.
  Log in as admin (`admin@manifesto.local` / `admin123`). Navigate to `/products`.
  The table shows seeded products. Click "New Product", fill the form, select a
  shipment, submit. The product appears in the list. Click a product row to edit.
  Change the name, submit. Click Delete on a product, confirm. Product removed.
- **Expected result:** Complete CRUD lifecycle works end-to-end in the browser.
- **Still incomplete:** Product pages have no automated frontend tests (no test
  infrastructure exists yet). Vendor and shipment pages remain placeholder.

---

## Not In This Commit

- Frontend component tests — no test infrastructure exists; tracked as a gap.
- Vendor management UI — separate forge task.
- Shipment management UI — separate forge task.
- Document management UI — separate forge task, unactioned handoff from Rex → Aria.
- Inline editing on the list page — out of scope.

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
