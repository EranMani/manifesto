from typing import Literal

from sqlalchemy import BigInteger, Computed, DateTime, ForeignKey, Integer, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID
from sqlalchemy.orm import Mapped, mapped_column
from pgvector.sqlalchemy import Vector
from app.core.database import Base
import datetime

PolicyDocumentStatus = Literal["pending", "processing", "ready", "failed"]


class PolicyDocument(Base):
    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    file_path: Mapped[str | None] = mapped_column(String, nullable=True)
    uploaded_by: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id"), nullable=True)
    uploaded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    # Provenance of the uploaded source file.
    original_filename: Mapped[str | None] = mapped_column(String, nullable=True)
    content_type: Mapped[str | None] = mapped_column(String, nullable=True)
    byte_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Ingestion lifecycle. A trigger enforces that 'ready' requires every chunk to
    # have a non-null embedding.
    status: Mapped[PolicyDocumentStatus] = mapped_column(String, nullable=False, server_default="pending")
    error_message: Mapped[str | None] = mapped_column(String, nullable=True)
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, server_default="0")

    # Embedding profile this document was indexed under. Retrieval filters to the
    # active profile; re-indexing under a new profile creates a new row rather than
    # mutating this one (see uq_policy_documents_checksum_profile).
    embedding_provider: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_model: Mapped[str | None] = mapped_column(String, nullable=True)
    embedding_dimensions: Mapped[int | None] = mapped_column(Integer, nullable=True)

    updated_at: Mapped[datetime.datetime] = mapped_column(
        DateTime(timezone=True), server_default=text("now()"), onupdate=text("now()")
    )

    __table_args__ = (
        UniqueConstraint(
            "sha256",
            "embedding_provider",
            "embedding_model",
            "embedding_dimensions",
            name="uq_policy_documents_checksum_profile",
        ),
    )


class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    document_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("policy_documents.id", ondelete="CASCADE"), nullable=False)
    chunk_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[str] = mapped_column(String, nullable=False)
    embedding: Mapped[list | None] = mapped_column(Vector(768), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    # Extraction provenance, when the source format can supply it.
    token_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    page_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    section: Mapped[str | None] = mapped_column(String, nullable=True)

    metadata_: Mapped[dict] = mapped_column(
        "metadata", JSONB, nullable=False, server_default=text("'{}'::jsonb")
    )

    # Generated column (to_tsvector over content) — read-only from the ORM, populated
    # by PostgreSQL via STORED GENERATED ALWAYS AS, backed by a GIN index for lexical
    # retrieval. Computed(..., persisted=True) excludes it from INSERT/UPDATE.
    search_vector: Mapped[str | None] = mapped_column(
        TSVECTOR, Computed("to_tsvector('english', coalesce(content, ''))", persisted=True), nullable=True
    )

    __table_args__ = (
        # Unique chunk ordering within a document. HNSW cosine index and the
        # full-text GIN index on search_vector are defined via migration — cannot
        # express dynamically in DDL here.
        UniqueConstraint("document_id", "chunk_index", name="uq_policy_chunks_document_chunk_index"),
    )
