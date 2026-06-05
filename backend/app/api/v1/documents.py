from fastapi import APIRouter
from fastapi.responses import JSONResponse

router = APIRouter()


@router.post("")
async def upload_document():
    return JSONResponse({"detail": "Not implemented"}, status_code=501)


@router.get("")
async def list_documents():
    return JSONResponse({"detail": "Not implemented"}, status_code=501)
