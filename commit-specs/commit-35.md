# Commit 35 - `policy-storage-db-url` - Rex

**Phase:** Product And Test Recovery
**Owner:** rex
**Depends on:** C34
**Estimated diff lines:** 145
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Make policy-storage tests use DATABASE_URL with a localhost fallback.

---

## Semantic Fit Review

- **Atomic outcome:** One test configuration defect is corrected.
- **Failure boundary:** No application database configuration changes.
- **Budget rationale:** 1 exact changed file(s), 3 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - backend/tests/models/test_policy_storage.py
initial_context:
  - backend/tests/models/test_policy_storage.py
forbidden:
  - frontend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/tests/models/test_policy_storage.py` | edit | Read the container database URL |

---

## Contract

Make policy-storage tests use DATABASE_URL with a localhost fallback.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C34 canonical container command available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/models/test_policy_storage.py -q
```

---

## Focused Tests

- Container execution resolves db:5432.
- Host fallback remains available.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Next milestone:** C37.

---

## Not In This Commit

- No model or migration changes.
- Full ingestion integration remains C36-C37.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
