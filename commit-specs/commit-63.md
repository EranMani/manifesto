# Commit 63 - `logistics-browse-intent` - Nova

**Phase:** Assistant hardening
**Owner:** nova
**Depends on:** C62
**Estimated diff lines:** 180
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Classify general logistics questions (no tracking code) as a distinct `logistics_browse` intent instead of failing on a blank tracking code.

## Semantic Fit Review
- **Atomic outcome:** Intent routing distinguishes single-shipment lookup from browse/list/summary queries.
- **Failure boundary:** DB query and answer generation for browse queries remain C64-C65.
- **Budget rationale:** Routing logic changes and tests fit the existing service/test pair.

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

## Context
```yaml
primary_files:
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py
initial_context:
  - backend/app/services/rag_logistics.py
  - backend/tests/services/test_rag_logistics.py
  - backend/app/services/assistant.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add `logistics_browse` to `AssistantIntent`. Add browse-vocabulary detection (list/all/show/how many/delayed/pending/shipments) to `classify_intent()`. Extract optional status/keyword filters from question text into `IntentRouting`. |
| `backend/tests/services/test_rag_logistics.py` | edit | Add routing tests for browse queries: "find all shipments", "show delayed shipments", "how many shipments are pending", ambiguous without identifier. Verify existing single-shipment and policy routing is unchanged. |

## Contract
- `AssistantIntent` gains `"logistics_browse"` as a fourth literal value.
- `IntentRouting` gains an optional `status_filter: str | None` field for detected status keywords (e.g., "delayed", "pending", "delivered").
- `classify_intent()` returns `logistics_browse` when the question contains browse vocabulary but no explicit `SHP-####` or `PO-YYYY-###` identifier. Confidence is 1.0 when browse vocabulary is explicit, 0.5 for the ambiguous default (previously this defaulted to `logistics`).
- All existing routing behavior for questions with explicit identifiers or policy terms is preserved.
- No DB queries, no answer generation, no schema changes.

## Environment Prerequisites
- C62 is committed.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k intent -q
```

## Focused Tests
- Browse vocabulary routes to `logistics_browse`.
- Status filter extraction detects "delayed", "pending", "delivered", etc.
- Existing `logistics`, `policy`, and `mixed` routing is unchanged.
- No identifier is invented for browse queries.

## Done When
- [ ] Routing tests pass for all browse cases.
- [ ] Existing routing tests still pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C65 browse answer generation ready.

## Not In This Commit
- DB queries for listing shipments.
- Answer generation for browse results.
- Schema or API changes.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
