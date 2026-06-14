# Commit 50 - `logistics-graph-evidence` - Nova

**Phase:** Logistics evidence
**Owner:** nova
**Depends on:** C49
**Estimated diff lines:** 260
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Project logistics evidence into stable graph nodes, edges, provenance, and a highlighted answer path.

## Semantic Fit Review
- **Atomic outcome:** Backend evidence has one frontend-ready graph contract.
- **Failure boundary:** Natural-language answering remains C53.
- **Budget rationale:** Projection and tests stay in the logistics service pair.

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
  - commit-specs/PHASE-3-GRAPH-RAG-DESIGN.md
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add graph evidence types and projection. |
| `backend/tests/services/test_rag_logistics.py` | edit | Verify IDs, edge paths, highlights, and provenance. |

## Contract
Return `nodes`, `edges`, `highlighted_path`, and `retrieved_at`. Node types are
`buyer|purchase_order|vendor|shipment|product|event`; IDs are stable
`<type>:<database-id>`. Edges use allowlisted relationships and the highlighted path
contains only IDs supporting the answer, ordered buyer to event/product.

## Environment Prerequisites
- C49 complete logistics evidence exists.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k graph -q
```

## Focused Tests
- Golden paths contain exact nodes and edges.
- IDs are stable and no orphan edges exist.
- Highlighting excludes unrelated products/events.

## Done When
- [ ] **Ready now:** Shipment facts, relationships, timelines, and graph paths.
- [ ] **How to test:** Run focused tests and inspect the golden SHP-1048 graph payload.
- [ ] **Expected result:** Every claim maps to a returned node or edge.
- [ ] **Still incomplete:** No unified assistant API or browser UI.

## Developer Test Checkpoint
**Ready now:** Traceable logistics evidence.
**How to test:** Execute the verification command and inspect representative service payloads.
**Expected result:** Golden shipments return correct facts and highlighted paths.
**Still incomplete:** Assistant synthesis starts C52-C56.

## Not In This Commit
- Policy evidence, routing, answers, or HTTP.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
