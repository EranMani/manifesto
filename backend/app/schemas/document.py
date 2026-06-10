"""Safe request/response schemas for the document ingestion API.

These schemas expose only metadata that is safe for manager/admin consumers:
no embeddings, no chunk content, no file paths, and no raw error messages.
"""

from __future__ import annotations

import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

DocumentStatus = Literal["pending", "processing", "ready", "failed"]

# Stable, non-leaking failure codes surfaced to clients when status == "failed".
DocumentFailureCode = Literal[
    "unsupported_content_type",
    "empty_document",
    "encrypted_document",
    "corrupt_document",
    "image_only_document",
    "invalid_encoding",
    "embedding_provider_error",
    "internal_error",
]


class DocumentRead(BaseModel):
    """Safe metadata for a single policy document."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    original_filename: str | None
    status: DocumentStatus
    chunk_count: int
    uploaded_by: str | None
    embedding_provider: str | None
    embedding_model: str | None
    embedding_dimensions: int | None
    uploaded_at: datetime.datetime
    updated_at: datetime.datetime
    failure_code: DocumentFailureCode | None = None


class DocumentListResponse(BaseModel):
    """Cursor-paginated list of documents, ordered by (uploaded_at DESC, id DESC)."""

    items: list[DocumentRead]
    next_cursor: str | None = None


class DocumentUploadResponse(DocumentRead):
    """Response returned for a successful upload (new or existing identical document)."""
