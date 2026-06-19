# Commit 77 - `enable-gfm-table-rendering` - Aria

**Phase:** Phase 3
**Owner:** aria
**Depends on:** C76
**Estimated diff lines:** 15
**Primary behavior count:** 1
**Developer test milestone:** yes

---

## Primary Behavior

Markdown tables in assistant responses render as styled HTML tables instead of raw pipe-delimited text, by installing `remark-gfm` and wiring it into the `ReactMarkdown` component.

---

## Semantic Fit Review

- **Atomic outcome:** GFM pipe tables parse and render — one plugin install, one prop addition, one observable result.
- **Failure boundary:** If remark-gfm fails to load, ReactMarkdown falls back to CommonMark (current behavior) — no regression risk.
- **Budget rationale:** Two files, ~15 diff lines, zero logic complexity. Well within XS budget.

---

## Execution Budget

```yaml
execution_budget:
  max_primary_files: 2
  max_changed_files: 3
  max_context_files: 4
  max_estimated_diff_lines: 350
  max_agent_invocations: 0
  max_tool_calls: 10
  max_expansions: 0
  max_context_chars: 15000
  max_implementor_tokens: 15000
```

---

## Context

```yaml
primary_files:
  - frontend/src/pages/Assistant.tsx
  - frontend/package.json

initial_context:
  - commit-specs/commit-77.md
  - frontend/src/pages/Assistant.tsx
  - frontend/package.json

forbidden:
  - backend/
  - hooks/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `frontend/package.json` | edit | Add `remark-gfm` to dependencies |
| `frontend/src/pages/Assistant.tsx` | edit | Import `remarkGfm` and pass as `remarkPlugins` prop to `ReactMarkdown` |
| `frontend/package-lock.json` | edit | Auto-generated lockfile update from npm install (override-approved) |

---

## Contract

- **Input:** Assistant response containing GFM pipe-table markdown (e.g. `| Header |\n|---|\n| Cell |`)
- **Output:** Rendered HTML `<table>` using the existing `markdownComponents` styles (border, padding, bg-gray-200 thead)
- **Default:** If `remark-gfm` is absent or fails to load, CommonMark parsing applies (current behavior — tables render as text)
- **Failure behavior:** No runtime failure possible — `remarkPlugins` is an optional array prop

---

## Environment Prerequisites

- Node.js and npm/yarn available for dependency installation
- `npm install` (or equivalent) run after `package.json` changes to install `remark-gfm`

---

## Verification Command

```powershell
cd frontend && npx tsc --noEmit && cd ..
```

---

## Focused Tests

- Happy path: Ask "what are our current shipments" in the assistant chat — response renders as a styled HTML table with borders, header row background, and aligned columns.
- Boundary path: Responses without tables (plain text, bullet lists, code blocks) continue rendering correctly — no regression.
- Regression: Existing `markdownComponents` styles (h1-h3, ul/ol, code/pre, strong) remain functional.

---

## Done When

- [ ] `remark-gfm` is listed in `frontend/package.json` dependencies.
- [ ] `Assistant.tsx` imports `remarkGfm` and passes `remarkPlugins={[remarkGfm]}` to `<ReactMarkdown>`.
- [ ] TypeScript compilation passes (`npx tsc --noEmit`).
- [ ] Pipe tables in assistant responses render as styled HTML tables in the browser.

---

## Developer Test Checkpoint

- **Ready now:** GFM markdown tables render properly in the assistant chat.
- **How to test:** Run `docker-compose up` and `cd frontend && npm install && npm run dev`. Log in as a manager. In the Assistant page, ask "what are our current shipments". The response should display a formatted table with borders and header styling — not raw pipe characters.
- **Expected result:** Shipment data appears in a clean HTML table with gray header row, bordered cells, and readable column alignment.
- **Still incomplete:** No other markdown rendering changes planned.

---

## Not In This Commit

- No changes to the backend response format or LLM prompt instructions.
- No additional markdown plugins (math, syntax highlighting, etc.) — future scope if needed.

---

## Return Contract

The implementor's final message must begin with this concise human summary:

```markdown
## Human Summary
**What I completed:** Plain-language description of the finished behavior.
**What changed:** Important files, interfaces, or behavior changed.
**What went wrong:** Problems encountered, or `None`.
**What remains:** Unfinished or deferred work, or `None`.
**Recommended next commit:** Suggested follow-up scope, or `None`.
**Developer attention:** Decisions, risks, or manual checks requiring attention, or `None`.
```

After the human summary, include the structured telemetry JSON required by the
generated delegation brief. If the commit cannot finish within its budget, also
include the `SPLIT_REQUIRED` report.
