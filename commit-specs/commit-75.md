# Commit 75 - `fix-stale-evidence-graph` - Aria

**Phase:** Phase 3 — Assistant Hardening
**Owner:** aria
**Depends on:** C74
**Estimated diff lines:** 15
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

When the user asks about a different shipment, the evidence graph clears and renders
the new shipment's graph instead of displaying the previous shipment's stale nodes.

---

## Semantic Fit Review

- **Atomic outcome:** One state-sync fix in one component — independently testable by
  querying two different shipments and verifying each graph renders correctly.
- **Failure boundary:** Only ReactFlow node/edge state sync is affected. If this fails,
  the graph displays stale data; no other component or data flow is involved.
- **Budget rationale:** One file, ~15 diff lines. The fix is adding two setter calls
  to an existing useEffect — well within all budget limits.

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
  - frontend/src/components/EvidenceGraph.tsx

initial_context:
  - commit-specs/commit-75.md
  - frontend/src/components/EvidenceGraph.tsx
  - frontend/src/store/assistant.ts
  - frontend/src/api/assistant.ts

forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/EvidenceGraph.tsx` | edit | Sync ReactFlow nodes/edges state when graph prop changes |

---

## Contract

**Before:**
- `useNodesState(initialNodes)` and `useEdgesState(initialEdges)` use the argument
  only on first mount.
- When the `graph` prop changes (new shipment), `initialNodes` and `initialEdges`
  recalculate via `useMemo`, but the ReactFlow internal state retains the old values.
- The existing `useEffect` on `graph` resets `selectedNode` and calls `fitView()` but
  does not update nodes or edges.

**After:**
- Destructure `setNodes` from `useNodesState` and `setEdges` from `useEdgesState`.
- In the existing `useEffect`, call `setNodes(initialNodes)` and
  `setEdges(initialEdges)` before `fitView()`.
- When the graph prop changes, the displayed nodes and edges update to match the new
  graph data.

**No changes to:**
- Store logic, API calls, or data flow.
- Node layout algorithm, edge rendering, or detail panel.
- The `EvidenceGraph` outer component or `ReactFlowProvider`.

---

## Environment Prerequisites

- Node.js and frontend dev dependencies installed.
- `npm run dev` in `frontend/` to verify visual result.

---

## Verification Command

```powershell
npx --prefix frontend tsc --noEmit
```

---

## Focused Tests

- Happy path: TypeScript compilation passes with no errors.
- Visual verification: ask about shipment A, see graph A; then ask about shipment B,
  see graph B (not graph A persisting).
- Regression: single-shipment queries still render their graph correctly on first load.

---

## Done When

- [ ] `setNodes` and `setEdges` are called in the useEffect when graph changes.
- [ ] `npx --prefix frontend tsc --noEmit` passes.
- [ ] Visual check confirms graph updates when switching shipments.

---

## Developer Test Checkpoint

**Next milestone:** No milestone — this is a bug fix within Phase 3 hardening.

---

## Not In This Commit

- Per-message graph snapshots (each message retaining its own graph inline).
- Store-level graph history or caching.
- Changes to graph layout, styling, or node interaction.

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
