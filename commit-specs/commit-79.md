# Commit 79 - `fix-chat-scroll-regression` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C78
**Estimated diff lines:** 5
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The chat messages area scrolls vertically when content overflows the viewport,
while the input area remains pinned at the bottom.

---

## Semantic Fit Review

- **Atomic outcome:** One CSS class addition that restores scrolling broken by C78.
- **Failure boundary:** Only Assistant.tsx layout classes change; no state, API, or
  component contract is affected.
- **Budget rationale:** One file, ~5 diff lines, no logic changes.

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

initial_context:
  - commit-specs/commit-79.md
  - frontend/src/pages/Assistant.tsx

forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Assistant.tsx` | edit | Add min-h-0 to inner flex column to restore scroll |

---

## Contract

**Scroll restoration:**
- The inner flex column div (child of the outer `h-screen overflow-hidden` div) gets
  `min-h-0` so it is height-constrained by its parent instead of growing to fit content.
- This allows the `flex-1 overflow-y-auto` messages area to activate vertical scrolling
  when messages overflow.

**No change to:**
- The `overflow-hidden` on the outer div (C78 scroll containment).
- The full-width assistant message background styling (C78).
- The pinned input area behavior (C78).
- Message state, API calls, markdown rendering, or any other behavior.

---

## Environment Prerequisites

- Node.js and the frontend dev server (`npm run dev` in `frontend/`).

---

## Verification Command

```powershell
node frontend/node_modules/typescript/bin/tsc --noEmit -p frontend/tsconfig.json
```

---

## Focused Tests

- Happy path: messages scroll within the container when they overflow the viewport
  (manual browser check).
- Boundary path: chat input stays pinned at the bottom during scroll
  (manual browser check).
- Regression: assistant messages still show full-width grey background; user messages
  retain blue bubble style (manual browser check).

---

## Done When

- [ ] `min-h-0` is on the inner flex column div.
- [ ] Messages scroll vertically when they overflow.
- [ ] Input area stays pinned at the bottom.
- [ ] `tsc --noEmit` passes.

---

## Developer Test Checkpoint

**Next milestone:** Post-Phase 3 hardening conclusion.

---

## Not In This Commit

- Any other layout or styling changes.
- Chat input auto-resize or multi-line expansion.

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
