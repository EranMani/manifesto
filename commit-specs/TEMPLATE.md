# Commit NN - `focused-kebab-name` - Owner

**Phase:** Phase name
**Owner:** rex
**Depends on:** CXX
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Describe one observable behavior only.

---

## Semantic Fit Review

- **Atomic outcome:** Explain why this is one independently testable result.
- **Failure boundary:** Explain what can fail here without reopening later behavior.
- **Budget rationale:** Explain why one agent can implement and verify it within the
  declared files, context, diff, tool, and token limits.

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
  - path/to/implementation.py

initial_context:
  - commit-specs/commit-NN.md
  - path/to/implementation.py
  - path/to/focused_test.py

forbidden:
  - unrelated/domain/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `path/to/implementation.py` | edit | Implement the primary behavior |
| `path/to/focused_test.py` | edit | Prove the primary behavior |

---

## Contract

Define exact inputs, outputs, defaults, status codes, and failure behavior.

---

## Environment Prerequisites

- State the runtime, services, fixtures, or environment variables required.

---

## Verification Command

```powershell
python -m pytest path/to/focused_test.py -q
```

---

## Focused Tests

- Happy path.
- Boundary or rejection path.
- Regression assertion for the contract.

---

## Done When

- [ ] The primary behavior is implemented.
- [ ] The verification command passes.

---

## Developer Test Checkpoint

Set `Developer test milestone` to `yes` only when this commit closes a coherent technical
or application capability.

When `yes`, define:

- **Ready now:** The capability Eran can test.
- **How to test:** Exact startup command, URL or API call, and short steps.
- **Expected result:** Observable successful behavior.
- **Still incomplete:** Later behavior that must not be mistaken as ready.

When `no`, state which later commit owns the next relevant milestone.

---

## Not In This Commit

- Name deferred behavior and the later commit that owns it.

---

## Return Contract

The implementor's final message must begin with this concise human summary:

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```

After the human summary, include the structured telemetry JSON required by the
generated delegation brief. If the commit cannot finish within its budget, also
include the `SPLIT_REQUIRED` report.
