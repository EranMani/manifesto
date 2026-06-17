# Commit 64 - `list-shipments-service` - Rex

**Phase:** Assistant hardening
**Owner:** rex
**Depends on:** C63
**Estimated diff lines:** 220
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Add a capped shipment listing query and wire the `logistics_browse` intent path through `answer_question()`.

## Semantic Fit Review
- **Atomic outcome:** Browse queries reach the DB and return structured shipment summaries instead of failing.
- **Failure boundary:** LLM-grounded answer generation for browse results remains C65.
- **Budget rationale:** One new query function, one orchestrator branch, and tests fit the service pair.

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
  - backend/app/services/assistant.py
initial_context:
  - backend/app/services/rag_logistics.py
  - backend/app/services/assistant.py
  - backend/tests/services/test_rag_logistics.py
  - backend/app/models/shipment.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add `list_shipments_summary(db, *, status_filter, limit=20) -> list[ShipmentEvidence]` query function and `_deterministic_browse_fallback(shipments) -> str` formatter. |
| `backend/app/services/assistant.py` | edit | Add `logistics_browse` branch in `answer_question()` that calls `list_shipments_summary()` and returns a `LogisticsAnswer` with shipment list text and empty graph. |
| `backend/tests/services/test_rag_logistics.py` | edit | Add tests for `list_shipments_summary()`: returns capped results, respects status filter, handles empty DB. |
| `backend/tests/api/test_assistant.py` | edit | Add test for browse intent through `answer_question()`: "find all shipments" returns a list instead of an error. |

## Contract
- `list_shipments_summary(db, *, status_filter: str | None = None, limit: int = 20) -> list[ShipmentEvidence]`: queries `Shipment` table with optional `WHERE status = status_filter`, ordered by `dispatched_at DESC`, capped at `limit`. Returns `ShipmentEvidence` dataclasses (lightweight — no vendor/PO/product/timeline joins).
- `_deterministic_browse_fallback(shipments: list[ShipmentEvidence], total_count: int) -> str`: formats a plain-text summary listing each shipment's tracking code, status, origin, destination, and dates. Includes "Showing N of M shipments" when truncated.
- `answer_question()` handles `routing.intent == "logistics_browse"` before the existing `logistics`/`mixed` paths. It calls `generate_browse_logistics_answer()` from `rag_logistics.py` (implemented in C65) with the `status_filter` from `IntentRouting` (added in C63). Until C65 lands, `generate_browse_logistics_answer()` is a thin wrapper that calls `list_shipments_summary()` and returns `_deterministic_browse_fallback()` — no LLM call.
- The existing single-shipment `logistics` path is unchanged.

## Environment Prerequisites
- C63 `logistics_browse` intent routing exists.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py tests/api/test_assistant.py -q
```

## Focused Tests
- `list_shipments_summary()` returns correct results with and without status filter.
- Result count respects the limit cap.
- Empty DB returns empty list, not an error.
- `answer_question()` with browse intent returns a `LogisticsAnswer` containing shipment summaries.
- Existing single-shipment and policy paths are unaffected.

## Done When
- [ ] Browse query tests pass.
- [ ] Existing assistant tests still pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C65 browse answer generation with LLM.

## Not In This Commit
- LLM-grounded answer generation for browse results.
- Schema or API changes.
- Frontend changes.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
