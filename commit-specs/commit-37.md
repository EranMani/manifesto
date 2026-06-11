# Commit 37 - `ingestion-status-transaction-integration` - Nova

**Phase:** Product And Test Recovery
**Owner:** nova
**Depends on:** C36
**Estimated diff lines:** 145
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Verify ingestion commits ready state and rolls back failed chunk transactions.

---

## Semantic Fit Review

- **Atomic outcome:** One integration contract covers terminal database state.
- **Failure boundary:** Retrieval behavior starts C38.
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
  - backend/tests/services/test_ingestion.py
initial_context:
  - backend/tests/services/test_ingestion.py
forbidden:
  - backend/app/api/
  - backend/app/models/
  - frontend/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/tests/services/test_ingestion.py` | edit | Add ready, failed, and rollback integration assertions |

---

## Contract

Verify ingestion commits ready state and rolls back failed chunk transactions.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- C36 real pgvector fixture available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_ingestion.py -k transaction -q
```

---

## Focused Tests

- Successful ingestion ends ready with chunk count.
- Failure leaves no partial chunks and records failed state.

---

## Done When

- [ ] The primary behavior is implemented exactly as contracted.
- [ ] The focused verification command passes.
- [ ] Changed files, diff lines, context, tools, expansions, and tokens remain within budget.

---

## Developer Test Checkpoint

**Ready now:** Document upload and ingestion database behavior is ready for testing.
**How to test:** Run `docker compose run --rm backend uv run pytest tests/api/test_documents.py tests/services/test_ingestion.py -q`.
**Expected result:** New and duplicate uploads have correct statuses; pgvector writes, terminal states, and rollback assertions pass.
**Still incomplete:** Policy retrieval and generation begin in C38.

---

## Not In This Commit

- No retrieval implementation.
- No route behavior changes.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
