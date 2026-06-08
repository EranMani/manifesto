# Commit 31 — `conversation-persistence` · Rex

**Phase:** 2C — Durable Conversation Orchestration
**Assignee:** Rex (Backend)
**Depends on:** C30 (policy-chat-routes)

**Sage runs on this commit (owner-scoped user data, durable stream state, and citations).**

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/chat.py          # C30 streaming route
  - backend/app/models/conversation.py  # existing model
  - backend/app/models/message.py       # existing model
  - backend/alembic/versions/0001_initial.py  # applied conversation/message DDL

tier2:
  - manifesto-spec.md (§9 Chat History Persistence)

forbidden:
  - frontend/
  - backend/app/services/

estimated_reads: 5
estimated_edits: 7   # migration, models, citation model, schemas, routes, tests
fits_single_agent: true
```

---

## What

Wire ownership-safe, idempotent conversation persistence into the stream and preserve
structured citation provenance for historical reloads. Conversation/message tables and
models already exist; this commit extends them instead of recreating them.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/alembic/versions/XXXX_conversation_stream_state.py` | new | Add message state/idempotency and citation table |
| `backend/app/models/conversation.py` | edit | Add list/query indexes or relationships as needed |
| `backend/app/models/message.py` | edit | Add client ID, status, and safe error state |
| `backend/app/models/message_citation.py` | new | Durable structured source provenance |
| `backend/app/schemas/conversation.py` | new | Paginated conversation/history schemas |
| `backend/app/api/v1/chat.py` | edit | Add persistence around C30 stream |
| `backend/tests/api/test_conversations.py` | new | Ownership, retry, concurrency, and history tests |

---

## Schema

Extend messages with:

- `client_message_id` for retry idempotency
- `status`: `streaming | completed | failed | cancelled`
- optional safe `error_code`
- index/constraint preventing duplicate user sends within a conversation

Create `message_citations` with assistant message ID, rank, source label, nullable
document/chunk IDs, title snapshot, page/section snapshot, and retrieval score. Snapshot
fields preserve useful history if a policy document is later removed.

Add an index for the user's conversation list and ensure `updated_at` changes on every
completed exchange.

---

## Chat Behavior

- Request extends C30 with optional `conversation_id`.
- New conversation is created from the first message with `chat_type='policy'`, fixed
  provider, and a normalized title derived from at most 60 characters.
- Existing conversations are loaded by both ID and current user ID. Do not distinguish
  "missing" from "belongs to another user" in the public response.
- The provider cannot change mid-conversation.
- The server loads a token-bounded history of completed messages; client history is never
  trusted.
- Persist/commit the user message before external provider work, using
  `client_message_id` to make a client retry idempotent.
- Create an assistant row as `streaming`, accumulate the bounded response in request
  memory, then persist content, sources, status, and conversation timestamp in one short
  completion transaction.
- On disconnect/provider failure, mark the assistant message `cancelled` or `failed`.
  Never label a partial answer completed.
- Do not keep a transaction open for the duration of the SSE stream.

The `meta` SSE event now returns real conversation and message IDs without changing its
schema version.

---

## History API

- `GET /api/v1/conversations?chat_type=policy&cursor=...&limit=...`
- `GET /api/v1/conversations/{id}/messages?before=...&limit=...`

Both are cursor-paginated, stable-ordered, owner-scoped, and return structured citations
for assistant messages. Internal failure details and retrieval scores may be omitted from
the employee-facing response.

---

## Concurrency and Retry Rules

- Concurrent first sends cannot create duplicate exchanges for one client message ID.
- A retry of a completed request returns/replays the stored result contract rather than
  calling the provider again.
- A second simultaneous message for the same conversation is rejected with a retryable
  conflict unless explicit ordering is implemented.

---

## Test Gate

- Ownership isolation, fixed provider, pagination, ordering, title generation, idempotent
  retry, simultaneous-send conflict, completion, provider error, and disconnect.
- Verify source rows and title/page snapshots survive historical reload.
- Verify no database transaction spans provider token delays.

---

## Done When

- [ ] Every terminal stream state has a corresponding durable message state
- [ ] Historical messages reproduce citations exactly
- [ ] Cross-user access leaks neither content nor object existence
- [ ] Retrying the same client message does not duplicate model calls or rows

---

## Handoffs Out

→ Aria (C33/C34): history endpoints are cursor-paginated and return the same structured
source shape as live SSE completion.

→ Nova (Phase 3): logistics messages may reuse the durable status/idempotency framework
and add persisted plan/SQL provenance.
