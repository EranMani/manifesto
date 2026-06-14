"""Integration tests for the C42 shipment lifecycle fields.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service: db=manifesto, user=manifesto, pass=manifesto, resolved via
DATABASE_URL inside the backend container) and require migrations up to
``0003_purchase_order_storage`` to be applied before this test module runs the
``0004_shipment_lifecycle_fields`` migration itself.

Each model-level test runs inside its own transaction that is rolled back on
teardown, so tests do not leak rows into each other or require manual cleanup.

Covers:
- A valid shipment row persists with its lifecycle fields and vendor link.
- Duplicate tracking codes violate uq_shipments_tracking_code.
- Invalid statuses violate shipment_status_check.
- Missing required route/timing fields violate their NOT NULL constraints.
- The 0004 migration upgrade adds the lifecycle columns and downgrade removes
  them without affecting other tables.
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
from sqlalchemy import inspect
from sqlalchemy.exc import IntegrityError, DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.shipment import Shipment
from app.models.vendor import Vendor

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

_NOW = datetime.datetime.now(datetime.timezone.utc)
_LATER = _NOW + datetime.timedelta(days=5)


@pytest.fixture(scope="module", autouse=True)
def _apply_head_migration():
    """Ensure the lifecycle columns exist before the model-level tests run."""
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


async def _make_vendor(session: AsyncSession) -> str:
    vendor = Vendor(name="Test Vendor " + uuid.uuid4().hex[:8])
    session.add(vendor)
    await session.flush()
    return vendor.id


def _make_shipment(vendor_id: str, **overrides) -> Shipment:
    defaults = dict(
        tracking_code="TRK-" + uuid.uuid4().hex[:12],
        vendor_id=vendor_id,
        origin="Shenzhen, CN",
        destination="Los Angeles, US",
        dispatched_at=_NOW,
        expected_arrival_at=_LATER,
    )
    defaults.update(overrides)
    return Shipment(**defaults)


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_shipment_persists_with_lifecycle_fields(session: AsyncSession):
    vendor_id = await _make_vendor(session)

    shipment = _make_shipment(vendor_id)
    session.add(shipment)
    await session.flush()
    await session.refresh(shipment)

    assert shipment.id is not None
    assert shipment.vendor_id == vendor_id
    assert shipment.purchase_order_id is None
    assert shipment.status == "pending"
    assert shipment.actual_arrival_at is None
    assert shipment.delay_reason is None


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_duplicate_tracking_code_rejected(session: AsyncSession):
    vendor_id = await _make_vendor(session)
    tracking_code = "TRK-" + uuid.uuid4().hex[:12]

    shipment1 = _make_shipment(vendor_id, tracking_code=tracking_code)
    session.add(shipment1)
    await session.flush()

    shipment2 = _make_shipment(vendor_id, tracking_code=tracking_code)
    session.add(shipment2)

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_invalid_status_rejected_by_check_constraint(session: AsyncSession):
    vendor_id = await _make_vendor(session)

    shipment = _make_shipment(vendor_id, status="bogus")
    session.add(shipment)

    with pytest.raises(DBAPIError):
        await session.flush()


@pytest.mark.asyncio
async def test_missing_required_route_field_rejected(session: AsyncSession):
    vendor_id = await _make_vendor(session)

    shipment = _make_shipment(vendor_id, origin=None)
    session.add(shipment)

    with pytest.raises(IntegrityError):
        await session.flush()


@pytest.mark.asyncio
async def test_missing_required_timing_field_rejected(session: AsyncSession):
    vendor_id = await _make_vendor(session)

    shipment = _make_shipment(vendor_id, dispatched_at=None)
    session.add(shipment)

    with pytest.raises(IntegrityError):
        await session.flush()


# ---------------------------------------------------------------------------
# Migration upgrade/downgrade
# ---------------------------------------------------------------------------


def _shipment_columns() -> list[str]:
    async def _inspect() -> list[str]:
        engine = create_async_engine(DB_URL, echo=False)
        try:
            async with engine.connect() as conn:
                return await conn.run_sync(lambda sync_conn: [c["name"] for c in inspect(sync_conn).get_columns("shipments")])
        finally:
            await engine.dispose()

    return asyncio.run(_inspect())


def test_migration_upgrade_adds_lifecycle_columns_and_downgrade_removes_them():
    cfg = Config("alembic.ini")

    command.upgrade(cfg, "head")
    columns = _shipment_columns()
    assert "tracking_code" in columns
    assert "purchase_order_id" in columns
    assert "actual_arrival_at" in columns
    assert "arrived_at" not in columns

    command.downgrade(cfg, "-1")
    columns = _shipment_columns()
    assert "tracking_code" not in columns
    assert "arrived_at" in columns
    assert "actual_arrival_at" not in columns

    command.upgrade(cfg, "head")
    columns = _shipment_columns()
    assert "tracking_code" in columns
    assert "actual_arrival_at" in columns
