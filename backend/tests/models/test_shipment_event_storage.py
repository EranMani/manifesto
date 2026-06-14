"""Integration tests for the C43 shipment_events storage schema.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service: db=manifesto, user=manifesto, pass=manifesto, resolved via
DATABASE_URL inside the backend container) and require migrations up to
``0004_shipment_lifecycle_fields`` to be applied before this test module runs
the ``0005_shipment_event_storage`` migration itself.

Each model-level test runs inside its own transaction that is rolled back on
teardown, so tests do not leak rows into each other or require manual cleanup.

Covers:
- Shipment events persist and sort deterministically by (occurred_at, id).
- Invalid event types violate shipment_event_type_check.
- Deleting a shipment cascades to delete its events.
- The 0005 migration upgrade creates shipment_events and downgrade removes it
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
from sqlalchemy import inspect, select
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.vendor import Vendor

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

_NOW = datetime.datetime.now(datetime.timezone.utc)


@pytest.fixture(scope="module", autouse=True)
def _apply_head_migration():
    """Ensure shipment_events exists before the model-level tests run."""
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


async def _make_shipment(session: AsyncSession) -> str:
    vendor = Vendor(name="Test Vendor " + uuid.uuid4().hex[:8])
    session.add(vendor)
    await session.flush()

    shipment = Shipment(
        tracking_code="TRK-" + uuid.uuid4().hex[:12],
        vendor_id=vendor.id,
        origin="Shenzhen, CN",
        destination="Los Angeles, US",
        dispatched_at=_NOW,
        expected_arrival_at=_NOW + datetime.timedelta(days=5),
    )
    session.add(shipment)
    await session.flush()
    return shipment.id


def _make_event(shipment_id: str, **overrides) -> ShipmentEvent:
    defaults = dict(
        shipment_id=shipment_id,
        event_type="dispatched",
        occurred_at=_NOW,
        location="Shenzhen, CN",
    )
    defaults.update(overrides)
    return ShipmentEvent(**defaults)


# ---------------------------------------------------------------------------
# Persistence and ordering
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_events_sort_deterministically_by_occurred_at(session: AsyncSession):
    shipment_id = await _make_shipment(session)

    later = _make_event(shipment_id, event_type="departed", occurred_at=_NOW + datetime.timedelta(days=1), location="Port of Shenzhen")
    earlier = _make_event(shipment_id, event_type="ordered", occurred_at=_NOW, location="Shenzhen, CN")
    session.add_all([later, earlier])
    await session.flush()

    result = await session.execute(
        select(ShipmentEvent)
        .where(ShipmentEvent.shipment_id == shipment_id)
        .order_by(ShipmentEvent.occurred_at, ShipmentEvent.id)
    )
    events = result.scalars().all()

    assert [e.event_type for e in events] == ["ordered", "departed"]


# ---------------------------------------------------------------------------
# Constraints
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_invalid_event_type_rejected_by_check_constraint(session: AsyncSession):
    shipment_id = await _make_shipment(session)

    event = _make_event(shipment_id, event_type="bogus")
    session.add(event)

    with pytest.raises(DBAPIError):
        await session.flush()


@pytest.mark.asyncio
async def test_deleting_shipment_cascades_to_events(session: AsyncSession):
    shipment_id = await _make_shipment(session)

    event = _make_event(shipment_id)
    session.add(event)
    await session.flush()

    shipment = await session.get(Shipment, shipment_id)
    await session.delete(shipment)
    await session.flush()

    result = await session.execute(select(ShipmentEvent).where(ShipmentEvent.shipment_id == shipment_id))
    assert result.scalars().all() == []


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
    assert "shipment_events" in tables
    assert "shipments" in tables

    command.downgrade(cfg, "0004_shipment_lifecycle_fields")
    tables = _table_names()
    assert "shipment_events" not in tables
    assert "shipments" in tables

    command.upgrade(cfg, "head")
    tables = _table_names()
    assert "shipment_events" in tables
    assert "shipments" in tables
