from typing import Literal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base
import datetime

PurchaseOrderStatus = Literal["draft", "approved", "fulfilled", "cancelled"]


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, server_default=text("gen_random_uuid()"))
    order_number: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    vendor_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False)
    buyer_id: Mapped[str] = mapped_column(UUID(as_uuid=False), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    ordered_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    requested_delivery_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[PurchaseOrderStatus] = mapped_column(String, nullable=False, server_default="approved")
    created_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'approved', 'fulfilled', 'cancelled')",
            name="purchase_order_status_check",
        ),
    )
