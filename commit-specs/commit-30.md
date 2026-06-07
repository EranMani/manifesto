# Commit 30 — `policy-chat-ui` · Aria

**Phase:** 2D — Chat Frontend
**Assignee:** Aria (Frontend)
**Depends on:** C28 (policy-chat-routes — SSE contract must exist; does not need C29's persistence to land first per Wave C)

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header — first 50 lines)

tier1:
  - frontend/src/api/client.ts        # Axios instance — confirm SSE/streaming approach fits, or use fetch directly for streams
  - frontend/src/store/auth.ts        # token access for Authorization header on the stream request
  - frontend/src/App.tsx              # routing — /chat/policy is in the role-based route table for all roles

tier2:
  - manifesto-spec.md (§7 Frontend Architecture — Chat Policy view, lines ~344-349)

forbidden:
  - backend/
```

---

## What

The policy chat page: message input, streaming response display, and a provider-selection
modal for new conversations. No sidebar yet (C31) and no citation rendering yet (C32) —
this commit is the chat shell and streaming mechanics.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `frontend/src/pages/PolicyChat.tsx` | new | Page: message list + input, mounted at `/chat/policy` |
| `frontend/src/components/chat/MessageInput.tsx` | new | Text input + send button |
| `frontend/src/components/chat/StreamingMessage.tsx` | new | Renders an in-progress streamed assistant message |
| `frontend/src/components/chat/ProviderSelectModal.tsx` | new | "New conversation" → Ollama / OpenAI picker |
| `frontend/src/api/chat.ts` | new | `streamPolicyChat(message, provider, conversationId?, history?)` — consumes the SSE endpoint |

---

## Behavior

- `/chat/policy` is reachable by all three roles (employee, manager, admin) — confirm it's
  not behind a role-restrictive guard in `ProtectedRoute` beyond "authenticated".
- "New conversation" opens `ProviderSelectModal` (Ollama / OpenAI) before the first message can be sent.
- Sending a message appends it to the list immediately, then renders the assistant's
  response token-by-token as the SSE stream arrives (`StreamingMessage`).
- `api/chat.ts` should use `fetch` with a `ReadableStream` reader (or `EventSource` if the
  backend's SSE format supports GET — confirm against C28's `POST` contract; `fetch` streaming
  is the safer default for a `POST` body).
- Attach `Authorization: Bearer <token>` from the auth store on the streaming request.

---

## Done When

- [ ] `/chat/policy` renders for employee, manager, and admin logins
- [ ] "New conversation" prompts provider selection before the first send
- [ ] Sent messages appear immediately; assistant responses render incrementally as they stream (not as one final blob)
- [ ] No browser console errors during a full send → stream → complete cycle
- [ ] Stream request carries the JWT `Authorization` header

---

## Handoffs Out

→ Aria (C31): `PolicyChat.tsx` will need a `conversationId` prop/route param to support
loading a past conversation from the sidebar — the message list should accept pre-loaded
history as initial state.
→ Aria (C32): `StreamingMessage` needs a slot for citations once the stream completes —
final SSE event carries `{ done: true, citations: string[] }` per C28's contract.
