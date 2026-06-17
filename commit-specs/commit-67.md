# Commit 67 - `evidence-graph-visual-overhaul` - Aria

**Phase:** Assistant hardening
**Owner:** aria
**Depends on:** C66
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Redesign the evidence graph for immediate readability: wider layout, logistics-aware node colors with status-based green/orange/red encoding, multi-column non-linear layout, and larger graph area.

## Semantic Fit Review
- **Atomic outcome:** The graph is visually readable and semantically meaningful on first sight.
- **Failure boundary:** Backend graph data shape is frozen by C66.
- **Budget rationale:** One component rewrite and one page layout tweak fit two files.

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

## Context
```yaml
primary_files:
  - frontend/src/components/EvidenceGraph.tsx
  - frontend/src/pages/Assistant.tsx
initial_context:
  - frontend/src/components/EvidenceGraph.tsx
  - frontend/src/pages/Assistant.tsx
  - frontend/src/api/assistant.ts
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/EvidenceGraph.tsx` | edit | Replace the color scheme, layout algorithm, and node styling. |
| `frontend/src/pages/Assistant.tsx` | edit | Increase evidence panel width and graph container height. |
| `frontend/src/api/assistant.ts` | edit | Add `status` and `status_category` fields to `GraphNodeSchema`. |

## Contract

### Layout changes (`Assistant.tsx`)
- Evidence panel: increase from `lg:w-96` (384px) to `lg:w-[540px]` (540px).
- Graph container: increase from `h-96` (384px) to `h-[500px]` (500px).

### Color scheme (`EvidenceGraph.tsx`)
Replace `TYPE_COLORS` and `TYPE_ORDER` with logistics-aware mappings:

**Node type colors** (base colors when no status):
- `buyer`: blue (`bg: #dbeafe`, `border: #3b82f6`)
- `purchase_order`: amber (`bg: #fef3c7`, `border: #f59e0b`)
- `vendor`: purple (`bg: #ede9fe`, `border: #8b5cf6`)
- `shipment`: slate (`bg: #f1f5f9`, `border: #64748b`) — overridden by status color
- `product`: teal (`bg: #ccfbf1`, `border: #14b8a6`)
- `event`: gray (`bg: #f3f4f6`, `border: #9ca3af`) — overridden by status category

**Status category overrides** (applied on top of type color when `status_category` is present):
- `"done"`: green (`bg: #dcfce7`, `border: #22c55e`) — delivered, completed
- `"active"`: orange/amber (`bg: #fff7ed`, `border: #f97316`) — in_transit, pending
- `"issue"`: red (`bg: #fee2e2`, `border: #ef4444`) — delayed, damaged, lost, cancelled

**Status badge**: when `status` is present, render it as a small colored badge/pill below the node label (e.g., "delivered" in green, "delayed" in red).

### Layout algorithm (`EvidenceGraph.tsx`)
Replace the single-column `typeColumn()` with a **hierarchical multi-column layout**:
- Column 0 (left): `buyer`
- Column 1: `purchase_order`
- Column 2: `vendor`
- Column 3 (center): `shipment`
- Column 4 (right-top): `product` nodes stacked vertically
- Column 4 (right-bottom): `event` nodes stacked vertically below products

Use `xGap = 220`, `yGap = 80` to spread nodes out. The shipment node is the visual hub — all edges radiate from/to it, making the graph look like a star/hub rather than a linear chain.

### Edge styling
- Highlighted edges: keep animated blue stroke.
- Non-highlighted edges: light gray, slightly thicker (`strokeWidth: 1.5`).
- Edge labels: capitalize relationship text, remove underscores (e.g., `"placed_order"` -> `"Placed Order"`).

### Frontend type update (`assistant.ts`)
Add to `GraphNodeSchema`:
```typescript
status: string | null
status_category: string | null
```

## Environment Prerequisites
- C66 graph metadata is deployed (status and status_category in API response).

## Verification Command
```powershell
npm run --prefix frontend build
```

## Focused Tests
- Build succeeds with no TypeScript errors.
- Visual verification: graph renders with colored nodes, multi-column layout, and status badges.
- Detail panel still opens on node click.
- Empty graph state still shows placeholder.

## Done When
- [ ] **Ready now:** Evidence graph is visually clear with status coloring.
- [ ] **How to test:** Login as manager, ask "Where is SHP-1001?", inspect the graph on the right.
- [ ] **Expected result:** Multi-column graph with colored nodes — green for delivered, orange for in-transit, red for delayed. Shipment node is the visual hub. Graph is large enough to read without zooming.
- [ ] **Still incomplete:** Interactive graph exploration, filtering, and browse-query graph visualization.

## Developer Test Checkpoint
**Ready now:** Readable, status-colored evidence graph.
**How to test:** Ask a logistics question and inspect the graph panel.
**Expected result:** Hub-and-spoke layout with green/orange/red status encoding.
**Still incomplete:** Advanced graph interaction features.

## Not In This Commit
- Backend changes.
- Browse query graph visualization.
- Graph legend or tooltip enhancements.
- Node drag-and-drop customization.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
