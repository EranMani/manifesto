# Commit 72 - `fix-policy-citation-uuid-types` - Rex

**Phase:** Assistant hardening
**Owner:** rex
**Depends on:** C71
**Estimated diff lines:** 60
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Fix HTTP 500 on policy questions by correcting `document_id` and `chunk_id` types from `int` to `str` across the citation schema and policy TypedDicts, matching the UUID column types in the database.

## Semantic Fit Review
- **Atomic outcome:** Policy questions that previously returned 500 now return 200 with correct UUID citation identifiers.
- **Failure boundary:** Frontend TypeScript type alignment is C73. No runtime logic changes — only type declarations and the response-conversion safety net.
- **Budget rationale:** Four files with small type-declaration edits and test fixture updates. Well within the 4-file limit and 350-line diff ceiling.

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
  - backend/app/services/rag_policy.py
initial_context:
  - backend/app/schemas/assistant.py
  - backend/app/services/rag_policy.py
  - backend/app/api/v1/assistant.py
  - backend/tests/api/test_assistant.py
  - backend/app/models/policy.py
forbidden:
  - frontend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `backend/app/schemas/assistant.py` | edit | Change `CitationSchema.document_id` and `chunk_id` from `int` to `str`. |
| `backend/app/services/rag_policy.py` | edit | Change `PolicyChunkCandidate` and `PolicyEvidence` TypedDict fields from `int` to `str`. |
| `backend/app/api/v1/assistant.py` | edit | Move `_to_response()` inside the try/except block for defensive safety. |
| `backend/tests/api/test_assistant.py` | edit | Update `_policy_answer()` and `_mixed_answer()` fixtures to use UUID strings instead of integers. |

## Contract

### `backend/app/schemas/assistant.py`
- `CitationSchema.document_id`: `int` → `str`
- `CitationSchema.chunk_id`: `int` → `str`

### `backend/app/services/rag_policy.py`
- `PolicyChunkCandidate.chunk_id`: `int` → `str`
- `PolicyChunkCandidate.document_id`: `int` → `str`
- `PolicyEvidence.document_id`: `int` → `str`
- `PolicyEvidence.chunk_id`: `int` → `str`

### `backend/app/api/v1/assistant.py`
- Move `return _to_response(result)` inside the existing try/except block so any conversion error returns 502 instead of 500.

### `backend/tests/api/test_assistant.py`
- `_policy_answer()`: change `"document_id": 1` → `"document_id": "doc-uuid-1"` and `"chunk_id": 10` → `"chunk_id": "chunk-uuid-10"`.
- `_mixed_answer()`: same UUID string substitution.
- Add a new test that verifies policy responses contain string-typed `document_id` and `chunk_id`.

## Environment Prerequisites
- Python 3.12 with `uv` package manager.
- Test suite runs without Docker (uses mock DB).

## Verification Command
```powershell
docker compose run --rm backend uv run pytest backend/tests/api/test_assistant.py -q
```

## Focused Tests
- Happy path: policy question returns 200 with string `document_id`/`chunk_id` in citations.
- Mixed intent: mixed question returns 200 with string citation identifiers.
- Regression: `_to_response()` error returns 502, not 500.

## Done When
- [ ] `CitationSchema` uses `str` for `document_id` and `chunk_id`.
- [ ] `PolicyChunkCandidate` and `PolicyEvidence` TypedDicts use `str`.
- [ ] `_to_response()` is inside the try/except block.
- [ ] Test fixtures use UUID strings.
- [ ] All `test_assistant.py` tests pass.

## Developer Test Checkpoint
**Next milestone:** No milestone — this is a targeted type-mismatch fix.

## Not In This Commit
- Frontend TypeScript type alignment (`CitationSchema` interface) — C73.

## Return Contract
```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```
