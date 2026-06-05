# TOKEN_RECORDS.md — Manifesto

> Maintained by Claude. Updated before every Team Lead approval prompt — no exceptions.
> Token counts come from the `<usage>` block returned by each Agent tool call.
> Exact numbers only. Estimated entries are worse than no entry.
> Last updated: 2026-06-05 (C08)

---

## Purpose

This file is the instrument that tells us whether token optimization strategies are working.
Without measurement, reduction is guesswork.

Each entry captures: which agent ran, on which model, at what cost, and how far from target.
The delta column is the signal — positive means over budget, negative means under.

---

## Targets (from team-preferences.md)

| Agent type | Target per invocation |
|---|---|
| Implementor (Rex, Adam, Aria) | ≤60k tokens |
| Reviewer (Viktor, Sage, Mira) | ≤15k tokens |
| Skill invocations | ≤5k tokens |

---

## Commit Log

| Commit | Name | Agent | Model | Tokens | Tool uses | vs. Target | Notes |
|---|---|---|---|---|---|---|---|
| C01 | project-scaffold | Adam | sonnet | 25,870 | 17 | -34,130 ✅ | First commit; fresh agent, no prior worklog |
| C02 | python-skeleton | Rex | sonnet | 23,116 | 25 | -36,884 ✅ | First Rex session; all 25 tool uses consumed — at cap |
| C03 | frontend-scaffold | Aria | sonnet | 33,895 | 49 | -26,105 ✅ | First Aria session; 49 tool uses — **exceeded 25-use cap** ⚠️; also fixed hook bugs in Claude's domain |
| C03 | frontend-scaffold (gate) | Sage | haiku | 20,274 | 8 | +5,274 ⚠️ | Triggered by .env.example; clean pass; 5k over reviewer target |
| C04 | config-and-security | Rex | sonnet | 24,064 | 11 | -35,936 ✅ | 2 files, 6 test gates; passlib replaced with direct bcrypt due to version incompatibility |
| C04 | config-and-security (gate) | Sage | haiku | 18,564 | 2 | +3,564 ⚠️ | BLOCKING — 2 dismissed (false pos + spec contradiction), 2 deferred to C04b |
| C04b | config-security-hardening | Rex | sonnet | — | — | — | Token data lost — session reset before capture; work complete, matches spec |
| C04b | config-security-hardening (gate) | Sage | haiku | 17,212 | 0 | +2,212 ⚠️ | PASS — both hardening measures clean; dismissed findings confirmed |
| C05 | database-session | Claude (direct) | — | 0 | 1 write | — | Spec fully prescriptive; no agent spawned |
| C05 | database-session (gate) | Viktor | haiku | 36,054 | 0 | +21,054 ⚠️ | Batch wave C01–C05; PASS — no findings |
| C06 | sqlalchemy-models | Rex | sonnet | 28,765 | 26 | -31,235 ✅ | 26 tool uses — 1 over cap; worklog write pushed it; no gate wave |
| C07 | alembic-migration | Rex | sonnet | 57,199 | 81 | -2,801 ✅ | **81 tool uses — 3× over cap** ⚠️; Docker port conflict required diagnostic iteration; tokens near target |
| C08 | seed-script | Claude (direct) | — | 0 | 1 write | — | Pre-invocation check: exact content known from tier1 reads; no agent spawned |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ⚠️ | | | Budget ⚠️ = verify script section-regex quirk; tool-usage line present in worklog |

---

## Session Totals

| Commit | Total tokens | Agents invoked | Gate wave cost | Notes |
|---|---|---|---|---|
| C01 | 25,870 | 1 (Adam) | none | 57% under target |
| C02 | 23,116 | 1 (Rex) | none | 61% under target |
| C03 | 54,169 | 1 (Aria) | Sage 20,274 | Aria 44% under target; Sage 35% over reviewer target |
| C04 | 42,628 | 1 (Rex) | Sage 18,564 | Rex 60% under target; Sage 24% over reviewer target; gate: BLOCKING → C04b inserted |
| C04b | — (lost) | Rex + Sage gate | Rex: sonnet / Sage: haiku | Rex tokens lost to session reset; Sage 17,212 | gate: PASS |
| C05 | 36,054 | Viktor gate only | haiku | Rex bypassed (direct write); Viktor 36,054 | gate: PASS |
| C06 | 28,765 | 1 (Rex) | none | Rex 28,765; 26 tool uses (1 over cap); no gate |
| C07 | 57,199 | 1 (Rex) | none | Rex 57,199; **81 tool uses — 3× over cap** ⚠️; Docker troubleshooting; no gate |
| C08 | 0 | none (direct write) | none | Orchestrator direct write; 1 tool use; no gate |

---

## Running Analysis

*Populated after 5+ commits — enough data to identify patterns.*

High-cost commits: —
Most expensive agent: —
Gate wave efficiency: —
Strategy impact: —

---

## How to Update (Claude's job)

1. After every agent invocation, note the token count from the `<usage>` block in the tool result
2. Before the approval prompt, append one row per agent to the Commit Log table
3. Add a row to Session Totals with the commit-level aggregate
4. After every 5 commits, update the Running Analysis section with patterns observed

Column definitions:
- **Tokens**: total input + output tokens from `<usage>` block
- **Tool uses**: number of tool calls the agent made
- **vs. Target**: `tokens - target` (negative = under budget ✅, positive = over ⚠️)
