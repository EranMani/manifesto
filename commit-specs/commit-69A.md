# Commit 69A - `browse-markdown-formatting` - Nova

**Phase:** Assistant hardening
**Owner:** nova
**Depends on:** C69
**Estimated diff lines:** 60
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Format browse logistics responses as markdown tables so the frontend markdown renderer (C70) can display structured shipment data.

## Semantic Fit Review
- **Atomic outcome:** Browse fallback and LLM-grounded responses produce markdown-formatted output (tables, bold, headers).
- **Failure boundary:** Frontend markdown rendering remains C70. Error handling fixes are C69.
- **Budget rationale:** Two targeted edits in one file — deterministic fallback formatter and LLM prompt instruction.

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
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/services/rag_logistics.py` | edit | Format `_deterministic_browse_fallback` as markdown table; add markdown instruction to `_build_browse_logistics_prompt`. |
| `backend/tests/services/test_rag_logistics.py` | edit | Update fallback assertions to match new markdown table format; add markdown instruction assertion to browse prompt test. |

## Contract

### Markdown table output for browse fallback (`rag_logistics.py`)
Update `_deterministic_browse_fallback` to format shipment data as a markdown table:
```markdown
**Found N shipments** (showing M):

| Tracking Code | Status | Origin | Destination |
|---|---|---|---|
| SHP-1001 | Delivered | Shanghai | Los Angeles |
| SHP-2050 | In Transit | Mumbai | Rotterdam |
```

### Browse logistics prompt update (`rag_logistics.py`)
In `_build_browse_logistics_prompt`, append to the system message:
`" Format your response using markdown. Use tables for shipment lists, bold for key figures, and headers for sections."`

## Environment Prerequisites
- C69 complete (LLM now passed to browse handler; error resilience deployed).
- Backend test suite runnable via `docker compose run --rm backend uv run pytest`.

## Developer Test Checkpoint
**Next milestone:** C71 evidence graph timeline layout.

## Verification Command
```powershell
docker compose run --rm backend uv run pytest tests/services/test_rag_logistics.py -x -q --tb=short -k "browse"
```

## Focused Tests
- Browse fallback output contains markdown table headers (`| Tracking Code |`).
- LLM prompt includes markdown formatting instruction.
- Existing browse tests still pass.

## Done When
- [ ] `_deterministic_browse_fallback` produces a markdown table.
- [ ] `_build_browse_logistics_prompt` system message includes markdown instruction.
- [ ] All existing browse tests pass.

## Not In This Commit
- Error handling fixes (C69).
- Frontend markdown rendering (C70).
- Evidence graph changes (C71).

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
