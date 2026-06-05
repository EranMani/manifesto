# Commit 15 — `stub-routes` · Rex

**Phase:** 1E — Service Stubs
**Assignee:** Rex (Backend)
**Depends on:** C14 (product-routes)

**Viktor wave runs on this commit (C15 is the 15th commit). Quinn is deferred — not active in Phase 1.**

---

## context

```
tier0:
  - .claude/agents/rex.md (Current State header only — first 50 lines)

tier1:
  - backend/app/main.py    # to register the two new routers

tier2: []

forbidden:
  - frontend/
  - backend/alembic/
  - backend/app/api/v1/   # existing routes — do not touch, just add new ones

estimated_reads: 1
estimated_edits: 3   # chat.py (new), documents.py (new), main.py (update)
fits_single_agent: true
```

---

## What

Register chat and document routes as stubs. They return 501 Not Implemented.
This reserves the URL space and ensures they appear in `/docs` for Phase 2 planning.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/chat.py` | new | Stub conversation + message endpoints, all return 501 |
| `backend/app/api/v1/documents.py` | new | Stub document upload endpoint, returns 501 |

---

## Files to Modify

| File | Change |
|---|---|
| `backend/app/main.py` | Register chat and documents routers |

---

## Stub Routes

```
# chat.py
POST /api/v1/chat/conversations         → 501
GET  /api/v1/chat/conversations         → 501
GET  /api/v1/chat/conversations/{id}/messages   → 501
POST /api/v1/chat/conversations/{id}/messages   → 501

# documents.py
POST /api/v1/documents                  → 501
GET  /api/v1/documents                  → 501
```

---

## Done When

- [ ] All stub routes return `{"detail": "Not implemented"}` with status 501
- [ ] All stub routes appear in `/docs`
- [ ] No existing routes broken by adding the new routers
