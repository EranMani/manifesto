"""shipment event storage

Revision ID: 0005_shipment_event_storage
Revises: 0004_shipment_lifecycle_fields
Create Date: 2026-06-14 00:00:00.000000

Adds the shipment_events table, an ordered event timeline per shipment with
cascade delete and a deterministic chronology index.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0005_shipment_event_storage"
down_revision: Union[str, None] = "0004_shipment_lifecycle_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "shipment_events",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shipment_id", UUID(as_uuid=False), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("location", sa.String(), nullable=False),
        sa.Column("details", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )
    op.create_check_constraint(
        "shipment_event_type_check",
        "shipment_events",
        "event_type IN ('ordered', 'dispatched', 'departed', 'arrived_hub', 'customs_hold', "
        "'customs_released', 'delay_reported', 'damaged', 'partial_delivery', 'delivered', "
        "'cancelled', 'returned', 'lost')",
    )
    op.create_index("ix_shipment_events_timeline", "shipment_events", ["shipment_id", "occurred_at", "id"])


def downgrade() -> None:
    op.drop_index("ix_shipment_events_timeline", table_name="shipment_events")
    op.drop_table("shipment_events")
