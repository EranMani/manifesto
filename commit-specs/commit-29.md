# Commit 29 — `conversation-persistence` · Rex

**Phase:** 2C — Policy Chat Core
**Assignee:** Rex (Backend)
**Depends on:** C28 (policy-chat-routes — the route this wires persistence into already exists)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header — first 50 lines)

tier1:
  - backend/app/api/v1/chat_policy.py   # Rex's own C28 — the route this commit extends
  - backend/app/models/__init__.py

tier2:
  - manifesto-spec.md (§4 schema — conversations/messages DDL, lines ~127-148; §9 Chat History Persistence, lines ~388-402)

forbidden:
  - frontend/
  - backend/app/services/
```

---

## What

Add the `conversations` and `messages` tables, models, and history routes — then wire
persistence into the C28 chat route so every exchange is saved and can be reloaded.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/alembic/versions/XXXX_conversations_messages.py` | new | `conversations`, `messages` tables + index |
| `backend/app/models/conversation.py` | new | `Conversation`, `Message` SQLAlchemy models |
| `backend/app/api/v1/conversations.py` | new | `GET /api/v1/conversations`, `GET /api/v1/conversations/{id}/messages` |
| `backend/app/api/v1/chat_policy.py` | edit | Create/look up conversation; persist user + assistant messages around the existing stream |

---

## Schema (per manifesto-spec.md §4)

```sql
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID REFERENCES users(id) ON DELETE CASCADE,
    chat_type    TEXT NOT NULL CHECK (chat_type IN ('policy', 'logistics')),
    llm_provider TEXT NOT NULL CHECK (llm_provider IN ('ollama', 'openai')),
    title        TEXT,
    created_at   TIMESTAMPTZ DEFAULT NOW(),
    updated_at   TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content         TEXT NOT NULL,
    sql_query       TEXT,
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX ON messages (conversation_id, created_at);
```

## Behavior

- New conversation: created on first message, with `chat_type='policy'` and the
  client-selected `llm_provider`. Title auto-generated from the first user message
  (trimmed to 60 chars).
- `llm_provider` is fixed at creation — cannot change mid-conversation (enforced at the route, not just DB).
- Every exchange persists both the user message and the assistant's full streamed response.
- `GET /api/v1/conversations` — list current user's conversations, grouped by `chat_type`.
- `GET /api/v1/conversations/{id}/messages` — full history for sidebar reload; 404/403 if not the owner.

---

## Done When

- [ ] Migration creates both tables with correct constraints, FKs, and index
- [ ] Sending a policy chat message creates a conversation (if new) and persists both messages
- [ ] Title is auto-generated from the first user message, ≤60 chars
- [ ] `GET /api/v1/conversations` returns only the current user's conversations
- [ ] `GET /api/v1/conversations/{id}/messages` returns ordered history; rejects access to another user's conversation
- [ ] Attempting to change `llm_provider` mid-conversation is rejected

---

## Handoffs Out

→ Aria (C31): `GET /api/v1/conversations` returns `{id, chat_type, llm_provider, title, created_at, updated_at}[]`.
`GET /api/v1/conversations/{id}/messages` returns `{id, role, content, sql_query, created_at}[]` ordered by `created_at`.
