# Commit 73 - `fix-citation-frontend-uuid-types` - Aria

**Phase:** Assistant hardening
**Owner:** aria
**Depends on:** C72
**Estimated diff lines:** 10
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Align the frontend `CitationSchema` TypeScript interface with the backend's corrected UUID string types for `document_id` and `chunk_id`.

## Semantic Fit Review
- **Atomic outcome:** Frontend TypeScript types match the backend JSON contract — `string` instead of `number` for citation identifiers.
- **Failure boundary:** Backend fix is complete in C72. This commit is type-safety only; the frontend already works at runtime because JSON deserialization produces strings regardless of the TS declaration.
- **Budget rationale:** Single file, two line changes. Well within all limits.

## Execution Budget
```yaml
execution_budget:
  max_primary_files: 1
  max_changed_files: 1
  max_context_files: 3
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
  - frontend/src/api/assistant.ts
initial_context:
  - frontend/src/api/assistant.ts
  - backend/app/schemas/assistant.py
forbidden:
  - backend/app/
  - hooks/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/api/assistant.ts` | edit | Change `document_id: number` → `document_id: string` and `chunk_id: number` → `chunk_id: string` in `CitationSchema`. |

## Contract

### `frontend/src/api/assistant.ts`
- `CitationSchema.document_id`: `number` → `string`
- `CitationSchema.chunk_id`: `number` → `string`
- No other fields change.

## Environment Prerequisites
- Node.js with npm/pnpm.
- TypeScript compiler (tsc) available via `npx`.

## Verification Command
```powershell
npx --prefix frontend tsc --noEmit
```

## Focused Tests
- TypeScript type check passes with the updated types.
- No runtime test needed — the change is type-declaration only.

## Done When
- [ ] `CitationSchema` uses `string` for `document_id` and `chunk_id`.
- [ ] TypeScript compilation passes without errors.

## Developer Test Checkpoint
**Next milestone:** No milestone — this is a companion type-alignment fix.

## Not In This Commit
- Backend type fix — completed in C72.

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
