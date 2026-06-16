from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.assistant import AssistantAnswer, DeniedAnswer, _EMPLOYEE_DENIAL, answer_question
from app.services.rag_logistics import IntentRouting, LogisticsAnswer
from app.services.rag_policy import MixedAnswer, PolicyAnswer


def _routing(intent: str, tracking_codes: list[str] | None = None) -> IntentRouting:
    return IntentRouting(
        intent=intent,
        confidence=1.0,
        tracking_codes=tracking_codes or [],
        purchase_order_numbers=[],
        reason="test",
    )


def _mock_db() -> AsyncMock:
    return AsyncMock()


def _mock_llm() -> MagicMock:
    return MagicMock()


def _mock_embeddings() -> MagicMock:
    return MagicMock()


async def _call(role: str, message: str, intent: str, tracking_codes: list[str] | None = None, **mocks: AsyncMock) -> AssistantAnswer:
    with patch("app.services.assistant.classify_intent", return_value=_routing(intent, tracking_codes)):
        return await answer_question(
            user_role=role,
            message=message,
            db=_mock_db(),
            llm=_mock_llm(),
            embeddings=_mock_embeddings(),
        )


class TestAuthorizationEmployeePolicy:
    async def test_authorization_employee_policy_proceeds(self):
        policy_answer = PolicyAnswer(answer="The policy states...", citations=[])
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("policy")),
            patch("app.services.assistant.generate_grounded_policy_answer", new=AsyncMock(return_value=policy_answer)),
        ):
            result = await answer_question(
                user_role="employee", message="What is the return policy?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, PolicyAnswer)
        assert result.answer == "The policy states..."


class TestAuthorizationEmployeeLogistics:
    async def test_authorization_employee_logistics_denied(self):
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("logistics", ["SHP-1001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer") as mock_gen,
        ):
            result = await answer_question(
                user_role="employee", message="Where is SHP-1001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, DeniedAnswer)
        assert result.message == _EMPLOYEE_DENIAL
        mock_gen.assert_not_called()

    async def test_authorization_employee_logistics_leaks_nothing(self):
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("logistics", ["SHP-1001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer") as mock_gen,
        ):
            result = await answer_question(
                user_role="employee", message="Where is SHP-1001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert "SHP-1001" not in result.message
        assert "tracking" not in result.message.lower()


class TestAuthorizationEmployeeMixed:
    async def test_authorization_employee_mixed_denied(self):
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("mixed", ["SHP-1001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer") as mock_log,
            patch("app.services.assistant.generate_grounded_mixed_answer") as mock_mix,
            patch("app.services.assistant.lookup_procurement") as mock_lookup,
        ):
            result = await answer_question(
                user_role="employee", message="What is the return policy for SHP-1001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, DeniedAnswer)
        assert result.message == _EMPLOYEE_DENIAL
        mock_log.assert_not_called()
        mock_mix.assert_not_called()
        mock_lookup.assert_not_called()


class TestAuthorizationManagerAdmin:
    async def test_authorization_manager_logistics_proceeds(self):
        logistics_answer = LogisticsAnswer(answer="Shipped.", graph=MagicMock(), follow_ups=[])
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("logistics", ["SHP-1001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer", new=AsyncMock(return_value=logistics_answer)),
        ):
            result = await answer_question(
                user_role="manager", message="Where is SHP-1001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, LogisticsAnswer)

    async def test_authorization_admin_logistics_proceeds(self):
        logistics_answer = LogisticsAnswer(answer="Delivered.", graph=MagicMock(), follow_ups=[])
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("logistics", ["SHP-2001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer", new=AsyncMock(return_value=logistics_answer)),
        ):
            result = await answer_question(
                user_role="admin", message="Where is SHP-2001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, LogisticsAnswer)

    async def test_authorization_manager_mixed_proceeds(self):
        logistics_answer = LogisticsAnswer(answer="Shipped.", graph=MagicMock(), follow_ups=[])
        mixed_answer = MixedAnswer(answer="Combined.", graph=MagicMock(), citations=[])
        procurement_evidence = MagicMock()
        with (
            patch("app.services.assistant.classify_intent", return_value=_routing("mixed", ["SHP-1001"])),
            patch("app.services.assistant.generate_grounded_logistics_answer", new=AsyncMock(return_value=logistics_answer)),
            patch("app.services.assistant.lookup_procurement", new=AsyncMock(return_value=procurement_evidence)),
            patch("app.services.assistant.generate_grounded_mixed_answer", new=AsyncMock(return_value=mixed_answer)),
        ):
            result = await answer_question(
                user_role="manager", message="What is the return policy for SHP-1001?",
                db=_mock_db(), llm=_mock_llm(), embeddings=_mock_embeddings(),
            )
        assert isinstance(result, MixedAnswer)
