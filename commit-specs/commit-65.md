# Commit 65 - `browse-answer-generation` - Nova

**Phase:** Assistant hardening
**Owner:** nova
**Depends on:** C64
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Generate LLM-grounded answers for multi-shipment browse queries with a deterministic fallback and count disclosure.

## Semantic Fit Review
- **Atomic outcome:** Browse queries produce a natural-language answer grounded in retrieved shipment data.
- **Failure boundary:** Advanced filtering, pagination UI, and graph visualization for browse results are later work.
- **Budget rationale:** Prompt template, generation function, fallback, and tests fit the logistics service/test pair within Nova's domain.

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
  - backend/app/services/llm.py
forbidden:
  - frontend/
  - backend/app/api/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Add `_format_browse_evidence_for_prompt(shipments, total_count) -> str`, `_build_browse_logistics_prompt(question, shipments, total_count) -> list[ChatMessage]`, and `generate_browse_logistics_answer(db, llm, question, status_filter, limit) -> LogisticsAnswer`. |
| `backend/tests/services/test_rag_logistics.py` | edit | Add tests for browse prompt formatting, LLM generation with shipment list evidence, and fallback behavior on provider failure. |

## Contract
- `_format_browse_evidence_for_prompt(shipments: list[ShipmentEvidence], total_count: int) -> str`: renders a plain-text evidence block listing each shipment's tracking code, status, origin, destination, dispatched_at, expected_arrival_at, and delay_reason. Includes "Showing {len(shipments)} of {total_count} shipments" header when `total_count > len(shipments)`.
- `_build_browse_logistics_prompt(question, shipments, total_count)`: returns system + user messages. System prompt instructs the LLM to answer using only the provided shipment list evidence. User prompt includes the formatted evidence and the question.
- `generate_browse_logistics_answer(db, llm, question, status_filter=None, limit=20) -> LogisticsAnswer`: calls `list_shipments_summary()` (from C64) to get shipments and a total count, builds the browse prompt, calls `llm.chat()`, and returns a `LogisticsAnswer`. On any `LLMError`, falls back to `_deterministic_browse_fallback()` (from C64). Graph is always an empty `ProcurementGraph`. Follow-ups suggest specific shipment lookups from the returned list.
- The 20-shipment cap prevents token blow-up. The count disclosure ensures the user knows when results are truncated.
- Existing single-shipment generation is unchanged.
- C64's `answer_question()` already calls into the browse path; this commit upgrades the generation from deterministic-only to LLM-grounded with deterministic fallback. C64 imports `generate_browse_logistics_answer` from `rag_logistics.py` — this commit implements that function.

## Environment Prerequisites
- C64 browse query path, `list_shipments_summary()`, and deterministic fallback exist.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -k browse -q
```

## Focused Tests
- Browse prompt contains only retrieved shipment evidence.
- LLM generation produces a coherent answer.
- Provider failure returns the deterministic fallback.
- Count disclosure is present when results are truncated.
- Follow-ups suggest specific tracking codes from the result set.
- Existing single-shipment tests still pass.

## Done When
- [ ] **Ready now:** General logistics queries return grounded multi-shipment answers.
- [ ] **How to test:** Start the stack, login as manager, POST "find all shipments" to `/api/v1/assistant/query`.
- [ ] **Expected result:** Natural-language answer listing shipments from the DB, with count disclosure if truncated.
- [ ] **Still incomplete:** Frontend browse UX and advanced filtering.

## Developer Test Checkpoint
**Ready now:** Browse logistics queries work end-to-end.
**How to test:** POST general logistics questions to the assistant API.
**Expected result:** Multi-shipment grounded answers with fallback on provider failure.
**Still incomplete:** Frontend browse UX and advanced filtering.

## Not In This Commit
- Frontend changes.
- Graph visualization for browse results.
- Pagination controls or cursor-based browsing.
- Advanced text search or semantic filtering.
- Changes to `assistant.py` or `tests/api/test_assistant.py` (Rex's domain, handled in C64).

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
