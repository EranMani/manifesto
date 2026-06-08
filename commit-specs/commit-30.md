# Commit 30 — `policy-chat-routes` · Rex

**Phase:** 2C — Streaming Policy API
**Assignee:** Rex (Backend)
**Depends on:** C29 (rag-policy-pipeline)

**Viktor + Sage + Mira wave runs on this commit (C30 batch review; authenticated streaming route with user input).**

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/chat.py          # existing registered 501 stubs
  - backend/app/services/rag_policy.py  # C29 event contract
  - backend/app/dependencies.py         # get_current_user
  - backend/app/main.py                 # existing chat router registration

tier2:
  - manifesto-spec.md (§6 Policy RAG, §7 role-based routing)

forbidden:
  - frontend/
  - backend/app/services/
  - backend/app/models/
  - backend/alembic/

estimated_reads: 5
estimated_edits: 3   # chat.py, schema, route/SSE tests
fits_single_agent: true
```

---

## What

Expose the policy pipeline through a versioned, cancellation-aware SSE contract for every
authenticated role. Persistence remains C31.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/chat.py` | edit | Replace policy stub with versioned SSE endpoint |
| `backend/app/schemas/chat.py` | new | Request and typed stream-event schemas |
| `backend/tests/api/test_chat_policy.py` | new | Role, stream framing, failure, and cancellation tests |

Do not create a competing router when `/api/v1/chat` is already registered.

---

## Request Contract

`POST /api/v1/chat/policy`

```json
{
  "message": "What is the leave policy?",
  "provider": "ollama",
  "client_message_id": "uuid"
}
```

Validate provider with a literal/enum, trim and bound message size, reject empty input,
and accept no client-supplied history. Until C31, history is empty; after C31 it is loaded
server-side from the owned conversation.

---

## SSE v1 Contract

Every event has an explicit name and one JSON `data:` payload:

- `meta`: schema version, request ID, provider, and nullable conversation/message IDs
- `delta`: incremental `{ "text": "..." }`
- `sources`: `{ "sources": [structured source objects] }`
- `done`: finish reason and usage fields when available
- `error`: stable public error code, retryable flag, and request ID

The server sends UTF-8 SSE frames separated by a blank line. It may send comment
heartbeats during long provider pauses. Headers include `Cache-Control: no-cache,
no-transform` and `X-Accel-Buffering: no`.

Exactly one terminal `done` or `error` event is emitted when the socket is writable.
Raw exceptions, prompts, document text, API keys, and provider payloads are never exposed.

---

## Reliability

- Start the stream only after authentication and request validation succeed.
- Detect disconnects and cancel retrieval/provider work promptly.
- Do not retry after any `delta` was emitted.
- Do not hold a database transaction or session operation open while waiting on model
  tokens.
- Map normalized provider failures to stable public codes and structured logs.

---

## Test Gate

- Role matrix, invalid provider/message, event ordering, JSON escaping, Unicode, multiline
  content, heartbeats, pre-stream failure, mid-stream failure, and disconnect cancellation.
- Verify deltas arrive before completion using an async test client; a buffered single
  response does not pass.
- Contract snapshot for every SSE event schema.

---

## Done When

- [ ] Employee, manager, and admin can stream policy answers
- [ ] The browser can parse arbitrary transport chunk boundaries
- [ ] Source objects contain stable IDs and provenance, not title strings alone
- [ ] C31 and C32 can build independently against the frozen SSE v1 schema

---

## Handoffs Out

→ Rex (C31): extend the frozen request/meta contract with durable IDs and server-loaded history.

→ Aria (C32): implement the named JSON SSE v1 events exactly; use `fetch`, not `EventSource`.
