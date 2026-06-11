# Commit 34 - `database-test-container-command` - Adam

**Phase:** Product And Test Recovery
**Owner:** adam
**Depends on:** C32
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Provide one reproducible container command for the full backend test suite.

---

## Semantic Fit Review

- **Atomic outcome:** One script standardizes environment startup and the test command.
- **Failure boundary:** Individual failing tests are repaired later.
- **Budget rationale:** 2 exact changed file(s), 3 initial context file(s), and one focused verification command fit one bounded invocation.

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
  - scripts/test_backend.ps1
initial_context:
  - scripts/test_backend.ps1
forbidden:
  - backend/app/
  - frontend/src/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `scripts/test_backend.ps1` | new | Run backend tests against the Docker database |
| `README.md` | edit | Document the canonical command |

---

## Contract

Provide one reproducible container command for the full backend test suite.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker Desktop and Compose available.

---

## Verification Command

```powershell
powershell -ExecutionPolicy Bypass -File scripts/test_backend.ps1 -CollectOnly
```

---

## Focused Tests

- Database hostname resolves inside the backend container.
- The script propagates pytest failure.

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

- OI-11 repair is C35.
- Ingestion integration is C36-C37.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
