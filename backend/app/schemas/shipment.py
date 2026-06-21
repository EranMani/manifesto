import datetime

from pydantic import BaseModel

from app.models.shipment import ShipmentStatus


class ShipmentBase(BaseModel):
    tracking_code: str
    vendor_id: str
    purchase_order_id: str | None = None
    client_id: str | None = None
    origin: str
    destination: str
    status: ShipmentStatus = "pending"
    dispatched_at: datetime.datetime
    expected_arrival_at: datetime.datetime
    actual_arrival_at: datetime.datetime | None = None
    delay_reason: str | None = None
    notes: str | None = None


class ShipmentItemCreate(BaseModel):
    product_id: str
    quantity: int


class ShipmentCreate(ShipmentBase):
    items: list[ShipmentItemCreate] = []


class ShipmentRead(ShipmentBase):
    id: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
