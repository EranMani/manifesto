# /forge-eval — Post-Forge Quality Evaluation

Evaluate the most recent `/forge` run against the forge evaluation
rubric. Read-only — no code changes, no state updates.

Run this immediately after `/forge` completes, before running another
`/forge` or `/next-step`.

---

## Step 1 — Gather Evidence

Read these artifacts from the most recent forge run:

1. `.forge/plan.json` — commit decomposition plan
2. `.forge/report.json` — codebase scan data
3. `project-state.json` — current state, pending commits
4. `commit-protocol.md` — identify the pending commits (status: pending)
5. Each pending commit spec in `commit-specs/commit-NN.md`
6. `.claude/stack-profile.json` — the Level 0 abstract
7. The relevant `.claude/stack/{domain}.json` files for each agent
   that was assigned in the pending specs

If `.forge/plan.json` or `.forge/report.json` does not exist, warn:
"No forge artifacts found. Run /forge first, then /forge-eval
immediately after."

---

## Step 2 — Identify Scope

From the gathered evidence, determine:

- **Commit range**: which commit numbers were created (e.g., C80-C82)
- **Task description**: from the plan or first spec's primary behavior
- **Scope**: XS / S / M / L from the plan or spec estimates
- **Agents invoked**: which agents were assigned as owners

---

## Step 3 — Score Each Section

Evaluate 30 binary checks across 6 sections. For each check, determine
Pass or Fail by inspecting the actual artifacts — not by assuming.

### Section 1 — Stack Alignment (5 checks)

Read each spec's file list and contract. Cross-reference against the
owning agent's `.claude/stack/{domain}.json`:

1. **Technologies match profile**: do the specs reference technologies
   from the stack profile (FastAPI, SQLAlchemy, React, etc.), or do
   they introduce alternatives not in the profile?
2. **No rogue libraries**: are any non-standard libraries introduced
   without explicit justification in the spec?
3. **Patterns followed**: do the specs follow the domain patterns
   (service layer for backend, component composition for frontend)?
4. **Database patterns**: if database changes are involved, do specs
   include migrations, timestamps, proper key strategy?
5. **Frontend patterns**: if frontend changes are involved, do specs
   use shadcn, Tailwind, Zustand (not alternatives)?

### Section 2 — Context Efficiency (5 checks)

Assess whether the forge run used context appropriately:

1. **Correct domain files**: were the right agents assigned to the
   right domains (Rex for backend, Aria for frontend, etc.)?
2. **No rediscovery**: do the specs show signs of the agent
   re-discovering stack choices (e.g., "after examining the codebase,
   we use FastAPI") instead of knowing them upfront?
3. **No instruction atrophy**: are the later specs in a multi-commit
   sequence as precise as the first ones?
4. **Tool budget reasonable**: is the estimated scope proportional to
   the task complexity (XS task shouldn't need L budget)?
5. **Cross-cutting loaded only when relevant**: were HITL, MCP, or
   context engineering concepts referenced only when the task actually
   involves those concerns?

### Section 3 — Design Quality (5 checks)

Assess the architectural decisions in the specs:

1. **Data flow explicit**: do specs define how data moves between
   components (request → service → database → response)?
2. **Failure modes addressed**: do specs mention what happens when
   dependencies fail, not just the happy path?
3. **Deterministic preferred**: does the design use deterministic logic
   where possible, reserving LLM calls for genuine reasoning tasks?
4. **Stages decoupled**: in multi-commit sequences, can earlier commits
   work independently without later ones?
5. **Atomic commits**: does each spec represent one observable behavior
   change that's independently testable?

### Section 4 — Specification Quality (5 checks)

Assess whether the specs are buildable:

1. **All 14 sections present**: every required section exists and is
   non-empty in each spec?
2. **Verification command specific**: the verification command is a
   runnable command (e.g., `pytest backend/tests/test_X.py`), not
   generic ("run the tests")?
3. **File list accurate**: the files listed match what the task
   actually requires — no missing files, no extras?
4. **Contract complete**: inputs, outputs, defaults, and failure
   behavior are all defined?
5. **Test plan covers edges**: tests include happy path, boundary
   case, and at least one edge case or regression scenario?

### Section 5 — Security and Validation (5 checks)

Assess security posture of the planned changes:

1. **Input validation at boundary**: specs that add API endpoints
   include Pydantic BaseModel validation (not raw dict or dataclass)?
2. **Auth checks included**: endpoints that should be role-gated
   include permission checks in the spec?
3. **No hardcoded secrets**: no API keys, passwords, or credentials
   appear in specs or are planned to be in code?
4. **AI output validated**: if the task involves LLM output reaching
   users, the spec includes structured output validation?
5. **Webhook handling secure**: if webhooks are involved, the spec
   follows verify → persist → dispatch pattern?

For checks that don't apply (e.g., no webhooks in this task), mark
as Pass with note "N/A — not applicable to this task."

### Section 6 — Product Alignment (5 checks)

Assess whether the plan solves the right problem:

1. **Real user need**: the task addresses something a user would
   notice, not pure engineering preference?
2. **Scope bounded**: the spec explicitly lists what is NOT included
   (the "Not In This Commit" section is meaningful)?
3. **Success measurable**: the "Done When" checklist has concrete,
   verifiable criteria?
4. **Escalation path**: if AI-powered features are involved, human
   escalation is defined?
5. **Turn-it-off test**: would someone notice if this feature didn't
   exist? Would they call if it stopped working?

---

## Step 4 — Calculate and Present

Present the evaluation as a filled scorecard:

```
FORGE EVALUATION — C{XX}-C{YY}
═══════════════════════════════════════════════════

Task: {description}
Scope: {XS/S/M/L}
Agents: {list}
Date: {YYYY-MM-DD}

───────────────────────────────────────────────────
Section                    Score   Checks
───────────────────────────────────────────────────
Stack Alignment            {n}/5   {P/F per check}
Context Efficiency         {n}/5   {P/F per check}
Design Quality             {n}/5   {P/F per check}
Specification Quality      {n}/5   {P/F per check}
Security & Validation      {n}/5   {P/F per check}
Product Alignment          {n}/5   {P/F per check}
───────────────────────────────────────────────────
TOTAL                      {n}/30  ({percentage}%)

Verdict: {Healthy / Acceptable / Needs Work / Unhealthy}

Failed checks:
  - {section > check: what was wrong}
  - {section > check: what was wrong}

What worked well:
  - {specific strength}

Stack profile adjustments needed:
  - {specific change, or "None"}
═══════════════════════════════════════════════════
```

Verdict thresholds:
- 25-30 (83-100%): **Healthy**
- 20-24 (67-82%): **Acceptable**
- 15-19 (50-66%): **Needs Work**
- Below 15 (<50%): **Unhealthy**

---

## Step 5 — Save Evaluation

Write the completed scorecard to `.forge/evaluations/eval-CXX-CYY.md`.
Create the `.forge/evaluations/` directory if it doesn't exist.

If previous evaluations exist, show a one-line trend:

```
Trend: eval-C78-C79 (87%) → eval-C80-C82 (93%) → this run ({n}%)
```

---

## Constraints

- Read-only. No file modifications except writing the evaluation file.
- Do not re-run forge or modify specs based on the evaluation.
- If a check cannot be assessed (artifact missing), mark as Fail with
  note "cannot assess — {artifact} missing."
- Be honest. A perfect score on a flawed forge run is worse than a low
  score that catches real issues.
