# Commit 29 - `agent-budget-circuit-breaker` - Claude

**Phase:** Workflow Redesign - Stop the Bleeding
**Owner:** Claude (workflow governance, under the C29 bootstrap exception)
**Depends on:** C28 (`document-upload-routes`)
**Product code:** Forbidden
**Status:** Draft for Eran's implementation approval
**Execution mode:** Orchestrator bootstrap; zero live implementor invocations
**Estimated diff lines:** 3000

---

## Primary Behavior

Prevent one commit from consuming repeated full-cost agent invocations.

Before any delegation is generated, the commit specification must pass structural scope
validation. During execution, tool calls, expansions, invocation count, and known token
usage must remain attached to the commit rather than resetting for each Agent call.

If the work cannot finish within the budget, the implementor returns `SPLIT_REQUIRED`.
Claude may draft a new sequential commit specification, but no continuation occurs until
Eran approves the split.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 4
  max_context_files: 6
  max_context_chars: 15000
  max_estimated_diff_lines: 350
  max_agent_invocations: 1
  max_tool_calls: 18
  max_expansions: 2
  max_implementor_tokens: 45000
```

These values become the default maximums for later commits.

### C29 Bootstrap Exception

```yaml
bootstrap_exception:
  reason: "Install the workflow circuit breaker atomically across governance, validation, hook state, delegation, and tests."
  applies_to_commit: 29
  max_changed_files: 18
  max_estimated_diff_lines: 3200
  expires_after_commit: 29
  product_code_allowed: false
```

The exception changes only C29's file-count and diff-size limits. It does not relax tool,
invocation, token, expansion, context, or single-behavior limits.

---

## Context

```yaml
initial_context:
  - commit-specs/commit-29.md
  - MULTI_AGENT_WORKFLOW_REDESIGN_ROADMAP.md  # sections 4-12 only
  - hooks/prepare_agent_delegation.py
  - hooks/tool_cap_start.py
  - hooks/tool_cap_enforce.py
  - hooks/tool_cap_end.py

primary_files:
  - hooks/validate_commit_spec.py
  - hooks/tool_cap_enforce.py

forbidden:
  - backend/
  - frontend/
  - docker-compose.yml
  - .env
```

The bootstrap starts from exactly six context files and at most 15,000 estimated
characters. The roadmap is supplied as targeted excerpts, not a whole-file read. Up to
two justified expansions may inspect an unresolved contract or failing test.

Because the current live Agent mechanism is the component being repaired, C29 does not
delegate its implementation. Claude applies the approved spec directly and verifies the
Agent behavior through isolated hook tests. The one-invocation maximum remains the
default installed for C30 and later commits.

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `MULTI_AGENT_WORKFLOW_REDESIGN_ROADMAP.md` | edit | Record the approved redesign contract and bootstrap exception |
| `commit-specs/commit-29.md` | edit | Replace the old product epic with this enforcement contract |
| `CLAUDE.md` | edit | Repair truncation and define mandatory pre-delegation validation, checkpoints, split handling, and non-waivable stops |
| `ORCHESTRATION.md` | edit | Make the commit-level state machine authoritative |
| `commit-protocol.md` | edit | Add micro-commit and sequential split rules |
| `project-state.json` | edit | Identify C29 as the active Claude-owned workflow bootstrap |
| `commit-specs/TEMPLATE.md` | new | Canonical machine-validatable specification template |
| `hooks/validate_commit_spec.py` | new | Validate scope, ownership, budgets, exclusions, tests, prerequisites, and numbering |
| `hooks/prepare_agent_delegation.py` | edit | Validate before graph refresh or artifact creation; render locked limits and split contract |
| `hooks/context_rules.json` | edit | Set six-file and 15,000-character package limits |
| `hooks/verify_constraints.py` | edit | Revalidate the spec and make budget failures non-waivable |
| `hooks/tool_cap_start.py` | edit | Start or reject an invocation without resetting commit totals |
| `hooks/tool_cap_enforce.py` | edit | Enforce calls, expansions, writes-started checkpoints, invocation type, and stop state |
| `hooks/tool_cap_end.py` | edit | Close the invocation while preserving commit state |
| `hooks/agent-config.json` | edit | Register the redesign roadmap as a Claude-owned governance document |
| `hooks/tests/test_validate_commit_spec.py` | new | Validator and rejection coverage |
| `hooks/tests/test_prepare_agent_delegation.py` | edit | Prove validation precedes all delegation side effects |
| `hooks/tests/test_tool_cap.py` | new | Commit-level invocation and repair-state coverage |

No application source, application tests, database files, dashboard implementation, or
telemetry aggregation code belongs in C29.

---

## Commit-Spec Validation Contract

`hooks/validate_commit_spec.py` must reject a specification when:

1. Filename, heading, owner, protocol row, or project-state identity disagree.
2. The identifier is not a normal integer commit ID.
3. Any required `execution_budget` field is missing, non-integer, or above the locked
   default.
4. More than one primary behavior or owner is declared.
5. More than two primary implementation files are declared.
6. More than four changed files are predicted without an exact generated-file or
   bootstrap exception.
7. Estimated changed lines exceed 350.
8. Focused tests, one verification command, environment prerequisites, or
   `Not In This Commit` are missing.
9. File entries use wildcards or vague wording such as "related files".
10. Dependencies refer to missing completed or pending commits.

The command exits nonzero and returns both readable output and structured JSON:

```json
{
  "status": "split_required",
  "commit": "C34",
  "violations": [
    {
      "rule": "max_primary_files",
      "actual": 4,
      "limit": 2
    }
  ]
}
```

The validator diagnoses scope. It does not rewrite or semantically split a specification.

---

## Pre-Delegation Behavior

`prepare_agent_delegation.py` must perform these steps in order:

1. Load project state and requested owner.
2. Validate the specification.
3. Run environment preflight checks that do not execute the feature.
4. Refresh or reuse the graph.
5. Build the bounded context package.
6. Reject the package if it exceeds six files or 15,000 characters.
7. Write the package, brief, initial telemetry, and dashboard preview.

If steps 1-6 fail, no delegation, telemetry, run package, or dashboard artifact is
created or modified.

---

## Commit-Level Circuit Breaker

The versioned state file must track at least:

```json
{
  "schema_version": 2,
  "commit": "C29",
  "agent": "claude",
  "status": "prepared",
  "invocation_count": 0,
  "active_invocation": null,
  "tool_calls": 0,
  "expansions": 0,
  "write_started": false,
  "known_implementor_tokens": 0,
  "known_total_tokens": 0,
  "repair_authorization": null,
  "stop_reason": null
}
```

### Normal invocation

- Exactly one normal implementor invocation is permitted.
- Starting another normal invocation for the same commit is blocked.
- Invocation end preserves commit totals and changes status; it never resets the commit.
- A research-only first invocation consumes the normal-invocation allowance.

### Tool checkpoints

- Calls 6-8: warn when implementation has not started.
- Call 12: emit mandatory budget-status guidance.
- Call 16: require completion or `SPLIT_REQUIRED` decision.
- Call 18: final allowed tool call.
- Call 19: blocked.
- Expansion 3: blocked.

### Token checkpoints

- 0-35,000 implementor tokens: green.
- 35,001-45,000: warning; no new discovery.
- Above 45,000: hard stop; no repair.
- At 60,000 known total commit tokens: absolute stop; block implementor, repair, and
  review activity.

Unknown token data is displayed as unknown. It is never converted to zero.

---

## Agentic `SPLIT_REQUIRED` Contract

An implementor that cannot finish safely must return:

```json
{
  "status": "split_required",
  "completed_scope": ["atomic behavior already completed"],
  "remaining_scope": ["unfinished behavior"],
  "reason": "scope_exceeds_budget",
  "suggested_commit_name": "focused-kebab-name",
  "suggested_owner": "nova",
  "required_files": ["path/to/file.py"],
  "acceptance_criteria": ["observable result"],
  "verification_command": "pytest path/to/test.py -q",
  "dependencies": ["C29"],
  "tool_calls": 16
}
```

Claude then stops execution, inspects whether the completed subset is independently safe,
drafts a new sequential specification for the remainder, validates it, and presents the
split to Eran. The implementor cannot edit specs, assign numbers, extend its budget, or
authorize another invocation.

---

## Narrow Repair Exception

A second invocation is allowed only when all conditions hold:

- The normal invocation wrote implementation files.
- A concrete verification command was run and failed.
- The remaining task is limited to repairing that failure.
- Claude creates a delta brief below 6,000 characters.
- The repair does not reread the original package or restart discovery.
- The commit remains below 45,000 known implementor tokens and 60,000 known total tokens.
- No prior repair invocation exists.

The repair authorization records the failing command, concise failure evidence, allowed
files, and expiry after one invocation.

---

## Failure Policy

- Specification failure stops before delegation.
- Context-package overflow stops before delegation.
- Tool, expansion, invocation, or token overflow stops execution.
- Missing or corrupt commit-level state blocks continuation.
- Missing implementor budget evidence fails verification.
- No configuration, decision-log entry, or human-readable waiver may convert a budget
  failure into pass.
- Claude may not directly complete unfinished application work after a scope stop.

Eran may approve a new specification or roadmap change. Approval creates new bounded
work; it does not erase the failed budget of the original commit.

---

## Environment Prerequisites

- Run from the repository root.
- Python must import the existing hook modules.
- Git must resolve the repository root.
- Hook tests must be runnable without Docker or application services.
- Existing C26-C28 telemetry files remain read-only historical evidence.

---

## Verification Command

```powershell
python -m pytest hooks/tests -q
```

---

## Required Tests

### Specification validation

- Valid template passes.
- Every missing required section fails.
- Every locked limit overflow fails.
- Multiple owners or primary behaviors fail.
- Invalid generated-file and bootstrap exceptions fail.
- Number, owner, state, protocol, and dependency mismatches fail.

### Delegation

- Validation occurs before graph refresh and artifact writes.
- Rejection leaves no delegation, run package, telemetry, or dashboard mutation.
- More than six selected files fails.
- More than 15,000 selected characters fails.
- Generated brief contains checkpoints, budget values, Return Contract, and
  `SPLIT_REQUIRED`.

### Circuit breaker

- First normal invocation starts.
- Second normal invocation is blocked.
- Invocation end preserves commit totals.
- Call 12 warns; call 19 blocks.
- Third expansion blocks.
- Research-only completion cannot continue normally.
- One valid narrow repair is allowed.
- Invalid, repeated, oversized, or discovery-oriented repair is blocked.
- Missing or malformed state fails closed for continuation.
- Token hard-stop and absolute-stop behavior is enforced when token totals are known.

### Post-execution verification

- Missing worklog or telemetry evidence cannot pass as a warning.
- Actual budget overflow fails.
- A budget failure cannot be waived.
- Existing forbidden-path and untracked-file checks remain green.

---

## Done When

- [ ] Invalid or oversized specs cannot generate delegation artifacts.
- [ ] Valid specs produce a brief within six files and 15,000 characters.
- [ ] One commit cannot start two normal implementor invocations.
- [ ] Tool call 19 and expansion 3 are mechanically blocked.
- [ ] An agent can return a validated `SPLIT_REQUIRED` proposal before exhaustion.
- [ ] One narrowly authorized failing-test repair works without reopening discovery.
- [ ] Budget failures are non-waivable in verification.
- [ ] `CLAUDE.md` execution constraints are complete rather than truncated.
- [ ] `python -m pytest hooks/tests -q` passes.
- [ ] No files under `backend/` or `frontend/` changed.

---

## Not In This Commit

- Per-invocation telemetry storage and contradiction reconciliation - C30.
- Dashboard invocation-ledger redesign - C30.
- Document upload HTTP 200/201 correction - C31.
- Database test baseline and OI-11 - C32.
- Real ingestion database integration - C33.
- Policy retrieval, rank fusion, grounding, streaming, citations, and evaluation - C34-C38.
- Renumbered chat and frontend product work - C39-C43.
- Automatic semantic decomposition without Eran's approval.
- Application, database, Docker, or frontend changes.

---

## Handoff Out

### Handoff -> C30

C29 provides versioned commit and invocation identifiers plus enforced stop states. C30
must store every invocation separately, aggregate commit totals, derive expansions from
actual reads, and report contradictions without changing C29's enforcement decisions.
