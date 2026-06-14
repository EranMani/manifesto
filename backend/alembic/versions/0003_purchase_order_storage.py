"""purchase order storage

Revision ID: 0003_purchase_order_storage
Revises: 0002_rag_storage_hardening
Create Date: 2026-06-14 00:00:00.000000

Adds the purchase_orders table linking one internal buyer (users) to one vendor
(vendors). Shipment linkage and lifecycle fields are deferred to C42.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0003_purchase_order_storage"
down_revision: Union[str, None] = "0002_rag_storage_hardening"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "purchase_orders",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_number", sa.String(), nullable=False),
        sa.Column("vendor_id", UUID(as_uuid=False), sa.ForeignKey("vendors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("buyer_id", UUID(as_uuid=False), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("requested_delivery_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False, server_default="approved"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
        sa.UniqueConstraint("order_number", name="uq_purchase_orders_order_number"),
        sa.CheckConstraint(
            "status IN ('draft', 'approved', 'fulfilled', 'cancelled')",
            name="purchase_order_status_check",
        ),
    )


def downgrade() -> None:
    op.drop_table("purchase_orders")
