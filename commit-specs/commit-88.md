# Commit 88 - `client-crud-pages` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C83
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Client list page displays all clients in a searchable table with badge color indicators, create and delete actions. Client detail page provides a combined create/edit form with a color picker for badge_color — matching the vendor page pattern.

---

## Semantic Fit Review

- **Atomic outcome:** Both client pages become functional CRUD interfaces with badge color support; neither works without the API client additions.
- **Failure boundary:** Client UI is self-contained — failure does not affect vendors, products, shipments, or any other page.
- **Budget rationale:** Four files following the established VendorList/VendorDetail pattern. Badge color adds ~20 lines. ~300 diff lines.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 7
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 550
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

---

## Context

```yaml
primary_files:
  - frontend/src/pages/ClientList.tsx
  - frontend/src/pages/ClientDetail.tsx

initial_context:
  - commit-specs/commit-88.md
  - frontend/src/pages/VendorList.tsx
  - frontend/src/pages/VendorDetail.tsx
  - frontend/src/api/products.ts
  - frontend/src/App.tsx

forbidden:
  - backend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/products.ts` | edit | Add ClientRead, ClientCreate, ClientUpdate types and listClients, getClient, createClient, updateClient, deleteClient functions. Remove shipment_id from ProductRead and ProductCreate types. |
| `frontend/src/pages/ClientList.tsx` | add | Client list table with badge color dots, search, delete (409 handling), create button |
| `frontend/src/pages/ClientDetail.tsx` | add | Combined create/edit form with color picker for badge_color |
| `frontend/src/App.tsx` | edit | Add /clients, /clients/new, /clients/:id routes; import ClientList and ClientDetail |
| `frontend/src/pages/Dashboard.tsx` | edit | Remove product-by-shipment grouping (shipment_id removed from ProductRead) |
| `frontend/src/pages/ProductDetail.tsx` | edit | Remove shipment dropdown (products are now standalone catalog items) |
| `frontend/src/pages/ProductList.tsx` | edit | Remove shipment tracking code column (shipment_id removed) |

---

## Contract

### API Client (`frontend/src/api/products.ts`)

New types:
- `ClientRead`: `{ id: string; name: string; contact: string | null; email: string | null; country: string | null; badge_color: string; created_at: string }`
- `ClientCreate`: `{ name: string; contact?: string | null; email?: string | null; country?: string | null; badge_color?: string }`
- `ClientUpdate`: `{ name?: string | null; contact?: string | null; email?: string | null; country?: string | null; badge_color?: string | null }`

New functions (mirror vendor pattern):
- `listClients() -> Promise<ClientRead[]>` — GET `/api/v1/clients`
- `getClient(id: string) -> Promise<ClientRead>` — GET `/api/v1/clients/{id}`
- `createClient(data: ClientCreate) -> Promise<ClientRead>` — POST `/api/v1/clients`
- `updateClient(id: string, data: ClientUpdate) -> Promise<ClientRead>` — PUT `/api/v1/clients/{id}`
- `deleteClient(id: string) -> Promise<void>` — DELETE `/api/v1/clients/{id}`

Type updates:
- `ProductRead`: remove `shipment_id: string` field
- `ProductCreate`: remove `shipment_id: string` field

### ClientList Page

- Fetches all clients on mount via `listClients()`
- Table columns: Badge (colored dot), Name, Contact, Email, Country, Created, Actions
- Badge column: 16px colored circle using the client's `badge_color` as background-color
- Search filter: filters by name, email, or country (case-insensitive)
- "New Client" button navigates to `/clients/new`
- Delete button: `window.confirm` then `deleteClient(id)`
  - On 409: extract error detail, display it
  - On other errors: "Failed to delete client."
- Empty state: "No clients yet." with "Create your first client" link
- Loading/error states same as VendorList

### ClientDetail Page

- Route param `id` — if absent, create mode
- Create mode: empty form with default badge_color '#6366f1', submit calls `createClient(data)`, navigates to `/clients`
- Edit mode: fetches via `getClient(id)`, populates form, submit calls `updateClient(id, data)`
- Fields: Name (required), Contact, Email, Country (all text inputs), Badge Color (`input[type="color"]`)
- Not-found handling: show "Client not found" with back link
- Cancel button navigates to `/clients`

### App.tsx Routes

Inside the manager+admin protected group, add:
```tsx
<Route path="/clients" element={<ClientList />} />
<Route path="/clients/new" element={<ClientDetail />} />
<Route path="/clients/:id" element={<ClientDetail />} />
```

Import `ClientList` and `ClientDetail` at the top.

---

## Environment Prerequisites

- Frontend dev server (`npm run dev` from `frontend/`)
- Backend API running with seeded clients (after C86)

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: ClientList renders table with badge color dots; ClientDetail form submits create and edit.
- Boundary path: ClientList shows empty state; ClientDetail shows not-found for invalid ID.
- Error path: Delete of client with shipments surfaces 409 error detail.
- Manual browser check: navigate to /clients, verify table with colored badges renders; create a client with a custom badge color via /clients/new; edit via /clients/:id; delete a client.

---

## Done When

- [ ] API client exports all client CRUD functions with correct types.
- [ ] ProductRead and ProductCreate no longer include shipment_id.
- [ ] ClientList renders a searchable table with badge color indicators.
- [ ] ClientDetail provides create/edit form with color picker.
- [ ] Routes registered in App.tsx.
- [ ] `tsc --noEmit` passes.
- [ ] Manual browser verification confirms CRUD flow works.

---

## Developer Test Checkpoint

- **Ready now:** Full client management with badge colors — list, create, edit, delete clients through the browser UI.
- **How to test:** `docker compose up -d` then `npm run dev` from `frontend/`. Navigate to `/clients`. Create a client with a custom badge color via "New Client", edit it by clicking the row, delete it.
- **Expected result:** CRUD operations complete successfully; badge colors are visible as colored dots in the list table; color picker works in the form.
- **Still incomplete:** Badge colors not yet shown on shipment cards (C89). Shipment form not yet available (C90).

---

## Not In This Commit

- Badge colors on shipment cards (Dashboard/Shipments page) — C89.
- Dashboard rename — C89.
- Sidebar "Clients" link — C89.
- Shipment form page — C90.

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
