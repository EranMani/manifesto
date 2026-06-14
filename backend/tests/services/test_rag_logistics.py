"""Tests for backend/app/services/rag_logistics.py — shipment identifier lookup.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service, resolved via DATABASE_URL inside the backend container). Each test
runs inside its own transaction that is rolled back on teardown.
"""

from __future__ import annotations

import datetime
import os
import uuid

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.shipment import Shipment
from app.models.vendor import Vendor
from app.services.rag_logistics import (
    ShipmentEvidence,
    ShipmentNotFoundError,
    lookup_shipment,
)

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)

_NOW = datetime.datetime.now(datetime.timezone.utc)
_LATER = _NOW + datetime.timedelta(days=5)


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


async def _make_shipment(session: AsyncSession, **overrides) -> Shipment:
    vendor = Vendor(name="Test Vendor " + uuid.uuid4().hex[:8])
    session.add(vendor)
    await session.flush()

    defaults = dict(
        tracking_code="TRK-" + uuid.uuid4().hex[:12].upper(),
        vendor_id=vendor.id,
        origin="Shenzhen, CN",
        destination="Los Angeles, US",
        dispatched_at=_NOW,
        expected_arrival_at=_LATER,
    )
    defaults.update(overrides)
    shipment = Shipment(**defaults)
    session.add(shipment)
    await session.flush()
    return shipment


@pytest.mark.asyncio
async def test_identifier_lookup_resolves_known_shipment(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )

    evidence = await lookup_shipment(session, f"  {shipment.tracking_code.lower()}  ")

    assert isinstance(evidence, ShipmentEvidence)
    assert evidence.id == shipment.id
    assert evidence.tracking_code == shipment.tracking_code
    assert evidence.status == "delayed"
    assert evidence.origin == "Shenzhen, CN"
    assert evidence.destination == "Los Angeles, US"
    assert evidence.dispatched_at == shipment.dispatched_at
    assert evidence.expected_arrival_at == shipment.expected_arrival_at
    assert evidence.actual_arrival_at is None
    assert evidence.delay_reason == "Customs hold"


@pytest.mark.asyncio
async def test_identifier_lookup_unknown_identifier_raises(session: AsyncSession):
    with pytest.raises(ShipmentNotFoundError):
        await lookup_shipment(session, "TRK-DOES-NOT-EXIST")


@pytest.mark.asyncio
async def test_identifier_lookup_blank_identifier_raises(session: AsyncSession):
    with pytest.raises(ShipmentNotFoundError):
        await lookup_shipment(session, "   ")


@pytest.mark.asyncio
async def test_identifier_lookup_executes_no_write_statement(session: AsyncSession):
    shipment = await _make_shipment(session)
    session.expunge_all()

    await lookup_shipment(session, shipment.tracking_code)

    assert not session.new
    assert not session.dirty
    assert not session.deleted
