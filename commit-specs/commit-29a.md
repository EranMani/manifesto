# Commit 29A - `deterministic-commit-preflight` - Adam

**Phase:** Workflow Preflight
**Owner:** adam
**Depends on:** C29
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Generate a deterministic commit-readiness report and block implementor delegation unless
the score is at least 80 and no blocking violation exists.

---

## Semantic Fit Review

- **Atomic outcome:** One gate converts existing planning evidence into a repeatable proceed/block decision.
- **Failure boundary:** It evaluates readiness only; it does not implement or predict the future commit's code.
- **Budget rationale:** Three changed files, one explicit supporting file, and one hook-test command fit one invocation.

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
  - hooks/preflight_commit.py
  - hooks/prepare_agent_delegation.py
initial_context:
  - hooks/validate_commit_spec.py
forbidden:
  - backend/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `hooks/preflight_commit.py` | new | Build, score, persist, and print deterministic readiness results |
| `hooks/prepare_agent_delegation.py` | edit | Require passing preflight before creating delegation state |
| `hooks/tests/test_preflight_commit.py` | new | Prove scoring, blockers, persistence, and compact output |

---

## Contract

The hook accepts `--commit <ID> --agent <agent-id> --json` and reuses existing commit-spec
validation, pending-graph validation, ownership rules, context-package construction,
budget checks, verification-command inspection, and environment-prerequisite evidence.

It writes details to `.context/preflight/C<ID>.json` and prints compact JSON:

```json
{
  "commit": "C30",
  "score": 92,
  "blocking_violations": [],
  "warnings": ["Docker availability was not confirmed"],
  "proceed": true,
  "report_path": ".context/preflight/C30.json"
}
```

The decision is exact:

```text
proceed = score >= 80 AND blocking_violations is empty
```

The score measures readiness evidence, not predicted implementation correctness. Its
documented categories total 100 points and cover specification/dependency validity,
ownership and scope, context quality, verification readiness, and prerequisites.

These conditions block regardless of score:

- Invalid commit specification or pending dependency graph.
- Missing dependency, ownership violation, or forbidden planned edit.
- Context-package failure or hard context-budget overflow.
- Missing or structurally invalid verification command.
- Missing acceptance criteria.

Warnings may reduce the score without independently blocking. Claude receives only the
compact result on a passing run. A blocked report explains each failed check, deduction,
and repair direction without invoking an LLM.

`prepare_agent_delegation.py` calls the preflight API before initializing telemetry,
tool-cap state, or the delegation brief. A blocked result exits without those side
effects.

---

## Environment Prerequisites

- Python hook test environment.
- Existing C29 validator, context engine, ownership configuration, and delegation hook.

---

## Verification Command

```powershell
pytest -p no:cacheprovider hooks/tests/test_preflight_commit.py hooks/tests/test_prepare_agent_delegation.py -q
```

---

## Focused Tests

- Score 80 or greater with no blocker permits delegation.
- Score below 80 blocks and identifies lost readiness points.
- A hard violation blocks even when the score remains at least 80.
- Identical inputs produce identical scores and findings.
- Detailed diagnostics persist while stdout remains compact.
- Blocked preflight creates no delegation, telemetry, or tool-cap state.

---

## Done When

- [ ] The report is deterministic and uses only existing local evidence.
- [ ] Score categories total 100 and explain every deduction.
- [ ] Hard violations override the threshold.
- [ ] Delegation cannot begin before `proceed` is true.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C32.

---

## Not In This Commit

- Running the future commit's implementation tests.
- Predicting whether unwritten code will be correct.
- LLM-based review or a second agent invocation.
- Dashboard presentation of preflight history.
- Changing C30-C76 feature behavior.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. Include the
score categories, hard-block rules exercised by tests, and confirmation that blocking
caused no delegation side effects. If completion is not credible by call 16, stop and
return `SPLIT_REQUIRED`.
