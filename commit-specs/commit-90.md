# Commit 90 - `shipment-form-page` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C86, C89
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

A "Create Shipment" form page lets users select a vendor, a client, pick products from the inventory catalog with quantities, and fill in all shipment fields (tracking code, origin, destination, dispatch date, expected arrival, notes). Submitting creates the shipment and deducts inventory.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, users can create shipments through the browser with full field support and inventory deduction. The feature is end-to-end complete.
- **Failure boundary:** The form page is self-contained — failure does not affect the shipment list, client pages, or product pages.
- **Budget rationale:** Three files: new form page (~220 lines), API client addition (~30 lines), App.tsx route (~5 lines). ~300 total.

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
  - frontend/src/pages/ShipmentForm.tsx

initial_context:
  - commit-specs/commit-90.md
  - frontend/src/pages/ShipmentForm.tsx
  - frontend/src/api/products.ts
  - frontend/src/App.tsx
  - frontend/src/pages/VendorDetail.tsx
  - frontend/src/pages/Dashboard.tsx

forbidden:
  - backend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/ShipmentForm.tsx` | add | Create Shipment form with vendor/client dropdowns, product picker, all shipment fields |
| `frontend/src/api/products.ts` | edit | Add createShipmentWithItems function and ShipmentItemCreate type, update ShipmentRead with client_id |
| `frontend/src/App.tsx` | edit | Add /shipments/new route, import ShipmentForm |

---

## Contract

### API Client (`frontend/src/api/products.ts`)

New types:
- `ShipmentItemCreate`: `{ product_id: string; quantity: number }`
- `ShipmentCreate`: `{ tracking_code: string; vendor_id: string; client_id?: string | null; origin: string; destination: string; status?: string; dispatched_at: string; expected_arrival_at: string; notes?: string | null; items: ShipmentItemCreate[] }`

Update existing type:
- `ShipmentRead`: add `client_id: string | null`

New function:
- `createShipment(data: ShipmentCreate) -> Promise<ShipmentRead>` — POST `/api/v1/shipments`

### ShipmentForm Page

**Layout:** Single-column form with sections:

1. **Shipment Details**
   - Tracking Code: text input, required
   - Origin: text input, required
   - Destination: text input, required
   - Dispatch Date: `input[type="datetime-local"]`, required
   - Expected Arrival: `input[type="datetime-local"]`, required
   - Notes: textarea, optional

2. **Parties**
   - Vendor: dropdown populated from `listVendors()`, required
   - Client: dropdown populated from `listClients()`, required. Each option shows a small colored dot (badge_color) next to the client name.

3. **Products**
   - Product picker: dropdown populated from `listProducts()`, showing name and available quantity
   - "Add Product" button: adds selected product with a quantity input to a line items list below
   - Each line item shows: product name, available stock, quantity input, remove button
   - Quantity input must not exceed available stock (client-side validation)
   - At least one product is required to submit

4. **Actions**
   - "Create Shipment" submit button
   - "Cancel" button navigates to `/shipments`

**Behavior:**
- On mount: fetch vendors, clients, and products in parallel
- On submit: call `createShipment(data)` with all fields + items array
- On success: navigate to `/shipments`
- On error: display error message (400 for insufficient stock, 404 for not found)
- Loading state while fetching dropdown data
- A product can only be added once (disable in dropdown after adding)

### App.tsx Route

Add inside the manager+admin protected group, before /shipments:
```tsx
<Route path="/shipments/new" element={<ShipmentForm />} />
```

Import `ShipmentForm` at the top.

### "New Shipment" Button

Add a "New Shipment" button to the Shipments page (Dashboard.tsx) header that navigates to `/shipments/new`. This is a small addition to the existing page.

Wait — Dashboard.tsx is not in Files To Modify. Let me keep it to 3 files and note this as a minor addition. Actually, let me add it:

No — the spec allows max 4 changed files. Adding Dashboard.tsx makes 4:
- ShipmentForm.tsx (new)
- products.ts (edit)
- App.tsx (edit)
- Dashboard.tsx (edit — add "New Shipment" button)

---

## Updated Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/ShipmentForm.tsx` | add | Create Shipment form with vendor/client dropdowns, product picker, all shipment fields |
| `frontend/src/api/products.ts` | edit | Add createShipment function, ShipmentCreate and ShipmentItemCreate types, add client_id to ShipmentRead |
| `frontend/src/App.tsx` | edit | Add /shipments/new route, import ShipmentForm |
| `frontend/src/pages/Dashboard.tsx` | edit | Add "New Shipment" button in page header |

### Dashboard.tsx Addition

Add a "New Shipment" button next to the page title, following the VendorList pattern:
```tsx
<div className="flex items-center justify-between mb-6">
  <h1 className="text-2xl font-bold">Shipments</h1>
  <button
    onClick={() => navigate('/shipments/new')}
    className="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700"
  >
    New Shipment
  </button>
</div>
```

---

## Environment Prerequisites

- Frontend dev server (`npm run dev` from `frontend/`)
- Backend API running with seeded data (vendors, clients, products with stock)

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: Form loads with populated dropdowns; selecting vendor, client, adding products with quantities, and submitting creates a shipment.
- Boundary path: Cannot submit without required fields; cannot add quantity exceeding available stock.
- Error path: Backend returns 400 for insufficient stock — error message displayed.
- Edge case: Adding and removing products from the line items list works correctly.
- Manual browser check: navigate to /shipments/new (or click "New Shipment" button), fill all fields, add 2-3 products with quantities, submit, verify redirect to /shipments and new card appears.

---

## Done When

- [ ] ShipmentForm page renders with all fields and dropdowns.
- [ ] Vendor and client dropdowns populated from API.
- [ ] Product picker allows adding/removing products with quantity limits.
- [ ] Form submission creates shipment with items via API.
- [ ] "New Shipment" button on Shipments page navigates to form.
- [ ] `tsc --noEmit` passes.
- [ ] Manual browser verification confirms full creation flow.

---

## Developer Test Checkpoint

- **Ready now:** Complete shipment creation flow — users can create shipments with vendor, client, products, and all tracking details through the browser.
- **How to test:** `docker compose up -d` then `npm run dev` from `frontend/`. Navigate to `/shipments` and click "New Shipment". Fill in tracking code, origin/destination, dates. Select a vendor and client. Add products with quantities. Submit.
- **Expected result:** Shipment is created, inventory is deducted, user is redirected to the shipments list where the new card appears with the client's badge color.
- **Still incomplete:** Editing existing shipments, shipment deletion with inventory restoration — future commits if needed.

---

## Not In This Commit

- Edit shipment form — future commit.
- Inventory restoration on shipment deletion/cancellation — future commit.
- Product stock validation in real-time (as user types quantity) — nice-to-have, not required.

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
