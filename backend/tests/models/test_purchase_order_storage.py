"""Integration tests for the C41 purchase_orders storage schema.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service: db=manifesto, user=manifesto, pass=manifesto, resolved via
DATABASE_URL inside the backend container) and require migrations up to
``0002_rag_storage_hardening`` to be applied before this test module runs the
``0003_purchase_order_storage`` migration itself.

Each model-level test runs inside its own transaction that is rolled back on
teardown, so tests do not leak rows into each other or require manual cleanup.

Covers:
- A valid purchase order persists with its vendor and buyer identifiers.
- Duplicate order numbers violate uq_purchase_orders_order_number.
- Invalid statuses violate purchase_order_status_check.
- The 0003 migration upgrade creates purchase_orders and downgrade removes it
  without affecting other tables.
"""

from __future__ import annotations

import asyncio
import datetime
import os
import uuid

import pytest
import pytest_asyncio
from alembic import command
from alembic.config import Config
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.purchase_order import PurchaseOrder
from app.models.user import User
from app.models.vendor import Vendor

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

_NOW = datetime.datetime.now(datetime.timezone.utc)
_LATER = _NOW + datetime.timedelta(days=7)


@pytest.fixture(scope="module", autouse=True)
def _apply_head_migration():
    """Ensure purchase_orders exists before the model-level tests run."""
    command.upgrade(Config("alembic.ini"), "head")


@pytest_asyncio.fixture
async def session():
    """Yield an AsyncSession bound to a transaction that is rolled back after the test."""
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            trans = await conn.begin()
            session_factory = async_sessionmaker(bind=conn, expire_on_commit=False, join_transaction_mode="create_savepoint")
            async with session_factory() as sess:
                yield sess
            await trans.rollback()
    finally:
        await engine.dispose()


async def _make_vendor_and_buyer(session: AsyncSession) -> tuple[str, str]:
    vendor = Vendor(name="Test Vendor " + uuid.uuid4().hex[:8])
    buyer = User(
        name="Test Buyer",
        email=f"buyer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        role="employee",
    )
    session.add_all([vendor, buyer])
    await session.flush()
    return vendor.id, buyer.id


def _make_order(vendor_id: str, buyer_id: str, **overrides) -> PurchaseOrder:
    defaults = dict(
        order_number="PO-" + uuid.uuid4().hex[:12],
        vendor_id=vendor_id,
        buyer_id=buyer_id,
        ordered_at=_NOW,
        requested_delivery_at=_LATER,
    )
    defaults.update(overrides)
    return PurchaseOrder(**defaults)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_purchase_order_persists_with_vendor_and_buyer(session: AsyncSession):
    vendor_id, buyer_id = await _make_vendor_and_buyer(session)

    order = _make_order(vendor_id, buyer_id)
    session.add(order)
    await session.flush()
    await session.refresh(order)

    assert order.id is not None
    assert order.vendor_id == vendor_id
    assert order.buyer_id == buyer_id
    assert order.status == "approved"


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_order_number_rejected(session: AsyncSession):
    vendor_id, buyer_id = await _make_vendor_and_buyer(session)
    order_number = "PO-" + uuid.uuid4().hex[:12]

    order1 = _make_order(vendor_id, buyer_id, order_number=order_number)
    session.add(order1)
    await session.flush()

    order2 = _make_order(vendor_id, buyer_id, order_number=order_number)
    session.add(order2)

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_invalid_status_rejected_by_check_constraint(session: AsyncSession):
    vendor_id, buyer_id = await _make_vendor_and_buyer(session)

    order = _make_order(vendor_id, buyer_id, status="bogus")
    session.add(order)

    with pytest.raises(DBAPIError):
        await session.flush()


# ---------------------------------------------------------------------------
# Migration upgrade/downgrade
# ---------------------------------------------------------------------------


def _table_names() -> list[str]:
    async def _inspect() -> list[str]:
        engine = create_async_engine(DB_URL, echo=False)
        try:
            async with engine.connect() as conn:
                return await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
        finally:
            await engine.dispose()

    return asyncio.run(_inspect())


def test_migration_upgrade_creates_table_and_downgrade_removes_it():
    cfg = Config("alembic.ini")

    command.upgrade(cfg, "head")
    tables = _table_names()
    assert "purchase_orders" in tables
    assert "policy_documents" in tables

    command.downgrade(cfg, "0002_rag_storage_hardening")
    tables = _table_names()
    assert "purchase_orders" not in tables
    assert "policy_documents" in tables

    command.upgrade(cfg, "head")
    tables = _table_names()
    assert "purchase_orders" in tables
    assert "policy_documents" in tables
