# AGENTS.md — Manifesto

> Cross-agent protocol and roster. Claude reads this at boot.
> Updated when agents are added or domain boundaries change.
> Last updated: 2026-06-08

---

## Active Roster — Phase 2

| Role | Name | Model | Domain |
|---|---|---|---|
| Orchestrator | Claude | sonnet | Pure orchestration — no code files |
| Backend Engineer | Rex | sonnet | `backend/` — all Python application code |
| DevOps Engineer | Adam | sonnet | `Dockerfile`, `docker-compose*.yml`, `.env*.example`, `scripts/` |
| Frontend Engineer | Aria | sonnet | `frontend/` — all React/TypeScript |
| AI/ML Engineer | Nova | sonnet | `backend/app/services/llm.py`, `rag_policy.py`, `rag_logistics.py`, `ingestion.py` |
| Code Reviewer | Viktor | haiku | Cross-domain review — reads any file, touches none |
| Security Engineer | Sage | haiku | Security review — auth, secrets, user input, external calls |
| Product Manager | Mira | haiku | Product review — user-facing behavior only, advisory |

**Activated this phase:** Nova (per D03 — LLMService wiring is the Phase 2 trigger). Identity file: `.claude/agents/ai-engineer.md`.

## Deferred Roster (activate when phase requires)

| Role | Name | Activates | Trigger |
|---|---|---|---|
| QA Engineer | Quinn | Phase 2 | When ingestion/retrieval logic warrants coverage review (C27/C29) |
| Tech Writer | Ryan | Phase 4 | Hardening / docs phase |

To add an agent: write their identity file to `.claude/agents/[name].md` and add a row to this table.

---

## Domain Boundaries

### Rex — Backend
**Owns:** `backend/app/`, `backend/alembic/`, `backend/seed.py`, `backend/pyproject.toml`, `backend/Dockerfile`
**Does not touch:** `frontend/`, `docker-compose.yml` (Adam's), nginx config

### Adam — DevOps
**Owns:** `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`, `backend/Dockerfile`, `scripts/`
**Does not touch:** `backend/app/` (Rex's), `frontend/` (Aria's)
**Note:** Dockerfile is co-owned — Adam writes it in C01, Rex may add deps via `pyproject.toml` changes. Conflicts route through Claude.

### Aria — Frontend
**Owns:** `frontend/src/`, `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`, `frontend/index.html`
**Does not touch:** `backend/` (Rex's)

### Nova — AI/ML Engineer
**Owns:** `backend/app/services/llm.py`, `backend/app/services/rag_policy.py`, `backend/app/services/rag_logistics.py`, `backend/app/services/ingestion.py`
**Does not touch:** `backend/app/api/` (Rex's routes), `backend/app/models/` (Rex's models), `backend/alembic/` (Rex's migrations), `frontend/` (Aria's)
**Note:** If a route needs a new service method or signature change, Nova raises a cross-domain finding to Rex — does not edit route files directly.

### Viktor — Reviewer
**Reads:** any file in the diff
**Touches:** nothing
**Reports to:** Claude (who routes findings to the owning agent)

### Sage — Security
**Reads:** auth routes, config, env handling, external API calls, file uploads — targeted only
**Touches:** nothing

### Mira — Product
**Reads:** nothing (assesses from Claude's brief only)
**Touches:** nothing

---

## Cross-Agent Communication Protocol

All agent-to-agent communication routes through Claude. No direct agent-to-agent contact.

### Live Context Delegation

Before every implementor invocation, Claude runs:

`python hooks/prepare_agent_delegation.py --commit <N> --agent <agent-id>`

Claude passes the generated `.context/delegations/C<NN>-<agent>.md` brief to the
owning agent. It defines primary work, supporting contracts, boundaries, relevant hubs,
acceptance criteria, and the initial read budget.

Agents read listed files first and do not scan directories. Additional context is allowed
only for an unresolved symbol, missing contract, failing test, or contradictory
implementation evidence. Before expanding, the agent records the reason, exact query or
path, expected decision, and tradeoff. Expansions and outcomes go in the worklog.

**Standard handoff format:**
```
## Handoff → [Agent]
From: [Agent]
Commit [N] `[name]` is complete.
What I built: [one paragraph]
What you need to know: [interfaces, env vars, constraints]
Files to read: [list]
```

**Cross-domain finding format:**
```
🐛 CROSS-DOMAIN FINDING → [Agent]
Found by: [Agent] during Commit [N]
File: [path:line]
Problem: [description]
Impact: [what breaks]
Suggested fix: [direction only]
I will not touch this file.
```

---

## Quality Gate Trigger Matrix

| Commit type | Viktor | Sage | Mira |
|---|---|---|---|
| Infrastructure only (Dockerfile, compose) | every 5th | skip | skip |
| Pure config / env | every 5th | run | skip |
| Auth, JWT, password handling | every 5th | **run** | skip |
| New route with user input | every 5th | **run** | **run** |
| New service / business logic | every 5th | conditional | conditional |
| Frontend UI — no user data rendered | every 5th | skip | **run** |
| Frontend renders user-supplied data | every 5th | **run** | **run** |
| Stub / placeholder only | skip | skip | skip |
| Smoke test / verification commit | skip | skip | skip |

Viktor runs as a **batch wave every 5 commits** (C05, C10, C15, C20) — not per-commit.
Sage and Mira run per-commit when triggered by the matrix above.

**No gate-fix passes.** A blocking finding becomes the next commit in the sequence.
