# Commit 71 - `evidence-graph-timeline-layout` - Aria

**Phase:** Assistant hardening
**Owner:** aria
**Depends on:** C70
**Estimated diff lines:** 250
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Reorganize the evidence graph into two visual groups — an entity section (buyer, vendor, PO, shipment, product) and a chronological event timeline with progression arrows — so users can distinguish "what it contains" from "what has happened."

## Semantic Fit Review
- **Atomic outcome:** The graph visually separates entity structure from event timeline, with events ordered chronologically and connected by progression arrows.
- **Failure boundary:** Backend graph data shape is frozen — no backend changes. Intent and error fixes are C68-C69.
- **Budget rationale:** One component rewrite for layout algorithm and grouping logic fits within budget.

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
| `frontend/src/components/EvidenceGraph.tsx` | edit | Replace layout algorithm with two-group entity/timeline design. |
| `frontend/src/pages/Assistant.tsx` | edit | Add section labels for entity and timeline groups in the evidence panel. |

## Contract

### Layout algorithm redesign (`EvidenceGraph.tsx`)

Replace `layoutNodes` (lines 67-112) with a two-group layout:

**Group 1 — Entity Structure (left side)**
Arrange non-event nodes in a compact hierarchy:
- Row 0: `buyer` node(s)
- Row 1: `purchase_order` node(s)
- Row 2: `vendor` node(s)
- Row 3: `shipment` node(s) — the central entity
- Row 4: `product` node(s)

Use vertical stacking with `yGap = 80`, positioned at `x = 0` to `x = 220` (two columns if multiple nodes exist at same level).

**Group 2 — Event Timeline (right side)**
Arrange event nodes in a vertical chronological timeline:
- Position all event nodes at `x = 500` (separated from entity group by a visual gap).
- Stack events vertically with `yGap = 70`, sorted by their natural order in the `graph.nodes` array (backend provides events in chronological order from seed data).
- The topmost event is the earliest; the bottommost is the latest/current.

### Timeline progression edges
After laying out the standard edges from the graph data, add **synthetic progression edges** between consecutive event nodes:
- For each pair of adjacent event nodes (event[i] → event[i+1]), add an edge with:
  - `relationship`: `"then"` (displayed as "Then")
  - `animated`: true if both nodes are highlighted
  - Dashed stroke style to distinguish from entity relationship edges

### Current event emphasis
The last event node in the timeline (most recent) receives additional visual emphasis:
- Slightly larger padding (`10px 14px` vs `8px 12px`)
- Bold font weight (`fontWeight: 700`)
- A subtle box shadow glow matching its status category color

### Visual group separation
Add a subtle visual separator between the two groups:
- A light gray vertical dashed line at `x = 400` (between entity group ending around `x = 220-300` and timeline starting at `x = 500`)
- Or use ReactFlow's built-in group node feature if simpler

### Group labels (`Assistant.tsx` or `EvidenceGraph.tsx`)
Add small text labels above each group:
- "Shipment Details" above the entity group (top-left)
- "Event Timeline" above the timeline group (top-right)

These can be implemented as non-interactive ReactFlow nodes with a label style, or as positioned HTML overlays.

### Edge source/target positions
- Entity nodes: keep `sourcePosition: Right`, `targetPosition: Left` for horizontal entity edges.
- Event nodes: use `sourcePosition: Bottom`, `targetPosition: Top` for vertical timeline flow.
- Cross-group edges (entity → event): use `sourcePosition: Right` on entity, `targetPosition: Left` on event.

## Environment Prerequisites
- C70 complete (markdown rendering deployed — graph labels may contain markdown text).
- Frontend dev server or build available.

## Verification Command
```powershell
npm run --prefix frontend build
```

## Focused Tests
- Build succeeds with no TypeScript errors.
- Visual verification: entity nodes appear on the left, event timeline on the right.
- Events are stacked vertically with "Then" arrows between them.
- The most recent event has visual emphasis (bold, glow).
- Detail panel still opens on node click.
- Empty graph and single-node graphs render without errors.

## Done When
- [ ] **Ready now:** Evidence graph splits entities from events.
- [ ] **How to test:** Login as manager, ask "Where is SHP-1001?", inspect the graph.
- [ ] **Expected result:** Left side shows buyer/vendor/PO/shipment/product hierarchy. Right side shows chronological event timeline with arrows. Current event is visually emphasized.
- [ ] **Still incomplete:** Interactive timeline filtering, event detail expansion.

## Developer Test Checkpoint
**Ready now:** Two-group evidence graph with entity structure and event timeline.
**How to test:** Ask a logistics question and inspect the evidence graph.
**Expected result:** Clear visual separation — entity details on left, chronological events on right with progression arrows.
**Still incomplete:** Advanced graph interaction, filtering, event detail panels.

## Not In This Commit
- Backend changes (graph data shape is frozen).
- Intent classification (C68).
- Error handling (C69).
- Markdown rendering (C70).
- Interactive event detail expansion.
- Timeline zoom or scroll.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
