# team-preferences.md — Manifesto

> Claude reads this file at every session boot, immediately after project-state.json.
> These preferences tune agent behavior for this project and Team Lead.
> Last updated: 2026-06-12

---

## Project Context

```
Project name:      manifesto
Team Lead:         Eran Mani
Phase:             greenfield — Phase 1 (core inventory, no AI)
Deadline pressure: none (quality over speed)
Public-facing:     internal tool (future AWS deployment)
```

---

## Core Rules (non-negotiable — read before every commit)

```
1. NO GATE-FIX PASSES. EVER.
   If Viktor or Sage blocks → surface to Eran → fix is its own next commit.
   Do NOT re-invoke the agent and re-run the gate in the same loop.

2. ALWAYS SPECIFY model: "haiku" FOR REVIEWER AGENTS.
   Viktor, Sage, Mira → model: "haiku" — no exceptions.
   Omitting it runs on Sonnet (3× cost).

3. VALIDATE THE SPEC BEFORE INVOKING ANY AGENT.
   Does the spec actually achieve the stated goal?
   A rejected agent pass costs the same tokens as a successful one.

4. NEVER SPAWN AN AGENT FOR A KNOWN EDIT.
   If the exact file, line, and new content are already known → use Edit directly.
   Agent overhead = 10–30k tokens. Edit = ~200 tokens.

5. CLAUDE-DIRECT IS THE DEFAULT EXECUTION ROUTE.
   Domain ownership does not require an agent invocation. Delegate only when a written
   justification identifies unresolved specialist uncertainty, independent implementation
   needed for risk control, or a clearly bounded specialist unit whose expected value
   exceeds invocation overhead. Workflow/governance changes, mechanical wiring, narrow
   repairs, known exact edits, and straightforward tests stay Claude-direct.

   Claude-direct work is limited to the active approved commit spec's
   `Files To Modify Or Add` table. The approval card names the executor and shows
   `Delegation justification: Not delegated.` when Claude executes directly.

5. DEBATES AND DECISIONS GO INTO DECISIONS.md IMMEDIATELY.
   Eran reads DECISIONS.md to build his understanding of the process.
   Every non-obvious choice and every Andrej/Boris debate gets recorded there.
```

---

## Viktor — Code Review Calibration

```
Trigger:    batch wave every 5 commits (C05, C10, C15, C20)
Model:      haiku — always
```

| Concern type | Behavior | Notes |
|---|---|---|
| Async/sync mixing | block | FastAPI async routes must not call sync SQLAlchemy |
| Type discipline | concern | strict on all new code |
| Error handling | concern | public-facing app |
| Unguarded input | block | any route that accepts user input without validation |
| Style / formatting | comment | advisory only |
| Performance | concern | flag O(n²) on unbounded input |

**How Claude passes context to Viktor:**
- Always pass a `git diff` — never paste full file contents
- Prompt under 200 words before the diff
- Viktor uses Read with line ranges for targeted inspection only

---

## Sage — Security Calibration

```
Trigger:    conditional — auth, secrets, user input, external API calls
Model:      haiku — always
```

| Finding level | Behavior |
|---|---|
| CRITICAL | hard block — always |
| HIGH | block |
| MEDIUM | flag — bundle into approval prompt |
| LOW | bundle into approval prompt |

**Manifesto-specific rules:**
- JWT secret: flag any commit where `SECRET_KEY` could reach production as "changeme"
- Login route: must never reveal which field (email vs password) failed — generic 401 only
- `added_by` field: must come from authenticated user, never from request body
- Admin routes: must be guarded by `require_role("admin")` — verify after any auth refactor

---

## Mira — Product Calibration

```
Trigger:    conditional — user-facing behavior changes only
Model:      haiku — always
```

Invoke Mira when: new routes with user-visible output, UI pages with real content, API shape changes.
Skip Mira on: stubs, placeholders, infra, migration, seed, smoke test.

---

## Model Assignments

```
Haiku  (fast, low cost):   Viktor, Sage, Mira — all reviewers
Sonnet (default):          Rex, Adam, Aria — all implementors
Opus   (never):            Banned — too expensive for any use
```

---

## Universal Tool Use Cap — All Agents

**18 tool uses maximum per agent invocation. Call 19 is mechanically blocked.**

The only exception is the greenfield-module budget (28 tool uses), opt-in via a spec's
`bootstrap_exception` block and authorized by Eran — see commit-protocol.md "Budget Profiles".

If an agent hits its cap and is not done, it stops and reports. Claude does not re-invoke to continue.

---

## Execution Constraints — Include Verbatim in Every Invocation

`hooks/prepare_agent_delegation.py` is invoked only on the delegated path. Before
invoking an implementor, Claude must run
`python hooks/prepare_agent_delegation.py --commit NN --agent NAME` and pass the generated
brief verbatim. Agents begin with the selected files and do not scan directories.
Additional context requires a stated reason, exact query/path, expected decision, and
tradeoff; the expansion and outcome are recorded in the worklog.

Claude-direct (the default) does not run `prepare_agent_delegation.py` at all. Its
readiness check is `python hooks/preflight_commit.py --direct --commit NN --agent OWNER`
— lean, ephemeral, no context package, no telemetry, no dashboard.

### Implementors (Rex, Adam, Aria)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 18 (28 only under an authorized greenfield bootstrap_exception). Plan reads
  upfront. Batch writes. Hit the cap → stop and report.
- Two phases only: Phase 1 — all reads. Phase 2 — all writes. No reads in Phase 2.
- Do not re-read any file already read this session.
- Worklog: one write at task completion only.
- Test runs: maximum 2. On second failure, report and stop.
- Code comments: one line max, functional only.
- Verbose output: alembic/pytest/docker/npm → summary line + ERROR/FAIL lines only. No full output.
- DO NOT run git add, git commit, or git push. Write files and run tests only.
  Stop after all files are written and tests pass. Report completion to Claude.
  Claude runs the gate, gets Team Lead approval, then commits. Never the agent.
```

### Reviewers (Viktor, Sage)

```
EXECUTION CONSTRAINTS:
- Max tool uses: 18. Work from the diff. Do NOT read files speculatively.
- Only Read a file if a specific diff line is ambiguous — max 15 lines per targeted read.
```

### Mira

```
EXECUTION CONSTRAINTS:
- Max tool uses: 5. Do not read any files — assess from Claude's brief only.
```

---

## Quality Gate Trigger

**Step 8 of every commit loop: invoke `/gate-triage` with the diff.**

The full triage matrix lives in `.claude/commands/gate-triage.md` — loaded on demand only.
This keeps always-loaded files lean. The rule here is simple: run the skill, get the verdict.

Do not reason through gate decisions manually. Do not skip `/gate-triage`. It is a protocol step.

---

## Orchestrator Post-Agent Verification Protocol

After every agent invocation, before any notification or approval prompt,
Claude completes these steps in order. This is the fixed commit loop sequence:

**Implement → capture telemetry → inspect logic → verify-commit → close scope
→ inspect diff/boundaries → update records → notify → request approval → commit**

```
STEP A0 — TELEMETRY CAPTURE (two sub-steps, always before inspection)
  (a) Persist agent self-report:
      Extract JSON block from agent's final message (Return Contract section).
      Run: python hooks/context_telemetry.py --agent-report NN AGENT '{...}'
      If agent omitted the block: use worklog tool-usage line for tool_calls,
      set all path arrays to null. Never skip. Never treat missing as zero.
  (b) Open orchestrator scope:
      Run: python hooks/context_telemetry.py --start-orchestrator CNN
      Opens before any Claude file reads so all inspection activity is captured.

STEP A — INSPECT LOGIC (mandatory, never skip)
  Read every file the agent edited.
  Check validators, defaults, and business rules against the commit contract.
  Passing tests do not substitute for this — tests can mirror a bug.
  Scope expansions: verify reason, path, expected decision, and tradeoff are in the worklog.
  If logic does not match the contract: fix before proceeding, note as orchestrator correction.

STEP B — INSPECT TESTS
  Does each test fail when the requirement is violated?
  Tests that pass because the implementation allows something are not correct.
  Negative tests for invalid values, boundaries, and conflicting configs are required.
  A test file with no rejection tests is incomplete — add them before proceeding.

STEP C — DIFF AND BOUNDARY REVIEW
  git status --short — report every modified and untracked file explicitly.
  git diff --check — confirm no whitespace errors.
  git diff --stat — review every changed file and line count.
  Confirm no files outside the agent's domain are modified.

STEP D — /verify-commit
  Always, without exception. If it fails: stop, fix, re-run.
  Never proceed to notification before this passes.
  /verify-commit checks structural compliance only (context block present, no
  forbidden-path files, tool budget respected) — it does not verify test results,
  logic correctness, or spec conformance. STEP A's independent logic inspection is
  what verifies correctness; passing /verify-commit is not a substitute.

STEP D.5 — CLOSE ORCHESTRATOR SCOPE (immediately after STEP D passes)
  Run: python hooks/context_telemetry.py --stop-orchestrator CNN
  Writes .context/telemetry/CNN-orchestrator.json. verify_constraints.py reads it
  in STEP 13 to build the complete dual-scope record in CONTEXT_METRICS.json.
  Never skip — missing file makes orchestrator scope show unavailable on dashboard.

STEP E — UPDATE RECORDS
  TOKEN_RECORDS.md: correct counts if orchestrator made post-session fixes.
  Worklog Current State: stays "currently active / pending approval" until git commit.
  Worklog session index: add orchestrator correction notes where applicable.
  Outbound handoffs: update with any corrected facts (model names, file counts, etc.).

STEP F — NOTIFY
  Only after STEP D passes and STEP E is complete.
  NOTIFY_WHAT and NOTIFY_WHY describe the final, corrected state — never a preliminary state.

STEP G — REQUEST APPROVAL
  Clearly label what is agent-written vs orchestrator corrections.
  Show git status --short output so every changed file is visible to Eran.
```

---

## Orchestrator Debugging Circuit Breaker (D37)

```
During orchestrator-led debugging or repair work (diagnosing a failing test, a
hook/telemetry defect, repairing corrupted state, etc.):
- Stop after 2 failed repair/verification cycles OR 25 orchestrator tool calls
  (self-monitored via .context/telemetry/orchestrator-active.json's tool_calls
  counter — no new enforcement hook).
- On hitting either limit: report the blocker, the evidence gathered, and a
  minimal proposed correction. Continue only after Eran's explicit approval.
- Does not apply to the normal STEP A0(b)-D.5 post-agent verification sequence
  when it proceeds without repeated failures.
```

---

## Post-Commit File Checklist (Claude's responsibility — no exceptions)

After every agent completes work, before presenting the next Commit Preview,
Claude must verify and update ALL of the following files as applicable:

```
□ project-state.json   — ALWAYS: advance last_completed_commit, next_commit,
                          next_commit_name, next_commit_assignee, clear resolved
                          handoffs, update notes.

□ TOKEN_RECORDS.md     — ALWAYS: add one row per agent invocation to Commit Log,
                          add one row to Session Totals.
□ CONTEXT_METRICS.json — ALWAYS: updated by verify_constraints from live telemetry.
                          Pass --execution claude-direct (forces tokens: null) or
                          --execution delegated --tokens N for delegated invocations.
□ constraint-dashboard.html — opt-in only: regenerated via verify_constraints
                          --render-dashboard, used manually or during the
                          five-commit Viktor review wave — not every commit.

□ DECISIONS.md         — if any non-obvious design choice was made this commit.

□ ARCHITECTURE.md      — if any new component, pattern, or data flow was introduced.

□ GLOSSARY.md          — if any new term was introduced.

□ team-preferences.md  — if execution constraints, protocol rules, hook behavior,
                          or agent calibration changed this commit.

□ Agent identity files — if an agent's domain, standards, or interfaces changed.

□ git status clean     — ALWAYS LAST: after all files above are updated, stage and
                          commit them immediately in a chore(state): advance state
                          after C-NN commit. Run git status and confirm no modified
                          or untracked files remain in protocol-managed paths.
                          Do NOT present the next Commit Preview until this is clean.
                          This is non-negotiable — files left behind accumulate
                          across sessions and become impossible to attribute.
```

**The first two are unconditional.** Missing project-state.json means the next
session boots with stale state. Missing TOKEN_RECORDS.md means cost data is lost.
Neither is acceptable.

**The last one closes the loop.** Every updated file must be committed in the same
session it was updated. No exceptions, no deferrals.

---

## Verbose Output Rules

Certain commands produce output that is mostly noise. Apply these filters in the execution constraints
block when invoking agents that will run these commands:

```
VERBOSE OUTPUT RULES:
- alembic upgrade/downgrade: capture last 5 lines + any line containing ERROR or FAIL
- pytest: capture summary line only ("X passed, Y failed in Zs") + any FAILED test names
- docker-compose up: capture service startup confirmations + any ERROR lines only
- npm install: capture final line only ("added N packages")
- uv sync: capture final line only
Do not paste full command output into the worklog or response. Summary only.
```

---

## Context Window Management

```
After every commit:              /clear — all state is in project files, nothing is lost
Mid-commit at ~60k:              /compact — preserves in-flight work
Before gate wave if >40k:        /compact first, then spawn reviewers
At Commit Preview if >30k
  and no agent invoked yet:      /compact before proceeding
```

**No speculative file reads mid-session.** Claude reads a file only at the moment its content
is needed to make a specific decision or write a specific edit. Reading files "just in case"
compounds across the session history and inflates every subsequent message.

**Agent context tiers:**
- Fresh agent (first commit, no worklog): Tier 0 only (identity file)
- Continuing agent (2+ commits done): Tier 0 + Current State Header
- Never pass full worklog history unless the task explicitly requires historical depth

---

## Commit Preview Format (locked 2026-06-04)

Every Commit Preview must follow this exact structure — no variations:

```
## Commit [N] — `[name]` · [Assignee]

**Summary:** [1-2 sentences plain English. Junior-readable. What it does and why it matters.
             This replaces the old "What" field — do not use "What".]
**Why now:** [one sentence — sequencing rationale]

**⚡ Parallel:** [only if applicable — omit this line entirely if no parallelism]

**Changes:**
- `path/to/file` — new/update/delete: [what, in 5 words]

**Test gates:** [gate 1] · [gate 2] · [gate 3]

**Quality gate:** [always state explicitly — e.g. "Viktor batch wave at C05. No per-commit gate — infrastructure only."
                  Never write "None" — always explain which rule applies and why no gate triggers.]

Invoke [Agent] to begin?
```

**Why this format (debate 2026-06-04):**
- "Summary" replaces "What" — same token cost, but junior-readable. Eran should be able to understand any commit without reconstructing it from the file list.
- "What" and "Summary" conveyed identical information — one field does both jobs.
- Parallel callout moved above Changes — it's an approval-time decision, not a footnote.
- Quality gate is always explicit — "None" implied the check was skipped; the rule statement shows the system is working as designed.

---

## Communication Preferences

```
Tone:                   Direct. Lead with what decision Eran needs to make.
Approval prompt:        Summary → test results → gate findings → "Approve to commit?"
Escalation threshold:   Low — escalate early rather than resolve autonomously
Address Team Lead as:   "Eran" always
```

---

## Commit Message Format (required for post-commit hook)

```
[conventional-commit subject line]

[body — what and why]

Commit #NN
-- AgentName
```

The post-commit hook parses `Commit #NN` to auto-update commit-protocol.md and project-state.json.

---

## Viktor Pre-Brief (include in every implementor invocation)

```
Viktor will check:
- All collection types explicitly typed (list[X], not bare list)
- All finite string fields use Literal[...], not str
- All routes are async — no sync SQLAlchemy calls
- Pydantic schemas for all route inputs/outputs
- No secrets in staged files
```

Add commit-specific items where the spec has known sharp edges.

---

## Change Log

| Date | Change | Reason |
|---|---|---|
| 2026-06-04 | Initial creation | Project initialized |
| 2026-06-04 | Gate matrix moved to /gate-triage skill | On-demand loading reduces always-loaded token cost (D06) |
| 2026-06-04 | Verbose output rules added to execution constraints | Alembic/pytest output can be 200+ lines — summary only (D05) |
| 2026-06-04 | Session checkpoint rules added | Token checkpoints before gate wave and at Commit Preview (D05) |
| 2026-06-04 | Agent context tier rules made explicit | Warm/cold agent distinction — no full worklog by default (D05) |
| 2026-06-04 | Added "DO NOT git commit" to Implementors constraints | Aria (C03) committed without gate/approval — rule now written in both CLAUDE.md and team-preferences.md |
| 2026-06-04 | Added Post-Commit File Checklist section | project-state.json and team-preferences.md were not being updated consistently — checklist now covers all required files |
| 2026-06-05 | Claude now commits after approval (D13) | Agents were invisible as GitHub contributors; Eran no longer runs git commands manually. Claude uses CLAUDE_COMMIT=1 + Co-Authored-By trailers. |
| 2026-06-06 | Added mandatory git status clean step to Post-Commit Checklist | Files were accumulating as unstaged/untracked across sessions — chore commit is now a required final step of every commit loop. |
| 2026-06-09 | Added Orchestrator Post-Agent Verification Protocol (Steps A–G) | C24 session: orchestrator presented a buggy commit without logic inspection; notified before /verify-commit passed; accepted tests that mirrored a bug rather than enforcing the contract; guessed agent email. 15 behavior corrections recorded across CLAUDE.md, ORCHESTRATION.md, and team-preferences.md. |
| 2026-06-09 | Added dual-scope telemetry steps A0 and D.5 to Verification Protocol | Agent and orchestrator activity must be recorded separately per commit. A0 persists agent self-report and opens orchestrator scope. D.5 closes it after /verify-commit so verify_constraints.py can write the complete dual-scope record. See D31. |
| 2026-06-13 | Added lean Claude-direct preflight (`preflight_commit.py --direct`), made dashboard rendering opt-in (`--render-dashboard`), and added honest "Not created (Claude-direct)" / "Legacy preview package (unused)" dashboard labels | Claude-direct (the default execution path) was forced through the full delegated-path preflight scoring and dashboard render every commit, producing misleading N/A-filled rows and unnecessary work. C29-C32 backfilled with `execution` field and corrected `tokens` (null where untracked). |
