# Commit 89 - `rename-dashboard-and-update-pages` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C88
**Estimated diff lines:** 150
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Dashboard page and sidebar label are renamed to "Shipments", the route changes from /dashboard to /shipments with a redirect for backwards compatibility, client badge colors appear on shipment cards, "Clients" link is added to the sidebar, and the product detail form removes the shipment dropdown.

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, the navigation reflects the new naming, badge colors are visible on shipment cards, and product forms work without shipment selection.
- **Failure boundary:** UI label and routing changes are self-contained; failure does not affect backend or other pages.
- **Budget rationale:** Four files, all small edits. Dashboard rename ~20 lines, badge color integration ~30 lines, sidebar ~10 lines, product form ~20 lines, App routing ~15 lines. ~150 total.

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
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/components/Sidebar.tsx

initial_context:
  - commit-specs/commit-89.md
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/components/Sidebar.tsx
  - frontend/src/App.tsx
  - frontend/src/pages/ProductDetail.tsx
  - frontend/src/api/products.ts

forbidden:
  - backend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Dashboard.tsx` | edit | Rename title "Dashboard" → "Shipments", fetch clients and display badge color dots on shipment cards |
| `frontend/src/components/Sidebar.tsx` | edit | Rename "Dashboard" → "Shipments" (label and route), add "Clients" nav item |
| `frontend/src/App.tsx` | edit | Change /dashboard route to /shipments, add /dashboard → /shipments redirect |
| `frontend/src/pages/ProductDetail.tsx` | edit | Remove shipment dropdown (products are standalone catalog items now) |

---

## Contract

### Dashboard.tsx → "Shipments"

1. Change page title `<h1>` from "Dashboard" to "Shipments".
2. Add `listClients` to the `Promise.all` fetch (alongside products, shipments, vendors).
3. Build a `clientMap` from client data: `new Map(clients.map(c => [c.id, c]))`.
4. In each shipment card header, after the vendor line, add a client badge if `shipment.client_id` exists:
   ```tsx
   {client && (
     <div className="flex items-center gap-1.5 text-xs text-gray-500 mt-1">
       <span
         className="inline-block w-3 h-3 rounded-full"
         style={{ backgroundColor: client.badge_color }}
       />
       Client: {client.name}
     </div>
   )}
   ```
5. Update `ShipmentGroup` interface to include `client: ClientRead | null`.
6. Add `clientFilter` state and dropdown (like vendorFilter).

### Sidebar.tsx

1. Change the Dashboard nav item: `{ to: '/shipments', label: 'Shipments', roles: ['manager', 'admin'] }`
2. Add Clients nav item: `{ to: '/clients', label: 'Clients', roles: ['manager', 'admin'] }`
3. Order: Shipments, Products, Clients, Vendors, Assistant, Admin

### App.tsx

1. Change `<Route path="/dashboard" element={<Dashboard />} />` to `<Route path="/shipments" element={<Dashboard />} />`
2. Add redirect: `<Route path="/dashboard" element={<Navigate to="/shipments" replace />} />`
3. Update RootRedirect to navigate to "/shipments" instead of "/assistant" (or keep as /assistant — defer to implementation judgment based on user flow).

### ProductDetail.tsx

Remove the shipment dropdown/select field from the form. The product creation form should no longer ask for or display a shipment association. Remove the `listShipments` import if no longer needed.

---

## Environment Prerequisites

- Frontend dev server (`npm run dev` from `frontend/`)
- Backend API running with seeded data (clients, shipment_items)

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: Sidebar shows "Shipments" and "Clients" links; /shipments page loads with badge color dots on cards.
- Boundary path: /dashboard redirects to /shipments; shipment cards without a client show no badge.
- Regression: All other sidebar links still work; product form still creates products without errors.
- Manual browser check: click "Shipments" in sidebar, verify badge colors appear on cards; click "Clients" link; navigate to /dashboard and verify redirect; create a product without needing a shipment.

---

## Done When

- [ ] Dashboard page title is "Shipments".
- [ ] Sidebar shows "Shipments" and "Clients" links.
- [ ] /dashboard redirects to /shipments.
- [ ] Badge colors appear on shipment cards next to client name.
- [ ] Product detail form has no shipment field.
- [ ] `tsc --noEmit` passes.

---

## Developer Test Checkpoint

- **Next milestone:** C90 — UI polish commit, not independently demonstrable as a new capability.

---

## Not In This Commit

- Shipment form page — C90.
- Renaming the Dashboard.tsx filename itself (keep as Dashboard.tsx to avoid unnecessary churn).

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
