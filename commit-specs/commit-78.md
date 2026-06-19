# Commit 78 - `fix-chat-layout-scroll-width` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C77
**Estimated diff lines:** 30
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

The chat input stays fixed at the bottom of the viewport (outside the scroll area),
and the assistant message grey background spans the full width of the chat layout.

---

## Semantic Fit Review

- **Atomic outcome:** Two CSS-level changes to the same component that together fix
  the chat layout; neither is independently useful without the other for a coherent
  visual result.
- **Failure boundary:** Only Assistant.tsx layout classes change; no state, API, or
  component contract is affected.
- **Budget rationale:** One file, ~30 diff lines, no logic changes — well within the
  XS envelope.

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
  - commit-specs/commit-78.md
  - frontend/src/pages/Assistant.tsx

forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Assistant.tsx` | edit | Fix scroll containment and assistant message background width |

---

## Contract

**Scroll containment:**
- The outer `h-screen` div gets `overflow-hidden` so the browser never scrolls the
  entire page; only the messages `overflow-y-auto` div scrolls.
- The chat input (textarea + Send button) and suggested questions remain pinned below
  the scroll area — never scroll with messages.

**Full-width assistant background:**
- Assistant message rows render with `bg-gray-100` spanning the full width of the chat
  container (edge to edge of the `max-w-3xl` column), using `-mx-4 px-4` to break out
  of the container's horizontal padding.
- `rounded-lg` is removed from assistant messages (full-width bands don't use rounded
  corners).
- `max-w-[80%]` is removed from the assistant message wrapper (content flows at full
  container width).
- User messages retain their existing right-aligned blue bubble style unchanged.
- The loading "Thinking..." indicator and error message adopt the same full-width
  background treatment as assistant messages for visual consistency.

**No change to:**
- Message state, API calls, markdown rendering, evidence graph, citations, or
  suggested questions behavior.

---

## Environment Prerequisites

- Node.js and the frontend dev server (`npm run dev` in `frontend/`).

---

## Verification Command

```powershell
npx --prefix frontend tsc --noEmit
```

---

## Focused Tests

- Happy path: the chat input is visually pinned at the bottom while messages scroll
  above it (manual browser check).
- Boundary path: assistant message grey background extends to the full container width
  with no horizontal gap (manual browser check).
- Regression: user messages still render as right-aligned blue bubbles with
  `max-w-[80%]`.

---

## Done When

- [ ] `overflow-hidden` is on the outer `h-screen` div.
- [ ] Assistant messages use full-width `bg-gray-100` band (no `max-w-[80%]`, no
  `rounded-lg`).
- [ ] User messages are unchanged (blue bubble, right-aligned, `max-w-[80%]`).
- [ ] `npx --prefix frontend tsc --noEmit` passes.

---

## Developer Test Checkpoint

**Next milestone:** Post-Phase 3 hardening conclusion.

---

## Not In This Commit

- Chat input auto-resize or multi-line expansion (future enhancement).
- Sidebar or navigation layout changes (not in scope).

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
