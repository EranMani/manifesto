# Commit 36 - `ingestion-pgvector-write-integration` - Nova

**Phase:** Product And Test Recovery
**Owner:** nova
**Depends on:** C35
**Estimated diff lines:** 145
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Verify real ingestion writes deterministic policy chunks and embeddings to pgvector.

---

## Semantic Fit Review

- **Atomic outcome:** One integration path proves successful database insertion.
- **Failure boundary:** Terminal failure and rollback behavior remain C37.
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
| `backend/tests/services/test_ingestion.py` | edit | Replace skipped insertion placeholder with a real database test |

---

## Contract

Verify real ingestion writes deterministic policy chunks and embeddings to pgvector.

The implementation must preserve prior committed contracts, use provider-neutral or typed
interfaces where applicable, and expose no unrelated behavior.

---

## Environment Prerequisites

- Docker database, migrations, and fake embedding vectors available.

---

## Verification Command

```powershell
docker compose run --rm backend uv run pytest tests/services/test_ingestion.py -k pgvector_write -q
```

---

## Focused Tests

- Document and chunks persist.
- Chunk order, provenance, and vector dimensions match.

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

- No ingestion algorithm changes.
- Failure transactions are C37.

---

## Return Contract

Begin with the required Human Summary, then provide structured telemetry. If completion
is not credible by call 16, stop and return `SPLIT_REQUIRED`.
