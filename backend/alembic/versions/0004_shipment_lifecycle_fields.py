"""shipment lifecycle fields

Revision ID: 0004_shipment_lifecycle_fields
Revises: 0003_purchase_order_storage
Create Date: 2026-06-14 00:00:00.000000

Adds shipment identity (tracking_code), purchase-order linkage, route, timing,
status, and delay reason fields to shipments. Replaces the legacy arrived_at
column with nullable actual_arrival_at. Event history is deferred to C43.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0004_shipment_lifecycle_fields"
down_revision: Union[str, None] = "0003_purchase_order_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("tracking_code", sa.String(), nullable=False))
    op.create_unique_constraint("uq_shipments_tracking_code", "shipments", ["tracking_code"])

    op.add_column(
        "shipments",
        sa.Column("purchase_order_id", UUID(as_uuid=False), sa.ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_shipments_purchase_order_id", "shipments", ["purchase_order_id"])

    op.add_column("shipments", sa.Column("origin", sa.String(), nullable=False))
    op.add_column("shipments", sa.Column("destination", sa.String(), nullable=False))

    op.add_column("shipments", sa.Column("status", sa.String(), nullable=False, server_default="pending"))
    op.create_check_constraint(
        "shipment_status_check",
        "shipments",
        "status IN ('pending', 'in_transit', 'delayed', 'delivered', 'partial', 'damaged', 'cancelled', 'returned', 'lost')",
    )
    op.create_index("ix_shipments_status", "shipments", ["status"])

    op.add_column("shipments", sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=False))
    op.add_column("shipments", sa.Column("expected_arrival_at", sa.DateTime(timezone=True), nullable=False))

    op.alter_column("shipments", "arrived_at", new_column_name="actual_arrival_at", nullable=True)

    op.add_column("shipments", sa.Column("delay_reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shipments", "delay_reason")
    op.alter_column("shipments", "actual_arrival_at", new_column_name="arrived_at", nullable=False)
    op.drop_column("shipments", "expected_arrival_at")
    op.drop_column("shipments", "dispatched_at")
    op.drop_index("ix_shipments_status", table_name="shipments")
    op.drop_constraint("shipment_status_check", "shipments", type_="check")
    op.drop_column("shipments", "status")
    op.drop_column("shipments", "destination")
    op.drop_column("shipments", "origin")
    op.drop_index("ix_shipments_purchase_order_id", table_name="shipments")
    op.drop_column("shipments", "purchase_order_id")
    op.drop_constraint("uq_shipments_tracking_code", "shipments", type_="unique")
    op.drop_column("shipments", "tracking_code")
