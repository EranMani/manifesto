# Commit 28 — `policy-chat-routes` · Rex

**Phase:** 2C — Policy Chat Core
**Assignee:** Rex (Backend)
**Depends on:** C27 (rag-policy-pipeline — `answer_policy_question()` must exist)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header — first 50 lines)

tier1:
  - backend/app/services/rag_policy.py   # Nova's C27 — answer_policy_question() contract
  - backend/app/api/v1/                  # existing route patterns
  - backend/app/dependencies.py          # require_role, get_current_user

tier2:
  - manifesto-spec.md (§7 role-based routing — /chat/policy is open to all roles incl. employee)

forbidden:
  - frontend/
  - backend/app/services/    # Nova's domain — call answer_policy_question(), do not edit it
  - backend/alembic/
```

---

## What

The streaming chat endpoint for policy Q&A — open to all roles (employee, manager, admin).
Accepts a message, calls Nova's RAG pipeline, and streams the response back to the client
via Server-Sent Events. Conversation persistence is **not** in this commit (that's C29) —
for now, the route accepts an optional `conversation_id` and a `provider`, and passes
history through if given. Persistence wiring lands in C29.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/chat_policy.py` | new | `POST /api/v1/chat/policy` — SSE streaming endpoint |
| `backend/app/schemas/chat.py` | new | `ChatRequest`, `ChatStreamChunk` Pydantic schemas |

---

## Route Behavior

```
POST /api/v1/chat/policy
  - get_current_user (any authenticated role — employee, manager, admin)
  - Body: { message: str, provider: "ollama" | "openai", conversation_id?: UUID, history?: list[Message] }
  - Construct LLMService(provider)
  - Call answer_policy_question(message, history, llm, db)
  - Stream chunks back as text/event-stream (SSE)
  - Final event includes citations: list[str]
```

Use FastAPI `StreamingResponse` with `media_type="text/event-stream"`. Do not buffer the
full response before sending — stream as `LLMService.chat()` yields.

---

## Done When

- [ ] `POST /api/v1/chat/policy` streams tokens incrementally (verified via curl `--no-buffer` or equivalent — not a full-buffer response)
- [ ] All three roles (employee, manager, admin) can call this route successfully
- [ ] Final SSE event carries `citations: string[]`
- [ ] Invalid `provider` value returns 422, not a 500
- [ ] No blocking calls inside the async generator

---

## Handoffs Out

→ Aria (C30): `POST /api/v1/chat/policy` returns an SSE stream. Each event is a text
chunk; the final event has shape `{ done: true, citations: string[] }`. Request body:
`{ message, provider, conversation_id?, history? }`.
→ Rex (C29): this route currently does not persist messages — C29 adds `conversation_id`
creation/lookup and message persistence around this same handler.
