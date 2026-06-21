# Commit 83 - `client-model-and-api` - Rex

**Phase:** Phase 3
**Owner:** rex
**Depends on:** C82
**Estimated diff lines:** 200
**Primary behavior count:** 1
**Developer test milestone:** no

---

## Primary Behavior

Client CRUD API endpoints exist with a badge_color field (hex string) for visual identification of physical shipments.

---

## Semantic Fit Review

- **Atomic outcome:** The client entity is independently usable through four REST endpoints; no other feature depends on partial client support.
- **Failure boundary:** Client endpoints are self-contained — failure here does not affect vendors, shipments, or products.
- **Budget rationale:** Four files following the exact vendor model/schema/routes pattern. No migration (deferred to C84). Estimated 200 diff lines.

---

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

---

## Context

```yaml
primary_files:
  - backend/app/models/client.py
  - backend/app/api/v1/clients.py

initial_context:
  - commit-specs/commit-83.md
  - backend/app/models/vendor.py
  - backend/app/schemas/vendor.py
  - backend/app/api/v1/vendors.py
  - backend/app/main.py

forbidden:
  - frontend/
  - hooks/
  - .claude/agents/
```

---

## Files To Modify Or Add

| File | Type | Purpose |
|---|---|---|
| `backend/app/models/client.py` | add | Client model with id, name, contact, email, country, badge_color, created_at |
| `backend/app/schemas/client.py` | add | ClientCreate, ClientRead, ClientUpdate Pydantic schemas |
| `backend/app/api/v1/clients.py` | add | CRUD routes: list, get, create, update, delete |
| `backend/app/main.py` | edit | Register client_router at /api/v1/clients |

---

## Contract

### Client Model (`backend/app/models/client.py`)

SQLAlchemy model mirroring Vendor with one addition:
- `id`: UUID primary key, server_default gen_random_uuid()
- `name`: String, not null
- `contact`: String, nullable
- `email`: String, nullable
- `country`: String, nullable
- `badge_color`: String, not null, server_default `'#6366f1'` (indigo)
- `created_at`: DateTime(timezone=True), server_default now()
- Table name: `clients`

### Schemas (`backend/app/schemas/client.py`)

- `ClientCreate`: name (str, required), contact/email/country (str | None, optional), badge_color (str, default '#6366f1')
- `ClientRead`: all fields including id and created_at, model_config from_attributes=True
- `ClientUpdate`: all fields optional (str | None)

### Routes (`backend/app/api/v1/clients.py`)

Mirror vendor routes exactly:
- `GET /api/v1/clients` → list all clients, requires admin|manager
- `GET /api/v1/clients/{client_id}` → get one, 404 if not found
- `POST /api/v1/clients` → create, 201
- `PUT /api/v1/clients/{client_id}` → update, 404 if not found
- `DELETE /api/v1/clients/{client_id}` → delete, 204, 404 if not found, 409 if client has shipments (after C84 adds client_id to shipments)

Delete conflict check: query `Shipment.client_id == client_id` — if any exist, return 409 with "Client has existing shipments". Import Shipment model. Since client_id doesn't exist on Shipment yet (added in C84), the delete check should be written but will only be exercisable after C84.

### Router Registration (`backend/app/main.py`)

Add import and `app.include_router(client_router, prefix="/api/v1/clients", tags=["clients"])`.

---

## Environment Prerequisites

- Backend running via `docker compose up`
- Database with existing schema (migration for clients table comes in C84)

---

## Verification Command

```powershell
npx tsc --noEmit --project frontend/tsconfig.json 2>$null; python -c "from app.models.client import Client; from app.schemas.client import ClientCreate, ClientRead, ClientUpdate; from app.api.v1.clients import router; print('imports ok')"
```

---

## Focused Tests

- Happy path: Client model, schemas, and routes import without errors; route functions have correct signatures.
- Boundary path: Delete route includes 409 conflict check for shipments.
- Regression: Existing vendor routes unaffected; main.py still registers all prior routers.

---

## Done When

- [ ] Client model with badge_color field exists.
- [ ] ClientCreate/Read/Update schemas exist.
- [ ] CRUD routes for clients are registered in main.py.
- [ ] All Python imports resolve without errors.

---

## Developer Test Checkpoint

- **Next milestone:** C88 — client API is not testable against the database until C84 creates the table via migration.

---

## Not In This Commit

- Alembic migration to create the clients table — C84.
- models/__init__.py registration — C84.
- Frontend client pages — C88.

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
