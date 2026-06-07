# Commit 26 — `document-upload-routes` · Rex

**Phase:** 2B — Ingestion Pipeline
**Assignee:** Rex (Backend)
**Depends on:** C25 (document-ingestion — `ingest_document()` must exist), Nova's cross-domain dependency finding from C25 (new `pyproject.toml` packages)

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header — first 50 lines)

tier1:
  - backend/app/services/ingestion.py   # Nova's C25 — ingest_document() contract
  - backend/app/api/v1/                 # existing route patterns to follow (e.g. products.py)
  - backend/app/dependencies.py         # require_role pattern

tier2:
  - manifesto-spec.md (§10 Document Ingestion — confirmation flow)

forbidden:
  - frontend/
  - backend/app/services/    # Nova's domain — call ingest_document(), do not edit it
  - backend/alembic/
```

---

## What

Routes for managers (any manager, not just admin) to upload policy documents and list
previously uploaded ones. Validates the upload, delegates to Nova's `ingest_document()`,
and returns the confirmation payload.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/documents.py` | new | `POST /api/v1/documents` (upload+ingest), `GET /api/v1/documents` (list) |
| `backend/app/schemas/document.py` | new | `DocumentUploadResponse`, `DocumentRead` Pydantic schemas |

Also: append the new router to `main.py` (`# routers registered below`), and apply
Nova's C25 dependency finding to `pyproject.toml` (PyMuPDF, python-docx).

---

## Route Behavior

```
POST /api/v1/documents
  - require_role("manager", "admin")
  - Validate file type (PDF, DOCX, TXT, MD) and size before calling ingestion
  - Call ingest_document(file_bytes, filename, title, uploaded_by=current_user.id, db)
  - Return { document_id, title, chunk_count }

GET /api/v1/documents
  - require_role("manager", "admin")
  - Return list of policy_documents: id, title, uploaded_by, uploaded_at
```

---

## Done When

- [ ] `POST /api/v1/documents` accepts a multipart upload, validates type, ingests, returns `{document_id, title, chunk_count}`
- [ ] `GET /api/v1/documents` returns the document list, manager/admin only
- [ ] Both routes reject employee-role JWTs with 403
- [ ] `pyproject.toml` updated with PyMuPDF + python-docx per Nova's C25 finding; `uv sync` succeeds
- [ ] Router registered in `main.py`

---

## Handoffs Out

→ Aria (future — if a document-management UI is added): `GET /api/v1/documents` returns
`DocumentRead[]` with `{id, title, uploaded_by, uploaded_at}`. Not in scope for Phase 2's
chat-focused commits — noted for later reference only.
