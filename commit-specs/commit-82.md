# Commit 82 - `vendor-crud-pages` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C81
**Estimated diff lines:** 280
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

The vendors list page displays all vendors in a searchable table with create and delete
actions, and the vendor detail page provides a combined create/edit form — matching the
products page pattern with full CRUD support.

---

## Semantic Fit Review

- **Atomic outcome:** Both vendor pages become functional CRUD interfaces; neither works
  without the API client additions, so they ship together as one testable result.
- **Failure boundary:** Vendor UI is self-contained — failure here does not affect
  products, shipments, or any other page.
- **Budget rationale:** Four files, all frontend, all following the established
  ProductList/ProductDetail pattern line-for-line. No backend changes. No new
  dependencies. Estimated 280 diff lines within the 350 ceiling.

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
  - frontend/src/pages/VendorList.tsx
  - frontend/src/pages/VendorDetail.tsx

initial_context:
  - commit-specs/commit-82.md
  - frontend/src/pages/VendorList.tsx
  - frontend/src/pages/VendorDetail.tsx
  - frontend/src/api/products.ts
  - frontend/src/pages/ProductList.tsx
  - frontend/src/pages/ProductDetail.tsx

forbidden:
  - backend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/products.ts` | edit | Add getVendor, createVendor, updateVendor, deleteVendor functions and VendorCreate/VendorUpdate types |
| `frontend/src/pages/VendorList.tsx` | edit | Replace placeholder with full vendor list table, search, delete, empty/loading/error states |
| `frontend/src/pages/VendorDetail.tsx` | edit | Replace placeholder with combined create/edit form for vendor CRUD |
| `frontend/src/App.tsx` | edit | Add `/vendors/new` route inside the manager+admin protected group |

---

## Contract

### API Client (`frontend/src/api/products.ts`)

New types:
- `VendorCreate`: `{ name: string; contact?: string | null; email?: string | null; country?: string | null }`
- `VendorUpdate`: `{ name?: string | null; contact?: string | null; email?: string | null; country?: string | null }`

New functions:
- `getVendor(id: string) -> Promise<VendorRead>` — GET `/api/v1/vendors/{id}`
- `createVendor(data: VendorCreate) -> Promise<VendorRead>` — POST `/api/v1/vendors`
- `updateVendor(id: string, data: VendorUpdate) -> Promise<VendorRead>` — PUT `/api/v1/vendors/{id}`
- `deleteVendor(id: string) -> Promise<void>` — DELETE `/api/v1/vendors/{id}`

Existing `listVendors()` and `VendorRead` remain unchanged.

### VendorList Page

- Fetches all vendors on mount via `listVendors()`
- Displays table: Name, Contact, Email, Country, Created, Actions
- Search filter: filters by name, email, or country (case-insensitive)
- "New Vendor" button navigates to `/vendors/new`
- Delete button: `window.confirm` then `deleteVendor(id)`
  - On 409 (vendor has shipments): extract error detail from response body and display it
  - On other errors: display "Failed to delete vendor."
- Empty state: "No vendors yet." with "Create your first vendor" link
- Loading state: "Loading..."
- Error state: red text

### VendorDetail Page

- Route param `id` from `/vendors/:id` — if absent, create mode
- Create mode: empty form, submit calls `createVendor(data)`, navigates to `/vendors`
- Edit mode: fetches vendor via `getVendor(id)`, populates form, submit calls `updateVendor(id, data)`
- Fields: Name (required, text input), Contact (optional, text input), Email (optional, text input), Country (optional, text input)
- Not-found handling: if `getVendor` fails in edit mode, show "Vendor not found" with back link
- Cancel button navigates to `/vendors`

### App.tsx Route

- Add `<Route path="/vendors/new" element={<VendorDetail />} />` inside the manager+admin protected group, before the existing `/vendors/:id` route

---

## Environment Prerequisites

- Frontend dev server (`npm run dev` from `frontend/`)
- Backend API running with seeded vendors (via `docker compose up`)

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: VendorList renders table with vendor data; VendorDetail form submits create and edit.
- Boundary path: VendorList shows empty state when no vendors exist; VendorDetail shows not-found for invalid ID.
- Error path: VendorList delete of vendor with shipments surfaces the 409 error detail.
- Manual browser check: navigate to /vendors, verify table renders; create a vendor via /vendors/new; edit via /vendors/:id; delete a vendor; attempt to delete a vendor with shipments and verify error message.

---

## Done When

- [ ] API client exports getVendor, createVendor, updateVendor, deleteVendor with correct types.
- [ ] VendorList renders a searchable table with create/delete actions and proper empty/loading/error states.
- [ ] VendorDetail provides create and edit forms with validation and navigation.
- [ ] /vendors/new route is registered in App.tsx.
- [ ] `tsc --noEmit` passes with zero errors.
- [ ] Manual browser verification confirms full CRUD flow works.

---

## Developer Test Checkpoint

- **Ready now:** Full vendor management — list, create, edit, delete vendors through the browser UI.
- **How to test:** `docker compose up -d` then `npm run dev` from `frontend/`. Navigate to `/vendors`. Create a vendor via "New Vendor", edit it by clicking the row, delete it. Try deleting a vendor that has shipments.
- **Expected result:** CRUD operations complete successfully; deleting a vendor with shipments shows a meaningful error message.
- **Still incomplete:** Vendor-shipment relationship is not visible from the vendor pages (no linked shipment list).

---

## Not In This Commit

- Vendor-to-shipment navigation (showing which shipments belong to a vendor) — future commit.
- Vendor form validation beyond HTML required attribute — future commit if needed.
- Pagination for large vendor lists — future commit if needed.

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
