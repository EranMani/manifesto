"""add status_reason column

Revision ID: 0007_add_status_reason
Revises: 0006_client_shipment_items
Create Date: 2026-06-21 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "0007_add_status_reason"
down_revision: Union[str, None] = "0006_client_shipment_items"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("shipments", sa.Column("status_reason", sa.String(), nullable=True))


def downgrade() -> None:
    op.drop_column("shipments", "status_reason")
