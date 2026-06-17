from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from app.core.security import create_access_token, hash_password
from app.dependencies import get_current_user
from app.main import app
from app.models.user import User
from app.services.assistant import DeniedAnswer, _EMPLOYEE_DENIAL
from app.services.llm import LLMError
from app.services.rag_logistics import (
    GraphEdge,
    GraphNode,
    IntentRouting,
    LogisticsAnswer,
    ProcurementGraph,
)
from app.services.rag_policy import MixedAnswer, PolicyAnswer


def _make_user(role: str) -> User:
    return User(
        id=str(uuid.uuid4()),
        name=f"{role.title()} User",
        email=f"{role}-{uuid.uuid4().hex[:8]}@example.com",
        password_hash=hash_password("Password123!"),
        role=role,
        is_active=True,
    )


def _routing(intent: str, tracking_codes: list[str] | None = None) -> IntentRouting:
    return IntentRouting(
        intent=intent,
        confidence=1.0,
        tracking_codes=tracking_codes or [],
        purchase_order_numbers=[],
        reason="test",
    )


def _override_current_user(user: User):
    async def _override():
        return user
    return _override


def _login_as(user: User) -> None:
    app.dependency_overrides[get_current_user] = _override_current_user(user)


@pytest_asyncio.fixture
async def client():
    from app.core.database import get_db

    async def _mock_db():
        yield AsyncMock()

    app.dependency_overrides[get_db] = _mock_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture(autouse=True)
async def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _auth_headers(user: User) -> dict[str, str]:
    token = create_access_token({"sub": user.id})
    return {"Authorization": f"Bearer {token}"}


def _policy_answer() -> PolicyAnswer:
    return PolicyAnswer(
        answer="The return policy allows 30-day returns.",
        citations=[
            {
                "source_title": "Returns Policy",
                "document_id": 1,
                "chunk_id": 10,
                "section": "Returns",
                "page_number": 2,
                "excerpt": "Items may be returned within 30 days.",
                "score": 0.92,
            }
        ],
    )


import datetime


def _logistics_answer() -> LogisticsAnswer:
    return LogisticsAnswer(
        answer="SHP-1001 is in transit to Chicago.",
        graph=ProcurementGraph(
            nodes=[
                GraphNode(id="s1", type="shipment", label="SHP-1001"),
                GraphNode(id="v1", type="vendor", label="Acme"),
            ],
            edges=[GraphEdge(source="v1", target="s1", relationship="ships")],
            highlighted_path=["v1", "s1"],
            retrieved_at=datetime.datetime(2026, 1, 1, tzinfo=datetime.timezone.utc),
        ),
        follow_ups=["When will it arrive?"],
    )


def _mixed_answer() -> MixedAnswer:
    return MixedAnswer(
        answer="SHP-1001 is in transit. The return policy applies.",
        graph=MagicMock(
            nodes=[GraphNode(id="s1", type="shipment", label="SHP-1001")],
            edges=[],
            highlighted_path=["s1"],
        ),
        citations=[
            {
                "source_title": "Returns Policy",
                "document_id": 1,
                "chunk_id": 10,
                "section": None,
                "page_number": None,
                "excerpt": "Returns within 30 days.",
                "score": 0.88,
            }
        ],
    )


class TestUnauthenticated:
    async def test_query_without_auth_returns_401(self, client: AsyncClient) -> None:
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "What is the return policy?"},
        )
        assert resp.status_code == 401


class TestValidation:
    async def test_blank_message_returns_422(self, client: AsyncClient) -> None:
        user = _make_user("employee")
        _login_as(user)
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "   "},
        )
        assert resp.status_code == 422

    async def test_empty_message_returns_422(self, client: AsyncClient) -> None:
        user = _make_user("employee")
        _login_as(user)
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": ""},
        )
        assert resp.status_code == 422

    async def test_context_too_many_turns_returns_422(self, client: AsyncClient) -> None:
        user = _make_user("employee")
        _login_as(user)
        context = [{"role": "user", "content": "hi"}] * 13
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "hello", "context": context},
        )
        assert resp.status_code == 422

    async def test_context_too_many_chars_returns_422(self, client: AsyncClient) -> None:
        user = _make_user("employee")
        _login_as(user)
        context = [{"role": "user", "content": "x" * 8001}]
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "hello", "context": context},
        )
        assert resp.status_code == 422


class TestPolicyIntent:
    @patch("app.api.v1.assistant.answer_question", new_callable=AsyncMock)
    async def test_policy_question_returns_citations(
        self, mock_aq: AsyncMock, client: AsyncClient
    ) -> None:
        user = _make_user("employee")
        _login_as(user)
        mock_aq.return_value = _policy_answer()
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "What is the return policy?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "policy"
        assert data["answer"] == "The return policy allows 30-day returns."
        assert len(data["citations"]) == 1
        assert data["citations"][0]["source_title"] == "Returns Policy"
        assert data["graph"] is None


class TestLogisticsIntent:
    @patch("app.api.v1.assistant.answer_question", new_callable=AsyncMock)
    async def test_logistics_question_returns_graph(
        self, mock_aq: AsyncMock, client: AsyncClient
    ) -> None:
        user = _make_user("manager")
        _login_as(user)
        mock_aq.return_value = _logistics_answer()
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "Where is SHP-1001?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "logistics"
        assert data["graph"] is not None
        assert len(data["graph"]["nodes"]) == 2
        assert len(data["graph"]["edges"]) == 1
        assert data["suggested_questions"] == ["When will it arrive?"]
        assert data["citations"] == []


class TestMixedIntent:
    @patch("app.api.v1.assistant.answer_question", new_callable=AsyncMock)
    async def test_mixed_question_returns_graph_and_citations(
        self, mock_aq: AsyncMock, client: AsyncClient
    ) -> None:
        user = _make_user("admin")
        _login_as(user)
        mock_aq.return_value = _mixed_answer()
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "What is the return policy for SHP-1001?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "mixed"
        assert data["graph"] is not None
        assert len(data["citations"]) == 1


class TestDenialIntent:
    @patch("app.api.v1.assistant.answer_question", new_callable=AsyncMock)
    async def test_employee_logistics_denial(
        self, mock_aq: AsyncMock, client: AsyncClient
    ) -> None:
        user = _make_user("employee")
        _login_as(user)
        mock_aq.return_value = DeniedAnswer(message=_EMPLOYEE_DENIAL)
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "Where is SHP-1001?"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["intent"] == "denied"
        assert data["answer"] == _EMPLOYEE_DENIAL
        assert data["graph"] is None
        assert data["citations"] == []


class TestFallback:
    @patch("app.api.v1.assistant.answer_question", new_callable=AsyncMock)
    async def test_llm_error_returns_502(
        self, mock_aq: AsyncMock, client: AsyncClient
    ) -> None:
        user = _make_user("manager")
        _login_as(user)
        mock_aq.side_effect = LLMError("provider down")
        resp = await client.post(
            "/api/v1/assistant/query",
            json={"message": "Where is SHP-1001?"},
        )
        assert resp.status_code == 502
        assert "temporarily unavailable" in resp.json()["detail"]
