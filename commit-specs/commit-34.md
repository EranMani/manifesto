# Commit 34 — `citations-ui` · Aria

**Phase:** 2D — Source Provenance UI
**Assignee:** Aria (Frontend)
**Depends on:** C31 (conversation-persistence), C32 (policy-chat-ui), C33 (conversation-sidebar-ui)

**Sage + Mira run on this commit (renders persisted source metadata beneath user-visible answers).**

---

## context

```
tier0:
  - .claude/agents/frontend.md (Current State header only — first 50 lines)

tier1:
  - frontend/src/components/chat/StreamingMessage.tsx  # C32 source slot/data
  - frontend/src/api/chat.ts                           # live source type
  - frontend/src/api/conversations.ts                  # historical source type

tier2:
  - manifesto-spec.md (§7 policy citations)

forbidden:
  - backend/

estimated_reads: 4
estimated_edits: 3   # citations component, stream integration, tests
fits_single_agent: true
```

---

## What

Render the structured source provenance delivered by streaming and history APIs. This is
not title decoration: the UI must preserve source identity and location accurately.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `frontend/src/components/chat/Citations.tsx` | new | Semantic structured source list |
| `frontend/src/components/chat/StreamingMessage.tsx` | edit | Render sources for completed messages |
| `frontend/src/components/chat/__tests__/citations.test.tsx` | new | Live/history, dedupe, safety, and state tests |

---

## Behavior

- Display sources only after the assistant message reaches a terminal completed state.
- De-duplicate by stable document/chunk identity, not title text.
- Preserve retrieval/citation order.
- Show document title plus page or section when available, for example
  `Employee Handbook v3 - page 12`.
- Do not expose retrieval scores, internal IDs, raw chunk text, or storage paths.
- Do not create a document link until an authorized document-view endpoint exists.
- Render no source block for an empty source list or an abstention.
- Historical completed messages use the same component and data shape as live messages;
  citations must survive reload.
- Failed/cancelled partial messages do not present sources as authoritative.

---

## Accessibility and Safety

- Use a semantic labelled list with clear "Sources" text.
- Treat titles/sections as plain text.
- Handle deleted-source snapshots gracefully without claiming the document is currently
  available.

---

## Test Gate

- Live completion, historical reload, empty list, duplicate IDs, same-title/different-ID
  documents, page/section formatting, deleted snapshots, and failed/cancelled messages.

---

## Done When

- [ ] Live and reloaded messages render identical source provenance
- [ ] Duplicate titles do not collapse distinct sources
- [ ] No empty or misleading source block appears
- [ ] The Phase 2 UI passes type-check, component tests, and one end-to-end
  upload -> ask -> stream -> reload -> citations scenario.

---

## Handoffs Out

*(none — this closes the Phase 2 Policy RAG user experience)*
