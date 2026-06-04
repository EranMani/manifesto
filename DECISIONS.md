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

*This document records decisions as they are made. Update it before every Team Lead approval prompt when a non-obvious choice was made.*
