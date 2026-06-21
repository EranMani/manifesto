import datetime

from pydantic import BaseModel


class ClientRead(BaseModel):
    id: str
    name: str
    contact: str | None
    email: str | None
    country: str | None
    badge_color: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ClientCreate(BaseModel):
    name: str
    contact: str | None = None
    email: str | None = None
    country: str | None = None
    badge_color: str = "#6366f1"


class ClientUpdate(BaseModel):
    name: str | None = None
    contact: str | None = None
    email: str | None = None
    country: str | None = None
    badge_color: str | None = None
