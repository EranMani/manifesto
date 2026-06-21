# Commit 97 - `badge-chips-frontend` - Aria

**Phase:** Phase 4 (Action Badges)
**Owner:** aria
**Depends on:** C96
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Clickable action badge chips appear below the assistant's logistics answer; clicking a badge pre-fills the chat input with the badge's prompt text (same interaction model as suggested questions, but visually distinct).

---

## Semantic Fit Review

- **Atomic outcome:** After this commit, users see badge chips below logistics answers and can click them to pre-fill the input. The full Phase 1 badge feature is user-testable.
- **Failure boundary:** If the backend returns `action_badges: []`, no chips render — existing UI behavior is unchanged. Badge rendering is additive-only.
- **Budget rationale:** Three frontend files (API type, store state, page component) in Aria's domain. The component follows the exact pattern of the existing suggested-questions chips with different styling.

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
  - frontend/src/api/assistant.ts

initial_context:
  - commit-specs/commit-97.md
  - frontend/src/pages/Assistant.tsx
  - frontend/src/api/assistant.ts
  - frontend/src/store/assistant.ts
  - docs/product-concepts/assistant-action-badges.md

forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/assistant.ts` | edit | Add ActionBadge interface and action_badges to AssistantQueryResponse |
| `frontend/src/store/assistant.ts` | edit | Store action_badges in state, reset on new query |
| `frontend/src/pages/Assistant.tsx` | edit | Render badge chips below assistant messages, click pre-fills input |

---

## Contract

### API Type Addition (`frontend/src/api/assistant.ts`)

```typescript
export interface ActionBadge {
  label: string
  prompt: string
}

export interface AssistantQueryResponse {
  // ... existing fields ...
  action_badges: ActionBadge[]
}
```

### Store Addition (`frontend/src/store/assistant.ts`)

- New state field: `actionBadges: ActionBadge[]` (default `[]`)
- Set from `response.action_badges` on successful query
- Reset to `[]` on `reset()`

### Component Behavior (`frontend/src/pages/Assistant.tsx`)

- Render badge chips BETWEEN the last assistant message and the suggested questions area
- Only show when `actionBadges.length > 0`
- Each badge is a button with:
  - Text: `badge.label`
  - Styling: visually distinct from suggested questions — use a colored border/background (blue-50 bg, blue-600 border, blue-700 text) to signal "action" vs. the neutral gray of suggested questions
  - On click: `setInput(badge.prompt)` — pre-fills the input textarea (does NOT auto-send)
  - Disabled when `loading` is true
- Layout: flex-wrap row, same horizontal alignment as suggested questions

### Interaction contract:
- Click badge → input pre-fills with `badge.prompt`
- User can edit the pre-filled text before sending
- User presses Enter or Send to execute
- After sending, badges disappear (reset with next response)

---

## Environment Prerequisites

- Frontend dev server running (`npm run dev` in frontend/)
- Backend running with seeded data (to produce logistics answers with badges)
- C96 must be committed (backend returns `action_badges` in response)

---

## Verification Command

```powershell
npx --prefix frontend tsc --noEmit
```

---

## Focused Tests

- **Happy path (manual browser check):** Ask "where is SHP-1001?" → assistant responds with answer + badge chips visible below → click a badge → input pre-fills with badge prompt text
- **Empty badges:** Ask a policy question → no badge chips appear (action_badges is empty)
- **Type safety:** `npx --prefix frontend tsc --noEmit` passes with the new types
- **Loading state:** While assistant is responding, badge buttons are disabled/not clickable

---

## Done When

- [ ] `ActionBadge` type exists in `assistant.ts`
- [ ] Store holds and resets `actionBadges`
- [ ] Badge chips render below logistics answers with distinct styling
- [ ] Clicking a badge pre-fills the input (does not auto-send)
- [ ] TypeScript compiles without errors
- [ ] Manual browser verification: badges appear and click behavior works

---

## Developer Test Checkpoint

- **Ready now:** Full action badges Phase 1 — contextual badge suggestions appear for logistics queries.
- **How to test:** Start the app (`docker compose up -d`, `npm run dev` in frontend/). Log in as admin. Ask "where is SHP-1001?" in the assistant. Below the answer, 2-3 colored action badge chips appear. Click one — the input box fills with the badge's prompt. Press Send to ask the follow-up.
- **Expected result:** Badge chips with labels like "Ask vendor for explanation" appear below delayed shipment answers. Clicking pre-fills the input. Sending the pre-filled message generates a relevant assistant response.
- **Still incomplete:** Badges don't execute real actions (no vendor emails, no estimate updates). Phase 2 will add confirmation flow. Phase 3 will add action handlers.

---

## Not In This Commit

- Badge click confirmation dialog (Phase 2, future)
- Real action execution (Phase 3, future)
- Badge animations or transitions (future polish)
- Badge tooltips with "why" explanation (future polish)

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
