from typing import Literal, Optional

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------
# All LLM-related settings are documented below.  Secrets (API keys) are
# server-side only and are never returned by any API endpoint.
#
# Chat providers
# --------------
#   OPENAI_API_KEY        – Required when OPENAI is selected for chat.
#                           Leave empty for Ollama-only deployments.
#   OPENAI_CHAT_MODEL     – Pinned OpenAI chat deployment name.
#                           Default: "gpt-4o-mini".  Never use a floating
#                           "latest" alias in production.
#   OLLAMA_BASE_URL       – Base URL for the Ollama server.
#   OLLAMA_CHAT_MODEL     – Ollama model tag used for chat.
#                           Default: "llama3.2".
#
# Embedding profile (deployment-wide, corpus-fixed)
# --------------------------------------------------
#   EMBEDDING_PROVIDER    – Corpus embedding provider: "ollama" or "openai".
#                           Changing this requires a full re-index.
#   EMBEDDING_MODEL       – Model used for embeddings. Phase 2 allows exactly one
#                           model per provider: "nomic-embed-text" (Ollama) and
#                           "text-embedding-3-small" (OpenAI). Any other value,
#                           including blank, is rejected at startup. Changing the
#                           model requires a full corpus re-index.
#   EMBEDDING_DIMENSIONS  – Must be exactly 768 for Phase 2 storage.
#                           Equal dimensions do NOT make providers
#                           interchangeable; model change ⇒ full re-index.
#
# HTTP / retry tuning
# -------------------
#   LLM_CONNECT_TIMEOUT   – Seconds to wait for initial TCP connection.
#   LLM_READ_TIMEOUT      – Seconds to wait between streamed response chunks.
#   LLM_TOTAL_TIMEOUT     – Hard ceiling on a full request/response cycle.
#   LLM_MAX_RETRIES       – Number of retries on transient network errors.
# ---------------------------------------------------------------------------


class Settings(BaseSettings):
    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------
    DATABASE_URL: str
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ------------------------------------------------------------------
    # Chat providers
    # ------------------------------------------------------------------
    OPENAI_API_KEY: str = ""
    OPENAI_CHAT_MODEL: str = "gpt-4o-mini"
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_CHAT_MODEL: str = "llama3.2"

    # ------------------------------------------------------------------
    # Embedding profile (deployment-wide)
    # ------------------------------------------------------------------
    EMBEDDING_PROVIDER: Literal["ollama", "openai"] = "ollama"
    EMBEDDING_MODEL: Optional[str] = None  # resolved by model_validator below
    EMBEDDING_DIMENSIONS: int = 768

    # ------------------------------------------------------------------
    # HTTP / retry tuning
    # ------------------------------------------------------------------
    LLM_CONNECT_TIMEOUT: float = 5.0
    LLM_READ_TIMEOUT: float = 60.0
    LLM_TOTAL_TIMEOUT: float = 120.0
    LLM_MAX_RETRIES: int = 3

    # ------------------------------------------------------------------
    # Document ingestion
    # ------------------------------------------------------------------
    # MAX_DOCUMENT_UPLOAD_BYTES – Hard cap enforced while streaming an upload.
    #                             Content-Length is never trusted; the request
    #                             body is read in chunks and aborted once this
    #                             limit is exceeded. Default: 25 MiB.
    MAX_DOCUMENT_UPLOAD_BYTES: int = 25 * 1024 * 1024

    # ------------------------------------------------------------------
    # Validators
    # ------------------------------------------------------------------
    @field_validator("SECRET_KEY")
    @classmethod
    def secret_key_min_length(cls, v: str) -> str:
        if len(v) < 32:
            raise ValueError("SECRET_KEY must be at least 32 characters")
        return v

    @field_validator("EMBEDDING_DIMENSIONS")
    @classmethod
    def embedding_dimensions_phase2(cls, v: int) -> int:
        if v != 768:
            raise ValueError(
                "EMBEDDING_DIMENSIONS must be 768 for Phase 2 storage. "
                "Changing the embedding profile requires a full re-index."
            )
        return v

    @field_validator("LLM_CONNECT_TIMEOUT", "LLM_READ_TIMEOUT", "LLM_TOTAL_TIMEOUT")
    @classmethod
    def timeouts_must_be_positive(cls, v: float, info: object) -> float:
        if v <= 0:
            raise ValueError(f"{getattr(info, 'field_name', 'timeout')} must be positive")
        return v

    @field_validator("LLM_MAX_RETRIES")
    @classmethod
    def retries_must_be_non_negative(cls, v: int) -> int:
        if v < 0:
            raise ValueError("LLM_MAX_RETRIES must be >= 0")
        return v

    @field_validator("MAX_DOCUMENT_UPLOAD_BYTES")
    @classmethod
    def max_upload_bytes_must_be_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("MAX_DOCUMENT_UPLOAD_BYTES must be positive")
        return v

    @model_validator(mode="after")
    def resolve_and_validate_embedding_model(self) -> "Settings":
        """Resolve provider-appropriate default, then enforce Phase 2 model contract.

        Phase 2 fixes a single vector space per deployment. Changing the model
        requires a full corpus re-index, so only the approved model for each
        provider is accepted.
          openai → text-embedding-3-small
          ollama → nomic-embed-text
        """
        _ALLOWED: dict[str, str] = {
            "openai": "text-embedding-3-small",
            "ollama": "nomic-embed-text",
        }

        # Resolve default before any validation
        if self.EMBEDDING_MODEL is None:
            self.EMBEDDING_MODEL = _ALLOWED[self.EMBEDDING_PROVIDER]

        # Reject blank values
        if not self.EMBEDDING_MODEL.strip():
            raise ValueError("EMBEDDING_MODEL must not be blank.")

        # Enforce Phase 2 provider/model contract
        expected = _ALLOWED[self.EMBEDDING_PROVIDER]
        if self.EMBEDDING_MODEL != expected:
            raise ValueError(
                f"EMBEDDING_MODEL='{self.EMBEDDING_MODEL}' is not valid for "
                f"EMBEDDING_PROVIDER='{self.EMBEDDING_PROVIDER}'. "
                f"Phase 2 requires '{expected}'. "
                "Changing the embedding model requires a full corpus re-index."
            )

        return self

    @model_validator(mode="after")
    def openai_key_required_when_selected(self) -> "Settings":
        """Require OPENAI_API_KEY only when OpenAI is actually in use."""
        openai_for_chat = False  # chat provider chosen at conversation time, not here
        openai_for_embeddings = self.EMBEDDING_PROVIDER == "openai"
        if openai_for_embeddings and not self.OPENAI_API_KEY:
            raise ValueError(
                "OPENAI_API_KEY is required when EMBEDDING_PROVIDER='openai'. "
                "Set EMBEDDING_PROVIDER='ollama' or provide the API key."
            )
        # Suppress unused variable warning; chat provider is runtime-selected
        _ = openai_for_chat
        return self

    class Config:
        env_file = ".env"


settings = Settings()
