# DECISIONS.md — Manifesto

> Maintained by Claude. Every non-obvious design choice made during this project
> is logged here with the reason it was made — including the debate that led to it.
> Last updated: 2026-06-04

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

### Consequences

- Every commit requires a two-step pattern: `printf ... > .git/COMMIT_EDITMSG`, then `git commit -m`
- Co-Authored-By must use single-word names matching agent-config.json keys
- This should be investigated in C21 (Adam's smoke test) to see if a hook fix is preferable

---

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*
