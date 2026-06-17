# Commit 66 - `graph-node-status-metadata` - Claude-direct (Rex domain)

**Phase:** Assistant hardening
**Owner:** rex
**Execution:** Claude-direct — adding optional fields to dataclass + Pydantic model and populating with a mapping; purely mechanical.
**Depends on:** C65
**Estimated diff lines:** 120
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Enrich graph nodes with optional status and status-category metadata so the frontend can color-code nodes by lifecycle state.

## Semantic Fit Review
- **Atomic outcome:** Graph API response includes status metadata per node.
- **Failure boundary:** Frontend rendering changes remain C67.
- **Budget rationale:** Schema addition, graph projection update, and test changes fit the allowed files.

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
  - backend/app/schemas/assistant.py
  - backend/app/api/v1/assistant.py
initial_context:
  - backend/app/schemas/assistant.py
  - backend/app/api/v1/assistant.py
  - backend/app/services/rag_logistics.py
  - backend/app/models/shipment.py
forbidden:
  - frontend/
  - backend/app/models/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/assistant.py` | edit | Add optional `status: str \| None` and `status_category: str \| None` fields to `GraphNodeSchema`. |
| `backend/app/services/rag_logistics.py` | edit | Add `status` and `status_category` to `GraphNode` dataclass. Populate them in `_project_procurement_graph()`: shipment nodes get the shipment's status; event nodes get a category derived from the event type; other nodes get `None`. Add `_status_category()` helper mapping statuses to `"done"`, `"active"`, or `"issue"`. |
| `backend/app/api/v1/assistant.py` | edit | Pass the new `status` and `status_category` fields through the `GraphNodeSchema` constructors in `_graph_from_logistics()` and the mixed-answer graph builder. |
| `backend/tests/api/test_assistant.py` | edit | Assert that logistics graph responses include `status` and `status_category` on shipment and event nodes. |

## Contract
- `GraphNode` dataclass gains `status: str | None = None` and `status_category: str | None = None`.
- `GraphNodeSchema` Pydantic model gains `status: str | None = None` and `status_category: str | None = None`.
- `_status_category(status: str) -> str` maps:
  - `"delivered"` -> `"done"`
  - `"pending"`, `"in_transit"` -> `"active"`
  - `"delayed"`, `"damaged"`, `"partial"`, `"cancelled"`, `"returned"`, `"lost"` -> `"issue"`
- Shipment nodes: `status=evidence.shipment.status`, `status_category=_status_category(status)`.
- Event nodes: `status=event.event_type`, `status_category="issue"` for exception event types, `"active"` otherwise.
- Buyer, vendor, purchase_order, product nodes: `status=None`, `status_category=None`.
- The API response is backward-compatible (new nullable fields default to `None`).

## Environment Prerequisites
- C65 is committed.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/api/test_assistant.py -q
```

## Focused Tests
- Logistics graph response includes `status` and `status_category` on shipment nodes.
- Event nodes carry `status_category` based on event type.
- Non-status nodes have `null` status fields.
- Existing graph structure tests still pass.

## Done When
- [ ] Graph metadata tests pass.
- [ ] Existing assistant tests still pass.
- [ ] Scope remains within budget.

## Developer Test Checkpoint
**Next milestone:** C67 graph visual overhaul.

## Not In This Commit
- Frontend rendering changes.
- Layout or color changes.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
