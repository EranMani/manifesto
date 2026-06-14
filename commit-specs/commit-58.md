# Commit 58 - `focused-evidence-graph` - Aria

**Phase:** Integrated prototype
**Owner:** aria
**Depends on:** C57
**Estimated diff lines:** 320
**Primary behavior count:** 1
**Developer test milestone:** no

## Primary Behavior
Render the focused logistics evidence graph with highlighted paths and clickable node details.

## Semantic Fit Review
- **Atomic outcome:** A graph payload has one reusable visual representation.
- **Failure boundary:** Chat/page integration remains C60.
- **Budget rationale:** Dependency metadata and one component fit three files.

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
  - frontend/src/components/EvidenceGraph.tsx
  - frontend/package.json
initial_context:
  - frontend/src/api/assistant.ts
  - frontend/src/index.css
  - frontend/package.json
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/components/EvidenceGraph.tsx` | add | Render focused nodes, edges, highlights, and detail drawer. |
| `frontend/package.json` | edit | Add `@xyflow/react`. |
| `frontend/package-lock.json` | edit | Lock the graph dependency. |

## Contract
Use a deterministic left-to-right layout by node type. Highlight IDs from
`highlighted_path`, visually mute supporting nodes, fit view on payload change, and show
safe node fields in a side panel on click. Empty graph renders an explanatory placeholder.

## Environment Prerequisites
- C57 graph wire types exist.

## Verification Command
```powershell
npm --prefix frontend run build
```

## Focused Tests
- Build validates React Flow integration.
- Empty and populated payloads render without unsafe HTML.

## Done When
- [ ] Build passes.
- [ ] Focused path and node details are implemented.

## Developer Test Checkpoint
**Next milestone:** C60 integrated prototype ready.

## Not In This Commit
- Conversation page or API sending.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
