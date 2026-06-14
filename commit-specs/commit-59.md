# Commit 59 - `unified-assistant-interface` - Aria

**Phase:** Integrated prototype
**Owner:** aria
**Depends on:** C58
**Estimated diff lines:** 300
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Provide one role-aware assistant conversation page with session messages and suggested prompts.

## Semantic Fit Review
- **Atomic outcome:** Users have one complete chat surface independent of graph integration.
- **Failure boundary:** Evidence rendering remains C60.
- **Budget rationale:** One page and router update fit two files.

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
  - frontend/src/pages/Assistant.tsx
  - frontend/src/App.tsx
initial_context:
  - frontend/src/store/assistant.ts
  - frontend/src/store/auth.ts
  - frontend/src/pages/ChatLogistics.tsx
  - frontend/src/pages/ChatPolicy.tsx
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Assistant.tsx` | add | Render conversation, composer, prompts, loading, and errors. |
| `frontend/src/App.tsx` | edit | Add `/assistant` and redirect legacy chat routes. |

## Contract
Managers/admins see logistics and policy prompts; employees see policy prompts only.
Disable send while loading or blank. Preserve session messages across route navigation,
allow reset, and render answer text as plain text. Legacy `/chat/*` routes redirect.

## Environment Prerequisites
- C57 store and client exist.

## Verification Command
```powershell
npm --prefix frontend run build
```

## Focused Tests
- Role-aware prompts and route access compile.
- Loading/error/reset states are visible.

## Done When
- [ ] Build passes.
- [ ] Unified chat surface is complete.

## Developer Test Checkpoint
**Next milestone:** C60 integrated prototype ready.

## Not In This Commit
- Graph or citation presentation.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
