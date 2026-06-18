# Commit 70 - `assistant-markdown-rendering` - Aria

**Phase:** Assistant hardening
**Owner:** aria
**Depends on:** C69
**Estimated diff lines:** 130
**Primary behavior count:** 1
**Developer test milestone:** yes

## Primary Behavior
Render assistant responses as formatted markdown instead of raw text, so tables, headers, lists, and bold text display correctly in the chat interface.

## Semantic Fit Review
- **Atomic outcome:** Assistant messages render with markdown formatting instead of plain monospace text.
- **Failure boundary:** Backend response formatting (browse fallback tables, LLM prompt markdown instructions) is handled in C69. Evidence graph reorganization remains C71.
- **Budget rationale:** One npm dependency addition and one message rendering component change fit two files within Aria's frontend domain.

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
  - frontend/package.json
initial_context:
  - frontend/src/pages/Assistant.tsx
  - frontend/src/store/assistant.ts
  - frontend/src/api/assistant.ts
  - frontend/package.json
forbidden:
  - backend/
```

## Files To Modify Or Add
| File | Type | Purpose |
|---|---|---|
| `frontend/src/pages/Assistant.tsx` | edit | Replace plain text message rendering with markdown-rendered output for assistant messages. |
| `frontend/package.json` | edit | Add `react-markdown` dependency (and `@tailwindcss/typography` if not present). |

## Contract

### Frontend markdown rendering (`Assistant.tsx`)
Install `react-markdown` and use it for assistant messages:

1. Add `import ReactMarkdown from 'react-markdown'` at the top.
2. In the message rendering loop (lines 124-139), replace the plain text content:
   - For `msg.role === 'user'`: keep as plain text with `whitespace-pre-wrap` (user messages don't need markdown).
   - For `msg.role === 'assistant'`: wrap content in `<ReactMarkdown>` with appropriate className styling.

The assistant message div changes from:
```tsx
<div className="... whitespace-pre-wrap">
  {msg.content}
</div>
```
to (for assistant messages only):
```tsx
<div className="... prose prose-sm max-w-none">
  <ReactMarkdown>{msg.content}</ReactMarkdown>
</div>
```

### Tailwind typography plugin
If `@tailwindcss/typography` is not already a dependency, add it and include `require('@tailwindcss/typography')` in the Tailwind config plugins array. This provides the `prose` classes needed for clean markdown rendering.

### Styling constraints
- Assistant message markdown should inherit the existing `bg-gray-100 text-gray-900` container styling.
- Tables should have borders and padding consistent with the app's design system.
- Code blocks (if any appear in responses) should use a monospace font with a subtle background.
- Links should not be rendered as clickable (assistant responses don't contain user-facing URLs).

## Environment Prerequisites
- C69 complete (backend browse fallback and LLM prompt produce markdown-formatted responses).
- `react-markdown` must be installed: `npm install --prefix frontend react-markdown`.

## Developer Test Checkpoint
**Ready now:** Formatted assistant responses with markdown tables.
**How to test:** Click any suggested question badge and inspect the response.
**Expected result:** Tables, headers, and bold text render correctly. User messages remain plain text.
**Still incomplete:** Evidence graph timeline layout (C71).

## Verification Command
```powershell
npm run --prefix frontend build
```

## Focused Tests
- Build succeeds with no TypeScript errors.
- Visual verification: assistant responses render with markdown formatting (tables, headers, bold).
- User messages still render as plain text.
- Browse query responses appear as formatted tables.

## Done When
- [ ] **Ready now:** Assistant responses are formatted with markdown.
- [ ] **How to test:** Login as manager, click "Which shipments are delayed?" badge, inspect the response.
- [ ] **Expected result:** Response appears with a formatted table of shipments, not raw text.
- [ ] **Still incomplete:** Structured card views for specific result types, evidence graph timeline (C71).

## Not In This Commit
- Evidence graph changes (C71).
- Backend response formatting (C69 handles browse fallback markdown and LLM prompt updates).
- Intent classification (C68).
- Custom card/table components for specific response types.

## Return Contract
Begin with the required Human Summary, then provide structured telemetry. If completion is not credible by call 16, return `SPLIT_REQUIRED`.
