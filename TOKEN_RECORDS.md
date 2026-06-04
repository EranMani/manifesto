# TOKEN_RECORDS.md — Manifesto

> Maintained by Claude. Updated before every Team Lead approval prompt — no exceptions.
> Token counts come from the `<usage>` block returned by each Agent tool call.
> Exact numbers only. Estimated entries are worse than no entry.
> Last updated: 2026-06-04 (C02 complete)

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

---

## Session Totals

| Commit | Total tokens | Agents invoked | Gate wave cost | Notes |
|---|---|---|---|---|
| C01 | 25,870 | 1 (Adam) | none | 57% under target |
| C02 | 23,116 | 1 (Rex) | none | 61% under target |

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
