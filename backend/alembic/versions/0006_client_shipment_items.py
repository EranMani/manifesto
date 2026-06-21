"""client shipment items refactor

Revision ID: 0006_client_shipment_items
Revises: 0005_shipment_event_storage
Create Date: 2026-06-21 00:00:00.000000

Creates the clients table, shipment_items join table, adds client_id FK to
shipments, migrates existing product-shipment relationships to shipment_items,
and makes products.shipment_id nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID


# revision identifiers, used by Alembic.
revision: str = "0006_client_shipment_items"
down_revision: Union[str, None] = "0005_shipment_event_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "clients",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("contact", sa.String(), nullable=True),
        sa.Column("email", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("badge_color", sa.String(), nullable=False, server_default=sa.text("'#6366f1'")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.create_table(
        "shipment_items",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("shipment_id", UUID(as_uuid=False), sa.ForeignKey("shipments.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", UUID(as_uuid=False), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()")),
    )

    op.add_column(
        "shipments",
        sa.Column("client_id", UUID(as_uuid=False), sa.ForeignKey("clients.id", ondelete="SET NULL"), nullable=True),
    )

    op.execute(
        "INSERT INTO shipment_items (shipment_id, product_id, quantity) "
        "SELECT shipment_id, id, quantity FROM products WHERE shipment_id IS NOT NULL"
    )

    op.alter_column("products", "shipment_id", nullable=True)


def downgrade() -> None:
    op.execute(
        "UPDATE products SET shipment_id = si.shipment_id "
        "FROM shipment_items si WHERE si.product_id = products.id"
    )
    op.alter_column("products", "shipment_id", nullable=False)

    op.drop_column("shipments", "client_id")
    op.drop_table("shipment_items")
    op.drop_table("clients")
