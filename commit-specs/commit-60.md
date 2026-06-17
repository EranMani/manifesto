# Commit 60 - `assistant-evidence-integration` - Aria

**Phase:** Integrated prototype
**Owner:** aria
**Depends on:** C59
**Estimated diff lines:** 260
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Connect assistant answers to policy citations or the focused logistics graph and node details.

## Semantic Fit Review
- **Atomic outcome:** The browser presents the complete answer-plus-evidence experience.
- **Failure boundary:** Evaluation and clean setup remain C61-C62.
- **Budget rationale:** Existing page and graph component contain the integration.

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
  - frontend/src/components/EvidenceGraph.tsx
initial_context:
  - frontend/src/pages/Assistant.tsx
  - frontend/src/components/EvidenceGraph.tsx
  - frontend/src/store/assistant.ts
  - frontend/src/api/assistant.ts
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Assistant.tsx` | edit | Add responsive evidence panel and citation cards. |
| `frontend/src/components/EvidenceGraph.tsx` | edit | Synchronize selected answer and graph details. |
| `frontend/src/store/assistant.ts` | edit | Persist intent and graph from queryAssistant response; reset intent/graph on reset. |

## Contract
Logistics/mixed answers show the graph; policy/mixed answers show source title, section,
page, and excerpt cards. Mixed answers show both in separate labelled regions. Evidence
updates only after a successful response and remains associated with its assistant turn.

## Environment Prerequisites
- C58-C59 components exist.

## Verification Command
```powershell
npm --prefix frontend run build
```

## Focused Tests
- All three evidence modes compile and render.
- Empty evidence and API errors retain understandable UI.

## Done When
- [ ] **Ready now:** Browser assistant with answers, citations, graph paths, and node details.
- [ ] **How to test:** Open `/assistant` as employee and manager and run the documented prompts.
- [ ] **Expected result:** Role-appropriate answers show their correct evidence.
- [ ] **Still incomplete:** Golden evaluation and clean-environment rehearsal.

## Developer Test Checkpoint
**Ready now:** Integrated prototype.
**How to test:** Run the stack, login, and use `/assistant`.
**Expected result:** Policy citations and logistics graph evidence appear beside answers.
**Still incomplete:** C61-C62 quality and setup gates.

## Not In This Commit
- Persistent history, streaming, or full-network exploration.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
