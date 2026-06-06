from typing import AsyncIterator, Literal


class LLMService:
    def __init__(self, provider: Literal["ollama", "openai"]) -> None:
        self.provider = provider

    async def chat(
        self,
        messages: list[dict[str, str]],
        stream: bool = True,
    ) -> AsyncIterator[str]:
        raise NotImplementedError

    async def embed(self, text: str) -> list[float]:
        raise NotImplementedError
