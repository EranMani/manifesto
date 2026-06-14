# ORCHESTRATION.md — Manifesto

> The master rules for running this project through the multi-agent workflow.
> CLAUDE.md is the boot sequence. This file is the full ruleset.
> When CLAUDE.md is ambiguous — this file is authoritative.
> Last updated: 2026-06-13 (lean Claude-direct preflight via --direct; honest dashboard
> labels for Claude-direct vs delegated; dashboard render is opt-in via --render-dashboard)

---

## 1. Philosophy

### What this system is

A team of specialized AI agents, each with deep expertise in their domain,
operating under strict discipline: one commit per concern, one owner per file,
and Eran — the Team Lead — who approves every change before it lands.

Claude is the orchestrator. Claude never writes application code. Claude routes
context, sequences handoffs, and makes sure every agent has exactly the
information they need — no more, no less.

### Three pillars

**Domain ownership is absolute.** Each agent owns a set of files. They never
touch anything outside that set. When they find a problem outside their domain,
they log it and flag it — they do not fix it. This prevents one agent's change
from silently breaking another agent's assumptions.

**Commit discipline is non-negotiable.** One commit per protocol step. One owner
per commit. Eran approves before every commit lands. This makes the system
auditable, reversible, and safe to run over long sessions.

**Context efficiency is engineered, not hoped for.** Token budgets are defined
per agent. Every invocation loads the minimum context needed. The system stays
fast and accurate across 21 commits as well as it does across 3.

---

## 2. The Commit Loop

Every commit follows this exact sequence. No step is skipped.

```
STEP 1 — Claude reads commit-protocol.md
└── Identifies step number, name, assignee, and testing gate

STEP 2 — Claude reads project-state.json
└── Checks for open blockers. Blocker exists → surface to Eran and stop.

STEP 3 — Claude validates scope, then checks readiness for the decided executor
└── After spec generation or renumbering, runs
    hooks/validate_commit_spec.py --all-pending --json
    (otherwise this graph-wide check is skipped)
    Claude decides the executor before running any preflight tooling:
    Claude-direct is the default (Non-Negotiable 10); delegation requires a
    written justification (unresolved specialist uncertainty, independent
    implementation for risk control, or a clearly bounded specialist unit whose
    expected value exceeds invocation overhead).
    - Claude-direct (default): runs
        python hooks/preflight_commit.py --direct --commit NN --agent OWNER
      where OWNER is the commit's owner (executor and owner are separate concepts).
      Lean, ephemeral check: validates only the active spec, this commit's own
      dependencies, ownership agreement, planned/forbidden files, and
      verification-command presence. Persists nothing, builds no context package,
      never touches the dashboard. Returns {status, proceed, violations}.
      proceed: false → stop and draft a smaller sequential spec for Eran.
    - Delegated (justified only): runs hooks/prepare_agent_delegation.py --preview
      Preview builds ignored approval artifacts only; it does not initialize tool-cap
      state, telemetry, or the tracked dashboard.
      Refreshes the cached graph only when stale
      Produces a bounded brief: primary files, contracts, dependencies, hubs, tests,
      boundaries, handoffs, acceptance criteria, and expansion triggers

STEP 3.5 — Claude presents the Commit Preview to Eran
└── For Claude-direct (the default), shows: READY/BLOCKED status (no numeric score),
    owner with domain, executor, one-sentence goal, every planned file with
    Add/Edit/Delete action, any `violations` as exact warning text, and whether a
    warning requires Eran's decision.
    For delegated execution, shows the scored readiness ([score]/100) plus the same
    owner/executor/goal/files/warnings fields, and the delegation justification.
    Full diagnostics appear only for BLOCKED results, decision-required warnings,
    changed scope, or repair/split proposals.
    Asks: "Proceed? [yes/no]"
    Eran must respond with explicit approval before Step 4 runs.

STEP 4 — Pre-invocation check (mandatory)
└── The executor was decided in STEP 3 and approved in STEP 3.5.
    Claude-direct → edit only files listed in the active commit spec. No further
                implementation tool call is allowed until this capture command runs:
                python hooks/prepare_claude_direct.py --commit CNN --owner OWNER
    Claude reads `.context/direct/CNN.md` first and follows the selected-file order.
    Repository-wide discovery is prohibited until the package has an unresolved
    symbol, missing contract, failing test, or contradictory implementation evidence.
    Delegated → rerun hooks/prepare_agent_delegation.py without --preview to activate
                tool-cap state and telemetry, then invoke the named agent.

STEP 5 — Agent executes
└── One normal invocation, maximum 18 tool calls and two expansions.
    Call 12 reports budget status. By call 16, finish or return SPLIT_REQUIRED.
    Writes worklog continuously. Decisions logged as made.

STEP 5.5 — Telemetry capture — two mandatory sub-steps, in this order:
└── (a) Persist agent self-report — DELEGATED EXECUTION ONLY:
        Extract the telemetry JSON block from the agent's final message (Return Contract).
        Run: python hooks/context_telemetry.py --agent-report NN AGENT '{...}'
        If the agent omitted the report: construct from worklog tool-usage line,
        set all path arrays to null (status: partial). Never skip. Never treat as zero.
        For Claude-direct commits, skip (a) entirely — no agent was invoked, so
        hooks/tool_cap.json has no matching invocation and --agent-report raises
        NoMatchingInvocationError (exit 1). telemetry.agent correctly records as
        "unavailable" (see C36; C37 fabricated a self-report this guard now blocks).
    (b) Open Claude review scope:
        Run: python hooks/context_telemetry.py --start-review CNN OWNER
        Claude-direct capture is already active from STEP 4. Delegated review capture
        opens BEFORE Claude reads any returned file.

STEP 6 — Agent completes
└── Updates Current State Header. Writes outgoing handoff notes.
    Worklog status is "pending approval" — not complete — until git commit succeeds.

STEP 6.5 — Claude inspects agent output (mandatory — never skip)
└── Read every file the agent edited. Check logic against the commit contract:
    validators, defaults, business rules, and acceptance criteria independently.
    Passing tests are not a substitute — tests can mirror a bug.
    Verify any scope expansions are recorded with reason, path, expected decision,
    and tradeoff in the worklog. Report any deviation from the spec to Eran.

STEP 7 — Test gate
└── Tests pass → continue.
    Tests fail → one narrow repair may be authorized from concrete failure evidence,
    with a delta brief below 6,000 characters and no renewed discovery.
    Gate does not surface to Eran until tests pass.
    Test suite must include negative tests for invalid values, boundaries, and
    conflicting configurations. A suite with no rejection tests is incomplete.

STEP 7.5 — Diff review and /verify-commit (mandatory — before any notification)
└── git status --short — report every modified and untracked file explicitly.
    git diff --check and git diff --stat — review every changed line and file count.
    /verify-commit — always, without exception. If it fails: stop, fix, re-run.
    Never send the completion notification before /verify-commit passes.
    /verify-commit checks structural compliance only (context block present, no
    forbidden-path files, tool budget respected) — it does not verify test results,
    logic correctness, or spec conformance. Step 6.5's independent logic inspection
    is what verifies correctness; passing /verify-commit is not a substitute.

STEP 7.75 — Close Claude scope (immediately after /verify-commit passes)
└── Run: python hooks/context_telemetry.py --stop-orchestrator CNN
    Finalises .context/telemetry/CNN-orchestrator.json so verify_constraints.py (STEP 13)
    can read it and write the complete dual-scope record into CONTEXT_METRICS.json.
    Never skip. Finalization rejects missing, mismatched, or incomplete capture.

STEP 8 — Quality gate wave (parallel where triggered)
└── Viktor: every 5th commit (C05, C10, C15, C20) — Haiku
    Sage:   conditional (auth, secrets, user input) — Haiku
    Mira:   conditional (user-facing behavior) — Haiku

    Blocking finding → a NEW commit using the standard Claude-direct-default routing
                       (no gate-fix passes)
    Viktor Hard Block → routes directly to Eran

STEP 9 — Records update (mandatory before notification)
└── DECISIONS.md — non-obvious choice or debate made?
    ARCHITECTURE.md — new component or data flow introduced?
    GLOSSARY.md — new term introduced?
    Worklog — update Current State and session index to reflect orchestrator corrections;
    correct outbound handoffs with any revised facts (model names, counts, etc.).
    Do NOT touch TOKEN_RECORDS.md here — STEP 10's finalize_commit.py runs
    verify_constraints --worktree, which flags any dirty file not in the owner's
    worklog as unplanned. TOKEN_RECORDS.md is added in STEP 13's chore sweep,
    after the primary commit.

STEP 10 — Notify Eran
└── Only after STEP 7.5 (/verify-commit) passes and STEP 9 (records) are current.
    The working tree must otherwise be clean (no pending TOKEN_RECORDS.md edit).
    Run hooks/finalize_commit.py --commit NN --agent OWNER --execution EXEC
      --notify-what "..." --notify-why "..." [--tokens N] [--render-dashboard]
    This runs verify_constraints --worktree, a conditional dashboard render, writes the
    pending-notify flag, AND writes the .context/finalize/CNN.json marker that STEP 12's
    commit requires (check_finalize_marker()). NOTIFY_WHAT/NOTIFY_WHY must describe the
    final, corrected state of the work. If it returns "status": "blocked", stop and fix
    before STEP 11. Do not call notify_agent_done.py separately — this supersedes it.

STEP 11 — Eran's approval
└── Approval prompt: what was built, test results, gate findings, "Approve to commit?"
    Clearly label any work that is an orchestrator correction vs agent-written.
    Show git status --short output so every changed file is visible.

STEP 12 — Claude commits on Eran's behalf
└── CLAUDE_COMMIT=1 git commit with Co-Authored-By trailer.
    Claude-direct commits include `Execution: Claude-direct` and credit Claude.
    Delegated commits credit the actual implementor. Co-Authored-By email is read from
    hooks/agent-config.json at commit time —
    never recalled from memory. Memory entries are convenience only.
    pre_commit_check.py runs (domain boundary, message format).
    CLAUDE_COMMIT=1 bypasses block_agent_commit.py only — it is NOT a bypass for
    pre_commit_check.py, which still validates this commit fully. ERAN_COMMIT=1
    is the only full bypass of pre_commit_check.py, reserved for Eran committing
    manually.
    Commit message must include "Commit #NN" and What/Why block.

STEP 13 — verify_constraints + post-commit doc sweep (mandatory)
└── Claude-direct: python hooks/verify_constraints.py --commit NN --agent NAME
                    --execution claude-direct
                    (forces tokens: null in CONTEXT_METRICS.json — do not pass --tokens)
    Delegated:      python hooks/verify_constraints.py --commit NN --agent NAME
                    --execution delegated --tokens N
    Writes CONSTRAINT_LOG.md and CONTEXT_METRICS.json. constraint-dashboard.html is
    regenerated only with --render-dashboard — render manually or during the
    five-commit Viktor review wave, not on every commit.

    Then immediately: stage and commit ALL protocol files as a chore:
      project-state.json, commit-protocol.md, TOKEN_RECORDS.md,
      CONSTRAINT_LOG.md, CONTEXT_METRICS.json,
      constraint-dashboard.html (only if re-rendered this commit),
      .context/finalize/CNN.json (written by STEP 10),
      .claude/agents/logs/<agent>-worklog.md,
      backend/DOMAIN_MAP.md, frontend/DOMAIN_MAP.md,
      ARCHITECTURE.md and GLOSSARY.md (if updated this commit)
    Commit: chore(state): advance state after C-NN, Co-Authored-By: Claude
    <claude@anthropic.com>. No "Commit #NN" or "Execution:" line — combined with any
    Co-Authored-By trailer, check_finalize_marker() would treat this chore commit as
    a primary commit needing its own (nonexistent) fresh marker. Always Claude, since
    .context/finalize/CNN.json is in Claude's domain regardless of the primary owner.
    Set GIT_MESSAGE with `export GIT_MESSAGE="$(cat <<'EOF' ... EOF)"` as its own
    statement before `CLAUDE_COMMIT=1 git commit -m "$GIT_MESSAGE"` — an env-prefix
    form (`GIT_MESSAGE="..." CLAUDE_COMMIT=1 git commit -m "$GIT_MESSAGE"`) expands
    $GIT_MESSAGE to empty in the current shell and aborts with an empty message.

    Final check: git status must show no modified or untracked files
    in protocol-managed paths. If any remain — commit them before Step 14.
    Worklog status updated to "complete" only after this step succeeds.
    BLOCKED: Do not proceed to Step 14 until git status is clean.

STEP 14 — Claude presents next Commit Preview
└── Eran approves → loop restarts at Step 1
    Eran defers → Claude holds. No agent invoked until approval.
```

### Claude-Direct Authorization (authoritative)

Claude-direct does not grant Claude broad domain ownership. An explicit
`Execution: Claude-direct` marker grants narrow, commit-specific authorization only
for the exact files listed in `Files To Modify Or Add`.

`validate_commit_spec.py` validates this planned authorization at spec-validation time
(STEP 3): every file in `Files To Modify Or Add` must already belong to the commit
owner's domain in `hooks/agent-config.json`, regardless of who executes the commit.
The approval card's `Executor: Claude (direct)` line (STEP 3.5) is Eran's authorization
for that route.

At commit time the message must carry both `Execution: Claude-direct` and
`Commit #NN`. `pre_commit_check.py` enforces the staged-file authorization and fails
closed: it resolves commit ID -> spec file -> `Files To Modify Or Add` table from those
two fields and treats that table as Claude's exact allowed-file set for the commit. A
missing marker resolution, missing spec, or missing/empty table raises
`DirectExecutionResolutionError` and hard-fails the commit (exit 2) — it never falls
back to a broader domain check. Claude edits only files in that table.

CLAUDE.md and `.claude/commands/next-step.md` reference this section rather than
restating it.

### Scope-stop path

When a delegated implementor returns `SPLIT_REQUIRED`, Claude stops the invocation and
inspects whether the completed subset is atomic and safe. Claude does not finish work
outside the approved file list. Claude drafts and validates the next sequential micro-commit,
then presents the disposition and proposed split to Eran.

Budget failures cannot be waived, accepted as documented overflow, or reset by another
normal invocation.

---

## 3. The Context Budget System

### Context Pyramid

```
TIER 0 — Always loaded (~4K tokens):
├── Agent identity file (.claude/agents/[name].md)
└── Current State Header from worklog (≤50 lines)

TIER 1 — Task context (~3K tokens, per invocation):
├── Active commit spec (commit-specs/commit-XX.md)
├── Relevant handoff notes
└── project-state.json blockers section

TIER 2 — Historical depth (~4K tokens, only when needed):
├── Most recent 2 worklog sessions
└── Specific DECISIONS.md entries referenced in the task

TIER 3 — Archive (only on explicit request):
└── Archived worklog sessions
```

Claude does not load Tier 2 by default. If the task does not explicitly require
historical depth, Tier 0 + Tier 1 is the entire context package.

### Live selection and expansion

The commit specification remains authoritative, but file selection is produced by
`hooks/prepare_agent_delegation.py`. The context engine adds only bounded structural
evidence: direct dependencies and callers, explicit cross-domain contracts, tests, and
at most the configured nearby domain hubs.

Agents do not scan folders. They read selected files first. Expansion is permitted only
for unresolved symbols, missing contracts, failing tests, or contradictory implementation
evidence. Every expansion states its reason, exact query/path, expected decision, and
tradeoff before the tool call, then records the result in the worklog.

Generated artifacts under `.context/` (preflight reports, run packages, telemetry) are
targeted-read-only: an agent that needs a specific field greps for it rather than reading
the whole file. Any generated JSON whose size exceeds the configured
`max_chars_per_file` (see `hooks/context_rules.json`) must never be fully read — this
applies to ad-hoc expansion reads, not just delegation-package files.

A normal invocation that exhausts its tool-call budget on discovery and reports
`SPLIT_REQUIRED` with zero files written is a process violation, not a normal split.
Claude records this distinctly in the agent self-report (e.g. note
`"process_violation": "zero_code_discovery_exhaustion"` alongside the telemetry) so the
dashboard and TOKEN_RECORDS.md can distinguish "split because the scope was genuinely
two commits" from "split because discovery alone overran the budget."

### Token budget targets

| Agent type | Target per invocation |
|---|---|
| Implementor (Rex, Adam, Aria, Nova) | warning at 35k; hard stop at 45k |
| Reviewer (Viktor, Sage, Mira) | ≤15k tokens |

The absolute observable commit stop is 60k tokens across implementation, repair, and
review. Missing token data remains unknown and cannot authorize continuation.

**Token budgets are post-hoc, cross-invocation circuit breakers — not real-time
limits.** `tool_cap_end.py` runs once, via `PostToolUse`/`matcher: "Agent"`, after a
subagent invocation has already finished and all of its tokens are spent. A "hard
stop at 45k" therefore cannot interrupt the agent that crosses it; it blocks the
*next* invocation for that commit (e.g. refuses an unauthorized repair once
`known_implementor_tokens` already meets the threshold). Tool-call and expansion caps
remain real-time (enforced on `PreToolUse` within the running invocation) — only token
caps are necessarily post-hoc.

`max_total_tokens` covers only the token usage the harness reports for Agent-tool
invocations (`<usage>subagent_tokens>` — input, output, and both cache fields summed).
It does not separately measure the orchestrator's own token usage for that commit. If
orchestrator usage needs to be bounded too, it must be measured and recorded
independently — `known_total_tokens` is not a whole-commit total.

### Orchestrator Debugging Circuit Breaker (instruction-level, D37)

The orchestrator's own token usage is unbounded by `tool_cap_end.py` (see above), so
debugging/repair sessions can run away without any enforcement hook noticing. This is
an instruction-level rule for Claude's own conduct — no new hook is built for it.

During orchestrator-led debugging or repair work (investigating a failing test,
diagnosing a telemetry/hook defect, repairing corrupted state, etc.):

- Stop after **2 failed repair/verification cycles** OR **25 orchestrator tool calls**
  (tracked via the existing `.context/telemetry/orchestrator-active.json` `tool_calls`
  counter — self-monitored, no new hook).
- On hitting either limit: report the blocker, the evidence gathered so far, and a
  minimal proposed correction.
- Continue only after Eran's explicit approval.

This does not apply to the normal Step A–G post-agent verification sequence when it
is proceeding without repeated failures — only to open-ended debugging loops.

When a session approaches 80% of context capacity:
1. Trigger `/archive-worklog` for any agent with >3 completed sessions
2. Compress context packages to Tier 0 + Tier 1 only
3. Alert Eran that compression has occurred

---

## 4. Quality Gate Rules

### Viktor — every 5th commit, Haiku

Batch review across all diffs since the last wave. Token target: ≤20k per wave.

**Blocks immediately (system-breaking only):**
- Import errors preventing app startup
- Unhandled exceptions on the happy path
- Async/sync mixing that blocks the event loop
- SQL injection, exposed secrets, auth bypass
- Missing required arguments causing TypeError at runtime

**Logged for deferred review (everything else):**
- Dead code, unused variables, style issues
- Missing type annotations
- Performance concerns (unless O(n²) on unbounded input)

### Sage — conditional, Haiku

Triggers when a commit touches: auth, JWT, secrets, env vars, user input, file uploads, external API calls.

**Blocks immediately:** Secrets in code, SQL injection, auth bypass, critical CVE-level issues.
**Logged:** LOW/MEDIUM findings, non-critical information disclosure.

### Mira — conditional, Haiku

Triggers on user-facing behavior changes. All findings are advisory — never blocks.

### No gate-fix passes

A blocking finding from any reviewer becomes its own next commit in the sequence.
The gate does not re-run in the same loop. Claude does not re-invoke the agent to fix and re-review.

---

## 5. Cross-Agent Communication

All agent-to-agent communication routes through Claude. No direct contact.

**Handoff format:**
```
## Handoff → [Agent]
From: [Agent] · Commit [N] `[name]` complete.
What I built: [one paragraph]
What you need to know: [interfaces, env vars, constraints]
Files to read: [list]
```

**Cross-domain finding:**
```
🐛 CROSS-DOMAIN FINDING → [Agent]
Found by: [Agent] during Commit [N]
File: [path:line]
Problem: [description]
Impact: [what breaks]
Suggested fix: [direction only — I will not touch this file]
```

---

## 6. Rollback Protocol

Rollbacks are revert commits — never force-pushes. History is never rewritten.

Before any git command: Claude assesses blast radius and surfaces to Eran.
Eran confirms blast radius before rollback proceeds.

After rollback:
1. Mark reverted commits as `⏪ reverted · [date]` in commit-protocol.md
2. Update project-state.json
3. Notify affected agents via worklog entries
4. Ask Eran: "Should the plan remain the same, or does this require a /replan?"

---

## 7. Replanning Protocol

When a discovery, changed requirement, or rollback invalidates part of the plan:

1. Claude drafts proposed changes to commit-protocol.md
2. Shows: what is removed, added, or reordered — and why
3. Surfaces to Eran with one-paragraph rationale
4. Eran approves or modifies
5. Claude updates commit-protocol.md and project-state.json
6. Claude notifies all agents whose upcoming work is affected

The commit index can only change with Eran's approval.
No agent can propose a replan that expands their own domain scope.

---

## 8. Slash Commands

| Command | What it does |
|---|---|
| `/status` | Full project status: commit progress, active step, open handoffs, blockers |
| `/next-step` | Identifies next pending commit, checks prerequisites, asks for approval |
| `/handoff-check` | Verifies all required handoffs are in place for the next step |
| `/rollback` | Blast radius assessment → revert commit → state update → agent notification |
| `/replan` | Formally revises the commit index: draft → Eran approval → apply |
| `/review-request` | Ad-hoc Viktor review outside the commit loop |
| `/security-audit` | Ad-hoc Sage review of specified files |
| `/archive-worklog` | Archives old worklog sessions to keep context lean |
| `/project-complete` | Final gate, handoff doc, project completion |

---

## 9. Non-Negotiables

These cannot be overridden by any agent or any instruction:

1. One commit per protocol step — no combining
2. Eran approves the compact preflight card before implementation or delegation — no exceptions
3. Eran approves the commit after quality gates — no exceptions
4. Tests pass before approval surfaces — no bypassing the gate
5. Viktor reviews every 5th commit — no skipping
6. No agent touches another's domain — findings are routed, not fixed in place
7. Worklogs are written in real time — not reconstructed after the fact
8. Secrets never appear in code — not in defaults, not in comments
9. Scope overflows are flagged immediately — not silently built
10. Never spawn an agent when the exact file, line, and content is already known — use Edit
11. Agent output is never approved without independent logic inspection — passing tests alone
    are not sufficient evidence that the implementation matches the contract
12. /verify-commit runs before every notification and approval prompt — no exceptions
13. Co-Authored-By emails are read from hooks/agent-config.json at commit time —
    never recalled from memory or prior sessions
14. Tool caps are hard limits — justified expansion is requested and recorded before
    the cap is reached, not reported after the fact
15. Completion notifications describe only the final, verified, corrected state of the
    work — never a preliminary or unreviewed state
16. Dual-scope telemetry is mandatory every commit: persist agent self-report (STEP 5.5a),
    open the required Claude scope, then close it after /verify-commit (STEP 7.75).
    Dashboard columns showing N/A when real data existed are a skipped step, not
    missing data. All three sub-steps run every commit without exception.
