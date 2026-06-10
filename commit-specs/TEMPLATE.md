# Commit NN - `focused-kebab-name` - Owner

**Phase:** Phase name
**Owner:** rex
**Depends on:** CXX
**Estimated diff lines:** 200

---

## Primary Behavior

Describe one observable behavior only.

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

## Not In This Commit

- Name deferred behavior and the later commit that owns it.
