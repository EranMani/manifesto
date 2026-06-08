# Commit 32 — `policy-chat-ui` · Aria

**Phase:** 2D — Streaming Chat UI
**Assignee:** Aria (Frontend)
**Depends on:** C30 (policy-chat-routes)

**Sage + Mira run on this commit (renders streamed user/provider data and introduces the primary chat interaction).**

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/pages/ChatPolicy.tsx  # existing placeholder to replace
  - frontend/src/api/client.ts         # auth/base URL conventions
  - frontend/src/store/auth.ts         # bearer token access
  - frontend/src/App.tsx               # policy route and role guard

tier2:
  - manifesto-spec.md (§7 Chat — Policy)

forbidden:
  - backend/
  - frontend/src/pages/                # except ChatPolicy.tsx

estimated_reads: 5
estimated_edits: 6   # page, 3 components, chat API, tests
fits_single_agent: true
```

---

## What

Replace the existing policy placeholder with an accessible chat state machine and a
transport-correct SSE client. Sidebar/history integration remains C33.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `frontend/src/pages/ChatPolicy.tsx` | edit | Replace placeholder with chat state machine |
| `frontend/src/components/chat/MessageInput.tsx` | new | Accessible message composer and Stop control |
| `frontend/src/components/chat/StreamingMessage.tsx` | new | Incremental assistant rendering |
| `frontend/src/components/chat/ProviderSelectModal.tsx` | new | New-conversation provider selection |
| `frontend/src/api/chat.ts` | new | Authenticated POST SSE parser/client |
| `frontend/src/components/chat/__tests__/policy-chat.test.tsx` | new | Parser and component behavior tests |

---

## Client Contract

`streamPolicyChat` uses `fetch` with `POST`, bearer auth, JSON body, and an
`AbortController`. Each send creates a stable `client_message_id` with
`crypto.randomUUID()`. Automatic retries must reuse that ID and must never silently
duplicate a model request.

Implement a real SSE parser that:

- buffers incomplete transport chunks
- recognizes named events and multiple `data:` lines
- handles CRLF/LF, UTF-8 boundaries, comments/heartbeats, and several events per read
- parses each completed JSON payload by event type
- rejects unsupported schema versions and malformed terminal ordering

Do not use `EventSource`; it cannot send this authenticated POST body.

---

## UI State

Model explicit states: provider selection, idle, submitting, streaming, completed,
cancelled, and failed. Keep user messages, assistant deltas, sources, IDs, and terminal
status as typed data rather than concatenated anonymous strings.

- Provider selection is required for a new conversation and locked after first send.
- The user message appears optimistically; one assistant placeholder receives deltas.
- Disable duplicate submit while a request is active, but provide Stop.
- Stop aborts the request and marks the local response cancelled.
- Errors preserve typed user input and show a retry action only when safe.
- Scrolling follows new output only while the user remains near the bottom.
- Render user and assistant content as text in this commit; no unsafe HTML injection.

---

## Accessibility

- Labeled input, keyboard submit with multiline behavior, visible focus, and modal focus
  trapping/restoration.
- Streaming output uses a restrained live region so every token is not announced
  separately.
- Controls expose disabled/busy state and do not rely on color alone.

---

## Test Gate

- Fragmented/coalesced SSE frames, Unicode split boundaries, heartbeat, malformed JSON,
  error and done events, abort, and unsupported schema version.
- Provider lock, optimistic message, incremental rendering, duplicate-submit prevention,
  safe retry ID, keyboard behavior, and cleanup on unmount.

---

## Done When

- [ ] All authenticated roles can complete a genuinely incremental response
- [ ] Abort closes the network work and leaves the UI usable
- [ ] No raw HTML, tokens, or provider errors leak into the page
- [ ] The data model already has optional conversation/message IDs and structured sources for
  C31/C33/C34.

---

## Handoffs Out

→ Aria (C33): page state accepts server-loaded history and URL-selected conversation IDs.

→ Aria (C34): `StreamingMessage` retains structured sources but does not render them yet.
