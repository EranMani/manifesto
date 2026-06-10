"""rag storage hardening

Revision ID: 0002_rag_storage_hardening
Revises: 0001_initial
Create Date: 2026-06-10 00:00:00.000000

Hardens the policy RAG storage schema before any production data is written:

- policy_chunks.embedding is changed from VECTOR(1536) to VECTOR(768) to match the
  Phase 2 embedding profile (Ollama nomic-embed-text / OpenAI text-embedding-3-small
  at dimensions=768). This migration FAILS LOUDLY if any non-null embeddings already
  exist, since silently truncating/casting an existing vector space would corrupt
  retrieval. Phase 2 has not ingested any production data, so this is expected to be
  a no-op data-wise.
- policy_documents gains profile/provenance/status columns so ingestion (C27) can be
  idempotent and recoverable.
- policy_chunks gains provenance, metadata, full-text search, and uniqueness/ordering
  constraints.
- The empty-corpus IVFFlat index is replaced with an HNSW cosine index, which can be
  built before data exists and offers a better speed/recall tradeoff for a growing
  corpus. Index parameters (m=16, ef_construction=64) are explicit defaults; production
  tuning must be revisited using measured recall/latency once real data exists.
- A trigger enforces that a policy_document cannot transition to status='ready' while
  any of its chunks have a NULL embedding.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers, used by Alembic.
revision: str = "0002_rag_storage_hardening"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- policy_documents: profile, provenance, status columns -------------------
    op.add_column("policy_documents", sa.Column("original_filename", sa.String(), nullable=True))
    op.add_column("policy_documents", sa.Column("content_type", sa.String(), nullable=True))
    op.add_column("policy_documents", sa.Column("byte_size", sa.BigInteger(), nullable=True))
    op.add_column("policy_documents", sa.Column("sha256", sa.String(length=64), nullable=True))
    op.add_column(
        "policy_documents",
        sa.Column("status", sa.String(), nullable=False, server_default="pending"),
    )
    op.add_column("policy_documents", sa.Column("embedding_provider", sa.String(), nullable=True))
    op.add_column("policy_documents", sa.Column("embedding_model", sa.String(), nullable=True))
    op.add_column("policy_documents", sa.Column("embedding_dimensions", sa.Integer(), nullable=True))
    op.add_column("policy_documents", sa.Column("error_message", sa.String(), nullable=True))
    op.add_column(
        "policy_documents",
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "policy_documents",
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    op.create_check_constraint(
        "policy_document_status_check",
        "policy_documents",
        "status IN ('pending', 'processing', 'ready', 'failed')",
    )

    # Idempotency: retrying the same upload under the same embedding profile resolves
    # to the existing document row instead of creating a duplicate. A future re-index
    # under a new embedding profile (different provider/model/dimensions) is a distinct
    # row and is not blocked by this constraint.
    op.create_unique_constraint(
        "uq_policy_documents_checksum_profile",
        "policy_documents",
        ["sha256", "embedding_provider", "embedding_model", "embedding_dimensions"],
    )

    # --- policy_chunks: provenance, metadata, full-text search --------------------
    op.add_column("policy_chunks", sa.Column("token_count", sa.Integer(), nullable=True))
    op.add_column("policy_chunks", sa.Column("page_number", sa.Integer(), nullable=True))
    op.add_column("policy_chunks", sa.Column("section", sa.String(), nullable=True))
    op.add_column(
        "policy_chunks",
        sa.Column("metadata", JSONB(), nullable=False, server_default=sa.text("'{}'::jsonb")),
    )

    # Generated tsvector column for lexical retrieval, backed by a GIN index.
    op.execute(
        "ALTER TABLE policy_chunks "
        "ADD COLUMN search_vector tsvector "
        "GENERATED ALWAYS AS (to_tsvector('english', coalesce(content, ''))) STORED;"
    )
    op.create_index(
        "ix_policy_chunks_search_vector",
        "policy_chunks",
        ["search_vector"],
        postgresql_using="gin",
    )

    # Unique chunk ordering within a document, enforced by PostgreSQL.
    op.create_unique_constraint(
        "uq_policy_chunks_document_chunk_index",
        "policy_chunks",
        ["document_id", "chunk_index"],
    )

    # --- embedding column: 1536 -> 768 ---------------------------------------------
    # Fail loudly if any non-null legacy embeddings exist; casting/truncating an
    # existing vector space silently would corrupt retrieval.
    op.execute(
        """
        DO $$
        DECLARE
            existing_count integer;
        BEGIN
            SELECT count(*) INTO existing_count
            FROM policy_chunks
            WHERE embedding IS NOT NULL;

            IF existing_count > 0 THEN
                RAISE EXCEPTION
                    'Cannot change policy_chunks.embedding from vector(1536) to vector(768): % '
                    'row(s) have a non-null embedding in the old vector space. '
                    'Re-index under the new embedding profile before retrying this migration.',
                    existing_count;
            END IF;
        END
        $$;
        """
    )

    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_embedding_ivfflat;")
    op.execute("ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector(768);")

    # HNSW cosine index. Can be built on an empty table; parameters (m, ef_construction)
    # are explicit Phase 2 defaults — production tuning must be revisited using measured
    # recall/latency once real data exists.
    op.execute(
        "CREATE INDEX ix_policy_chunks_embedding_hnsw "
        "ON policy_chunks USING hnsw (embedding vector_cosine_ops) "
        "WITH (m = 16, ef_construction = 64);"
    )

    # --- ready-state invariant: ready documents require fully embedded chunks -----
    op.execute(
        """
        CREATE OR REPLACE FUNCTION policy_document_ready_requires_embeddings()
        RETURNS trigger AS $$
        DECLARE
            missing_count integer;
        BEGIN
            IF NEW.status = 'ready' THEN
                SELECT count(*) INTO missing_count
                FROM policy_chunks
                WHERE document_id = NEW.id AND embedding IS NULL;

                IF missing_count > 0 THEN
                    RAISE EXCEPTION
                        'policy_documents.status cannot be set to ready: % chunk(s) for '
                        'document % have a null embedding.',
                        missing_count, NEW.id;
                END IF;
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_policy_document_ready_requires_embeddings
        BEFORE INSERT OR UPDATE OF status ON policy_documents
        FOR EACH ROW
        EXECUTE FUNCTION policy_document_ready_requires_embeddings();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS trg_policy_document_ready_requires_embeddings ON policy_documents;")
    op.execute("DROP FUNCTION IF EXISTS policy_document_ready_requires_embeddings();")

    op.execute("DROP INDEX IF EXISTS ix_policy_chunks_embedding_hnsw;")

    op.execute(
        """
        DO $$
        DECLARE
            existing_count integer;
        BEGIN
            SELECT count(*) INTO existing_count
            FROM policy_chunks
            WHERE embedding IS NOT NULL;

            IF existing_count > 0 THEN
                RAISE EXCEPTION
                    'Cannot downgrade policy_chunks.embedding from vector(768) to vector(1536): '
                    '% row(s) have a non-null embedding in the new vector space. '
                    'Re-index under the prior embedding profile before retrying this downgrade.',
                    existing_count;
            END IF;
        END
        $$;
        """
    )
    op.execute("ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector(1536);")
    op.execute(
        "CREATE INDEX ix_policy_chunks_embedding_ivfflat "
        "ON policy_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);"
    )

    op.drop_constraint("uq_policy_chunks_document_chunk_index", "policy_chunks", type_="unique")

    op.drop_index("ix_policy_chunks_search_vector", table_name="policy_chunks")
    op.execute("ALTER TABLE policy_chunks DROP COLUMN search_vector;")

    op.drop_column("policy_chunks", "metadata")
    op.drop_column("policy_chunks", "section")
    op.drop_column("policy_chunks", "page_number")
    op.drop_column("policy_chunks", "token_count")

    op.drop_constraint("uq_policy_documents_checksum_profile", "policy_documents", type_="unique")
    op.drop_constraint("policy_document_status_check", "policy_documents", type_="check")

    op.drop_column("policy_documents", "updated_at")
    op.drop_column("policy_documents", "chunk_count")
    op.drop_column("policy_documents", "error_message")
    op.drop_column("policy_documents", "embedding_dimensions")
    op.drop_column("policy_documents", "embedding_model")
    op.drop_column("policy_documents", "embedding_provider")
    op.drop_column("policy_documents", "status")
    op.drop_column("policy_documents", "sha256")
    op.drop_column("policy_documents", "byte_size")
    op.drop_column("policy_documents", "content_type")
    op.drop_column("policy_documents", "original_filename")
