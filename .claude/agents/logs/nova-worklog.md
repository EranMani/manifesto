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
wired for real — your domain. Here's what you need to know before C25:

- **Your domain:** `backend/app/services/llm.py`, `rag_policy.py`, `rag_logistics.py`, `ingestion.py`.
  Identity file: `.claude/agents/ai-engineer.md`. Read it first — it has your stack, standards,
  and the provider-neutral service contract in `commit-specs/commit-25.md`.
- **Your first commit:** C25 `llm-service-impl` — implement per-conversation generation
  providers plus the deployment-wide embedding service.
- **Embedding decision:** C24 fixes a deployment-wide 768-dimensional profile. Local
  deployments use Ollama `nomic-embed-text`; OpenAI deployments request 768 dimensions
  from `text-embedding-3-small`. C26 migrates the current vector column before ingestion.
- **Cross-domain rule:** you don't touch routes, models, or migrations — that's Rex's. If your
  pipeline needs a dependency or route change, raise a cross-domain finding through Claude.

**Open Handoffs — Inbound:**
- ← Rex (C24): validated provider settings, dependencies, and one 768-dimensional
  embedding profile.
- ← Rex (C23): `policy_chunks.embedding` is `VECTOR(1536)`.

**Open Handoffs — Outbound:**
- (none yet — first commit not started)

**Key Interfaces I Will Own:**
- `backend/app/services/llm.py` — `LLMService` (Ollama + OpenAI abstraction)
- `backend/app/services/rag_policy.py` — retrieval + generation + citations for policy chat
- `backend/app/services/ingestion.py` — document chunking + embedding pipeline
- `backend/app/services/rag_logistics.py` — graph-plan-to-SQL pipeline (Phase 3)

**Archive Reference:**
No archived sessions yet.

---

## Session Index

| # | Commit | Status | Key Decision |
|---|--------|--------|--------------|
| — | — | — | — |
