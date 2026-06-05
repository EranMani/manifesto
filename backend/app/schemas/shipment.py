import datetime

from pydantic import BaseModel


class ShipmentBase(BaseModel):
    vendor_id: str
    arrived_at: datetime.datetime
    notes: str | None = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentRead(ShipmentBase):
    id: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
