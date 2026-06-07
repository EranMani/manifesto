# Commit 31 — `conversation-sidebar-ui` · Aria

**Phase:** 2D — Chat Frontend
**Assignee:** Aria (Frontend)
**Depends on:** C29 (conversation-persistence — history endpoints must exist), C30 (policy-chat-ui — sidebar mounts alongside the chat shell)

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header — first 50 lines)

tier1:
  - frontend/src/pages/PolicyChat.tsx        # Aria's own C30 — sidebar mounts alongside this
  - frontend/src/api/chat.ts                 # Aria's own C30 — confirm conversationId plumbing

tier2:
  - manifesto-spec.md (§9 Chat History Persistence, lines ~388-402)

forbidden:
  - backend/
```

---

## What

The conversation history sidebar: lists past conversations grouped by type (policy /
logistics — though only `/chat/policy` exists in Phase 2), and loads full message history
on click.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `frontend/src/components/chat/ConversationSidebar.tsx` | new | List of past conversations, grouped, clickable |
| `frontend/src/api/conversations.ts` | new | `listConversations()`, `getConversationMessages(id)` |

---

## Behavior

- Fetch via `GET /api/v1/conversations` (Rex's C29) — group by `chat_type`; Phase 2 only
  populates `policy`, but render the grouping so `logistics` slots in cleanly in Phase 3.
- Clicking a conversation calls `GET /api/v1/conversations/{id}/messages` and loads the
  full history into `PolicyChat.tsx`'s message list (pass via the prop/state Aria added in C30).
- Each item shows the auto-generated `title` and a relative timestamp (`updated_at`).
- "New conversation" remains available from the sidebar — opens `ProviderSelectModal` from C30.

---

## Done When

- [ ] Sidebar lists the current user's conversations, grouped by `chat_type`
- [ ] Clicking a conversation loads its full message history into the chat view
- [ ] Newly created conversations (sent from `PolicyChat.tsx`) appear in the sidebar without a full page reload
- [ ] No cross-user data is visible (sidebar only ever calls the authenticated user's endpoints)

---

## Handoffs Out

→ Aria (C32): loaded historical messages must also carry citation data if present —
confirm `getConversationMessages` response shape includes whatever C32 needs to re-render citations on reload.
