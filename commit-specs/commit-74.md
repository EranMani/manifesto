# Commit 74 - `inline-evidence-graph-layout` - Aria

**Phase:** Phase 3 — Assistant Hardening
**Owner:** aria
**Depends on:** C73
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The evidence graph and policy citations render inline within the chat message flow
(below the assistant's last response) instead of in a separate right sidebar panel.

---

## Semantic Fit Review

- **Atomic outcome:** The layout change is one visual restructuring — the evidence
  moves from a side panel to inline placement. Independently testable by checking that
  the sidebar is gone and evidence appears within the chat column.
- **Failure boundary:** Layout-only change; no data flow, API, or store changes. If the
  layout breaks, only the visual arrangement is affected.
- **Budget rationale:** Two files in Aria's domain, both already read. The change is
  structural JSX rearrangement plus a height adjustment — well within budget.

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
  - frontend/src/pages/Assistant.tsx
  - frontend/src/components/EvidenceGraph.tsx

initial_context:
  - commit-specs/commit-74.md
  - frontend/src/pages/Assistant.tsx
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
| `frontend/src/pages/Assistant.tsx` | edit | Remove sidebar layout; render EvidenceGraph and CitationCards inline after the last assistant message in the chat flow |
| `frontend/src/components/EvidenceGraph.tsx` | edit | Adjust container height from `h-[500px]` to `h-[400px]` for inline context |

---

## Contract

**Before:**
- Assistant page uses `flex-col lg:flex-row` with a `lg:w-[540px]` right sidebar
  for evidence graph and citations.
- Evidence is only visible on large screens as a separate panel.

**After:**
- Assistant page uses a single-column layout (`flex-col`, centered `max-w-3xl`).
- After the last assistant message (and before the input area), if evidence exists:
  - The EvidenceGraph renders inline with a section header.
  - Citations render below the graph with a section header.
- The evidence block scrolls with the chat messages.
- EvidenceGraph uses `h-[400px]` instead of `h-[500px]`.

**No changes to:**
- Data flow (store, API calls, graph/citation state).
- EvidenceGraph's internal ReactFlow rendering, node layout, or interaction.
- CitationCard component.

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
- Visual verification: `npm run dev` shows evidence graph and citations inline in the
  chat flow after an assistant response, with no sidebar visible.
- Regression: The empty-state prompt grid, user/assistant message bubbles, loading
  indicator, error display, and suggested questions still render correctly.

---

## Done When

- [ ] The right sidebar panel is removed from Assistant.tsx.
- [ ] EvidenceGraph and citations render inline in the chat message flow.
- [ ] EvidenceGraph container height is adjusted for inline context.
- [ ] `npx --prefix frontend tsc --noEmit` passes.
- [ ] Visual check confirms the layout matches the approved mockup.

---

## Developer Test Checkpoint

**Next milestone:** No milestone — this is a layout refinement within Phase 3 hardening.

---

## Not In This Commit

- Collapsible/expandable evidence panel (future enhancement if needed).
- Changes to graph data flow, store logic, or API contracts.
- Mobile-specific responsive breakpoints for inline evidence.

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
