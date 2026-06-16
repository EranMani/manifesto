from __future__ import annotations

from dataclasses import dataclass
from typing import TypeAlias

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.llm import EmbeddingService, LLMService
from app.services.rag_logistics import (
    LogisticsAnswer,
    classify_intent,
    generate_grounded_logistics_answer,
    lookup_procurement,
)
from app.services.rag_policy import (
    MixedAnswer,
    PolicyAnswer,
    generate_grounded_mixed_answer,
    generate_grounded_policy_answer,
)


_EMPLOYEE_DENIAL = (
    "I can only answer questions about company policies and procedures. "
    "For shipment or order information, please contact your manager."
)


@dataclass(frozen=True)
class DeniedAnswer:
    message: str


AssistantAnswer: TypeAlias = PolicyAnswer | LogisticsAnswer | MixedAnswer | DeniedAnswer

_LOGISTICS_ROLES = frozenset({"admin", "manager"})


async def answer_question(
    *,
    user_role: str,
    message: str,
    db: AsyncSession,
    llm: LLMService,
    embeddings: EmbeddingService,
) -> AssistantAnswer:
    """Route an assistant question and enforce role-based evidence access."""
    routing = classify_intent(message)
    role = user_role.lower()

    if routing.intent in {"logistics", "mixed"} and role not in _LOGISTICS_ROLES:
        return DeniedAnswer(message=_EMPLOYEE_DENIAL)

    if routing.intent == "policy":
        return await generate_grounded_policy_answer(db, llm, message, embeddings)

    tracking_code = _primary_tracking_code(routing.tracking_codes)
    logistics_answer = await generate_grounded_logistics_answer(
        db,
        llm,
        tracking_code,
        message,
    )

    if routing.intent == "logistics":
        return logistics_answer

    logistics_evidence = await lookup_procurement(db, tracking_code)
    return await generate_grounded_mixed_answer(
        db,
        llm,
        message,
        embeddings,
        logistics_answer,
        logistics_evidence,
    )


def _primary_tracking_code(tracking_codes: list[str]) -> str:
    return tracking_codes[0] if tracking_codes else ""
