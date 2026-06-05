import datetime

from pydantic import BaseModel


class ProductBase(BaseModel):
    shipment_id: str
    category_id: str | None = None
    name: str
    description: str | None = None
    quantity: int = 0
    unit: str | None = None


class ProductCreate(ProductBase):
    pass


class ProductRead(ProductBase):
    id: str
    added_by: str | None
    created_at: datetime.datetime

    model_config = {"from_attributes": True}


class ProductUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    quantity: int | None = None
    unit: str | None = None
    category_id: str | None = None
