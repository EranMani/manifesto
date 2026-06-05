from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("/conversations")
async def create_conversation():
    return JSONResponse({"detail": "Not implemented"}, status_code=501)


@router.get("/conversations")
async def list_conversations():
    return JSONResponse({"detail": "Not implemented"}, status_code=501)


@router.get("/conversations/{conversation_id}/messages")
async def get_messages(conversation_id: str):
    return JSONResponse({"detail": "Not implemented"}, status_code=501)


@router.post("/conversations/{conversation_id}/messages")
async def create_message(conversation_id: str):
    return JSONResponse({"detail": "Not implemented"}, status_code=501)
