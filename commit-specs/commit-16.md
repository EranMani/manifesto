# Commit 16 — `llm-service-stub` · Rex

**Phase:** 1E — Service Stubs
**Assignee:** Rex (Backend)
**Depends on:** C15 (stub-routes)

---

## What

Define the LLMService interface and service stubs for Phase 2/3.
Raises NotImplementedError everywhere — no actual LLM calls.
This establishes the interface contract that Phase 2 will implement against.

---

## Files to Create

| File | Type | Description |
|---|---|---|
| `backend/app/services/llm.py` | new | LLMService class — interface only |
| `backend/app/services/rag_policy.py` | new | Stub |
| `backend/app/services/rag_logistics.py` | new | Stub |
| `backend/app/services/ingestion.py` | new | Stub |

---

## llm.py Interface

```python
from typing import AsyncIterator, Literal

class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]) -> None:
        self.provider = provider

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = True
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError
```

---

## Done When

- [ ] `from app.services.llm import LLMService` imports without error
- [ ] `LLMService("openai")` and `LLMService("ollama")` instantiate without error
- [ ] Calling `chat()` or `embed()` raises `NotImplementedError`
- [ ] All 4 service files exist and import cleanly

---

## Handoffs Out

→ Nova (Phase 2): `LLMService.chat()` signature is `messages: list[dict[str, str]], stream: bool = True → AsyncIterator[str]`. `embed()` returns `list[float]`. Implement both methods — do not change the signature.
