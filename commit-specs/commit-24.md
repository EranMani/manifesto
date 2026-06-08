# Commit 24 — `llm-runtime-config` · Rex

**Phase:** 2A — Provider Foundation
**Assignee:** Rex (Backend)
**Depends on:** C23 (pgvector-migration)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/app/core/config.py     # settings pattern and current provider variables
  - backend/pyproject.toml         # direct runtime dependencies
  - backend/app/services/llm.py    # C16 provisional interface consumed by C25

tier2:
  - manifesto-spec.md (§5 LLM Provider Abstraction)

forbidden:
  - frontend/
  - backend/app/api/
  - backend/app/models/
  - backend/alembic/
  - .env.example                   # Adam owns this file; handoff only

estimated_reads: 4
estimated_edits: 3   # config.py, pyproject.toml, uv.lock
fits_single_agent: true
```

---

## What

Prepare the Rex-owned runtime surface required by Nova's provider implementation. This
keeps dependency and application configuration changes out of Nova's service-only domain.

---

## Files to Change

| File | Type | Description |
|---|---|---|
| `backend/pyproject.toml` | edit | Add official OpenAI client, pooled async HTTP client, and tokenizer |
| `backend/uv.lock` | edit | Lock the new direct dependencies |
| `backend/app/core/config.py` | edit | Add validated model, embedding-profile, timeout, and retry settings |

---

## Contract

Add direct dependencies for the official OpenAI async client, a pooled async HTTP client
for Ollama, and the tokenizer used by ingestion. Add validated settings for:

- `OPENAI_API_KEY`
- `OPENAI_CHAT_MODEL` (a pinned deployment default, not a floating "latest" alias)
- `OLLAMA_BASE_URL`
- `OLLAMA_CHAT_MODEL`
- `EMBEDDING_PROVIDER`
- `EMBEDDING_MODEL`
- `EMBEDDING_DIMENSIONS=768`
- connect/read/total timeouts and maximum retry count

The corpus embedding profile is deployment-wide and independent of the conversation's
generation provider. Phase 2 standardizes storage at 768 dimensions: local deployments
default to Ollama `nomic-embed-text`, while OpenAI deployments use
`text-embedding-3-small` with `dimensions=768`. Equal dimensions do not make providers
interchangeable; changing provider or model requires a full re-index.

Secrets remain server-side and are never returned by an API.

---

## Done When

- [ ] `uv sync --locked` succeeds
- [ ] Settings reject unsupported providers, non-positive timeouts, and dimensions other
  than the Phase 2 value of 768.
- [ ] The app can start without an OpenAI key when OpenAI is not selected for either chat or
  embeddings.
- [ ] The new settings and defaults are documented in `config.py` and this commit's handoff

---

## Handoffs Out

→ Nova (C25): rely on validated settings and direct dependencies. The embedding profile
is fixed to one deployment-wide vector space.

→ Adam (next DevOps config commit): mirror the new non-secret setting names into `.env.example`.
configuration commit. Rex does not edit Adam's file in C24.
