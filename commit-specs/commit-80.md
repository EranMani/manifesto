# Commit 80 - `product-api-and-list-page` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C79
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Managers and admins can navigate to `/products` and see a table of all products with
working delete-and-confirm; a typed API client connects to the existing backend CRUD
endpoints.

---

## Semantic Fit Review

- **Atomic outcome:** The list page and API client form one independently testable
  result — the table renders data from the backend and the delete flow works end-to-end.
- **Failure boundary:** If the API client is wrong, only this page breaks; no other
  frontend page imports from `api/products.ts`. If the table rendering fails, the
  detail/form page (C81) is unaffected.
- **Budget rationale:** Three new files plus one edit, all in Aria's domain, following
  established patterns from `api/auth.ts` and `pages/Assistant.tsx`. No new libraries
  or architectural decisions required.

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
  - frontend/src/api/products.ts
  - frontend/src/pages/ProductList.tsx

initial_context:
  - commit-specs/commit-80.md
  - frontend/src/api/products.ts
  - frontend/src/pages/ProductList.tsx
  - frontend/src/App.tsx
  - frontend/src/api/client.ts
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
| `frontend/src/api/products.ts` | add | Typed API client: listProducts, getProduct, createProduct, updateProduct, deleteProduct, listShipments, listVendors |
| `frontend/src/pages/ProductList.tsx` | add | Flat searchable product table with delete confirmation |
| `frontend/src/pages/Dashboard.tsx` | edit | Shipment-grouped product grid with filters (status, destination, origin, vendor, tracking code) |
| `frontend/src/components/Sidebar.tsx` | add | Vertical sidebar navigation with role-gated links and sign-out |
| `frontend/src/App.tsx` | edit | Add `/products` route, wrap authenticated routes in SidebarLayout |

---

## Contract

### API Client (`frontend/src/api/products.ts`)

Typed functions wrapping `apiClient` from `./client`:

- `listProducts(): Promise<ProductRead[]>` — GET `/api/v1/products`
- `getProduct(id: string): Promise<ProductRead>` — GET `/api/v1/products/{id}`
- `createProduct(data: ProductCreate): Promise<ProductRead>` — POST `/api/v1/products`
- `updateProduct(id: string, data: ProductUpdate): Promise<ProductRead>` — PUT `/api/v1/products/{id}`
- `deleteProduct(id: string): Promise<void>` — DELETE `/api/v1/products/{id}`
- `listShipments(): Promise<ShipmentRead[]>` — GET `/api/v1/shipments` (for C81 create form)

TypeScript interfaces mirror `backend/app/schemas/product.py`:

```typescript
interface ProductRead {
  id: string
  shipment_id: string
  category_id: string | null
  name: string
  description: string | null
  quantity: number
  unit: string | null
  added_by: string | null
  created_at: string
}
```

### List Page (`frontend/src/pages/ProductList.tsx`)

- Fetches products on mount via `listProducts()`.
- Renders a table with columns: Name, Quantity, Unit, Shipment ID, Created.
- Each row has a "Delete" button that calls `window.confirm()` then `deleteProduct(id)`.
- On successful delete, removes the product from local state (no full refetch).
- "New Product" link navigates to `/products/new` (wired in C81).
- Empty state: "No products yet" message with the "New Product" link.
- Loading state: "Loading..." text while fetching.
- Error state: red error message if the fetch or delete fails.

### Routing (`frontend/src/App.tsx`)

- Add `/products` inside the existing `ProtectedRoute allowedRoles={['manager', 'admin']}` block (alongside `/dashboard`, `/vendors`, `/vendors/:id`).

---

## Environment Prerequisites

- Frontend dev server running (`npm run dev` in `frontend/`)
- Backend API running with seeded data (`docker compose up -d`)
- A manager or admin user account for testing

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: navigate to `/products`, table renders with product data from the API.
- Empty state: when API returns an empty array, "No products yet" message displays.
- Delete flow: clicking Delete → confirm dialog → product removed from table.
- Delete cancel: clicking Delete → canceling confirm → product remains.
- Error state: if API is unreachable, error message displays.
- Manual browser check: visually verify the table renders correctly in the browser.

---

## Done When

- [ ] `frontend/src/api/products.ts` exports all 6 typed API functions.
- [ ] `frontend/src/pages/ProductList.tsx` renders a product table from live API data.
- [ ] Delete with confirmation works end-to-end.
- [ ] `/products` route is accessible to manager and admin roles.
- [ ] `tsc --noEmit` passes with zero type errors.
- [ ] Manual browser verification confirms the table renders correctly.

---

## Developer Test Checkpoint

**Next milestone:** C81 (`product-detail-form`) — full product CRUD lifecycle.

---

## Not In This Commit

- Product create form — C81 (`product-detail-form`)
- Product edit form — C81 (`product-detail-form`)
- Product detail view — C81 (`product-detail-form`)
- `/products/new` and `/products/:id` routes — C81

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
