# Nova — Worklog
# Project: Manifesto
# Stack: FastAPI + SQLAlchemy + PostgreSQL + pgvector + LLMService (Ollama/OpenAI)

---

## Current State
*Last updated: Onboarding · 2026-06-07*

**Last completed:** none — Nova activates this phase
**Currently active:** none
**Blocked by:** none

**📋 Onboarding Notice — 2026-06-07**

Welcome, Nova. You're activating because Phase 2 ("Policy RAG") requires `LLMService` to be
wired for real — your domain. Here's what you need to know before C24:

- **Your domain:** `backend/app/services/llm.py`, `rag_policy.py`, `rag_logistics.py`, `ingestion.py`.
  Identity file: `.claude/agents/ai-engineer.md`. Read it first — it has your stack, standards,
  and the frozen `LLMService` interface contract from Rex's C16 stub.
- **Your first commit:** C24 `llm-service-impl` — implement `chat()` and `embed()` for both
  `ollama` and `openai` providers. The signatures are frozen — do not change them.
- **Critical early decision:** pick ONE provider for embeddings (Ollama `nomic-embed-text`,
  768-dim, vs. OpenAI `text-embedding-3-small`, 1536-dim) and document it — `policy_chunks.embedding`
  (created in Rex's C23, spec'd at `VECTOR(1536)`) must match. If you choose 768-dim, raise a
  cross-domain finding to Rex for a follow-up migration before C25.
- **Cross-domain rule:** you don't touch routes, models, or migrations — that's Rex's. If your
  pipeline needs a new dependency (e.g. PyMuPDF, python-docx for C25) or a route change, raise
  a cross-domain finding through Claude. You'll need this in C25.

**Open Handoffs — Inbound:**
- ← Rex (C16): `LLMService.chat(messages: list[dict[str, str]], stream: bool = True) -> AsyncIterator[str]`,
  `embed(text: str) -> list[float]`. Frozen — implement against these signatures.
- ← Rex (C23, when complete): `policy_chunks.embedding` dimension — confirm it matches your provider choice.

**Open Handoffs — Outbound:**
- (none yet — first commit not started)

**Key Interfaces I Will Own:**
- `backend/app/services/llm.py` — `LLMService` (Ollama + OpenAI abstraction)
- `backend/app/services/rag_policy.py` — retrieval + generation + citations for policy chat
- `backend/app/services/ingestion.py` — document chunking + embedding pipeline
- `backend/app/services/rag_logistics.py` — text-to-SQL pipeline (Phase 3)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| — | — | — | — |
