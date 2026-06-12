"""API tests for the C28 document upload/list/detail endpoints.

These tests run against a real PostgreSQL + pgvector database (the docker-compose
``db`` service: db=manifesto, user=manifesto, pass=manifesto on localhost:5432) and
require migrations up to ``0002_rag_storage_hardening`` to be applied
(``alembic upgrade head``).

Each test runs inside its own transaction that is rolled back on teardown, so
tests do not leak rows or require manual cleanup. ``ingest_document`` is monkeypatched
to a no-op AsyncMock so these tests exercise only the route's auth, validation,
idempotency, pagination, and response-shape behaviour -- not the ingestion pipeline
(covered separately in tests/services/test_ingestion.py).
"""

from __future__ import annotations

import io
import os
import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1 import documents as documents_module
from app.core.database import get_db
from app.core.security import create_access_token, hash_password
from app.dependencies import get_current_user
from app.main import app
from app.models.policy import PolicyDocument
from app.models.user import User
from app.services.llm import EmbeddingProfile

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

PDF_BYTES = b"%PDF-1.4\n%mock pdf content for tests\n%%EOF"
DOCX_BYTES = b"PK\x03\x04mock docx zip container bytes"


@pytest_asyncio.fixture
async def session():
    """Yield an AsyncSession bound to a transaction that is rolled back after the test."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session_factory = async_sessionmaker(
                bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint"
            )
            async with session_factory() as sess:
                yield sess
            await trans.rollback()
    finally:
        await engine.dispose()


def _make_user(role: str) -> User:
    return User(
        id=str(uuid.uuid4()),
        name=f"{role.title()} User",
        email=f"{role}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("Password123!"),
        role=role,
        is_active=True,
    )


@pytest_asyncio.fixture
async def manager_user(session: AsyncSession) -> User:
    user = _make_user("manager")
    session.add(user)
    await session.flush()
    return user


@pytest_asyncio.fixture
async def employee_user(session: AsyncSession) -> User:
    user = _make_user("employee")
    session.add(user)
    await session.flush()
    return user


_FAKE_PROFILE = EmbeddingProfile(provider="ollama", model="nomic-embed-text", dimensions=768)


class _FakeEmbeddingService:
    profile = _FAKE_PROFILE


@pytest_asyncio.fixture
async def client(session: AsyncSession, monkeypatch: pytest.MonkeyPatch):
    """An AsyncClient wired to the app with db/auth/embedding dependencies overridden."""

    async def _override_get_db():
        yield session

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[documents_module.get_embedding_service] = lambda: _FakeEmbeddingService()

    mock_ingest = AsyncMock(return_value=None)
    monkeypatch.setattr(documents_module, "ingest_document", mock_ingest)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        ac._mock_ingest = mock_ingest  # type: ignore[attr-defined]
        yield ac

    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(documents_module.get_embedding_service, None)


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def _override_current_user(user: User):
    async def _override():
        return user

    return _override


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = _override_current_user(user)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Auth / role matrix
# ---------------------------------------------------------------------------


class TestAuthAndRoles:
    @pytest.mark.asyncio
    async def test_upload_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_list_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_employee_upload_returns_403_no_metadata_leak(
        self, client: AsyncClient, employee_user: User
    ) -> None:
        _login_as(employee_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 403
        body = resp.json()
        # No document metadata should leak in a 403 body.
        assert "id" not in body
        assert "embedding_provider" not in body
        assert "chunk_count" not in body

    @pytest.mark.asyncio
    async def test_employee_list_returns_403(self, client: AsyncClient, employee_user: User) -> None:
        _login_as(employee_user)
        resp = await client.get("/api/v1/documents")
        assert resp.status_code == 403

    @pytest.mark.asyncio
    async def test_employee_get_document_returns_403(self, client: AsyncClient, employee_user: User) -> None:
        _login_as(employee_user)
        resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert resp.status_code == 403


# ---------------------------------------------------------------------------
# Upload validation
# ---------------------------------------------------------------------------


class TestUploadValidation:
    @pytest.mark.asyncio
    async def test_unsupported_content_type_returns_415(
        self, client: AsyncClient, manager_user: User
    ) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.exe", io.BytesIO(b"MZ\x90\x00"), "application/x-msdownload")},
            data={"title": "A title"},
        )
        assert resp.status_code == 415
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_extension_mismatch_returns_415(self, client: AsyncClient, manager_user: User) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.txt", io.BytesIO(PDF_BYTES), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 415
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_signature_mismatch_returns_415(self, client: AsyncClient, manager_user: User) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(b"not a pdf at all"), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 415
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_empty_file_returns_422(self, client: AsyncClient, manager_user: User) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(b""), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 422
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_blank_title_returns_422(self, client: AsyncClient, manager_user: User) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
            data={"title": "   "},
        )
        assert resp.status_code == 422
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

    @pytest.mark.asyncio
    async def test_oversize_file_returns_413(
        self, client: AsyncClient, manager_user: User, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        monkeypatch.setattr(documents_module.settings, "MAX_DOCUMENT_UPLOAD_BYTES", 16)
        _login_as(manager_user)
        oversized = PDF_BYTES + b"x" * 100
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("a.pdf", io.BytesIO(oversized), "application/pdf")},
            data={"title": "A title"},
        )
        assert resp.status_code == 413
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Successful upload + idempotency
# ---------------------------------------------------------------------------


class TestUploadSuccessAndIdempotency:
    @pytest.mark.asyncio
    async def test_upload_success_calls_ingest_and_returns_metadata(
        self, client: AsyncClient, manager_user: User, session: AsyncSession
    ) -> None:
        _login_as(manager_user)
        resp = await client.post(
            "/api/v1/documents",
            files={"file": ("policy.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
            data={"title": "Policy Doc"},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Policy Doc"
        assert body["original_filename"] == "policy.pdf"
        assert client._mock_ingest.await_count == 1  # type: ignore[attr-defined]

        # Safe metadata only.
        for forbidden in ("embedding", "content", "file_path", "raw_error", "error_message"):
            assert forbidden not in body

    @pytest.mark.asyncio
    async def test_duplicate_upload_is_idempotent(
        self, client: AsyncClient, manager_user: User, session: AsyncSession
    ) -> None:
        _login_as(manager_user)

        sha256 = "b" * 64
        existing = PolicyDocument(
            title="Existing Ready Doc",
            original_filename="existing.pdf",
            content_type="application/pdf",
            byte_size=len(PDF_BYTES),
            sha256=sha256,
            status="ready",
            uploaded_by=manager_user.id,
            embedding_provider=_FAKE_PROFILE.provider,
            embedding_model=_FAKE_PROFILE.model,
            embedding_dimensions=_FAKE_PROFILE.dimensions,
        )
        session.add(existing)
        await session.flush()

        # Compute matching content: PDF bytes whose sha256 == sha256 above is not
        # feasible to fabricate, so instead patch hashlib to return the fixed digest.
        import hashlib as _hashlib

        class _FixedDigest:
            def __init__(self, *_args, **_kwargs):
                pass

            def hexdigest(self) -> str:
                return sha256

        import app.api.v1.documents as docs_mod

        original_sha256 = _hashlib.sha256
        try:
            docs_mod.hashlib.sha256 = lambda *_a, **_k: _FixedDigest()  # type: ignore[assignment]

            resp = await client.post(
                "/api/v1/documents",
                files={"file": ("dup.pdf", io.BytesIO(PDF_BYTES), "application/pdf")},
                data={"title": "Duplicate Upload"},
            )
        finally:
            docs_mod.hashlib.sha256 = original_sha256

        assert resp.status_code == 200
        body = resp.json()
        assert body["id"] == existing.id
        assert body["title"] == "Existing Ready Doc"

        # Ingestion must not run for an idempotent duplicate.
        assert client._mock_ingest.await_count == 0  # type: ignore[attr-defined]

        # No duplicate row was created.
        result = await session.execute(
            text("SELECT count(*) FROM policy_documents WHERE sha256 = :sha"), {"sha": sha256}
        )
        assert result.scalar_one() == 1


# ---------------------------------------------------------------------------
# List pagination ordering
# ---------------------------------------------------------------------------


class TestListPagination:
    @pytest.mark.asyncio
    async def test_list_orders_by_uploaded_at_desc_then_id_desc(
        self, client: AsyncClient, manager_user: User, session: AsyncSession
    ) -> None:
        _login_as(manager_user)

        # Create documents with explicit, identical uploaded_at to exercise the
        # id DESC tiebreaker, plus one earlier doc.
        common_ts = datetime(2025, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
        docs = []
        for i in range(3):
            doc = PolicyDocument(
                title=f"Doc {i}",
                sha256=f"{i}" * 64,
                status="ready",
                uploaded_by=manager_user.id,
                embedding_provider=_FAKE_PROFILE.provider,
                embedding_model=_FAKE_PROFILE.model,
                embedding_dimensions=_FAKE_PROFILE.dimensions,
            )
            session.add(doc)
            docs.append(doc)
        await session.flush()

        for doc in docs:
            await session.execute(
                text("UPDATE policy_documents SET uploaded_at = :ts WHERE id = :id"),
                {"ts": common_ts, "id": doc.id},
            )
        await session.flush()

        resp = await client.get("/api/v1/documents", params={"limit": 100})
        assert resp.status_code == 200
        body = resp.json()

        ids_with_common_ts = [doc.id for doc in docs]
        returned_ids = [item["id"] for item in body["items"] if item["id"] in ids_with_common_ts]

        # Same uploaded_at -> ordered by id DESC.
        assert returned_ids == sorted(ids_with_common_ts, reverse=True)

    @pytest.mark.asyncio
    async def test_get_document_not_found_returns_404(
        self, client: AsyncClient, manager_user: User
    ) -> None:
        _login_as(manager_user)
        resp = await client.get(f"/api/v1/documents/{uuid.uuid4()}")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Safe metadata exposure
# ---------------------------------------------------------------------------


class TestSafeMetadata:
    @pytest.mark.asyncio
    async def test_get_document_does_not_expose_internal_fields(
        self, client: AsyncClient, manager_user: User, session: AsyncSession
    ) -> None:
        _login_as(manager_user)

        doc = PolicyDocument(
            title="Failed Doc",
            sha256="c" * 64,
            status="failed",
            error_message="some raw internal traceback detail",
            uploaded_by=manager_user.id,
            embedding_provider=_FAKE_PROFILE.provider,
            embedding_model=_FAKE_PROFILE.model,
            embedding_dimensions=_FAKE_PROFILE.dimensions,
        )
        session.add(doc)
        await session.flush()

        resp = await client.get(f"/api/v1/documents/{doc.id}")
        assert resp.status_code == 200
        body = resp.json()

        for forbidden in ("embedding", "embeddings", "content", "file_path", "raw_error_message"):
            assert forbidden not in body

        # error_message must never be exposed verbatim.
        assert "error_message" not in body
        if "raw_error_message" in body:
            assert body["raw_error_message"] != "some raw internal traceback detail"
