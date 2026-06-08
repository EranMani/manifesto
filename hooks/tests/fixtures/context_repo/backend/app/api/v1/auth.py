from app.schemas.auth import LoginRequest
from app.services.auth import authenticate


async def login(request: LoginRequest) -> str:
    return await authenticate(request.email, request.password)
