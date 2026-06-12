# AGENTS.md — Manifesto

> Cross-agent protocol and roster. Claude reads this at boot.
> Updated when agents are added or domain boundaries change.
> Last updated: 2026-06-12 (Claude-direct execution is the default route)

---

## Active Roster — Phase 2

| Role | Name | Model | Domain |
|---|---|---|---|
| Orchestrator / Default Implementor | Claude | sonnet | Direct execution by default, limited to the active approved commit spec |
| Backend Engineer | Rex | sonnet | `backend/` — all Python application code |
| DevOps Engineer | Adam | sonnet | Infrastructure plus workflow automation under `hooks/` (except `hooks/agent-config.json`, `hooks/tool_cap_end.py`, `hooks/tests/test_tool_cap.py`, `hooks/tool_cap_start.py`, `hooks/tool_cap_enforce.py`, `hooks/post_commit_next_step.py`, `hooks/generate_domain_map.py`, `hooks/tests/test_post_commit_next_step.py`, `hooks/tests/test_generate_domain_map.py`, `hooks/pre_commit_check.py`, `hooks/tests/test_pre_commit_check.py`, `hooks/context_telemetry.py`, `hooks/tests/test_context_telemetry.py`, `hooks/verify_constraints.py`, and `hooks/tests/test_verify_constraints.py` — a narrow Claude/orchestrator exception for the agent identity registry, token telemetry capture/persistence, the commit-gate hook that enforces this protocol, the quality-gate verification script, and the tool-cap budget-gating/enforcement and post-commit protocol-advance/domain-map scripts that drive the commit loop's automated state transitions) |
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
**Owns:** `backend/app/`, `backend/alembic/`, `backend/seed.py`, `backend/pyproject.toml`, `backend/Dockerfile`, `backend/tests/` (except `backend/tests/services/`, Nova's)
**Does not touch:** `frontend/`, `docker-compose.yml` (Adam's), nginx config

### Adam — DevOps
**Owns:** `docker-compose.yml`, `docker-compose.prod.yml`, `.env.example`,
`backend/Dockerfile`, `scripts/`, `hooks/`, and `hooks/tests/`
**Does not touch:** `backend/app/` (Rex's), `frontend/` (Aria's)
**Note:** Dockerfile is co-owned — Adam writes it in C01, Rex may add deps via `pyproject.toml` changes. Conflicts route through Claude.
**Workflow note:** Claude owns orchestration decisions and protocol approval. Adam
implements and tests workflow automation only from an approved commit specification.

### Aria — Frontend
**Owns:** `frontend/src/`, `frontend/package.json`, `frontend/package-lock.json`,
`frontend/vite.config.ts`, `frontend/tailwind.config.ts`, `frontend/tsconfig.json`,
`frontend/index.html`
**Does not touch:** `backend/` (Rex's)

### Nova — AI/ML Engineer
**Owns:** `backend/app/services/llm.py`, `backend/app/services/rag_policy.py`, `backend/app/services/rag_logistics.py`, `backend/app/services/ingestion.py`, `backend/tests/services/`
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

### Execution Routing

Claude is the default implementor after Eran approves the compact preflight card. The
named domain owner remains accountable for domain boundaries and may be consulted or
delegated to, but ownership does not force an invocation.

Claude delegates only with a written justification: unresolved specialist uncertainty,
independent implementation needed for risk control, or a clearly bounded specialist unit
whose expected value exceeds invocation overhead. Workflow/governance changes,
mechanical wiring, narrow repairs, exact known edits, and straightforward tests remain
Claude-direct.

Claude-direct edits are mechanically limited to the active commit specification's
`Files To Modify Or Add` table. A direct commit records `Execution: Claude-direct` and
uses Claude's Co-Authored-By identity. Delegated commits use the implementing agent's
identity.

### Live Context Delegation

Only when the approved execution route is delegated, Claude runs:

`python hooks/prepare_agent_delegation.py --commit <N> --agent <agent-id>`

Claude passes the generated `.context/delegations/C<NN>-<agent>.md` brief to the
named delegated agent. It defines primary work, supporting contracts, boundaries, relevant hubs,
acceptance criteria, and the initial read budget.

Agents read listed files first and do not scan directories. Additional context is allowed
only for an unresolved symbol, missing contract, failing test, or contradictory
implementation evidence. Before expanding, the agent records the reason, exact query or
path, expected decision, and tradeoff. Expansions and outcomes go in the worklog.

### Return Contract (required in every agent's final message)

Every implementor must begin their final message with a concise plain-language report:

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```

This summary is for Eran, Claude, and reviewers. It must be understandable without
reading telemetry, diffs, or worklogs.

After the human summary, every implementor must include a structured telemetry report.
The delegation brief's **Return Contract** section specifies the exact format:

```json
{
  "tool_calls": <total count>,
  "read_paths": ["path/a.py", "path/b.py"],
  "write_paths": ["path/c.py"],
  "searches": [{"tool": "Grep", "path": ".", "query": "pattern"}],
  "commands": ["pytest backend/tests/"],
  "expansions": ["path/outside-package.py"]
}
```

Set any array to `null` if path-level detail is unavailable (e.g. after a context gap).
`tool_calls` is always required — never omit it.
Claude validates and persists this report as the agent scope of the commit's telemetry.
Missing report → Claude constructs a partial report from the worklog's tool-usage line.

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
