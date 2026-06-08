# Notes for Future

Important technical findings discovered while reviewing and learning the project.

## Authentication

### Password verification may block the async event loop

**Location:** `backend/app/api/v1/auth.py`

The asynchronous login endpoint calls `verify_password(...)` directly. Password
verification uses bcrypt, which is intentionally CPU-intensive and synchronous.
Under many simultaneous login attempts, it may block the event-loop thread and
increase latency for unrelated requests handled by the same worker.

Current pattern:

```python
if not verify_password(request.password, user.password_hash):
    ...
```

Consider running password verification in a worker thread:

```python
from starlette.concurrency import run_in_threadpool

password_valid = await run_in_threadpool(
    verify_password,
    request.password,
    user.password_hash,
)
```

This improves concurrency while bcrypt is running, but does not make bcrypt
itself faster. Capacity still depends on CPU resources, worker count, rate
limiting, and the configured bcrypt cost.

## FastAPI Dependencies

### Role checking does not require asynchronous I/O

`require_role(...)` is a synchronous dependency factory. It returns the
request-time `_check_role` dependency configured with the accepted roles.

FastAPI resolves and awaits `get_current_user` before passing the resulting
`User` object into `_check_role`. The role comparison itself is a small
in-memory operation and does not need to be asynchronous.

## API Design

### Partial updates currently use PUT semantics

The CRUD routes use `PUT /{id}` together with:

```python
payload.model_dump(exclude_unset=True)
```

This updates only fields explicitly provided by the client, which behaves like
a partial update. By HTTP convention, partial updates are normally represented
by `PATCH`, while `PUT` normally replaces the complete resource.

Consider making the API semantics consistent by either:

1. Changing these partial-update routes from `PUT` to `PATCH`.
2. Keeping `PUT`, but requiring and replacing the complete resource.

## User Administration

### Users are deactivated instead of deleted

The admin API intentionally does not provide `DELETE /users/{id}`. The product
specification defines user management as creating and deactivating accounts.
Admins deactivate users by updating `is_active` to `false`.

Keeping the user record:

- Preserves ownership and audit history.
- Avoids breaking records that reference the user.
- Allows the account to be reactivated.
- Prevents the former user from passing `get_current_user` on future requests.

This is better described as account deactivation than hard deletion.

### An admin can currently deactivate their own account

**Location:** `backend/app/api/v1/admin.py`

The update route prevents an admin from changing their own role away from
`admin`, but it does not prevent the same admin from setting their own
`is_active` field to `false`.

Consider adding a self-deactivation guard similar to the self-demotion guard.
Depending on product requirements, also consider protecting the system from
deactivating or demoting the final active administrator.

## SQLAlchemy

### `refresh()` reloads database row values

After creating a model, the common lifecycle is:

```python
db.add(user)
await db.commit()
await db.refresh(user)
```

- `add()` places the Python model instance in the current SQLAlchemy session.
- `commit()` persists the transaction to the database.
- `refresh()` reloads the current row values from the database into the Python
  model instance.

This is useful for database-generated values such as `id`, `created_at`, and
server defaults like `is_active`.

`refresh()` does not retrieve transaction metadata such as a transaction ID,
execution duration, or affected-row count. It retrieves the latest column
values for the model's database row.

### Keep the ORM object lifecycle distinct from response serialization

The SQLAlchemy model instance is already a Python object before it is added,
committed, or refreshed:

```python
product = Product(...)
```

The lifecycle is:

```text
Create ORM object in Python
        |
        v
db.add(product)       Track it in the SQLAlchemy session
        |
        v
db.commit()           Persist the transaction in PostgreSQL
        |
        v
db.refresh(product)   Reload current row values into the same ORM object
        |
        v
return product        FastAPI/Pydantic validates and serializes ProductRead
```

For updates, the object was loaded from the database first, but the final steps
are the same:

```python
setattr(product, field, value)
await db.commit()
await db.refresh(product)
return product
```

The responsibilities should not be confused:

- SQLAlchemy's `refresh()` synchronizes the ORM object's attributes with the
  database row.
- Pydantic's response model converts and validates those attributes according
  to the public API schema.
- FastAPI serializes the validated response to JSON.

`refresh()` can be especially important after inserts or updates involving
server-generated defaults, triggers, computed values, timestamps, or other
database-side changes. It is not always strictly required when every resulting
value is already known locally, but using it ensures the response reflects the
database's current values.

## Authentication Architecture

### Stateless JWT authentication is a trade-off

The project uses bearer JWTs rather than traditional server-side sessions.
FastAPI does not store the JWT as a session. The client stores it, sends it in
the `Authorization: Bearer <token>` header, and the backend validates it on
each protected request.

JWT advantages include convenient API usage, no central session store, and
easier horizontal scaling. Disadvantages include harder immediate revocation,
continued access if a token is stolen before expiration, and additional
refresh-token complexity.

Server-side sessions can provide simpler immediate logout and revocation for a
single browser application, especially when the session ID is stored in an
`HttpOnly`, `Secure`, and appropriately configured `SameSite` cookie. They
require server-side session storage and CSRF protection.

JWT is not automatically preferable to server sessions. The decision depends
on whether the API serves only the browser application or also mobile and
third-party clients.

### Review where the frontend stores the access token

The frontend's token storage should receive a targeted security review. If the
JWT is stored in JavaScript-accessible storage such as `localStorage`, an XSS
vulnerability could read and exfiltrate it.

Consider whether an `HttpOnly` secure cookie would better fit the product's
client model, while accounting for the required CSRF protections.

## Database Relationships

### Foreign keys and ORM relationships serve different purposes

The current models define database foreign keys without SQLAlchemy
`relationship()` attributes. For example, `Product.shipment_id` references
`Shipment.id`.

A foreign key is sufficient to establish the relationship in PostgreSQL. It:

- Prevents a product from referencing a nonexistent shipment.
- Enables joins between products and shipments.
- Supports database behavior such as `ON DELETE CASCADE`.
- Keeps relational integrity enforced even outside the Python application.

Related rows can still be loaded explicitly:

```python
select(Product).where(Product.shipment_id == shipment_id)
```

The current product-to-shipment cardinality is:

```text
One Shipment -> Many Products
One Product  -> One Shipment
```

This is not a many-to-many relationship because each product row contains only
one required `shipment_id`.

### What SQLAlchemy `relationship()` would add

ORM relationships provide Python object navigation:

```python
shipment.products
product.shipment
```

They do not create or replace the database foreign key. Both are often used
together: the foreign key enforces the database relationship, while
`relationship()` makes related object access more convenient in application
code.

Benefits of adding `relationship()` include:

- More natural object-oriented navigation.
- Convenient nested response construction.
- Centralized cascade and bidirectional mapping configuration.

Trade-offs include:

- Loading strategy must be chosen deliberately.
- Lazy loading can create hidden extra queries, including N+1 query problems.
- Implicit lazy loading is awkward or unsafe with async SQLAlchemy.
- ORM cascade configuration can overlap with database `ON DELETE CASCADE`.
- Bidirectional model references require careful import and typing setup.

With async SQLAlchemy, prefer explicit eager loading when relationships are
needed:

```python
select(Shipment).options(selectinload(Shipment.products))
```

If ORM delete cascades are added alongside database `ON DELETE CASCADE`,
consider `passive_deletes=True` and configure ownership intentionally.

The project does not document an explicit decision to omit ORM relationships.
Their absence appears to be a reasonable simplification because the current
routes use direct queries and do not return nested shipment/product objects.
Add them when object navigation or nested loading provides concrete value.

## Configuration

### Why the project uses `pydantic-settings`

`backend/app/core/config.py` defines one typed `Settings` object that loads
configuration from environment variables and the `.env` file.

Benefits include:

- Centralized access through values such as `settings.DATABASE_URL`.
- Automatic conversion of environment strings into types such as `int`.
- Required fields fail at application startup when missing.
- Invalid configuration fails early with clear validation errors.
- Defaults can be declared for non-secret settings.
- Environment variables can override defaults without changing source code.
- Custom validation can enforce security requirements, such as the minimum
  `SECRET_KEY` length.
- Development, test, and production can use the same code with different
  configuration.
- Secrets do not need to be hard-coded in the repository.

Fields without defaults, such as `DATABASE_URL` and `SECRET_KEY`, are required.
Fields with defaults, such as `ALGORITHM`, can be overridden by the
environment.

### `.env` path resolution depends on the working directory

The configuration currently uses:

```python
class Config:
    env_file = ".env"
```

The relative `.env` path can depend on the process's working directory. Docker
Compose already injects the root `.env` values through its `env_file` setting,
but manually starting the backend from another directory may produce different
file-discovery behavior.

If this becomes unreliable, consider resolving the `.env` path explicitly or
standardizing the directory from which backend commands are run.

## SQLAlchemy Database Core

### Engine, session factory, and sessions have different responsibilities

`backend/app/core/database.py` creates an asynchronous SQLAlchemy engine:

```python
engine = create_async_engine(settings.DATABASE_URL, echo=False)
```

The engine knows how to connect to the database and manages database
connections through a connection pool. It does not configure FastAPI or
Uvicorn worker processes. Pool settings such as `pool_size`, `max_overflow`,
and `pool_timeout` can be configured separately when needed.

`echo=False` disables SQL statement logging from the engine.

The following value is a session factory, not one global database session:

```python
AsyncSessionLocal = async_sessionmaker(
    engine,
    expire_on_commit=False,
)
```

Calling `AsyncSessionLocal()` creates an `AsyncSession`. A session executes
queries, tracks ORM objects, and groups database changes into transactions. It
borrows connections from the engine's pool.

The `get_db` FastAPI dependency creates and closes a session around a request:

```python
async with AsyncSessionLocal() as session:
    yield session
```

### Meaning of `expire_on_commit=False`

This setting does not prevent database rows or frontend data from being
deleted. It keeps already-loaded ORM attributes available in Python after a
commit.

With SQLAlchemy's expiration behavior enabled, committed ORM attributes may be
marked as expired and require a database reload on their next access.
Unexpected implicit reloads are especially awkward in async code because
database I/O must normally happen through an explicit `await`.

Keeping attributes unexpired does not guarantee they still match the latest
database state. `db.refresh(model)` can explicitly reload current row values.

### `DeclarativeBase` registers ORM model mappings

The project defines one shared model base:

```python
class Base(DeclarativeBase):
    pass
```

Models such as `User`, `Shipment`, and `Product` inherit from `Base`. This tells
SQLAlchemy to map those Python classes to database tables and collects their
definitions in:

```python
Base.metadata
```

The metadata includes table names, columns, types, primary keys, foreign keys,
constraints, and indexes.

`DeclarativeBase` defines the Python ORM mappings, but it does not by itself
guarantee that the tables exist in PostgreSQL. Alembic uses `Base.metadata` to
support schema migrations, while migration scripts create and modify the
actual database tables.

## Security Helpers

### Bcrypt password flow

`hash_password()` converts the plain Python string to bytes because bcrypt
operates on bytes:

```text
"password" -> b"password"
```

`bcrypt.gensalt()` creates a random salt and includes the bcrypt cost
configuration. Because the salt is random, hashing the same password twice
normally produces different hashes.

After bcrypt returns hash bytes, Python's `.decode()` converts those bytes into
a string suitable for database storage. It does not reverse or decrypt the
password hash. Bcrypt hashes are designed to be one-way.

`verify_password()` uses `bcrypt.checkpw()` with the submitted plain password
and stored hash. Bcrypt reads the salt and cost from the stored hash and checks
whether the submitted password corresponds to it.

### JWT mental model

The login route provides claims such as:

```python
{"sub": user_id, "role": user_role}
```

`create_access_token()` copies that dictionary, adds an `exp` expiration claim,
and calls `jwt.encode()` with the server's secret key and configured algorithm.
The result is a JWT string.

Conceptually:

```text
header + payload claims
        |
        | sign using SECRET_KEY and ALGORITHM
        v
header.payload.signature
```

The token contains the header, payload, and signature. It does not contain the
server's secret key.

JWT payload data is encoded, not encrypted. Someone holding the token can
usually read claims such as `sub`, `role`, and `exp`. Sensitive secrets should
not be placed in the payload.

The signature makes unauthorized changes detectable. If someone changes the
role or subject without knowing the secret key, the existing signature will no
longer match.

`decode_token()`:

1. Parses the token.
2. Restricts validation to the configured algorithm.
3. Recalculates and verifies the signature using the server's secret key.
4. Validates the `exp` expiration claim.
5. Returns the payload dictionary when valid.
6. Raises `401 Unauthorized` when the token is invalid or expired.

Token decoding does not merely check whether a secret key exists. It proves
that the token was signed with the expected secret and has not been modified,
subject to the security of the key and algorithm.

The configured secret is required to be at least 32 characters in this
project. It is not limited to letters and should be a long, cryptographically
random value.

## Shipment API

### Shipment update support is missing

The shipment API currently implements list, read, create, and delete routes,
but it has no `PUT` or `PATCH` endpoint and no `ShipmentUpdate` schema.

There is no documented business rule stating that shipments are immutable.
Additionally, `commit-specs/commit-13.md` describes the shipment API as "Full
CRUD," which includes update behavior. This appears to be an implementation
gap or specification mismatch rather than an intentional immutability rule.

Potential mutable fields include:

- `vendor_id`
- `arrived_at`
- `notes`

A partial update schema could make each field optional and use
`model_dump(exclude_unset=True)`. If `vendor_id` is provided, the route should
verify that the referenced vendor exists before updating the shipment.

For nullable fields such as `notes`, `exclude_unset=True` preserves an
important distinction:

- Omitted `notes` leaves the existing value unchanged.
- Explicit `"notes": null` clears the existing value.

## Schema Design

### Resource IDs and foreign-key IDs have different roles

A create schema normally omits the new resource's own ID when PostgreSQL
generates it. For example, `VendorCreate` does not accept `Vendor.id`.

A create schema may still require foreign-key IDs. `ShipmentCreate` accepts
`vendor_id` because the client must identify the existing vendor associated
with the new shipment.

When creating a shipment:

```text
Shipment.id        -> generated by PostgreSQL
Shipment.vendor_id -> supplied by the client; references Vendor.id
```

The `vendor_id` is primarily required to store and enforce the database
relationship. It is not required merely to convert a SQLAlchemy model into a
Pydantic response.

Because `ShipmentRead` inherits from `ShipmentBase`, the current response
contains the foreign-key value:

```json
{
  "id": "shipment-id",
  "vendor_id": "vendor-id"
}
```

It does not automatically contain the complete vendor object. A nested vendor
response would require:

- Loading the related vendor through an explicit join or ORM relationship.
- Defining a nested response schema such as `vendor: VendorRead`.

In short, the foreign key stores the association, while the Pydantic schema
controls how that association is exposed through the API.

## FastAPI Application Hardening

### Restrict CORS origins outside local development

The application currently configures:

```python
allow_origins=["*"]
```

This allows browser JavaScript from any origin to call the API, subject to the
rest of the CORS configuration and authentication design. It is convenient
during development when the frontend may run from changing local ports or
hosts, but production should normally allow only known frontend origins.

For example:

```python
allow_origins=[
    "https://app.example.com",
    "https://admin.example.com",
]
```

The change should happen through environment-specific configuration before the
API is exposed to untrusted networks. Development can allow localhost origins;
staging and production should list their exact deployed frontend origins.

CORS is a browser access control and is not a replacement for authentication
or authorization. Non-browser clients can still call the API directly.
Restricting CORS reduces unintended cross-origin browser access and becomes
especially important if authentication later uses cookies or enables
credentials.

### Separate liveness, readiness, and dependency health

The current root endpoint only proves that FastAPI can return a response. It
does not verify PostgreSQL, Ollama, model availability, or other dependencies.

Consider separate checks:

- **Liveness:** the process and event loop can respond. Keep this lightweight;
  failure may trigger a container restart.
- **Readiness:** the instance can serve real traffic, including required
  database connectivity. Failure should remove it from traffic without
  necessarily restarting it.
- **Dependency diagnostics:** report or monitor PostgreSQL, Ollama, configured
  models, and external providers separately.

Do not make a liveness endpoint depend on every external service. A temporary
database or model outage could otherwise cause unnecessary restart loops.
Dependency checks should use strict timeouts and avoid expensive work.

Docker Compose currently defines a PostgreSQL health check but no backend
health check or restart policy based on the FastAPI endpoint. Any restart or
traffic-routing behavior must be explicitly configured in Docker, Kubernetes,
or the chosen deployment platform.

### Add targeted request observability and protection

Potential production-hardening capabilities include:

- Structured request logging.
- Request or correlation IDs.
- Request latency metrics.
- Error and status-code metrics.
- Rate limiting, especially for login, uploads, chat, and expensive AI calls.
- Request body and upload-size limits.
- Security headers.
- Centralized unexpected-error handling.
- Distributed tracing when multiple services justify it.

These do not all need to be custom FastAPI middleware. Prefer the most suitable
layer:

- Reverse proxy or API gateway for coarse rate limits, body limits, TLS, and
  some security headers.
- FastAPI middleware for application-aware timing, request IDs, and logging.
- Metrics or tracing libraries for observability.
- Route-level controls for limits that depend on user identity, operation cost,
  or business rules.

Avoid logging passwords, bearer tokens, authorization headers, uploaded
document contents, or other sensitive data. Middleware also runs on every
request, so keep it lightweight and measure its overhead.

These capabilities are useful for production reliability and security, but a
"perfect" development check does not require implementing every option.
Prioritize them based on threat model, deployment architecture, and expected
traffic. Authentication rate limiting, safe logging, health separation, and
restricted production CORS are strong early priorities.

## Deletion Strategy

### Cascading hard deletes can remove an entire data tree

The current foreign keys create this database cascade:

```text
Vendor
  -> Shipments
       -> Products
```

Deleting a vendor directly in PostgreSQL can delete all of its shipments and
all products in those shipments in the same transaction.

The vendor API currently blocks deletion when shipments exist, but the database
still uses `ON DELETE CASCADE`. Direct SQL or another service could therefore
bypass the route's safety rule. Review whether the database should instead use
`RESTRICT` or `NO ACTION` so every access path follows the same policy.

### Prefer soft deletion for historical business records when appropriate

For records needed for audits, analytics, recovery, or relationship history,
consider a timestamp:

```python
deleted_at: Mapped[datetime.datetime | None]
```

`deleted_at` is often more informative than only `is_active` because it records
when the record was archived.

Soft deletion is not always correct. Hard deletion may still be appropriate
for disposable data or when privacy and retention requirements demand actual
removal. Soft deletion also increases storage, filtering, uniqueness, and
restoration complexity.

### Soft deletion does not trigger `ON DELETE CASCADE`

Changing `vendor.deleted_at` is an SQL `UPDATE`, not a `DELETE`. PostgreSQL will
not automatically update or soft-delete shipments and products.

Two possible designs are:

1. Mark only the vendor deleted and hide descendants through queries.
2. Add deletion state to every level and cascade soft deletion in application
   logic.

For this project, marking only the vendor and preserving unchanged historical
shipments and products is likely the simpler default. Restoring the vendor can
make the historical tree visible again without rewriting child rows.

### Parent-aware filtering

Normal shipment queries can hide rows whose parent vendor is soft-deleted:

```python
select(Shipment).join(
    Vendor,
    Shipment.vendor_id == Vendor.id,
).where(
    Vendor.deleted_at.is_(None)
)
```

Product queries may need to traverse both parent levels:

```python
select(Product).join(
    Shipment,
    Product.shipment_id == Shipment.id,
).join(
    Vendor,
    Shipment.vendor_id == Vendor.id,
).where(
    Vendor.deleted_at.is_(None)
)
```

This does not require SQLAlchemy `relationship()` attributes. Foreign keys and
explicit joins are sufficient.

### Centralize visibility rules

Once soft deletion is introduced, repeating these joins and filters manually
in every endpoint creates a risk of accidentally exposing archived data.

Use repository or query-builder functions such as:

```python
def visible_shipments_query():
    return (
        select(Shipment)
        .join(Vendor, Shipment.vendor_id == Vendor.id)
        .where(Vendor.deleted_at.is_(None))
    )
```

Then extend the shared query for individual operations:

```python
visible_shipments_query().where(Shipment.id == shipment_id)
```

Provide clearly named alternatives for privileged historical access, such as
`all_shipments_query()`. This makes the difference between normal visibility
and audit/admin access explicit.

Repository functions are strongly recommended for this project's current size,
though service-layer queries, SQLAlchemy global criteria, database views, or
row-level security are possible alternatives for more complex systems.

Before implementing soft deletion, define:

- Whether descendants are hidden or independently archived.
- Who may view archived data.
- Whether restoring a parent restores descendant visibility.
- How unique fields behave after deletion.
- Whether hard deletion is ever allowed and by whom.

## Database Indexes

### Message history uses a composite index

The message model defines:

```python
Index(
    "ix_messages_conversation_created",
    "conversation_id",
    "created_at",
)
```

This is a composite index ordered first by `conversation_id` and then by
`created_at`. It is designed for the common chat-history query:

```python
select(Message)
.where(Message.conversation_id == conversation_id)
.order_by(Message.created_at)
```

It allows PostgreSQL to locate messages for one conversation and return them
in chronological order without scanning and sorting the full messages table.

This index does not optimize lookup by `Message.id`. The primary key already
creates an index for ID-based lookup.

Column order matters. An index on `(conversation_id, created_at)` is effective
for filtering by `conversation_id` and optionally ordering or filtering by
`created_at`. It is generally less useful for queries that search only by
`created_at`.

### Index trade-offs

Indexes provide:

- Faster reads for matching query patterns.
- Faster ordering when the index order matches the query.

They cost:

- Additional disk space.
- Slower inserts because new index entries must be created.
- Slower updates when indexed values change.
- Slower deletes because index entries must be removed.

Indexes should support real query patterns rather than being added to every
column. For chat messages, this composite index is a good trade-off because
conversation history is frequently read in order, while existing messages are
rarely updated.

## Remaining Model Review

### Understand and validate vector embedding storage

`PolicyChunk.embedding` uses:

```python
Vector(1536)
```

This stores a 1,536-dimensional embedding for semantic similarity search. The
embedding model must always produce the same dimension expected by the column.

The initial migration creates an IVFFlat index using cosine-distance operators.
Review and document:

- Which embedding provider and model produce the vectors.
- Why the expected dimension is 1,536.
- How cosine similarity and distance are used by retrieval queries.
- IVFFlat speed, recall, training-data, and `lists` configuration trade-offs.
- What migration is required if the embedding model or dimension changes.

The IVFFlat index is created explicitly in the migration because this
PostgreSQL-specific index configuration is not represented by the current
model declaration.

### `updated_at` does not currently update automatically

`Conversation.updated_at` has only:

```python
server_default=text("now()")
```

This sets the value when the row is inserted. It does not automatically change
whenever the conversation is updated.

If the field is intended to represent the most recent modification, update it
through application logic, SQLAlchemy `onupdate`, or a database trigger.
Choose one ownership mechanism and verify that bulk updates also follow it.

### Foreign-key deletion policies are inconsistent

Some foreign keys cascade:

- Vendor -> shipments
- Shipment -> products
- User -> conversations
- Conversation -> messages
- Policy document -> policy chunks

Other user references, including `Product.added_by` and
`PolicyDocument.uploaded_by`, do not specify `ondelete`. PostgreSQL therefore
uses its default `NO ACTION` behavior and may prevent hard deletion of a
referenced user.

Review every relationship and explicitly choose among cascade, restrict/no
action, set null, or soft deletion based on record ownership and audit needs.

### Product quantity permits negative values

The current model and schema accept any integer for `quantity`, including
negative values.

If negative inventory is not meaningful, validate it in both layers:

- Pydantic input validation for immediate API feedback.
- A database `CheckConstraint("quantity >= 0")` for integrity across all write
  paths.

### Add intentional input and storage length limits

Most text columns use unrestricted `String`, and request schemas generally do
not define maximum lengths. PostgreSQL can store these values, but application
limits may still be needed for:

- Names
- Emails
- Titles
- Notes and descriptions
- Chat content
- File paths

Limits help control accidental or abusive payloads, storage growth, and UI
problems. Choose limits from product requirements rather than applying one
arbitrary size everywhere.

### Review case sensitivity for unique values

PostgreSQL uniqueness on ordinary string columns is generally case-sensitive.
Values such as these may be treated as distinct:

```text
User@example.com
user@example.com
```

Decide whether user emails and category names should be case-insensitive.
Potential approaches include normalization before storage, PostgreSQL `citext`,
or a unique index on a normalized expression such as `lower(email)`.

Normalization and the database constraint should agree so concurrent requests
cannot create logical duplicates.

### Models and migrations must remain aligned

SQLAlchemy models describe the desired Python mappings. Alembic migration
scripts create and alter the actual PostgreSQL schema.

Changing a model alone does not update an existing database. Every schema
change should include and verify an Alembic migration, including constraints,
foreign-key actions, indexes, defaults, and vector configuration.

## Alembic

### `env.py` connects model metadata to migration execution

Alembic uses:

```python
target_metadata = Base.metadata
```

All imported model classes that inherit from the shared `Base` register their
table definitions in this metadata. The import below is therefore important:

```python
from app.models import *
```

If a model is not imported before metadata is inspected, Alembic
autogeneration may not see its table.

`env.py` also configures:

- Online migration execution against a real database connection.
- Offline SQL generation using only a configured database URL.
- The bridge between the async SQLAlchemy engine and Alembic's synchronous
  migration operations.
- Alembic logging.

The functions are mostly standard Alembic plumbing, but they are project-owned
configuration rather than untouchable internals. Edit them when the project
needs custom autogeneration filters, naming conventions, multiple databases,
schema selection, environment URL handling, or custom type comparison.

Normal schema work usually belongs in generated and reviewed files under
`alembic/versions/`.

### Async migration execution

The application creates an `AsyncEngine`, and `env.py` currently imports and
reuses that same engine:

```python
from app.core.database import engine
```

Online migrations open an async connection and call:

```python
await connection.run_sync(do_run_migrations)
```

This lets Alembic's synchronous migration operations run through the async
connection. Alembic does not inherently require an async engine; projects may
instead use a separate synchronous migration engine. Reusing the application
engine is a valid project choice.

### Use one environment-driven database URL

The project currently has two possible database URL sources:

- Online mode imports the application engine, which uses
  `settings.DATABASE_URL`.
- Offline mode reads `sqlalchemy.url` from `alembic.ini`.

The `alembic.ini` URL is hard-coded with local development credentials. These
two values can drift apart, causing online and offline commands to target
different databases. Hard-coded credentials also create configuration and
security risks.

Configure Alembic so both online and offline modes derive their URL from the
same environment-driven settings source. For example, `env.py` can load the
application setting and apply it to Alembic's config before either mode runs:

```python
config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)
```

Then remove the real credential-bearing URL from `alembic.ini` or replace it
with a non-secret placeholder.

Before running migrations, especially in staging or production, print or
otherwise verify the target host and database without exposing passwords. This
reduces the risk of applying migrations to the wrong environment.

### Alembic is version control for database schema

Alembic versions schema changes, not application data. The normal lifecycle is:

```text
Edit SQLAlchemy model
        |
        v
Generate an Alembic revision
        |
        v
Review and correct the migration
        |
        v
Apply it to the database
        |
        v
Commit the model and migration together
```

From the `backend` directory, the main commands are:

```powershell
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
uv run alembic current
uv run alembic history
uv run alembic downgrade -1
```

Autogeneration compares `Base.metadata` with the current database schema. It is
a starting point, not a guarantee of correctness. Always review generated
operations, especially for column renames, populated non-null columns, custom
PostgreSQL types, extensions, vector indexes, constraints, and data changes.

A rename may be incorrectly generated as dropping the old column and creating
a new one, which can destroy data. Express renames and other intent-sensitive
operations explicitly.

### Structure of a migration revision

Each revision has identifiers such as:

```python
revision = "0001_initial"
down_revision = None
```

`revision` identifies the migration. `down_revision` points to its parent and
forms the ordered migration graph. The first migration has no parent.

`upgrade()` moves the schema forward. `downgrade()` defines how to move it
backward when a safe reversal exists.

Alembic stores the database's applied revision in its `alembic_version` table.
It uses this value to apply only pending migrations.

### What `0001_initial.py` does

The first migration is the versioned recipe for building the initial schema
from an empty PostgreSQL database. It is not a database dump and contains no
business data.

Its `upgrade()`:

- Enables `vector` for pgvector functionality.
- Enables `pgcrypto` for `gen_random_uuid()`.
- Creates tables in foreign-key dependency order.
- Creates primary keys, foreign keys, unique constraints, check constraints,
  defaults, and indexes.
- Converts the policy embedding column to `vector(1536)`.
- Creates the PostgreSQL-specific IVFFlat cosine-distance index.

Tables are created parent-first so referenced tables already exist. The
`downgrade()` drops children before parents to avoid foreign-key conflicts.

The downgrade intentionally does not remove PostgreSQL extensions. This can be
appropriate because other database objects may depend on them.

### Production migration requirements

Before treating migrations as production-ready, plan for:

- Tested database backups and restore procedures.
- Applying and verifying migrations in staging first.
- Recording and checking the exact target database and current revision.
- Deployment ordering between backward-compatible application code and schema
  changes.
- Lock duration and table-scan impact on large tables.
- Transaction behavior and operations PostgreSQL cannot safely run in one
  transaction.
- Batched data backfills instead of one large blocking update.
- Adding non-null columns safely, often through add/backfill/validate/enforce
  phases.
- Creating large indexes with appropriate online or concurrent strategies.
- Expand-and-contract migrations for zero- or low-downtime deployments.
- Roll-forward recovery plans when downgrade would lose data.
- Migration observability, timeouts, and failure handling.
- Coordination and revision-graph management when branches create competing
  migration heads.
- Compatibility testing with both old and new application versions during
  rolling deployments.
- Explicit handling of sensitive data transformations and retention rules.

Do not assume every migration should be downgraded in production. A downgrade
that drops columns or tables may destroy data; a corrective forward migration
is often safer.

For large or highly available systems, separate schema expansion, data
backfill, application rollout, and old-schema cleanup into multiple deployable
steps rather than one migration.


Backend:
    FastAPI startup, middleware, health endpoint, and routers.
    Dependency injection and role authorization.
    Login, bcrypt, JWT creation, and validation.
    Pydantic request/response schemas.
    CRUD route patterns.
    Async SQLAlchemy engine, sessions, commits, and refreshes.
    ORM models, constraints, foreign keys, indexes, and cascades.
    Soft-deletion strategies and parent-aware filtering.
    PostgreSQL and pgvector foundations.
    Alembic configuration, revisions, and production migration concerns.
    Configuration through pydantic-settings.