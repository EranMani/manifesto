class IngestionService:
    async def ingest(self, document_id: str, content: str) -> None:
        raise NotImplementedError
