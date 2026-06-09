"""Persistent tests for Settings validation — LLM provider and embedding profile."""
import pytest
from pydantic import ValidationError

from app.core.config import Settings

# Required fields with no defaults; override per-test as needed.
# OPENAI_API_KEY is explicitly "" so .env values don't bleed into tests.
_BASE = {
    "DATABASE_URL": "postgresql+asyncpg://user:pass@localhost/testdb",
    "SECRET_KEY": "x" * 32,
    "OPENAI_API_KEY": "",
}


def make(**overrides) -> Settings:
    return Settings(**{**_BASE, **overrides})


# ---------------------------------------------------------------------------
# Embedding model defaults — the core fix for C24
# ---------------------------------------------------------------------------

class TestEmbeddingModelDefaults:
    def test_ollama_provider_defaults_to_nomic_embed_text(self):
        s = make(EMBEDDING_PROVIDER="ollama")
        assert s.EMBEDDING_MODEL == "nomic-embed-text"

    def test_openai_provider_defaults_to_text_embedding_3_small(self):
        s = make(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="sk-test")
        assert s.EMBEDDING_MODEL == "text-embedding-3-small"

    def test_openai_never_silently_receives_nomic_embed_text(self):
        """The bug this commit fixed: EMBEDDING_MODEL must not default to an
        Ollama model name when EMBEDDING_PROVIDER='openai'."""
        s = make(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="sk-test")
        assert s.EMBEDDING_MODEL != "nomic-embed-text"

    def test_correct_model_accepted_for_ollama(self):
        s = make(EMBEDDING_PROVIDER="ollama", EMBEDDING_MODEL="nomic-embed-text")
        assert s.EMBEDDING_MODEL == "nomic-embed-text"

    def test_correct_model_accepted_for_openai(self):
        s = make(
            EMBEDDING_PROVIDER="openai",
            OPENAI_API_KEY="sk-test",
            EMBEDDING_MODEL="text-embedding-3-small",
        )
        assert s.EMBEDDING_MODEL == "text-embedding-3-small"

    # --- rejection: invalid provider/model combinations ---

    def test_nomic_embed_text_rejected_for_openai(self):
        with pytest.raises(ValidationError, match="text-embedding-3-small"):
            make(
                EMBEDDING_PROVIDER="openai",
                OPENAI_API_KEY="sk-test",
                EMBEDDING_MODEL="nomic-embed-text",
            )

    def test_text_embedding_3_small_rejected_for_ollama(self):
        with pytest.raises(ValidationError, match="nomic-embed-text"):
            make(EMBEDDING_PROVIDER="ollama", EMBEDDING_MODEL="text-embedding-3-small")

    def test_nonstandard_model_rejected_for_openai(self):
        with pytest.raises(ValidationError, match="text-embedding-3-small"):
            make(
                EMBEDDING_PROVIDER="openai",
                OPENAI_API_KEY="sk-test",
                EMBEDDING_MODEL="text-embedding-ada-002",
            )

    def test_nonstandard_model_rejected_for_ollama(self):
        with pytest.raises(ValidationError, match="nomic-embed-text"):
            make(EMBEDDING_PROVIDER="ollama", EMBEDDING_MODEL="mxbai-embed-large")

    # --- rejection: blank model ---

    def test_blank_model_rejected(self):
        with pytest.raises(ValidationError, match="blank"):
            make(EMBEDDING_PROVIDER="ollama", EMBEDDING_MODEL="")


# ---------------------------------------------------------------------------
# Embedding dimensions
# ---------------------------------------------------------------------------

class TestEmbeddingDimensions:
    def test_768_accepted(self):
        s = make(EMBEDDING_DIMENSIONS=768)
        assert s.EMBEDDING_DIMENSIONS == 768

    def test_1536_rejected(self):
        with pytest.raises(ValidationError, match="768"):
            make(EMBEDDING_DIMENSIONS=1536)

    def test_512_rejected(self):
        with pytest.raises(ValidationError, match="768"):
            make(EMBEDDING_DIMENSIONS=512)


# ---------------------------------------------------------------------------
# Timeout validation
# ---------------------------------------------------------------------------

class TestTimeoutValidation:
    def test_negative_connect_timeout_rejected(self):
        with pytest.raises(ValidationError):
            make(LLM_CONNECT_TIMEOUT=-1.0)

    def test_zero_read_timeout_rejected(self):
        with pytest.raises(ValidationError):
            make(LLM_READ_TIMEOUT=0.0)

    def test_zero_total_timeout_rejected(self):
        with pytest.raises(ValidationError):
            make(LLM_TOTAL_TIMEOUT=0.0)

    def test_positive_timeouts_accepted(self):
        s = make(LLM_CONNECT_TIMEOUT=5.0, LLM_READ_TIMEOUT=30.0, LLM_TOTAL_TIMEOUT=60.0)
        assert s.LLM_CONNECT_TIMEOUT == 5.0

    def test_negative_retries_rejected(self):
        with pytest.raises(ValidationError):
            make(LLM_MAX_RETRIES=-1)

    def test_zero_retries_accepted(self):
        s = make(LLM_MAX_RETRIES=0)
        assert s.LLM_MAX_RETRIES == 0


# ---------------------------------------------------------------------------
# OpenAI API key requirement
# ---------------------------------------------------------------------------

class TestOpenAIKeyRequirement:
    def test_openai_embedding_without_key_rejected(self):
        with pytest.raises(ValidationError, match="OPENAI_API_KEY"):
            make(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="")

    def test_openai_embedding_with_key_accepted(self):
        s = make(EMBEDDING_PROVIDER="openai", OPENAI_API_KEY="sk-test")
        assert s.EMBEDDING_PROVIDER == "openai"

    def test_ollama_embedding_without_openai_key_accepted(self):
        s = make(EMBEDDING_PROVIDER="ollama", OPENAI_API_KEY="")
        assert s.EMBEDDING_PROVIDER == "ollama"
