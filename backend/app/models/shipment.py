from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import datetime

ShipmentStatus = Literal[
    "pending",
    "in_transit",
    "delayed",
    "delivered",
    "partial",
    "damaged",
    "cancelled",
    "returned",
    "lost",
]


class Shipment(Base):
    __tablename__ = "shipments"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    tracking_code: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    vendor_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="CASCADE"), nullable=False)
    purchase_order_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)
    origin: Mapped[str] = mapped_column(String, nullable=False)
    destination: Mapped[str] = mapped_column(String, nullable=False)
    status: Mapped[ShipmentStatus] = mapped_column(String, nullable=False, server_default="pending")
    dispatched_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    expected_arrival_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    actual_arrival_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    delay_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    notes: Mapped[str | None] = mapped_column(String, nullable=True)
    client_id: Mapped[str | None] = mapped_column(UUID(as_uuid=False), ForeignKey("clients.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "status IN ('pending', 'in_transit', 'delayed', 'delivered', 'partial', 'damaged', 'cancelled', 'returned', 'lost')",
            name="shipment_status_check",
        ),
    )
