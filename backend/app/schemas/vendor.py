import datetime

from pydantic import BaseModel


class VendorRead(BaseModel):
    id: str
    name: str
    contact: str | None
    email: str | None
    country: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class VendorCreate(BaseModel):
    name: str
    contact: str | None = None
    email: str | None = None
    country: str | None = None


class VendorUpdate(BaseModel):
    name: str | None = None
    contact: str | None = None
    email: str | None = None
    country: str | None = None
