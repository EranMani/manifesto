from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel


class UserRead(BaseModel):
    id: UUID
    name: str
    email: str
    role: str
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserCreate(BaseModel):
    name: str
    email: str
    password: str
    role: Literal["admin", "manager", "employee"]


class UserUpdate(BaseModel):
    name: str | None = None
    email: str | None = None
    password: str | None = None
    role: Literal["admin", "manager", "employee"] | None = None
    is_active: bool | None = None
