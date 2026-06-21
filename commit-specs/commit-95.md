# Commit 95 - `expandable-shipment-cards` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C92
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Clicking a shipment card on the Shipments page expands it to show the full detail:
products with quantities, key dates, status reason, notes, and event timeline.
Clicking again or clicking a different card collapses it.

---

## Semantic Fit Review

- **Atomic outcome:** One interactive UI behavior — expand/collapse with on-demand
  data fetching. Testable by clicking cards in the browser and verifying content.
- **Failure boundary:** If the detail fetch fails, a loading or error state is shown
  within the card. The rest of the page is unaffected.
- **Budget rationale:** Two files in Aria's domain. The API type and function are
  small additions; the Dashboard changes are the main work.

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
  - frontend/src/api/products.ts

initial_context:
  - commit-specs/commit-95.md
  - frontend/src/pages/Dashboard.tsx
  - frontend/src/api/products.ts
  - backend/app/schemas/shipment.py

forbidden:
  - backend/app/
  - hooks/
  - docker-compose.yml
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/products.ts` | edit | Add `ShipmentDetailRead` type and `getShipmentDetail()` function |
| `frontend/src/pages/Dashboard.tsx` | edit | Expand/collapse cards with on-demand detail fetch |

---

## Contract

### API client additions (`products.ts`)

- **`ShipmentItemDetail`** interface:
  - `product_id: string`
  - `product_name: string`
  - `product_unit: string | null`
  - `quantity: number`

- **`ShipmentEventDetail`** interface:
  - `event_type: string`
  - `occurred_at: string`
  - `location: string`
  - `details: string | null`

- **`ShipmentDetailRead`** extends `ShipmentRead`:
  - `status_reason: string | null`
  - `items: ShipmentItemDetail[]`
  - `events: ShipmentEventDetail[]`

- **`getShipmentDetail(id: string): Promise<ShipmentDetailRead>`**:
  `GET /api/v1/shipments/{id}/detail`

- Update **`ShipmentRead`** to include `status_reason: string | null`.

### Dashboard behavior

- **State**: `expandedId: string | null` — tracks which card is expanded.
  `detailCache: Map<string, ShipmentDetailRead>` — caches fetched details locally
  so re-expanding a card is instant.
- **Click handler**: On card click:
  - If this card is already expanded → collapse (set `expandedId` to null).
  - If a different card is expanded → collapse it, expand the clicked card.
  - On first expand of a card: fetch `getShipmentDetail(id)`, show a loading
    indicator inside the card, store result in `detailCache`.
  - On subsequent expand: read from `detailCache`, no API call.
- **Expanded content** (below the existing card header):
  - **Products**: table with columns: Product, Quantity, Unit.
    If no items, show "No products".
  - **Dates**: Dispatched, Expected Arrival, Actual Arrival (if set).
    Format as locale date strings.
  - **Status Reason**: Show `status_reason` if non-null, with a label.
  - **Notes**: Show `notes` if non-null.
  - **Timeline**: Ordered list of events with event type (humanized),
    date, location, and details (if set). Most recent first or chronological —
    chronological (matching backend sort).
- **Visual**: Expanded area has a subtle top border separating it from the header.
  Smooth appearance (no animation required but no jarring layout shift).
- **Cursor**: Cards show `cursor-pointer` to indicate clickability.

---

## Environment Prerequisites

- Frontend dev server running (`npm run dev` from `frontend/`).
- Backend running with seed data loaded (provides shipments with items and events).

---

## Verification Command

```powershell
npx --prefix frontend tsc --noEmit
```

---

## Focused Tests

- Happy path: Click a shipment card → expanded section shows products, dates, status
  reason, and timeline. Manual browser check.
- Collapse path: Click the same card again → expanded section closes. Manual browser
  check.
- Switch path: Click card A (expands), then click card B → A collapses, B expands.
  Manual browser check.
- Empty items: Expand a card for a shipment with no items → "No products" shown.
  Manual browser check.
- Cache path: Expand card A, collapse, re-expand → no loading spinner on second
  expand (served from local cache). Manual browser check.

---

## Done When

- [ ] Clicking a shipment card expands it with detail content.
- [ ] Expanded card shows products, dates, status reason, notes, and timeline.
- [ ] Clicking the expanded card collapses it.
- [ ] Only one card is expanded at a time.
- [ ] Re-expanding a previously expanded card uses cached data (no API call).
- [ ] TypeScript compiles without errors.
- [ ] Visual verification in running browser confirms no layout regressions.

---

## Developer Test Checkpoint

- **Ready now:** Shipment cards expand on click to show full details — products,
  quantities, dates, status reason, notes, and event timeline.
- **How to test:** `docker compose up -d` then `npm run dev --prefix frontend`.
  Open `http://localhost:5173/shipments`. Click any shipment card to expand it.
  Click again to collapse. Click a different card to see the switch behavior.
- **Expected result:** Expanded card shows a products table, formatted dates, status
  reason (for exception-status shipments), notes, and a chronological event timeline.
  Data loads on first click; re-expanding is instant.
- **Still incomplete:** Redis caching (C94) operates transparently on the backend;
  the frontend cache is local React state only.

---

## Not In This Commit

- Redis caching layer — C94 (transparent to frontend).
- Shipment editing or status updates from the expanded view.
- Filtering or searching within expanded content.

---

## Return Contract

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```
