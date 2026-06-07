# Commit 27 — `rag-policy-pipeline` · Nova

**Phase:** 2C — Policy Chat Core
**Assignee:** Nova (AI/ML Engineer)
**Depends on:** C24 (llm-service-impl)

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header — first 50 lines)

tier1:
  - backend/app/services/rag_policy.py   # C16 stub
  - backend/app/services/llm.py          # Nova's own C24 work

tier2:
  - manifesto-spec.md (§6 RAG Pipeline — Policy Chat, lines ~261-289)

forbidden:
  - frontend/
  - backend/app/api/        # Rex builds the route in C28 — Nova provides the pipeline only
  - backend/app/models/
  - backend/alembic/
```

---

## What

Implement the policy-chat RAG pipeline: embed the user's query, retrieve the most
relevant document chunks via cosine similarity, build a grounded prompt, stream the
LLM's answer, and surface document-title citations. Exposed as an async generator that
C28's chat route consumes — Nova does not write the route.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/rag_policy.py` | edit | Implement retrieve → prompt → stream → cite pipeline |

---

## Pipeline (per manifesto-spec.md §6)

```
Embed query via LLMService.embed()
  → Cosine similarity search in pgvector (top-k=5, policy_chunks.embedding)
  → Build prompt: system prompt + retrieved chunks + last 6 messages of conversation history
  → Stream response via LLMService.chat()
  → Track which policy_documents the retrieved chunks came from → citations
```

**System prompt (verbatim from spec):**
```
You are Manifesto, a company assistant. Answer only using the policy excerpts
provided below. If the answer is not found in the excerpts, say so clearly —
do not invent policies or procedures. Where relevant, cite which document your
answer comes from by name.
```

Suggested entry point (Nova may refine — this is the contract C28 builds against):
```python
async def answer_policy_question(
    query: str,
    history: list[dict[str, str]],   # last 6 messages, {role, content}
    llm: LLMService,
    db: AsyncSession,
) -> AsyncIterator[PolicyChatChunk]:  # streamed text + final citations payload
```

---

## Done When

- [ ] Query embedding uses the same provider/dimension fixed in C24
- [ ] Top-5 chunks retrieved via pgvector cosine similarity (`<=>` operator / `vector_cosine_ops`)
- [ ] Prompt includes system prompt + retrieved chunk text + last 6 conversation messages
- [ ] Response streams token-by-token via `LLMService.chat()`
- [ ] Citations resolve to `policy_documents.title` (e.g. "Employee Handbook v3"), not raw chunk IDs
- [ ] If no relevant chunks are found, the model is instructed to say so rather than invent an answer

---

## Handoffs Out

→ Rex (C28): `answer_policy_question(query, history, llm, db)` yields streamed text chunks
followed by a citations payload. Wire this into an SSE response — the frontend (C30/C32)
expects streamed text plus a `citations: string[]` field at stream end.
