# Commit 24 — `llm-service-impl` · Nova

**Phase:** 2A — RAG Storage Foundation
**Assignee:** Nova (AI/ML Engineer) — **first commit, Nova activates here**
**Depends on:** C23 (pgvector-migration — confirms embedding dimension before Nova commits to a provider)

---

## context

```
tier0:
  - .claude/agents/ai-engineer.md (Current State header — first 50 lines; this is Nova's onboarding read)

tier1:
  - backend/app/services/llm.py        # C16 stub — interface contract Nova implements against
  - backend/app/core/config.py         # confirm OLLAMA_BASE_URL / OPENAI_API_KEY env var names

tier2:
  - manifesto-spec.md (§5 LLM Provider Abstraction, lines ~186-221)

forbidden:
  - frontend/
  - backend/app/api/        # Rex's routes — not touched this commit
  - backend/app/models/     # Rex's models — not touched this commit
  - backend/alembic/        # Rex's migrations

estimated_reads: 3
estimated_edits: 1   # llm.py — implement in place, signature frozen
fits_single_agent: true
```

---

## What

Implement `LLMService.chat()` and `LLMService.embed()` for both `ollama` and `openai`
providers, replacing the `NotImplementedError` stubs from C16. **Do not change the
method signatures** — they were frozen in the C16 handoff and routes will be built
against them in C28.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/app/services/llm.py` | edit | Implement `chat()` and `embed()` with provider branching |

---

## Interface (frozen — from C16)

```python
class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]) -> None: ...

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = True
    ) -> AsyncIterator[str]: ...

    async def embed(self, text: str) -> list[float]: ...
```

- `chat()`: branch on `self.provider` → `_ollama_chat` (`llama3` via local Ollama HTTP API)
  or `_openai_chat` (`gpt-4o` via OpenAI SDK). Stream tokens as they arrive when `stream=True`.
- `embed()`: branch on `self.provider` → `_ollama_embed` (`nomic-embed-text`, 768-dim) or
  `_openai_embed` (`text-embedding-3-small`, 1536-dim).

**Provider/dimension decision:** Pick ONE provider for embeddings and document it in your
worklog — `policy_chunks.embedding` (C23) must match. If you choose Ollama (768-dim) and
C23 shipped `VECTOR(1536)`, raise a cross-domain finding to Rex for a follow-up migration
*before* C25 starts.

---

## Done When

- [ ] `LLMService("ollama").chat([...])` and `LLMService("openai").chat([...])` both stream real tokens (no `NotImplementedError`)
- [ ] `LLMService("ollama").embed(text)` and `LLMService("openai").embed(text)` both return `list[float]` of the documented dimension
- [ ] No provider SDK is imported or called outside `llm.py`
- [ ] Method signatures unchanged from C16

---

## Handoffs Out

→ Nova (C25, C27): provider chosen for embeddings is **[fill in at commit time]**, dimension
**[768 | 1536]**. `chat()` streams `AsyncIterator[str]` — consume with `async for`.
→ Rex (C28): `LLMService.chat()` is ready to wire into a streaming SSE route. Pass
`messages: list[dict[str, str]]` (OpenAI-style `{role, content}` dicts).
