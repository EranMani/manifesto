# DECISIONS.md — Manifesto

> Maintained by Claude. Every non-obvious design choice made during this project
> is logged here with the reason it was made — including the debate that led to it.
> Last updated: 2026-06-09

---

## How to read this file

Each entry captures three things: what was decided, why alternatives were rejected,
and — where a real debate happened — the actual back-and-forth between Andrej and Boris.
The debates are the most valuable part. They show the thinking, not just the conclusion.

---

## D01 — Phase 1 Commit Index Structure

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Pre-development. Planning the Phase 1 commit sequence before any code is written.

### The debate

**Andrej's initial proposal** was a 21-commit index sequenced as: infrastructure → python skeleton → frontend scaffold → config → database → models → migration → auth → routes → stubs → seed → frontend pages → login → smoke test.

**Boris raised three objections:**

**Objection 1 — `main.py` coupling across commits.**
Every route commit (C09–C13) touches `main.py` to call `include_router`. This makes `main.py` a shared file that multiple commits modify, creating implicit coupling. Boris flagged this as a coordination smell.

Andrej's response: Rex owns `main.py` sequentially — there's no concurrent modification risk since Rex owns all backend commits. The touches are clean because they're additive (append-only). Convention: `main.py` gets a `# routers registered below` comment block in C02, and each route commit appends. Accepted as-is.

**Objection 2 — Seed script placed too late (C16).**
The original index put `seed.py` after all routes were built. But Rex needs a real credential to test auth manually during C08–C10. Without seed data, auth testing is blind.

Andrej conceded immediately. Seed moved to C08, immediately after the Alembic migration (C07). The dependency chain becomes `C07 → C08 → C09` (migration → seed → auth), which is strictly correct.

**Objection 3 — C21 smoke test wrong owner.**
Original draft assigned the integration smoke test to Rex. Boris argued: Rex built the application layer; Adam owns docker-compose and the assembled container stack. "Does the stack run" is an infrastructure concern, not a backend concern. The smoke test is Adam verifying the assembled system, not Rex verifying his own routes.

Andrej conceded. C21 → Adam.

**Boris's final push on parallelization:**
C03 (frontend scaffold) has zero dependency on C01 or C02 — it's pure frontend with no shared files. It should be explicitly marked `∥ C02` in the index, not just "noted as parallelizable."

Andrej agreed. Marked explicitly.

### Decision

21-commit index, phased as:
- Phase 1A: Infrastructure foundation (C01–C03, C03 ∥ C02)
- Phase 1B: Backend core — config, DB session, models, migration, seed (C04–C08)
- Phase 1C: Auth and user management (C09–C11)
- Phase 1D: Inventory routes (C12–C14)
- Phase 1E: Service stubs (C15–C16)
- Phase 1F: Frontend core — store, routing, placeholders, login (C17–C20)
- Phase 1G: Integration verification (C21, Adam)

### Consequences

- Each commit has one owner and one concern — clean revert boundary on every step
- Seed data exists before any auth route is built — Rex can test with real credentials from C09 onward
- Smoke test is owned by infrastructure, not the application layer — correct domain boundary
- Frontend scaffold can run in parallel with Python skeleton — time saved on early sessions

---

## D02 — Package Manager: uv over pip/requirements.txt

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** C02 (python-skeleton) originally specified `requirements.txt`. Eran directed switch to `uv`.

### Decision

Use `uv` as the Python package manager. `pyproject.toml` replaces `requirements.txt`.

### Rationale

`uv` is significantly faster than pip for installs (Rust-based resolver). It is the modern standard for Python project management. Lock file (`uv.lock`) provides reproducible installs without the overhead of manual `requirements.txt` maintenance.

### Consequences

- C02 produces `pyproject.toml` + `uv.lock` instead of `requirements.txt`
- Dockerfile uses `uv sync` instead of `pip install -r requirements.txt`
- All agents working in the backend must use `uv add <package>` not `pip install`

---

## D03 — Agent Roster: Lean Start, Add Later

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** rag-from-scratch used 11 agents at peak. Manifesto Phase 1 has no AI layer yet.

### Decision

Start with the minimum viable roster. Add agents when their domain becomes active.

**Active from Phase 1:**
- Rex (backend) — owns all Python application code
- Adam (devops) — owns all infrastructure
- Aria (frontend) — owns all React/TypeScript
- Viktor (reviewer) — quality gate, every 5 commits
- Sage (security) — conditional, auth/secrets/input routes only
- Mira (product) — conditional, user-facing behavior changes only

**Deferred:**
- Nova (AI engineer) — activates Phase 2 when LLMService is wired
- Quinn (QA) — activates Phase 2 when business logic warrants coverage review
- Ryan (tech writer) — activates Phase 4 hardening
- Lara (curriculum) — not applicable to this project

### Consequences

- Smaller context packages per invocation — fewer agent identity files loaded
- Quality gate wave is leaner — Viktor + Sage only (not 4 parallel reviewers)
- Agents are added by writing their identity file and registering in AGENTS.md — no ceremony

---

## D04 — Commit Preview Format: "Summary" replaces "What"

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** First Commit Preview rendered for C01. Eran asked: would a junior developer understand this?

### The debate

**Andrej's position:** The preview optimized entirely for the approval decision — technical gates, file paths — and gave nothing to the learning reader. A 1-2 sentence plain-English summary at the top costs ~30 tokens and pays back every time Eran reads a preview without needing to mentally reconstruct what the commit does from the file list.

**Boris's constraint:** The summary must not duplicate the "What" line. If we add a summary, "What" becomes redundant — paying tokens for the same information twice. Fix: replace "What" with the plain-English summary. One field, two jobs.

**Andrej conceded and extended:** Correct. "Why now" already handles sequencing. So the structure becomes Summary (human-readable, replaces What) + Why now (sequencing) + everything else unchanged. Zero tokens added, one field renamed.

**Two additional changes agreed:**
- Parallel callout moved above Changes — it's an approval-time decision, not a footnote
- Quality gate always stated explicitly — "None" implied the check was skipped; the rule statement shows the system is working as designed

### Decision

Replace "What" with "Summary" in the Commit Preview format. Summary is 1-2 sentences, plain English, junior-readable. Parallel callout moves above Changes. Quality gate line always states the rule, never "None".

### Consequences

- Any reader — including a junior developer — can understand a commit from the Summary line alone
- No token cost increase — same field count, one renamed
- Explicit quality gate line builds Eran's understanding of when and why gates trigger

---

## D05 — Token Optimization Strategy: What We Adopt and What We Reject

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Pre-development review of 4 published token optimization strategies before C01 begins.

### Strategy 1 — Codebase indexing (CodeGraph)

**Initial position (Andrej):** Domain boundaries make this redundant — Rex doesn't scan `frontend/`, so a graph adds no value.

**Boris's reversal:** Correct for cross-domain reads, but wrong for within-domain navigation. As `backend/app/` grows across 15+ commits, Rex will spend tool uses tracing import chains internally. A pre-built domain graph lets him query structure instead of reading 4 files to answer one structural question.

**Decision:** Build lightweight per-domain import graphs scoped to each agent's domain only. Rex gets a graph of `backend/`. Aria gets a graph of `frontend/src/`. Implemented as a post-commit hook script (`hooks/generate_domain_map.py`) that writes `backend/DOMAIN_MAP.md` and `frontend/DOMAIN_MAP.md`. No agent sees the full project graph — domain boundaries preserved.

**Deferred:** Not built before C01. Added to the pre-C01 build list for the next preparation session.

### Strategy 2 — Output compression (RTK)

**Decision:** Adopt the principle, skip the library. Two additions to execution constraints in `team-preferences.md`:
- Verbose command output rules: alembic and pytest return summary line + any ERROR/FAIL lines only
- Bash filter snippets for known-verbose commands

Rationale: Our agents don't consume raw logs by default. The problem only manifests on specific commands. A one-line convention in the invocation prompt costs zero tokens and solves the same problem.

### Strategy 3 — Forced output shortening (Caveman)

**Decision:** Reject. Worklogs and handoffs are the connective tissue of the system — truncating them degrades the context loop on subsequent invocations. The 25-tool cap and one-write-at-completion rule already enforce discipline without sacrificing meaning. The risk is asymmetric: save tokens on output, pay more on the next invocation when the agent re-derives lost context.

### Strategy 4 — Session management

**Decision:** Already implemented at a high level. Four specific improvements added from the debate:

1. **No speculative file reads mid-session.** No file reads that aren't directly required by the active commit spec. Every speculative read compounds across session history.
2. **Agent warm/cold context distinction.** Fresh agent (no worklog) → Tier 0 only. Continuing agent (3+ commits) → Tier 0 + Current State Header. No full worklog history passed by default.
3. **Token checkpoint before gate wave.** If session tokens > 40k before spawning Viktor/Sage/Mira → `/compact` first, then run the gate wave.
4. **Commit Preview as natural checkpoint.** If session tokens > 30k at Preview time and no agent has been invoked yet → `/compact` before proceeding.

---

## D06 — Gate-Triage: Skill vs. Inline Matrix

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Gate-triage matrix currently lives in `team-preferences.md` and `AGENTS.md` — always loaded, always consuming tokens.

### The debate

**Boris (initial):** The matrix is already in `team-preferences.md` — Claude reads it at boot. Making it a skill adds invocation overhead for a decision Claude should already be making. Encoding it twice adds maintenance burden.

**Andrej's reversal:** Boris was wrong on this one, and the logic is sound. The matrix in `team-preferences.md` is *always* loaded — it costs tokens whether it's needed or not. Moving it to a skill means it's loaded only when Claude explicitly invokes it. Smaller always-loaded files, on-demand logic. Net token reduction.

**Boris's risk flag:** If Claude forgets to invoke the skill, the gate decision gets made without the matrix. Mitigation: make invocation mandatory and mechanical — the commit loop protocol says "Step 8 always starts with `/gate-triage`." Not a judgment call — a protocol step.

### Decision

Build `gate-triage` as a skill. Remove the full matrix from `team-preferences.md` — keep only the pointer: "Step 8: invoke `/gate-triage` with the diff." Matrix logic lives in the skill only.

### Consequences

- Always-loaded files (`team-preferences.md`, `AGENTS.md`) shrink
- Gate logic is on-demand — zero cost on commits where no gate runs
- Risk: invocation must be mechanical (protocol step), not optional

---

## D07 — Skills Build List: What to Build Before C01

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** 21 skill ideas in skillsmith/skills_ideas reviewed against Manifesto's needs.

### Skills to build now (before C01)

| Skill | Rationale |
|---|---|
| `gate-triage` | Replaces inline matrix — on-demand, token-efficient |
| `pre-commit-doc-checklist` | Evaluates DECISIONS/ARCHITECTURE/GLOSSARY checklist against diff — saves Claude reasoning tokens every commit |
| `parallel-wave-detector` | Detects parallelizable commits — gets harder to reason manually as project grows |

### Infrastructure to build now

| Item | Rationale |
|---|---|
| `hooks/generate_domain_map.py` | Per-agent import graph, scoped to domain, updated post-commit |
| `TOKEN_RECORDS.md` | Token usage tracker — schema defined now, first entry after C01 |
| `team-preferences.md` updates | Verbose output rules, session checkpoint rules, gate-triage pointer |

### Skills deferred

Everything else from the 21-idea catalog — either already implemented as project files (`agentic-workflow-bootstrap`, `hook-bundle-installer`), applicable only Phase 2+ (`commit-spec-from-issue`, `repo-risk-surface-map`), or redundant with existing conventions (`tool-cap-enforcer`, `worklog-current-state`).

---

## D08 — TOKEN_RECORDS.md: Schema and Purpose

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (debate), Eran (approval)
- **Context:** Token measurement needed to track cost per commit and per agent, validate optimization strategies over time.

### Schema (per commit entry)

```
| Commit | Agent | Model | Tokens | Tool uses | vs. Target |
```

One row per agent invocation. Session total at the bottom. Delta vs. target shows whether optimization strategies are working.

### Rules

- Updated by Claude before every approval prompt — no agent needed
- Token counts come from the `<usage>` block returned by each Agent tool call
- First entry: C01 after Adam completes
- File must never be estimated — exact counts only. An estimated entry is worse than no entry.

### Why this matters

Without measurement, token reduction is guesswork. `TOKEN_RECORDS.md` is the instrument that tells us whether the per-domain graphs, skill extractions, and session checkpoints are actually reducing cost — or just adding complexity.

---

## D09 — Git Hook: sh Wrapper Instead of Direct Python Copy (Windows)

- **Date:** 2026-06-04
- **Decided by:** Adam (C01 execution)
- **Context:** `hooks/pre_commit_check.py` has a `#!/usr/bin/env python3` shebang. On Windows, Git for Windows runs hooks through its bundled `sh`. A bare `.py` file is not reliably executable there because `python3` is not always on PATH in Git's sh environment.

### Decision

Install `.git/hooks/pre-commit` as a POSIX sh wrapper that explicitly calls `python hooks/pre_commit_check.py` rather than copying the `.py` file directly.

### Rationale

The wrapper pattern is portable: Git's sh executes the wrapper; the wrapper calls Python with an explicit path. Direct copy would require `python3` to be on PATH within Git's sh environment — not guaranteed on Windows.

### Consequences

- Pre-commit hook works reliably on Windows Git for Windows
- The hook file at `.git/hooks/pre-commit` is a small sh wrapper, not the Python script itself
- If `hooks/pre_commit_check.py` is moved, the wrapper path must be updated

---

## D10 — Pre-Commit Hook: COMMIT_EDITMSG Pre-Write Workaround (Windows)

- **Date:** 2026-06-04
- **Decided by:** Claude (orchestrator, C01 commit)
- **Context:** On this Windows setup, `git commit -m "message"` does not update `.git/COMMIT_EDITMSG` before the pre-commit hook runs. The hook reads the stale previous commit's message, causing false format validation failures.

### Decision

Pre-write `.git/COMMIT_EDITMSG` with the intended commit message immediately before every `git commit -m` call. Git overwrites it with the same content anyway — the pre-write ensures the hook reads the correct message.

Also: the `Co-Authored-By` regex in `pre_commit_check.py` uses `\S+\s+<email>` — it expects a single-word name before the email. Multi-word names like "Claude Sonnet 4.6" are not matched. Convention: use single-word agent names in `Co-Authored-By` trailers (e.g., `Co-Authored-By: Adam <adam@manifesto.local>`).

**Superseded by D12:** The `GIT_MESSAGE` env-var priority fix in D12 makes the pre-write workaround unnecessary. The two-step pattern remains harmless if used but is no longer required.

### Consequences

- `GIT_MESSAGE` env var must be set before `git commit -m` is called (D12)
- Co-Authored-By must use single-word names matching agent-config.json keys (still active)

---

## D11 — Agent Commit Blocker: ERAN_COMMIT=1 Bypass Pattern

- **Date:** 2026-06-04
- **Decided by:** Andrej + Boris (analysis of /insight report), Eran (approval)
- **Context:** /insight report (5 sessions, 47 messages): 9 dissatisfied moments, 1 happy. Primary violations: Aria committed without approval (gate-triage bypass), governance docs updated partially, encoding fix cascaded into blocking Eran's next commit.

### The problem

Protocol rules live in files. Files don't enforce themselves. Between session resets, Claude loses working context of stored preferences — the same violations recur because the enforcement layer was trust-based, not mechanical.

### Decisions

**1. `block_agent_commit.py` — PreToolUse hook on Bash**
Intercepts any bash command containing `git commit`, `git push`, `git merge`, `git rebase`.
Blocks with exit 2 and a clear message. Eran bypasses with `ERAN_COMMIT=1 git commit -m "..."`.
Agents never set this env var — they are always blocked mechanically.

**2. CLAUDE.md Critical Rules callout at the very top**
Four rules added as the first block in CLAUDE.md, before the boot sequence:
- Always address Eran by name
- Never commit without Eran's explicit approval
- When updating any governance file, update all related files in the same pass
- Before staging, verify domain ownership

**3. Governance sync check added to pre-commit-doc-checklist skill**
When any governance file changes, the skill greps for related files and flags missed updates.
Related file map defined: editing commit-protocol.md → also check project-state.json + team-preferences.md, etc.

**4. Root-cause discipline rule**
If a fix fails once, stop patching symptoms. State the root-cause hypothesis explicitly before trying another approach. (From the Chroma health-check session in rag-from-scratch — 3+ failed attempts before the real cause was found.)

### Consequences

- Aria-style unauthorized commits are mechanically impossible — hook blocks before git runs
- Eran can commit freely: `ERAN_COMMIT=1 git commit -m "..."`
- Partial governance updates are caught by the skill's sync check before approval is surfaced
- The same enforcement now exists in CLAUDE.md (read every session) + hooks (run every commit)

---

## D12 — Pre-Commit Hook: GIT_MESSAGE Priority Order Fix

- **Date:** 2026-06-04
- **Decided by:** Aria (C03 execution), retroactively noted by Claude
- **Context:** Pre-commit hook's `get_commit_message()` originally checked `COMMIT_EDITMSG` before the `GIT_MESSAGE` env var. On Windows, `COMMIT_EDITMSG` contains the *previous* commit's message when the pre-commit hook fires (git hasn't written the new message yet). This caused format validation failures on every commit.

**Updates D10:** D10 described a workaround — pre-write `COMMIT_EDITMSG` before every `git commit -m` call. This fix eliminates the need for that workaround.

### Decision

In `get_commit_message()`, check `GIT_MESSAGE` env var **first**, fall back to `COMMIT_EDITMSG`, then return `""`.

### Rationale

`GIT_MESSAGE` is explicitly set by commit wrappers and CI before calling `git commit`. It is always the intended message. `COMMIT_EDITMSG` at pre-commit time contains the prior commit's message on Windows — an unreliable source. The priority inversion was the root cause of D10's pre-write workaround.

### Consequences

- `GIT_MESSAGE` must be set in the environment before `git commit -m` is called
- D10's pre-write-COMMIT_EDITMSG workaround is no longer needed but remains harmless if done
- Sage confirmed this change cannot be exploited: message still passes through the conventional-commit format validator regardless of source

---

## D13 — Commit Protocol: Claude Commits on Eran's Behalf After Approval

- **Date:** 2026-06-05
- **Decided by:** Eran
- **Context:** Every commit required Eran to manually run `ERAN_COMMIT=1 git commit -m "..."`. Agents were not appearing as GitHub contributors because no `Co-Authored-By` trailers were being added.

### Decision

After Eran approves a commit, Claude commits on his behalf using:
```
GIT_MESSAGE="<msg>" CLAUDE_COMMIT=1 git commit -m "<msg>"
```
with `Co-Authored-By` trailers for the agent who did the work.

`CLAUDE_COMMIT=1` is a new bypass added to `block_agent_commit.py` — distinct from `ERAN_COMMIT=1` so the two paths remain distinguishable in the hook.

### Commit message format

```
type(scope): imperative subject line (max 72 chars)

2-3 sentences, plain English: what changed and why it matters.
No internal jargon (no "D13", "C05 governance sync", etc.).

Co-Authored-By: AgentName <agent@email>
Co-Authored-By: Claude <claude@anthropic.com>
```

Types: `feat / fix / chore / refactor / test / docs`
Scopes: `backend / frontend / devops / config / governance`

### Co-Authored-By convention

- Names must be single-word (D10 constraint: pre-commit hook regex `\S+\s+<email>`)
- Emails from `hooks/agent-config.json`
- Agent work: `Co-Authored-By: Rex <rex.stockagent@gmail.com>` etc.
- Claude direct writes: `Co-Authored-By: Claude <claude@anthropic.com>`
- Always add Claude as co-author on all commits (orchestrator)
- `GIT_MESSAGE` env var must contain the full message including trailers (hook validates from it)

### Consequences

- Agents appear as GitHub contributors on every commit they own
- Eran no longer needs to run any git command after approval
- Implementor agents (Rex, Adam, Aria) still cannot commit — their constraint is unchanged

---

## D14 — Dockerfile CMD: uvicorn Must Be Invoked via uv run

- **Date:** 2026-06-04
- **Decided by:** Observed during C01 Docker validation
- **Context:** `docker-compose up` failed: `exec: "uvicorn": executable file not found in $PATH` in the backend container.

### Root cause

`uv sync` installs all dependencies — including uvicorn — into a `.venv/` virtual environment inside the container. The `.venv/bin/` directory is not on the system PATH, so `CMD ["uvicorn", ...]` cannot find the executable.

### Fix

Changed `backend/Dockerfile` CMD from:
```
CMD ["uvicorn", "app.main:app", ...]
```
to:
```
CMD ["uv", "run", "uvicorn", "app.main:app", ...]
```

`uv run` activates the virtual environment before executing the command.

### Consequences

- Any executable installed by `uv sync` must be invoked via `uv run <executable>` in Docker CMD/ENTRYPOINT
- This applies to all future Dockerfiles in this project using uv (alembic, pytest, etc.)
- Rex must use `uv run` for any process-launch commands in Docker context

---

## D15 — Sage Gate C04: Two Findings Dismissed, Two Deferred to C04b

- **Date:** 2026-06-04
- **Decided by:** Claude (gate analysis), Eran (approval)
- **Context:** Sage returned BLOCKING on C04 with 2 CRITICAL and 2 HIGH findings. Claude assessed each against Sage's identity-file blocking criteria before surfacing.

### Findings assessed

| # | Sage severity | Finding | Verdict |
|---|---|---|---|
| 1 | CRITICAL | `SECRET_KEY` needs minimum-length validator | Deferred to C04b — valid defense-in-depth, overstated severity |
| 2 | CRITICAL | `OPENAI_API_KEY: str = ""` is a "plaintext credential" | **Dismissed** — empty string is not a secret; Sage's own rule requires "secrets committed to code" |
| 3 | HIGH | `create_access_token(data: dict)` should accept typed params | **Dismissed** — contradicts C04 spec and C08/C09 handoff contracts; internal callers only |
| 4 | HIGH | `decode_token` needs warning log on JWTError | Deferred to C04b — valid forensics improvement |

### Decision

Insert C04b (`config-security-hardening`) immediately after C04. Rex adds a `SECRET_KEY` minimum-length validator and a structlog warning in `decode_token`. C04 commits as-is; C04b follows before C05 begins.

### Consequences

- C04b is a new row in commit-protocol.md between C04 and C05
- Future Sage invocations on these files should not re-flag findings 2 or 3
- `SECRET_KEY` now fails fast at startup with a clear error message if weak
- `decode_token` failures emit structured logs without leaking details to callers

---

## D16 — JWT Library: PyJWT replaces python-jose

- **Date:** 2026-06-04
- **Decided by:** Eran
- **Context:** During C04 review, Eran noted `python-jose` has had periods of slow maintenance.

### Decision

Replace `python-jose[cryptography]` with `PyJWT>=2.8.0` in `pyproject.toml`.
Update `security.py` imports: `from jwt.exceptions import InvalidTokenError` instead of `from jose import JWTError, jwt`.

### Rationale

`PyJWT` is more actively maintained, has a cleaner API, and is the more common choice in greenfield Python projects post-2023. The interface change is a two-line import swap — no behaviour changes.

### Consequences

- `pyproject.toml`: `python-jose[cryptography]>=3.3.0` → `PyJWT>=2.8.0`
- `security.py`: `JWTError` → `InvalidTokenError`; `jwt` module is now the top-level `jwt` package
- `uv sync` must be re-run after this change to update the lockfile
- No other files reference `jose` — change is fully contained in `security.py`

---

## D17 — PolicyChunk IVFFlat Index Deferred to Alembic Migration

- **Date:** 2026-06-05
- **Decided by:** Rex (C06 execution)
- **Context:** `PolicyChunk.embedding` (Vector 1536) requires an IVFFlat index with pgvector-specific DDL (`USING ivfflat (embedding vector_cosine_ops)`). This cannot be expressed as a standard SQLAlchemy `Index` object.

### Decision

Leave `PolicyChunk.__table_args__` as an empty dict tuple in C06. The IVFFlat index will be created in C07 via `op.execute("CREATE INDEX ... USING ivfflat (embedding vector_cosine_ops) ...")` in the Alembic migration.

### Rationale

SQLAlchemy's `Index` constructor does not support pgvector-specific index methods. The correct pattern for pgvector indexes is to define them in the migration, not the model.

### Consequences

- `PolicyChunk` in C06 has no index on `embedding` — correct until C07 runs
- C07 Alembic migration must include `op.execute(...)` for this index explicitly
- Rex (C07) handed off via worklog

---

## D18 — Alembic Must Run Inside Docker Container (Windows Postgres Conflict)

- **Date:** 2026-06-05
- **Decided by:** Rex (C07 execution)
- **Context:** A native Windows Postgres instance unrelated to this project is bound to `localhost:5432`. When `uv run alembic upgrade head` runs from the host, asyncpg connects to the native Windows instance and receives auth failures.

### Decision

All Alembic commands (and any asyncpg operations) must run inside the Docker backend container, which connects to the `db` service by hostname rather than localhost:

```
docker-compose run --rm --no-deps backend sh -c "cd /app && uv run alembic upgrade head"
```

This bypasses the port conflict entirely.

### Consequences

- C08 seed script and all future migration commands must use this invocation pattern
- `alembic.ini` `sqlalchemy.url` placeholder is irrelevant — `DATABASE_URL` env var injected by Docker overrides it
- CI/CD must also run Alembic inside the container, not the host

---

## D19 — JWT Auth: Accepted TOCTOU Trade-off on User State

- **Date:** 2026-06-05
- **Decided by:** Eran (approval), Claude (gate triage of Sage C09 Finding #2)
- **Context:** Sage flagged that `get_current_user` fetches user state (is_active, role) from the DB once at request entry, but a concurrent admin operation could deactivate or demote the user between token issuance and the next request.

### Decision

Accept the standard stateless JWT trade-off: user state is checked once per request against the DB, but the JWT is not revoked on deactivation. A deactivated user's existing tokens remain valid until they expire (governed by `ACCESS_TOKEN_EXPIRE_MINUTES`).

### Why

Re-fetching user state per operation (serializable transactions, re-verify after every ORM action) adds complexity and latency with minimal practical security gain at this scale. The short token TTL (default 30 min) bounds the exposure window.

### Consequences

- Admin revocation is "eventually consistent" — takes effect within one token TTL window
- If immediate revocation is required in a future phase, add a token denylist (Redis or DB table)
- All route implementations (C10–C14) rely on this pattern without modification

---

## D20 — Viktor BLOCK Dismissed: Timing Trade-off on Inactive User Check (C10)

- **Date:** 2026-06-05
- **Decided by:** Eran (Option A approval), Claude (gate triage)
- **Context:** Viktor's C10 gate raised a BLOCK on `auth.py:18` — combining `not user or not user.is_active` in one condition means an inactive user exits before bcrypt runs, creating a timing difference versus "wrong password" (which runs bcrypt). Sage reviewed the same class of issue and rated it WARN, not BLOCK.

### Decision

Dismiss Viktor's BLOCK. Sage (dedicated security reviewer) supersedes Viktor on security severity classification. Accept the timing trade-off and queue for future hardening.

### Why

Viktor's proposed fix rearranges the inactive-user check to after `verify_password`, closing the "inactive vs. wrong-password" timing gap. But it does not address the broader "user not found vs. wrong password" timing gap (Sage Finding #1, also WARN). Neither Viktor's fix nor the current code is fully constant-time. Sage's explicit WARN classification — "timing enumeration is a known trade-off in most auth implementations, addressable in a future hardening pass" — makes the BLOCK an over-escalation.

### Consequences

- Current `auth.py` logic remains: `not user or not user.is_active` → early 401, then `verify_password` → 401
- Timing side-channel acknowledged: email-not-found and inactive paths skip bcrypt; wrong-password path runs it
- Future hardening (post-Phase 1): add constant-time dummy verify for all failure paths
- Sage C09 Finding #1 CLOSED — login route issues tokens only from verified, active users

---

## D21 — Admin Route PUT: user_id Typed as str, Not UUID

- **Date:** 2026-06-05
- **Decided by:** Rex (C11 execution)
- **Context:** `PUT /api/v1/admin/users/{user_id}` path parameter. The `User.id` column is declared `UUID(as_uuid=False)` — SQLAlchemy stores it as a plain Python string, not a `uuid.UUID` object. FastAPI path-param coercion to `uuid.UUID` would cause a silent type mismatch in the `WHERE User.id == user_id` query.

### Decision

Type `user_id` as `str` in the route signature, not `UUID`.

### Rationale

Matching the path param type to the storage representation avoids a silent comparison failure. Casting to `UUID` and back adds noise with no practical benefit.

### Consequences

- All routes querying by ID on `UUID(as_uuid=False)` columns must use `str` path params
- C12–C14 routes should follow the same convention for their respective ID columns
- If `User.id` is ever migrated to `UUID(as_uuid=True)`, all affected path params need revisiting

---

## D22 — Admin User Creation: Unrestricted Role Assignment (Viktor C15 Finding 2)

- **Date:** 2026-06-05
- **Decided by:** Closed 2026-06-09 — Option A accepted (implicit, by Phase 1 completion without change)
- **Context:** Viktor flagged (WARN) that `create_user` in `admin.py` accepts any role including `"admin"` with no secondary confirmation or audit log. An admin can create new admins in one step.

### Finding

Viktor Finding 2 (C11 batch wave, C15 wave): `UserCreate.role` accepts `"admin"` freely. No friction, no escalation check, no audit event.

### Status: CLOSED — Option A accepted

No change was made through Phase 1 completion (C24). For an internal tool with a small, controlled admin set, unrestricted role assignment is acceptable. If Phase 2+ introduces self-service admin creation flows or audit requirements, revisit this decision.

**If reopened:** Option B would require either a separate `require_role("superadmin")` guard or an explicit audit log entry when an admin-role user is created.

---

## D23 — Axios Interceptors: useAuthStore.getState() Instead of Hook

- **Date:** 2026-06-06
- **Decided by:** Aria (C17 execution)
- **Context:** `api/client.ts` Axios interceptors need to read the auth token and call `logout()`. Interceptors are registered once at module initialization and execute outside the React component tree.

### Decision

Use `useAuthStore.getState()` inside the Axios request and response interceptors, not `useAuthStore()` (the React hook).

### Rationale

React hooks (`useAuthStore()`) can only be called inside React components or custom hooks — using them in module-level code throws an invariant violation. Zustand's `.getState()` is the correct API for accessing store state outside of React's rendering lifecycle. The interceptor always reads the current token at request time (not at module load time), so no stale-closure issue exists.

### Consequences

- Any non-React code that needs Zustand state must use `.getState()`, not the hook
- The interceptor pattern is idiomatic Zustand — safe and documented
- C20 login page uses the hook normally (`useAuthStore()`) since it runs inside a component

---

## D24 — Login Page: Deriving `User.name` from Email Local Part

- **Date:** 2026-06-07
- **Decided by:** Aria (C20 execution)
- **Context:** The JWT access token payload only carries `{sub, role}` (per the auth flow contract in `frontend.md`). The Zustand `User` shape requires a `name` field, but the backend exposes no display-name claim or profile endpoint at this stage of the project.

### Decision

Derive `name` deterministically from the email's local part (the text before `@`): split on `.`/`_`/`-`, title-case each segment, and join with spaces. Example: `admin@manifesto.local` → `"Admin"`.

### Rationale

This unblocks the login flow without inventing a backend contract that doesn't exist yet, and produces a readable display name for the common `firstname.lastname@...` convention. It is a placeholder, not a permanent contract.

### Consequences

- If the backend later adds a `name`/`full_name` claim to the JWT or a `/users/me` profile endpoint, this derivation should be replaced — `deriveNameFromEmail` in `Login.tsx` is the single place to update
- Until then, all displayed user names are derived from email addresses, not stored profile data

### Gate wave note (C20 batch wave, 2026-06-07)

Both Mira (advisory) and Viktor (deferred) independently flagged the same edge case during the C16–C20 review wave: unusual email formats — e.g. `a.b.c.d@company.com` → `"A B C D"`, or `firstname.lastname+tag@company.com` → `"Firstname Lastname +tag"` — produce fragmented or broken display names. This is the exact trade-off already named above as a placeholder; no new action taken. Confirms the consequence note is the right place to revisit when a real name source becomes available.

---

## D25 — ProtectedRoute Redirects Role-Mismatches to `/login`, Not `/dashboard`

- **Date:** 2026-06-07
- **Decided by:** Aria (C18 execution); confirmed during C22 closeout verification (Eran + Claude)
- **Context:** While manually verifying C22's fix, Eran logged in as the throwaway manager user (`manager.smoke@manifesto.local`) and navigated to `/admin`. The app redirected straight to `/login` — initially surprising, since the user was already authenticated.

### Decision

This is intentional, pre-existing behavior from `ProtectedRoute.tsx` (built C18), not a bug: both failure paths — no token *and* wrong role — redirect to `/login` (lines 12-18, `<Navigate to="/login" replace />` in both branches). Aria documented this choice in her C18 worklog ("role check + token check both redirect to /login"). No code change made; the C21/C22 manual verification confirms the role gate correctly blocks `/admin` for non-admin roles — it just routes through `/login` rather than `/dashboard` or a dedicated 403 view.

### Rationale

A single redirect target keeps `ProtectedRoute` simple — one component, one fallback, no need to thread "why you got redirected" state through the router. For Phase 1 (auth scaffolding only, no real admin UI to protect yet), this is sufficient.

### Consequences

- UX trade-off: an *already-logged-in* user who lacks permission for a route is sent to the login page, which can read as "you got logged out" rather than "you don't have access." A clearer signal (redirect to `/dashboard` with a toast, or a dedicated `/403` view) would be a better long-term UX.
- Logged here as a placeholder for Phase 2+ refinement — `ProtectedRoute.tsx` is the single place to change if/when this is revisited. Not a blocker for Phase 1 sign-off.

---

## D26 — Notify-Pipeline Bug: Two Root Causes Behind "Wrong Files Shown" and "Total Silence"

- **Date:** 2026-06-07
- **Decided by:** Eran (reported + drove validation), Claude (diagnosed + fixed)
- **Context:** The commit-approval email's "Files changed" section was showing the *previous* commit's files instead of the pending one, and was blind to brand-new untracked files. Eran asked for validation-first diagnosis rather than blind fixes ("if we can validate it properly, its a better choice").

### What was wrong (two distinct bugs, found in sequence)

**Bug 1 — untracked files invisible.** `get_diff_files()` used `git diff --cached --name-status`, which only sees staged/tracked changes — brand-new files (`git status` code `??`) never appeared. Fixed by switching to `git status --porcelain`, parsing the 2-character status code (staged, unstaged, and untracked), with a `PROTOCOL_PREFIXES` filter and dedup.

**Bug 2 — wrong fallback branch (the actual root cause of "shows previous commit's files").** `PRE_COMMIT` was computed as `"--pre-commit" in sys.argv` only. The `--write-flag` invocation path (used to cache the file list *before* `git commit` runs and the index goes empty) never set this flag, so `get_diff_files()` fell through to the `git diff-tree ... HEAD` branch — which shows the *last completed* commit's changes, not the pending one. Fixed by adding `or "--write-flag" in sys.argv` to the `PRE_COMMIT` computation.

**Bug 3 — surfaced after Bugs 1–2 were fixed: total silence ("no email, nothing").** `hooks/.pending_notify.json` was found truncated mid-JSON-string twice in a row. Root cause: `write_pending_notify()` used a direct `flag.write_text()`, which can be interrupted mid-stream (process kill, session transition, filesystem hiccup) and leave a half-written file. `notify_on_stop.py`'s exception handler then silently deleted the corrupt flag and returned — no error, no email, no visible signal of any kind.

### Fixes applied

1. **Atomic flag write** (`notify_agent_done.py` → `write_pending_notify()`): build the full JSON payload in memory, write it to a `.tmp` file, then `os.replace()` it into place. The Stop hook can now only ever see a complete file or no file — never a partial one.
2. **Loud failure on corrupt flag** (`notify_on_stop.py`): if the flag still can't be parsed for any reason, the script now sends an explicit "⚠ notify flag was corrupt (no commit email sent)" alert email — including the parse error and the truncated raw content — using the existing `send_email`/SMTP machinery, instead of silently deleting the flag and exiting.

### Validation

A throwaway `TEST` commit slot was added to `commit-protocol.md` (clearly marked, not part of real numbering) and exercised through the full real pipeline: `--write-flag` → flag written → commit landed (`832db17`) → Stop hook → email. The final validation run produced a clean, well-formed flag and the approval email arrived with the exact correct file list and statuses. Pipeline confirmed working end-to-end. Test artifacts were removed in a follow-up `chore` commit.

### Consequences

- The notify pipeline now correctly reflects the *pending* commit's real changes, including brand-new files, in every approval email.
- A corrupted or interrupted flag write can no longer produce silent total failure — Eran will always get *some* signal (either the correct email, or a corrupt-flag alert).
- General lesson for this hook system: any "cache to disk, read later from a different process/environment" pattern (sandbox → Windows) needs both an atomic write and a loud failure path — silent partial state is the worst combination for cross-environment handoffs.

---

## D27 — Constraint-Log Dedup Guard: Case-Insensitive Agent Comparison

- **Date:** 2026-06-07
- **Decided by:** Eran (asked to investigate before fixing — "investigate the source first"), Claude (diagnosed + fixed)
- **Context:** Discovered immediately after committing the Phase 2 replan (`aa13f76`): `CONSTRAINT_LOG.md` and `constraint-dashboard.html` showed an unexpected duplicate row for C22 — identical to the existing row except the agent name was lowercased (`aria` vs `Aria`).

### What was wrong

`hooks/auto_verify.py` (the Stop hook wrapper, gated on `CLAUDE_COMMIT=1`) re-runs `verify_constraints.py` against `project-state.json`'s `last_completed_commit` on **every** `CLAUDE_COMMIT=1` commit — including direct orchestrator writes like this replan's `docs(protocol)` commit, which don't advance `last_completed_commit` (it correctly stayed at `"22"`; only `next_commit` moved to `"23"`).

`verify_constraints.py` already has a dedup guard in `append_to_log()` meant to make exactly this re-fire a no-op — it skips writing if a row for `commit_key + agent` already exists. But the comparison was **case-sensitive** (`cells[2] == agent`). The existing C22 row was logged with `Aria` (proper-cased, from whatever wrote the original row). `auto_verify.py`'s `get_agent_from_spec()` reads the assignee straight from the commit spec and **lowercases it** (`.lower()`) before passing it on — producing `aria`. `"Aria" == "aria"` is `False`, so the guard missed the existing row and a duplicate was appended.

### Fix applied

One-line change to the dedup comparison in `hooks/verify_constraints.py::append_to_log` (line ~293):
```python
# before
if len(cells) >= 3 and cells[1] == commit_key and cells[2] == agent:
# after
if len(cells) >= 3 and cells[1] == commit_key and cells[2].lower() == agent.lower():
```
This makes the guard casing-agnostic, so any re-fire against an already-logged commit — regardless of which code path's casing differs — becomes a true no-op. The stray duplicate rows themselves were reverted via `git checkout -- CONSTRAINT_LOG.md constraint-dashboard.html` before this fix landed (they were never committed).

### Consequences

- `auto_verify.py` still re-runs `verify_constraints.py` on every `CLAUDE_COMMIT=1` commit (including non-advancing direct writes) — that behavior is unchanged and is arguably wasteful, but is now harmless: the dedup guard correctly absorbs the redundant call instead of producing a duplicate row.
- General lesson: any "is this already logged?" guard that compares agent/identity strings across two different code paths must normalize casing — one path read a stored proper-cased name, the other derived and lowercased a fresh one. Mismatched normalization between read and write paths is a recurring failure shape in this hook system (cf. D26's atomic-write/loud-failure lesson).

---

## D28 — C23 (`pgvector-migration`) Marked Done-by-Prior-Work, No Commit Made

- **Date:** 2026-06-08
- **Decided by:** Rex (investigated), Claude (surfaced + reconciled), Eran (approved)
- **Context:** Commit 23 was specced to create `backend/alembic/versions/XXXX_pgvector_policy_tables.py` plus `policy.py` models. Before invoking Rex, Claude found `policy.py` and its `__init__.py` registration already existed (committed in C06, `f712343`, 2026-06-05). Eran chose to invoke Rex anyway to complete the remaining migration-file work.

### What Rex found

The entire pgvector/policy schema — `CREATE EXTENSION IF NOT EXISTS vector`, `policy_documents`, `policy_chunks`, FKs, and the `ix_policy_chunks_embedding_ivfflat` ivfflat index — is already present inside `backend/alembic/versions/0001_initial.py` (lines 101–141), dated 2026-06-05 (the same day as C06). `0001_initial` is the sole migration and the current head. Rex verified live against the dev DB inside Docker: `alembic current` → `0001_initial (head)`, `pgvector` extension active (v0.8.2), both tables present with correct columns/FKs/types, ivfflat index confirmed with `vector_cosine_ops`, and `PolicyDocument`/`PolicyChunk` ORM models map cleanly onto the live schema.

### Why no migration was written

Writing a new `0002_...` migration would either fail outright (duplicate `CREATE TABLE`/`CREATE EXTENSION`/`CREATE INDEX` against existing objects) or — if made defensively idempotent — falsify the migration history by claiming new work for a schema that's already fully present. Running `alembic downgrade -1` to "test reversibility" would tear down the *entire* `0001_initial` schema (users, products, everything), not a scoped policy-only change — destructive, irreversible to a correct end-state, and not what the spec intended to test.

### Resolution

C23 is recorded as satisfied by prior work — no code changed, so no `git commit` was made for it. `commit-protocol.md` row C23 is marked `✅ done · pre-existing (0001_initial.py) · 2026-06-08`, and `project-state.json` advances `last_completed_commit` to `"23"` / `next_commit` to `"24"` directly, without a commit hash. The original provider/dimension handoff was superseded by the 2026-06-08 architecture review: C24 fixes one deployment-wide 768-dimensional embedding profile, independent of the per-conversation generation provider, and C26 migrates the pre-ingestion vector column from 1536 to 768 dimensions.

### Consequences

- General lesson: this is the second instance (after the `policy.py` discovery moments earlier in the same session) of Phase 2 schema work having been built ahead of schedule during Phase 1's C06/C07. Before invoking any remaining Phase 2 commit whose spec describes "new" backend files, check whether the artifact already exists — `0001_initial.py` and `policy.py` both predate the Phase 2 replan (2026-06-07) by two days, suggesting Rex anticipated the RAG schema while building the initial migration and model set.
- No process change needed beyond this awareness — the "verify before invoking" check (CLAUDE.md's pre-invocation question: "do I already know the exact file/line/content?") already caught half of this; the agent invocation caught the rest cleanly and stopped rather than forcing a false deliverable into existence.
- **No `CONSTRAINT_LOG.md` row exists for C23 — intentionally.** `verify_constraints.py --commit 23 --agent Rex` was run once against the `chore(state)` commit (`9f29431`) and produced a false-positive `forbidden_paths FAIL`: that commit bundled both `backend/DOMAIN_MAP.md` and `frontend/DOMAIN_MAP.md` (auto-regenerated date-stamp bumps for *both* domains, not Rex touching frontend) because there was no separate feature commit to absorb them into — the defining trait of this no-deliverable commit. Running the domain-ownership check against a pure-bookkeeping commit is a category mismatch: the check is designed to catch an agent's *work* commit touching another agent's domain, not an orchestrator state-reconciliation commit that happens to bundle a routine cross-domain doc regeneration. The stray FAIL row and dashboard update were reverted via `git checkout -- CONSTRAINT_LOG.md constraint-dashboard.html` (same remedy as D27's stray-row incident) and the check intentionally was not re-run. Any future no-deliverable commit of this shape should skip `verify_constraints` for the same reason.

---

## D29 — Context Package V2 Starts in Shadow Mode

- **Date:** 2026-06-08
- **Decided by:** Eran and Codex
- **Context:** Static commit context is lean, but it can omit callers, tests, structural
  wiring, or cross-domain contracts. Direct activation would risk making agents
  efficiently wrong.

### Decision

Add an explainable context engine under `hooks/` and validate it in shadow mode before
changing real agent prompts. The engine combines the existing commit-spec context with
structural anchors, one-hop dependencies from changed files, tests, and explicit
cross-domain contract bridges. Generated previews are written under `.context/runs/`.

### Tradeoffs

- **Chosen:** deterministic rules and import graphs before embeddings or LLM retrieval.
  This is cheap, reproducible, and easy to debug, but cannot discover every dynamic
  runtime relationship.
- **Chosen:** expand dependencies only from primary changed files. Expanding every
  contract or shared hub produced unrelated sibling routes and wasted context.
- **Chosen:** project-specific contract bridges for known cross-domain interfaces.
  They require maintenance, but make critical contracts explicit and testable.
- **Chosen:** preserve a reserved context budget and report exclusions. This may omit
  low-priority neighbors, but prevents uncontrolled context growth.
- **Reversibility:** high. Phase A does not modify commit execution, hooks, or prompts.

### Activation condition

Keep shadow mode until automated tests pass and historical/planned commit previews show
complete required-contract recall without harmful unrelated context.

### Phase A2 extension — cached codebase network

Reuse Skillsmith's deterministic classification and graph concepts through a local
Manifesto implementation rather than importing scripts from another project directory.
The cache makes full-repository mapping reusable across context requests and can also
feed an Obsidian visualization.

### Phase A3 extension — activate live delegation

Claude now prepares a state-validated live package before every implementor invocation and
passes the generated brief verbatim. The approval gate remains unchanged: preparing
context does not authorize agent execution.

### Phase B — measure context efficiency in the existing dashboard

Use the existing constraint dashboard as the single visual measurement surface. Runtime
hooks capture context behavior automatically, and post-commit verification stores compact
records in `CONTEXT_METRICS.json`.

### Phase D — embed the codebase graph in the dashboard

Add a second dashboard tab for the whole-codebase graph. A commit dropdown overlays one
context package at a time while the remaining network stays visible for comparison.

Tests live under `hooks/tests/` and cover path safety, Python and TypeScript import
resolution, context parsing, dependency expansion, contract bridges, and historical
Manifesto cases.

---

## D30 — Local Setup: npm install Must Run Before npm run build

- **Date:** 2026-06-04
- **Decided by:** Observed during C03 local validation
- **Context:** `npm run build` failed with `'tsc' is not recognized` on Eran's machine after C03 was marked done. Session notes recorded "npm install and npm run build both pass" — this referred to the agent's execution environment, not the developer's local machine. `node_modules/` is gitignored and was never present locally.

### Fix

Run `npm install` in `frontend/` before any build or dev command on a fresh checkout.

---

## D31 — Dual-Scope Telemetry: Agent and Orchestrator Recorded Separately

- **Date:** 2026-06-09
- **Decided by:** Eran (requirement), Claude (design)
- **Context:** Phase B telemetry was recording a single flat usage record per commit, sourced entirely from hook-captured agent tool calls. C24 exposed two problems: the hooks were not firing inside nested agent sessions (the project hooks cannot observe sub-agent tool events), and Claude's own post-agent activity (inspection, verification, corrections) was invisible to the dashboard.

### What was decided

Two telemetry scopes per commit, stored in the same `CONTEXT_METRICS.json` record under a `telemetry` key:

**Agent scope** (`telemetry.agent`) — sourced from the agent's structured self-report returned in its final message. Self-report takes priority over any hooks-captured data. Status is `available` when path arrays are present, `partial` when only `tool_calls` is known, `unavailable` when neither exist.

**Orchestrator scope** (`telemetry.orchestrator`) — sourced from hook-captured events during the explicitly-bounded review phase. Claude opens the scope with `--start-orchestrator` before inspection and closes it with `--stop-orchestrator` after `/verify-commit` passes. Scope is hooks-native, so it can be fully automated.

### Why not a single merged scope

Merging would make it impossible to distinguish agent efficiency (did Rex over-read?) from orchestrator overhead (did Claude correct logic after the fact?). Keeping them separate makes each independently auditable. The dashboard shows both plus a combined total.

### Why self-report for agent scope instead of hooks

The Claude Code hooks framework fires for the outer Claude session. When Claude spawns a sub-agent (the Agent tool), the sub-agent's internal tool calls are not observable by the outer hooks. The only reliable source is the agent itself. Self-report is therefore the canonical source for agent scope. It is not guesswork — it is the agent recording what it did before returning control to the orchestrator.

### Why not zero when self-report is absent

Treating a missing report as zero is a false measurement. A missing report means "we don't know", not "nothing happened". The dashboard shows `N/A` for unavailable fields and `Unknown` for expansion status that cannot be determined. The "Expansion-free" summary card counts only records where the status is positively known.

### Consequences

- Every delegation brief includes a **Return Contract** section (added to `prepare_agent_delegation.py`).
- Commit loop gains STEP 5.5 (persist self-report + open scope) and STEP 7.75 (close scope).
- `context_telemetry.py` gains `--agent-report`, `--start-orchestrator`, `--stop-orchestrator` flags.
- `context_metrics.py` `build_metric_record` produces `telemetry.agent` + `telemetry.orchestrator`.
- Dashboard Phase B table gains Agent calls, Orch calls, Combined, and Unknown expansion columns.
- C24 history corrected: agent scope shows 26 tool calls (self-reported), path-level null.

### Consequences

- Any new machine or fresh clone must run `npm install` in `frontend/` before `npm run build`
- C03's "Done When" criteria should be read as: "passes in the build environment" — local setup requires `npm install` first
- README.md quick-start should include `cd frontend && npm install` as a setup step

---

## D32 — Quinn (QA) Activated for C27 `document-ingestion`

- **Date:** 2026-06-10
- **Decided by:** Claude (recommendation), Eran (approval)
- **Context:** OI-05 required a decision before C27 was approved on whether Quinn's
  activation criterion ("ingestion/retrieval service has ≥3 public methods with
  non-trivial logic and no parametric test suite") is met by C27. The C27 spec's test
  gate covers four file-format parsers (PDF/DOCX/TXT/MD), seven-plus failure-mode cases
  (empty/encrypted/corrupt/image-only/invalid UTF-8/oversized/duplicate), chunking
  determinism/overlap/cap rules, and batched embedding/concurrency/idempotency paths —
  well past the threshold.

### What was decided

Quinn runs a coverage review on C27 after Nova's implementation, in addition to the
standard test gate. OI-05 is resolved.

### Consequences

- C27's commit loop gains a Quinn pass alongside (or in place of) the gate-triage outcome.
- Quinn checks Nova's `test_ingestion.py` for negative tests, boundary conditions, and
  per-format coverage — not just that tests pass.

---

## D33 — Sage CRITICAL Finding on C27 Dismissed Pending Live Verification

- **Date:** 2026-06-10
- **Decided by:** Claude (recommendation), Eran (approval)
- **Context:** Sage's gate review of C27 `document-ingestion` raised a CRITICAL finding —
  "PyMuPDF decompression bomb: `fitz.open()` may allocate memory before the `_MAX_PAGES`
  check fires." Sage's calibration treats CRITICAL as a hard block.

### What was decided

Dismissed as a likely false positive for now, same pattern as the two C25 Viktor
hard-block dismissals:
- The `_MAX_PAGES` check (line ~158 of `ingestion.py`) runs immediately after
  `fitz.open()` and *before* the per-page extraction loop that decodes content
  streams — MuPDF does not eagerly decompress all page content on open.
- The C27 spec explicitly frames `_MAX_PAGES`/`_MAX_BLOCKS`/`_MAX_BLOCK_CHARS` as
  in-service defenses layered *on top of* the upload route's byte-size limit (C28,
  not yet built) — exactly as implemented.

Eran will exercise this empirically (e.g. a crafted oversized/pathological PDF) once
the upload route exists and decide then whether it's a real blocker.

### Consequences

- C27 proceeds to commit without a fix for this finding.
- New open issue (OI-09): verify PyMuPDF memory behavior on a pathological/oversized
  PDF against `_MAX_PAGES` once C28 (upload route) lands; revisit D33 if the live
  test shows real unbounded memory growth before the page-count check.
- The two MEDIUM Sage findings (plain-text decode-before-size-check; DOCX zip handling
  has no extra zip-bomb guard) are non-blocking per Sage calibration and are bundled
  here for visibility, not tracked as separate open issues — both are mitigated by the
  same C28 upload byte-size limit.

---

## D34 — C27 Phase-Budget FAIL Accepted as Documented Scope Overflow

- **Date:** 2026-06-10
- **Decided by:** Claude (recommendation), Eran (approval)
- **Context:** `/verify-commit` for C27 returned `phase_budget: FAIL` —
  Nova's combined worklog tool usage across two invocations
  (reads=14, writes=10, total=53) exceeds the single-invocation cap
  (reads<=10, total<=25) checked by `verify_constraints.py`.

### What was decided

Accepted as a real, pre-approved scope overflow rather than a protocol violation
to fix:
- C27's scope (PDF/DOCX/TXT/MD extractors, structure-then-token chunking,
  idempotent `ingest_document()` orchestration, 31 tests, 6 binary fixtures)
  genuinely exceeded a single 25-tool-use invocation.
- Both Nova invocations were individually scoped and approved by Eran during
  this session (invocation A: implementation, hit cap at 26; invocation B:
  fixtures+tests, approved separately, hit cap at 27).
- This mirrors C26 (Rex, 2 invocations, 51 combined tool uses), which produced
  a WARN rather than FAIL only because its combined tool-usage line fell outside
  the regex-matched worklog section — not because the underlying situation
  differed.

### Consequences

- C27 proceeds to commit with `phase_budget: FAIL` recorded honestly in
  CONSTRAINT_LOG.md / CONTEXT_METRICS.json / constraint-dashboard.html — per
  non-negotiable #9 (scope overflows flagged, not hidden), this is the intended
  outcome, not a defect to suppress.
- No process change required for single-invocation commits; this only applies
  when a commit's scope requires Eran-approved multi-invocation splits.

---

## D35 — C28 Phase-Budget FAIL Accepted as Documented Scope Overflow; OI-08 Resolved

- **Date:** 2026-06-10
- **Decided by:** Claude (recommendation), Eran (approval pending)
- **Context:** `/verify-commit` for C28 returned `phase_budget: FAIL` —
  Rex's combined worklog tool usage across five invocations
  (reads=70, writes=10, total=116) exceeds the single-invocation cap
  (reads<=10, total<=25) checked by `verify_constraints.py`.

### What was decided

Accepted as a real, pre-approved scope overflow rather than a protocol violation
to fix:
- C28's 9-file context budget (~21.5k chars) plus a 25-tool Phase 1 read cap
  meant research alone consumed two full invocations before any write.
- A third and fourth invocation implemented `app/schemas/document.py`,
  rewrote `documents.py` (upload/list/detail routes), added
  `MAX_DOCUMENT_UPLOAD_BYTES` to `config.py`, and wrote
  `backend/tests/api/test_documents.py` (16 tests).
- A fifth invocation hit OI-08 (host port 5432 conflict) attempting to run the
  new tests from the host, and in the process applied a non-destructive
  `ALTER USER manifesto WITH PASSWORD 'manifesto'` to the docker `db` container
  to re-align it with `.env`/`docker-compose.yml` (the password had drifted).
  This did not resolve OI-08 (the host's native `postgresql-x64-18` Windows
  service still intercepts `localhost:5432`).
- **OI-08 resolved for this commit by the orchestrator directly**: ran
  `docker compose run --rm backend uv run pytest ...` (resolves `db` via the
  compose network, bypassing the host port conflict entirely — the C07/OI-08
  documented workaround), fixed the test file's hardcoded
  `postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto` to read
  `DATABASE_URL` from the environment (falling back to the old literal for
  host runs), and ran `alembic upgrade head` against the docker `db` (was at
  base — migrations had never been applied to this volume).
- Result: 16/16 new tests pass; full backend suite 123 passed / 1 skipped.
  `tests/models/test_policy_storage.py` (C26) has the same hardcoded-`localhost`
  pattern and still errors (7 errors) — out of scope for C28, logged as a
  follow-up (see Open Issue note below).
- The orchestrator also closed a real spec gap found during code-inspection:
  `DocumentRead.failure_code` was always `None` because `PolicyDocument` has no
  `failure_code` attribute. Added `_failure_code_for()` in `documents.py`,
  mapping `error_message` text to `DocumentFailureCode` — a best-effort mapping
  coupled to `ingestion.py`'s exact sanitized message strings. Flagged as a
  handoff for Nova to replace with a structured error code on `IngestResult`/
  `policy_documents` in a future commit.

### Consequences

- C28 proceeds to commit with `phase_budget: FAIL` recorded honestly in
  CONSTRAINT_LOG.md / CONTEXT_METRICS.json / constraint-dashboard.html — per
  non-negotiable #9, this is the intended outcome, not a defect to suppress.
- OI-08 is resolved as a *procedure* (always run DB-touching backend tests via
  `docker compose run --rm backend ...`, never from the host) — the host port
  conflict itself is untouched and may still affect ad-hoc host-side tooling.
  `backend.md` / a future devops note should document this as the standard.
- New follow-up: `tests/models/test_policy_storage.py` needs the same
  `DATABASE_URL`-from-env fix applied to its hardcoded `DB_URL` constant before
  its 7 tests can run. Not blocking C28 — tracked as a small fix for a future
  commit.

---

## D36 — C28 Gate Wave (Sage + Mira): No Blockers, Two Follow-Ups Logged

- **Date:** 2026-06-10
- **Decided by:** Sage, Mira (haiku, per commit-28 spec — new authenticated
  upload route), Claude (synthesis)

### Sage (security)

- Authorization placement correct: `require_role` runs before any parsing/SHA256/DB work.
- **HIGH (non-blocking per Sage's own verdict — "no blocking issues"):** the new
  `_FAILURE_CODE_BY_MESSAGE` mapping in `documents.py` is coupled to the exact
  sanitized strings `ingestion.py` raises. If Nova changes a message, the
  response silently degrades to `failure_code: "internal_error"` with no log/error
  — already flagged in D35 as a handoff for Nova to add a structured error code
  to `IngestResult`/`policy_documents`. Logged as OI-10.
- MEDIUM: logging hygiene around the `(IngestionError, LLMError)` catch — acceptable
  given C27's "never raises to caller" contract; no action needed unless that
  contract changes.
- MEDIUM: txt/md have no signature check — by design, deferred to extraction. Acceptable.
- **OI-09 (PyMuPDF decompression-bomb, dismissed CRITICAL from C27/D33):**
  `MAX_DOCUMENT_UPLOAD_BYTES` (25 MiB streamed cap) is one layer of defense at
  the HTTP boundary but does **not** resolve OI-09 — a small PDF can still
  decompress to a large in-memory document inside C27's `fitz.open()`. OI-09
  stays open; verify with a real pathological PDF post-C28 as originally planned.

### Mira (product, advisory only)

- 200 (duplicate-identical) vs 201 (new) for upload have identical response
  shapes — a future UI (C32+) needs to surface this distinction explicitly so
  managers don't read "200" as "nothing happened."
- `failure_code` values (e.g. `corrupt_document`) are not user-actionable on
  their own — C32 should pair them with remediation copy.
- `embedding_provider`/`model`/`dimensions` in the response is intentional per
  the C26→C28 handoff (safe profile metadata); Mira flagged it as possible UI
  noise — left as-is per spec, future UI may choose not to render it.
- Logged as a handoff to Aria for C32+ (see project-state.json).

### Outcome

No blocking findings. C28 proceeds to commit. OI-09 remains open (deadline
already "after C28" — unchanged). New OI-10 opened for the failure-code mapping
fragility (Nova, low priority, no deadline).

---

## D37 — Pre-C30 Telemetry Integrity Fix: Orchestrator Scope Cross-Commit Duplication (OI-13)

**Date:** 2026-06-12

### What was found

C29A and C29B's orchestrator telemetry (`CONTEXT_METRICS.json` and
`.context/telemetry/C29B-orchestrator.json`) were byte-identical (133 tool
calls, identical read/write/search/command lists), both internally stamped
`"commit": "C29A"`.

### Root cause (persistence layer)

`finalize_orchestrator_scope()` in `hooks/context_telemetry.py` had no check
that the active scope in `orchestrator-active.json` actually belonged to the
commit being finalized. `--start-orchestrator C29B` was never called (a
process-discipline lapse). When `--stop-orchestrator C29B` ran, it picked up
the stale "completed" C29A scope, re-stamped `ended_at`, and persisted it as
`C29B-orchestrator.json` — duplicating C29A's history under C29B's name and
corrupting the C29B record in `CONTEXT_METRICS.json`.

C29C's orchestrator record (201 tool calls, `"commit": "C29C"`, distinct
`started_at`) was checked and confirmed genuine — not part of this defect.

### Fix

- `hooks/context_telemetry.py`: added `_commit_key()` helper; rewrote
  `finalize_orchestrator_scope()` to compare the active scope's commit against
  the requested commit (case-insensitive, `C`-prefix normalized) and return
  `None` — writing nothing — on mismatch or missing scope. `main()`'s
  `--stop-orchestrator` branch now prints a stderr warning when `None` is
  returned, explaining that `--start-orchestrator` may not have been called.
- `hooks/tests/test_context_telemetry.py`: added 3 regression tests —
  no-active-scope returns `None`/writes nothing, stale-commit (the exact
  C29A→C29B scenario) is rejected and writes nothing, and the matching-commit
  happy path still succeeds. 11/11 pass.
- `CONTEXT_METRICS.json`: repaired the C29B record's `telemetry.orchestrator`
  block from the duplicated C29A data to `status: "unavailable"` with all
  arrays `null` (matching the existing convention used by other commits with
  no orchestrator telemetry, e.g. C24).
- Deleted the stale, gitignored `.context/telemetry/C29B-orchestrator.json`
  (confirmed false duplicate of `C29A-orchestrator.json`).

### Remaining limitation — NOT repaired (collection layer, separate issue)

C29A's and C29C's token totals (`TOKEN_RECORDS.md`, marked "—") are genuinely
lost and **not** deterministically repairable:
- C29A: Adam's `<usage>` self-report block was not captured before
  session-context compaction.
- C29C: `hooks/tool_cap.json` (a single mutable file, not commit-keyed) was
  not updated for that invocation and currently reflects C29B's data.

Per the "preserve historical records unless a deterministic repair is
possible" constraint, both remain recorded as lost. No code change addresses
this — it is a collection-timing issue distinct from the persistence bug fixed
above. Future work, if desired, would need to make `tool_cap.json` commit-keyed
or capture self-reports before any compaction point.

### Orchestrator Debugging Circuit Breaker (new instruction-level rule)

Added to `ORCHESTRATION.md`, `CLAUDE.md`, and `team-preferences.md`: during
orchestrator-led debugging/repair work, stop after 2 failed repair/verification
cycles OR 25 orchestrator tool calls (tracked via the existing
`orchestrator-active.json` `tool_calls` counter — no new hook). On hitting
either limit, report the blocker, the evidence gathered, and a minimal proposed
correction, then wait for Eran's approval before continuing. This is guidance
for Claude's own conduct, not an enforced gate.

---

## D38 — OI-13 Prose-Only Fix Insufficient: Adding a Deterministic Bash-Lint Hook

### Problem

The C33B fix for OI-13 (documented above as part of D37, and in
`team-preferences.md` "Bash Command Conventions") was **documentation only**:
prose telling a future Claude session not to use `cd` in Bash commands and
not to chain `ls ... 2>/dev/null && ls ... 2>/dev/null`. This relies entirely
on the session reading `team-preferences.md` at boot and choosing to comply.

Eran observed the identical pattern recur in the very next session (`cd
hooks && pytest tests/`, `pwd`, `cd ..` recovery calls) — proof that an
advisory note in a markdown file cannot reach the reliability needed to stop
a recurring token-waste pattern. Eran asked for "10000000%" confidence, which
a behavioral instruction to an LLM cannot provide.

### Fix

Add `hooks/bash_command_lint.py`, a `PreToolUse` hook on the `Bash` matcher
in `.claude/settings.json`. It runs as plain deterministic Python (no LLM
tokens) before any Bash command executes and rejects (non-zero exit, message
on stderr — Claude Code blocks the call and surfaces the message) commands
that:

1. Contain a `cd ` token (including subshell forms like `(cd path && ...)`),
   per the existing convention to always use repo-relative paths.
2. Chain `2>/dev/null` immediately followed by `&&` or `;` — the
   exit-code-propagating pattern that produces false "Error: Exit code N"
   reports on missing-but-harmless paths.

This converts OI-13's prose convention into a hard gate: a violating command
never executes, so there is no failed-command output to read and no recovery
turn to spend tokens on. OI-13 remains `resolved` (the convention itself is
unchanged); this decision adds enforcement on top of it.

---

## D39 — C33B's `check_finalize_marker()` Gate Was Not Reflected in CLAUDE.md/ORCHESTRATION.md Steps 11-13 (OI-15)

### Problem

C33B (commit `41d1c97`) added `hooks/finalize_commit.py` and a fail-closed
`check_finalize_marker()` to `pre_commit_check.py`, but did not update CLAUDE.md
step 11 / ORCHESTRATION.md STEP 10 (which still described the superseded
standalone `notify_agent_done.py --write-flag` call). During C34, this produced
three avoidable failures in the commit step alone:

1. `git commit` was attempted before `finalize_commit.py` had ever run, so
   `check_finalize_marker()` blocked it (no marker existed).
2. `finalize_commit.py --notify-what/--notify-why` are required args, discovered
   only via `--help` after a first call failed.
3. The `chore(state)` doc-sweep commit was first drafted with the primary
   commit's "Commit #34" + "Execution: Claude-direct" + `Co-Authored-By: Adam`
   header. This both mis-attributed `.context/finalize/` (Claude's domain per
   `hooks/agent-config.json`) — triggering a domain-boundary block — and, once
   re-attributed to Claude, still carried "Commit #34" + an execution/co-author
   marker, which made `check_finalize_marker()` treat the chore commit itself
   as a primary commit requiring its own (nonexistent) fresh marker.

Separately, an env-prefix `GIT_MESSAGE="$(cat <<'EOF' ... EOF)" CLAUDE_COMMIT=1
git commit -m "$GIT_MESSAGE"` produced an empty commit message — `$GIT_MESSAGE`
expands in the current shell before the prefix-scoped assignment applies, so it
was empty. This is a separate, pre-existing bash-syntax pitfall, not new in C33B.

Eran flagged this session's commit-step friction as unacceptable token waste,
the same category as OI-13/OI-14.

### Fix

Logged as OI-15 (resolved same session). Updated, in the same pass:

- **CLAUDE.md** step 11: replaced the standalone `notify_agent_done.py
  --write-flag` call with `hooks/finalize_commit.py --commit NN --agent OWNER
  --execution EXEC --notify-what "..." --notify-why "..."`, run before
  presenting the commit proposal — this writes both the notify flag and the
  `.context/finalize/CNN.json` marker step 12 requires. Removed the now-duplicate
  "Pre-approval notification" block from step 12.
- **CLAUDE.md** step 12.3 (doc sweep): added `.context/finalize/CNN.json` to the
  swept files; specified the chore commit must omit "Commit #NN"/"Execution:"
  lines and must use `Co-Authored-By: Claude <claude@anthropic.com>`.
- **CLAUDE.md** Critical Rule 2 and step 12 "Commit command format": replaced
  the env-prefix `GIT_MESSAGE=` example with the `export GIT_MESSAGE=...` /
  separate-statement form.
- **ORCHESTRATION.md** STEP 10 and STEP 13: mirrored all of the above.
- **team-preferences.md** "Bash Command Conventions": added rules #3
  (GIT_MESSAGE export syntax), #4 (finalize_commit.py before commit), #5
  (chore-commit template), with this session's incident as the example.

### Why Not Revert or Defer C33B's Gate

The gate itself (a fresh finalize marker required before a primary commit)
is working as designed and catches a real class of skipped-verification bugs.
The defect was purely in the *documented orchestrator sequence* around it, not
in the gate's logic — fixing the docs in place, in the same session the gap
was found, keeps the gate active without a regression window.

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*
