# Commit 28 — `document-upload-routes` · Rex

**Phase:** 2B — Ingestion API
**Assignee:** Rex (Backend)
**Depends on:** C27 (document-ingestion)

**Sage + Mira run on this commit (new route with authenticated user input and file upload).**

---

## context

```
tier0:
  - .claude/agents/backend.md (Current State header only — first 50 lines)

tier1:
  - backend/app/api/v1/documents.py   # existing 501 stub to replace
  - backend/app/services/ingestion.py # C27 frozen contract
  - backend/app/dependencies.py       # require_role pattern
  - backend/app/main.py               # router is already registered

tier2:
  - manifesto-spec.md (§10 Document Ingestion)

forbidden:
  - frontend/
  - backend/app/services/
  - backend/app/models/
  - backend/alembic/

estimated_reads: 5
estimated_edits: 3   # documents.py, schema, route tests
fits_single_agent: true
```

---

## What

Expose a bounded manager/admin document API around the frozen ingestion contract. The
existing `documents.py` stub is edited, not recreated.

---

## Files to Create / Change

| File | Type | Description |
|---|---|---|
| `backend/app/api/v1/documents.py` | edit | Replace stub with upload/list/detail routes |
| `backend/app/schemas/document.py` | new | Safe document request/response schemas |
| `backend/tests/api/test_documents.py` | new | Role, validation, idempotency, and error tests |

No parser or embedding logic belongs in the route.

---

## Route Behavior

`POST /api/v1/documents`

- Requires manager or admin.
- Accepts multipart `file` and a validated, trimmed title.
- Enforces a configured byte limit while reading in chunks; never trusts
  `Content-Length`.
- Validates extension, declared MIME type, and detected file signature. Sanitizes the
  original filename and never treats it as a filesystem path.
- Computes SHA-256, resolves the checksum/profile idempotency key, and invokes ingestion.
- Returns `201` for a new ready document or `200` for an existing identical ready
  document. Returns a stable problem response for unsupported, corrupt, empty, too-large,
  or failed ingestion.

`GET /api/v1/documents`

- Requires manager or admin.
- Cursor-paginated and ordered by `(uploaded_at DESC, id DESC)`.
- Returns metadata and status, never embeddings, chunk contents, paths, or internal error
  details.

`GET /api/v1/documents/{id}`

- Returns one document's status and safe metadata, supporting eventual migration to a
  durable background ingestion worker without changing the read contract.

---

## Response Contract

Document responses include `id`, title, original filename, status, chunk count, uploader,
embedding profile, timestamps, and a safe failure code when applicable.

---

## Security and Reliability

- Authorization is checked before expensive parsing/provider calls.
- Known validation failures map to 4xx; normalized provider/ingestion failures map to 503;
  raw exceptions and secrets are never returned.
- A client disconnect cancels work where possible and leaves a retryable document state.
- Upload logs contain IDs, sizes, status, and latency, not document contents.

---

## Test Gate

- Role matrix, missing auth, extension/MIME/signature mismatch, size limit, empty input,
  duplicate upload, pagination, ownership metadata, and normalized failures.
- Assert ingestion is not called after authorization or validation failure.

---

## Done When

- [ ] Supported uploads are searchable only after status becomes `ready`
- [ ] Duplicate retries do not duplicate chunks
- [ ] Employee tokens receive 403 and no document metadata
- [ ] OpenAPI accurately describes multipart input and response/error schemas

---

## Handoffs Out

→ Aria (future document UI): list/detail responses expose safe document status and profile
metadata, never chunk text or embeddings.
