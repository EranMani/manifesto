# Commit 32 — `citations-ui` · Aria

**Phase:** 2D — Chat Frontend
**Assignee:** Aria (Frontend)
**Depends on:** C30 (policy-chat-ui — `StreamingMessage` citation slot), C27 (rag-policy-pipeline — citations are document titles, not raw chunk IDs)

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header — first 50 lines)

tier1:
  - frontend/src/components/chat/StreamingMessage.tsx   # Aria's own C30 — citation slot lives here
  - frontend/src/api/chat.ts                            # Aria's own C30 — final SSE event shape

tier2:
  - manifesto-spec.md (§7 — "Citations shown below assistant responses: 'Source: Employee Handbook v3'", line ~348)

forbidden:
  - backend/
```

---

## What

Render source citations beneath each assistant message in the policy chat — the final
piece of the Phase 2 chat experience. Small, focused commit.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `frontend/src/components/chat/Citations.tsx` | new | Renders `"Source: <title>"` line(s) below a message |
| `frontend/src/components/chat/StreamingMessage.tsx` | edit | Mount `Citations` once the stream's final event delivers `citations: string[]` |

---

## Behavior

- Citations appear only after the stream completes (final SSE event: `{ done: true, citations: string[] }`).
- Format: `Source: Employee Handbook v3` — one line per cited document title, de-duplicated.
- If `citations` is empty (model found nothing relevant and said so), render nothing —
  do not show an empty "Source:" line.
- Citations must also render correctly when a historical conversation is reloaded from
  the sidebar (C31) — confirm the persisted/reloaded message shape carries citation data,
  or that it's acceptable for reloaded messages to show no citations (raise to Claude if
  the persistence contract from C29 doesn't carry this — may need a follow-up).

---

## Done When

- [ ] Citations render below an assistant message immediately after streaming completes
- [ ] Format matches `Source: <document title>`, de-duplicated, one per line
- [ ] No "Source:" block renders when there are zero citations
- [ ] Citations behave correctly (render or gracefully absent) on reloaded historical conversations

---

## Handoffs Out

*(none — this closes the Phase 2 "Policy RAG" chat experience per manifesto-spec.md §1 Phase 2 scope)*
