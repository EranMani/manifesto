import datetime

from pydantic import BaseModel

from app.models.shipment import ShipmentStatus


class ShipmentBase(BaseModel):
    tracking_code: str
    vendor_id: str
    purchase_order_id: str | None = None
    origin: str
    destination: str
    status: ShipmentStatus = "pending"
    dispatched_at: datetime.datetime
    expected_arrival_at: datetime.datetime
    actual_arrival_at: datetime.datetime | None = None
    delay_reason: str | None = None
    notes: str | None = None


class ShipmentCreate(ShipmentBase):
    pass


class ShipmentRead(ShipmentBase):
    id: str
    created_at: datetime.datetime

    model_config = {"from_attributes": True}
