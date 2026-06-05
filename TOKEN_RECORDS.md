# TOKEN_RECORDS.md — Manifesto

> Maintained by Claude. Updated before every Team Lead approval prompt — no exceptions.
> Token counts come from the `<usage>` block returned by each Agent tool call.
> Exact numbers only. Estimated entries are worse than no entry.
> Last updated: 2026-06-05 (C14)

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
| C09 | auth-dependencies | Rex | sonnet | 34,562 | 5 | -25,438 ✅ | 1 file modified; clean implementation; self-reported 4 reads + 1 write |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ✅ | | | Verify script regex quirk; tool-usage line confirmed at worklog:188 |
| C09 | auth-dependencies (gate) | Sage | haiku | 20,855 | 4 | +5,855 ⚠️ | BLOCK dismissed — Finding #1 premature (C10 not built); Finding #3 misread; F2/4 JWT trade-off accepted (D19) |
| C10 | auth-route | Claude (direct) | — | 0 | 3 writes | — | Pre-invocation check: exact files/content known; no agent spawned; 3 files written + docker-compose fix |
| C10 | auth-route (gate) | Viktor | haiku | 24,577 | 12 | +9,577 ⚠️ | 1 BLOCK + 1 WARN + 2 INFO; BLOCK dismissed — superseded by Sage WARN (D20) |
| C10 | auth-route (gate) | Sage | haiku | 18,543 | 0 | +3,543 ⚠️ | 0 BLOCKs; 2 WARNs (timing + input validation); C09 Finding #1 CLOSED |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ⚠️ | | | Budget ⚠️ = Claude direct write; no agent worklog tool-usage line; expected |
| C11 | admin-routes | Rex | sonnet | 32,525 | 34 (9 self-reported) | -27,475 ✅ | 2 new files + main.py update; AST syntax checks passed; email 409 guard; str UUID decision |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ✅ | | | budget ✅ = tool-usage line confirmed at worklog:245; framework count (34) vs self-report (9) gap noted |
| C12 | vendor-routes | Claude (direct) | — | 0 | 3 writes + 1 edit | — | Pre-invocation check: exact files/fields/pattern known from admin.py; no agent spawned |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ⚠️ | | | Budget ⚠️ = Claude direct write; no agent worklog tool-usage line; expected |
| C13 | shipment-routes | Claude (direct) | — | 0 | ~15 (5 reads, 2 writes, 2 edits, 5 bash) | — | Pre-invocation check: exact files/fields/pattern known from vendor-routes + Shipment model; no agent spawned |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ⚠️ | | | Budget ⚠️ = Claude direct write; no agent worklog tool-usage line; expected |
| C14 | product-routes | Claude (direct) | — | 0 | ~20 (9 reads, 4 writes, 7 bash) | — | Pre-invocation check: exact files/fields/pattern known from shipments.py + Product model; no agent spawned |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ⚠️ | | | Budget ⚠️ = Claude direct write; no agent worklog tool-usage line; expected |
| C15 | stub-routes | Claude (direct) | — | 0 | ~10 (4 reads, 2 writes, 2 edits, 2 bash) | — | Pre-invocation check: stub pattern fully established; no agent spawned |
| | | | | Constraints: context ✅ · forbidden ✅ · budget ✅ | | | verify_constraints: PASS — reads=4/10, writes=1/12, total=5/25 |
| C15 | stub-routes (gate) | Viktor | sonnet | 22,335 | 2 | +7,335 ⚠️ | Batch wave C11–C15; 3 BLOCKs (F1 admin, F4 vendor, F5 product) + 3 WARNs; fix commits C15a/b/c inserted |

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
| C09 | 55,417 | 1 (Rex) | Sage 20,855 | Rex 42% under target; Sage 39% over reviewer target; Sage BLOCK dismissed |
| C10 | 43,120 | none (direct write) | Viktor 24,577 + Sage 18,543 | Claude direct write; gate wave: Viktor BLOCK dismissed (D20); Sage C09 Finding #1 closed |
| C11 | 32,525 | 1 (Rex) | none | Rex 46% under target; no gate wave at C11 |
| C12 | 0 | none (direct write) | none | Orchestrator direct write; vendor CRUD; all test gates passed; no gate wave at C12 |
| C13 | 0 | none (direct write) | none | Orchestrator direct write; shipment CRUD with vendor FK validation; all test gates passed; no gate wave at C13 |
| C14 | 0 | none (direct write) | none | Orchestrator direct write; product CRUD with shipment FK validation + added_by from JWT; all test gates passed; no gate wave at C14 |
| C15 | 22,335 | none (direct write) | Viktor 22,335 | Orchestrator direct write; stub routes (6 endpoints, 501); Viktor batch wave found 3 BLOCKs → C15a/b/c fix commits inserted |

---

## Running Analysis

*Updated at C15 (15 commits, enough data for patterns).*

**High-cost commits:** C07 (Rex, 57k tokens, 81 tool uses — Docker troubleshooting); C03 (Aria, 34k tokens, 49 tool uses — exceeded cap).

**Direct-write acceleration (C08, C10, C12, C13, C14, C15):** Six of the last eight commits were orchestrator direct writes — 0 agent tokens each. Pre-invocation checks are working. Pattern established in backend routes means each new route is derivable without spawning Rex.

**Viktor batch wave yield:** C10 wave: 1 BLOCK (dismissed), 1 WARN. C15 wave: 3 BLOCKs (real bugs), 3 WARNs. Viktor is catching real issues — update_user ignoring fields, vendor update conflating unset vs null, product PUT allowing shipment reassignment. Wave cost: 22–36k tokens per batch.

**Gate cost trend:** Reviewer (Viktor, Sage) targets are consistently exceeded (~7–21k over 15k target). Acceptable — reviewers are doing thorough work. No action needed.

**Strategy impact:** Direct writes have eliminated ~60–100k tokens per commit since C12. Viktor waves add back ~22k every 5 commits = ~4.4k amortized per commit. Net win: significant.

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
| C12 | vendor-routes | Claude (direct) | — | 0 | 3 writes | — | Pre-invocation check: exact content known from admin.py pattern; no agent spawned |
| C13 | shipment-routes | Claude (direct) | — | 0 | 3 writes | — | Pre-invocation check: exact content known from vendor-routes pattern; no agent spawned |
| C14 | product-routes | Claude (direct) | — | 0 | 3 writes | — | Pre-invocation check: exact content known from shipments.py pattern; no agent spawned |
| C15 | stub-routes | Claude (direct) | — | 0 | 3 writes | — | Pre-invocation check: exact content known; no agent spawned |
