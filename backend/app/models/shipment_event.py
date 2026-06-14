from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import datetime

ShipmentEventType = Literal[
    "ordered",
    "dispatched",
    "departed",
    "arrived_hub",
    "customs_hold",
    "customs_released",
    "delay_reported",
    "damaged",
    "partial_delivery",
    "delivered",
    "cancelled",
    "returned",
    "lost",
]


class ShipmentEvent(Base):
    __tablename__ = "shipment_events"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    shipment_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False)
    event_type: Mapped[ShipmentEventType] = mapped_column(String, nullable=False)
    occurred_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    location: Mapped[str] = mapped_column(String, nullable=False)
    details: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "event_type IN ('ordered', 'dispatched', 'departed', 'arrived_hub', 'customs_hold', "
            "'customs_released', 'delay_reported', 'damaged', 'partial_delivery', 'delivered', "
            "'cancelled', 'returned', 'lost')",
            name="shipment_event_type_check",
        ),
        Index("ix_shipment_events_timeline", "shipment_id", "occurred_at", "id"),
    )
