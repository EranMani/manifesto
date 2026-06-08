# Commit 33 — `conversation-sidebar-ui` · Aria

**Phase:** 2D — Conversation History
**Assignee:** Aria (Frontend)
**Depends on:** C31 (conversation-persistence), C32 (policy-chat-ui)

**Mira runs on this commit (new user-facing navigation and history workflow).**

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/pages/ChatPolicy.tsx   # C32 chat state
  - frontend/src/api/chat.ts            # live stream IDs and source types
  - frontend/src/main.tsx                # QueryClient configuration

tier2:
  - manifesto-spec.md (§9 Chat History Persistence)

forbidden:
  - backend/

estimated_reads: 4
estimated_edits: 4   # sidebar, conversation API, page integration, tests
fits_single_agent: true
```

---

## What

Add a paginated, race-safe conversation sidebar and make the selected conversation
addressable and reloadable without corrupting an active stream.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `frontend/src/components/chat/ConversationSidebar.tsx` | new | Paginated policy conversation navigation |
| `frontend/src/api/conversations.ts` | new | Typed list/history API functions |
| `frontend/src/pages/ChatPolicy.tsx` | edit | URL selection, history loading, and cache updates |
| `frontend/src/components/chat/__tests__/conversation-sidebar.test.tsx` | new | Race, navigation, pagination, and history tests |

---

## Behavior

- Fetch policy conversations through TanStack Query using the backend cursor contract.
- Use a URL query parameter such as `?conversation=<uuid>` as the selection source of
  truth so reload/back/forward behavior is predictable.
- Clicking an item aborts or explicitly confirms leaving an active stream, cancels stale
  history requests, then loads paginated messages and structured sources.
- Guard against out-of-order responses: a late response for conversation A must never
  replace the currently selected conversation B.
- "New conversation" clears the URL selection and opens the provider modal.
- After the first `meta` event provides a conversation ID, update the URL and query cache
  immediately; after completion, update title/timestamp without a page reload.
- Show loading, empty, pagination, and recoverable-error states. Long titles truncate
  visually while retaining accessible full text.
- Group by `chat_type` only if the endpoint is shared across chat pages; on the policy page,
  query `chat_type=policy` instead of fetching unrelated logistics history.

---

## State Rules

- Server data lives in Query cache; transient draft/stream state stays local to the page.
- Switching conversations resets draft assistant state but not cached completed history.
- Provider is read from the selected conversation and cannot be changed.
- Historical message ordering remains stable while older pages are prepended.

---

## Test Gate

- Empty/list/pagination states, URL deep link, back/forward, stale-response race, new
  conversation cache insertion, timestamp update, provider lock, history citations, and
  active-stream navigation.

---

## Done When

- [ ] Reloading a selected URL restores the same owned conversation
- [ ] Newly completed conversations appear and reorder without full-page refresh
- [ ] Rapid selection cannot display messages from the wrong conversation
- [ ] History remains bounded through cursor pagination

---

## Handoffs Out

→ Aria (C34): historical assistant messages already carry the same structured source
objects as live completed messages.
