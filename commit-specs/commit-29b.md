# Commit 29B - `preflight-delegation-gate` - Adam

**Phase:** Workflow Preflight
**Owner:** adam
**Depends on:** C29A
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Require a passing deterministic preflight result before `prepare_agent_delegation.py`
creates any delegation, telemetry, or tool-cap state.

---

## Semantic Fit Review

- **Atomic outcome:** One gate call converts C29A's persisted readiness evidence into a pass/fail precondition for delegation.
- **Failure boundary:** It only short-circuits `prepare()` on a blocked result; it does not change scoring, persistence, or the report schema from C29A.
- **Budget rationale:** One primary file edit plus its existing test file, with C29A's contract already known and importable — no exploration of `validate_commit_spec.py` or `context_engine.py` is required.

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

---

## Context

```yaml
primary_files:
  - hooks/prepare_agent_delegation.py
initial_context:
  - hooks/preflight_commit.py
  - hooks/tests/test_prepare_agent_delegation.py
forbidden:
  - backend/
  - frontend/
  - hooks/preflight_commit.py
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/prepare_agent_delegation.py` | edit | Call the C29A preflight gate first and block on a non-proceeding result |
| `hooks/tests/test_prepare_agent_delegation.py` | edit | Prove a blocked preflight prevents all delegation side effects |

---

## Discovery Notes (carried over from the C29A research-only invocation)

- `prepare_agent_delegation.prepare(repo_root, rules, commit, agent, force_refresh=False)`
  currently begins by loading `project-state.json`, checking `next_commit`/
  `next_commit_assignee` against the requested `commit`/`agent`, then calls (in order)
  `require_valid_pending_graph`, `require_valid_commit_spec`, graph refresh,
  `ContextPackageBuilder(...).build(...)`, writes `.context/runs/<commit>-<agent>-live.json`,
  renders and writes `.context/delegations/<commit>-<agent>.md`, calls
  `initialize_commit_state(...)` (writes `hooks/tool_cap.json`), `initialize_telemetry(...)`,
  and `render_dashboard(repo_root)`.
- `hooks/preflight_commit.py` (C29A) exposes `evaluate(repo_root, commit, agent) -> dict`,
  the same compact result shape `prepare_agent_delegation.py` is the consumer of, including
  `proceed`, `score`, `blocking_violations`, `warnings`, `report_path`.

---

## Contract

`prepare()` calls `preflight_commit.evaluate(repo_root, commit, agent)` as its first
action — before the `next_commit`/`next_commit_assignee` mismatch checks and before
`require_valid_pending_graph`, `require_valid_commit_spec`, graph refresh,
`ContextPackageBuilder`, `initialize_commit_state`, `initialize_telemetry`, and
`render_dashboard`.

When `result["proceed"]` is `False`, `prepare()` raises `PreflightBlocked`, a new
exception carrying the full compact result (`.args[0]` or an attribute such as
`.result`). No file is written or modified by `prepare()` in this case: no
`.context/runs/*-live.json`, no `.context/delegations/*.md`, no `hooks/tool_cap.json`
mutation, no telemetry initialization, and no dashboard render. The preflight report at
`.context/preflight/C<ID>.json` (written by `evaluate()` itself, per C29A) is the only
file touched.

`prepare_agent_delegation.py`'s CLI (`main()`) catches `PreflightBlocked`, prints the
compact result (matching C29A's compact JSON shape) to stdout, and exits with a non-zero
status. It does not print a stack trace.

When `result["proceed"]` is `True`, `prepare()` continues exactly as before with no
behavioral change to the existing pipeline.

---

## Environment Prerequisites

- C29A's `preflight_commit.evaluate(repo_root, commit, agent)` is importable and returns
  the documented compact result shape.
- Per commit-protocol.md rule 17, Claude has manually run
  `python hooks/preflight_commit.py --commit 29B --agent adam --json` and confirmed
  `score >= 80` with zero `blocking_violations` before this commit is delegated. C29B is
  the last commit gated this way; from C29C onward `prepare_agent_delegation.py` enforces
  this automatically.
- Python hook test environment.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_prepare_agent_delegation.py -q
```

---

## Focused Tests

- A blocked preflight (`proceed: false`) raises `PreflightBlocked` and creates no
  `.context/runs/*-live.json`, `.context/delegations/*.md`, `hooks/tool_cap.json`
  mutation, telemetry record, or dashboard render.
- A blocked preflight's compact result is printed by the CLI and the process exits
  non-zero, with no traceback.
- A passing preflight (`proceed: true`) leaves the existing delegation pipeline's
  behavior, outputs, and file contents unchanged from before this commit.
- `preflight_commit.evaluate` is called with the exact `commit`/`agent` values `prepare()`
  received, before any other validation or side-effecting call.
- `PreflightBlocked` carries the full compact result, including `score`,
  `blocking_violations`, `warnings`, and `report_path`.

---

## Done When

- [ ] `prepare()` cannot create delegation, telemetry, or tool-cap state before
      `preflight_commit.evaluate(...)` returns `proceed: true`.
- [ ] A blocked result raises `PreflightBlocked` with the full compact result attached.
- [ ] The CLI surfaces a blocked result as compact JSON with a non-zero exit and no
      traceback.
- [ ] A passing preflight does not change any existing delegation output.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within
      budget.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Changing C29A's scoring, categories, or persistence format.
- Dashboard presentation of preflight history (C29C).
- Refactoring or removing `require_valid_pending_graph`/`require_valid_commit_spec` (they
  remain as defense in depth after a passing preflight).
- Changing C30-C76 feature behavior.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. Confirm that a
blocked preflight produces zero delegation side effects and that a passing preflight is
behaviorally identical to the pre-C29B pipeline. If completion is not credible by call
16, stop and return `SPLIT_REQUIRED`.
