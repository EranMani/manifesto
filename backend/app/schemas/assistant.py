from __future__ import annotations

from pydantic import BaseModel, ConfigDict, field_validator


_MAX_CONTEXT_TURNS = 12
_MAX_CONTEXT_CHARS = 8_000


class ContextTurn(BaseModel):
    model_config = ConfigDict(strict=True)

    role: str
    content: str


class AssistantQueryRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    message: str
    context: list[ContextTurn] = []

    @field_validator("message")
    @classmethod
    def message_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("message must not be blank")
        return v

    @field_validator("context")
    @classmethod
    def context_within_limits(cls, v: list[ContextTurn]) -> list[ContextTurn]:
        if len(v) > _MAX_CONTEXT_TURNS:
            raise ValueError(
                f"context must have at most {_MAX_CONTEXT_TURNS} turns"
            )
        total = sum(len(t.content) for t in v)
        if total > _MAX_CONTEXT_CHARS:
            raise ValueError(
                f"total context characters must not exceed {_MAX_CONTEXT_CHARS}"
            )
        return v


class CitationSchema(BaseModel):
    source_title: str
    document_id: str
    chunk_id: str
    section: str | None
    page_number: int | None
    excerpt: str
    score: float


class GraphNodeSchema(BaseModel):
    id: str
    type: str
    label: str
    status: str | None = None
    status_category: str | None = None


class GraphEdgeSchema(BaseModel):
    source: str
    target: str
    relationship: str


class GraphSchema(BaseModel):
    nodes: list[GraphNodeSchema]
    edges: list[GraphEdgeSchema]
    highlighted_path: list[str]


class ActionBadgeSchema(BaseModel):
    label: str
    prompt: str


class AssistantQueryResponse(BaseModel):
    intent: str
    answer: str
    graph: GraphSchema | None = None
    citations: list[CitationSchema] = []
    suggested_questions: list[str] = []
    action_badges: list[ActionBadgeSchema] = []
