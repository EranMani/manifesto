# GLOSSARY.md — Manifesto

> Maintained by Claude. New terms are added when first introduced — not retroactively.
> Last updated: 2026-06-09 (C24)

---

## Terms

### asyncpg
PostgreSQL async driver for Python. Used via the `postgresql+asyncpg://` connection string prefix. Chosen over psycopg2 because FastAPI uses async I/O — a sync driver would block the event loop. See also: `DATABASE_URL`.

### DATABASE_URL
The full PostgreSQL connection string used by SQLAlchemy. Format in this project: `postgresql+asyncpg://manifesto:manifesto@db:5432/manifesto`. The `db` hostname resolves to the Docker Compose `db` service — does not work outside the container network.

### pgvector
PostgreSQL extension for storing and querying vector embeddings. Enables similarity search directly in the database without a separate vector store. Docker image: `pgvector/pgvector:pg16`.

### uv
Rust-based Python package manager. Replaces pip + requirements.txt. Install command: `uv sync` (reads from `pyproject.toml`). Add packages with `uv add <package>`. Significantly faster than pip. See D02.

### uvicorn
ASGI server that runs the FastAPI application. Launched with `--reload` in dev so file changes restart automatically. Bind mount `./backend:/app` makes reloads instant without rebuilding the container.

### Ollama
Local LLM serving layer. Runs as a Docker service (`ollama/ollama`). Exposes an API at `http://ollama:11434` inside the Docker network. Used to serve embedding and generation models locally without cloud API calls.

### structlog
Python structured logging library. Produces log output as key-value pairs or JSON instead of plain text — makes logs machine-parseable and searchable. Imported in `main.py` as `logger = structlog.get_logger()`. Added in C02.

### commit-protocol
The ordered build sequence for Phase 1. Each entry is one atomic unit of work with one owner and one test gate. No commit is made without Eran's approval. Stored in `commit-protocol.md` (index) and `commit-specs/` (full specs).

### Gate wave
The batch of reviewer agents (Viktor, Sage, Mira) that runs after every 5th commit. Viktor always runs. Sage runs conditionally (auth, secrets, external API commits). Mira runs conditionally (user-facing behavior changes). See AGENTS.md.

### handoff
A structured note passed between agents at commit boundaries. Written by the outgoing agent in their worklog; received by the next agent before they begin. Handoffs carry decisions, interface contracts, or constraints that aren't visible from the code alone.

### LLMService
The project's LLM provider interface, defined in `backend/app/services/llm.py`. Wraps either `ollama` or `openai` as the provider (injected at construction). Exposes two async methods: `chat()` for streaming text generation and `embed()` for vector embeddings. Phase 1: both methods raise `NotImplementedError`. Phase 2 (Nova): implements both without changing the signature. Routes always call this interface, never the provider SDK directly.

### RAGPolicy / RAGLogistics
Service stubs for retrieval-augmented generation. `RAGPolicy` (`rag_policy.py`) queries policy document embeddings stored in pgvector. `RAGLogistics` (`rag_logistics.py`) queries logistics and shipment data for the logistics chat flow. Both raise `NotImplementedError` in Phase 1; Phase 2/3 implements `query()`.

### IngestionService
Service stub for document ingestion into the pgvector store, defined in `backend/app/services/ingestion.py`. Phase 2/3 will implement `ingest()` to parse, chunk, embed, and persist documents. Raises `NotImplementedError` in Phase 1.

### EmbeddingService
The deployment-wide embedding provider class, defined in `backend/app/services/llm.py` (C25). Separate from `LLMService` — the chat generation provider (Ollama or OpenAI) and the embedding provider are independent concerns. Exposes `embed_documents(texts)` and `embed_query(text)`. All ingestion and retrieval use the same configured profile; a conversation's chat provider never changes the vector space.

### EmbeddingProfile
Dataclass holding the three embedding parameters: `provider` (ollama/openai), `model` (e.g. `nomic-embed-text`), and `dimensions` (768). Retrieved via `EmbeddingService.profile`. Ingestion stores this profile; retrieval asserts the current profile matches what was used at index time.

### ChatMessage
Typed dict `{"role": "user"|"assistant", "content": str}` used as elements of the `messages` argument to `LLMService.chat()`. Routes pass a list of `ChatMessage`s; the service forwards them to the provider without coupling routes to provider SDK types.

### policy chunk
One atomic fragment of a policy document, stored as a row in `policy_chunks`. Each chunk has an `embedding` vector (768 dimensions) and a `source_label` identifying its parent document and page/section range. The retrieval pipeline scores chunks by cosine similarity to the query embedding and returns the top-k as grounding context for generation.

### RAG (Retrieval-Augmented Generation)
The pattern of fetching semantically relevant context from a store before generating a response. In Manifesto: a user query is embedded → top-k policy chunks retrieved by cosine similarity → chunks injected into the generation prompt as grounding context. The LLM generates only within the retrieved evidence, reducing hallucination.

### HNSW index
Hierarchical Navigable Small World — a graph-based approximate nearest-neighbor index. C26 migrates `policy_chunks.embedding` from IVFFlat to HNSW, which offers better query-time performance at the cost of higher build time and memory. Created via pgvector's `USING hnsw` clause.

### hybrid retrieval
Combining vector similarity search (embedding-based) with lexical search (keyword/tsvector-based) to improve retrieval quality. Pure vector search can miss exact keyword matches; pure lexical search misses semantic synonyms. Planned for C29 (rag-policy-pipeline).

### tiktoken
OpenAI's tokenizer library for counting tokens in a text string. Added in C24. Used by `LLMService` to estimate prompt token counts for logging and budget enforcement without calling the API.

---

*This document is updated by Claude when a new term is introduced that would be ambiguous or non-obvious to a reader unfamiliar with this project's conventions.*
