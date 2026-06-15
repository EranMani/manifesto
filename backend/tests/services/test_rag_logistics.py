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

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.user import User
from app.models.vendor import Vendor
from app.services.rag_logistics import (
    ProcurementEvidence,
    ShipmentEvidence,
    ShipmentNotFoundError,
    lookup_procurement,
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


async def _make_buyer(session: AsyncSession) -> User:
    buyer = User(
        name="Test Buyer",
        email=f"buyer-{uuid.uuid4().hex[:8]}@example.com",
        password_hash="x",
        role="employee",
    )
    session.add(buyer)
    await session.flush()
    return buyer


async def _make_purchase_order(session: AsyncSession, vendor_id: str, buyer_id: str, **overrides) -> PurchaseOrder:
    defaults = dict(
        order_number="PO-" + uuid.uuid4().hex[:12],
        vendor_id=vendor_id,
        buyer_id=buyer_id,
        ordered_at=_NOW,
        requested_delivery_at=_LATER,
    )
    defaults.update(overrides)
    order = PurchaseOrder(**defaults)
    session.add(order)
    await session.flush()
    return order


async def _make_product(session: AsyncSession, shipment_id: str, **overrides) -> Product:
    defaults = dict(
        shipment_id=shipment_id,
        name="Widget",
        quantity=1,
    )
    defaults.update(overrides)
    product = Product(**defaults)
    session.add(product)
    await session.flush()
    return product


async def _make_event(session: AsyncSession, shipment_id: str, **overrides) -> ShipmentEvent:
    defaults = dict(
        shipment_id=shipment_id,
        event_type="dispatched",
        occurred_at=_NOW,
        location="Shenzhen, CN",
    )
    defaults.update(overrides)
    event = ShipmentEvent(**defaults)
    session.add(event)
    await session.flush()
    return event


@pytest.mark.asyncio
async def test_timeline_orders_events_by_occurred_at_then_id(session: AsyncSession):
    shipment = await _make_shipment(session)

    middle = await _make_event(
        session, shipment.id, event_type="departed", occurred_at=_NOW + datetime.timedelta(hours=1)
    )
    earliest = await _make_event(
        session, shipment.id, event_type="ordered", occurred_at=_NOW
    )
    latest = await _make_event(
        session, shipment.id, event_type="arrived_hub", occurred_at=_NOW + datetime.timedelta(hours=2)
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert isinstance(evidence, ProcurementEvidence)
    assert [event.id for event in evidence.timeline] == [earliest.id, middle.id, latest.id]
    assert [event.event_type for event in evidence.timeline] == [
        "ordered",
        "departed",
        "arrived_hub",
    ]


@pytest.mark.asyncio
async def test_timeline_orders_simultaneous_events_by_id(session: AsyncSession):
    shipment = await _make_shipment(session)

    first = await _make_event(session, shipment.id, event_type="ordered", occurred_at=_NOW)
    second = await _make_event(session, shipment.id, event_type="dispatched", occurred_at=_NOW)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    expected_order = sorted([first.id, second.id])
    assert [event.id for event in evidence.timeline] == expected_order


@pytest.mark.asyncio
async def test_timeline_delay_evidence_maps_to_latest_exception_event(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="delayed",
        delay_reason="Customs hold",
        actual_arrival_at=None,
    )

    await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=1),
        details="First delay notice",
    )
    latest_exception = await _make_event(
        session,
        shipment.id,
        event_type="delay_reported",
        occurred_at=_NOW + datetime.timedelta(hours=2),
        details="Customs hold confirmed",
    )
    await _make_event(
        session,
        shipment.id,
        event_type="customs_hold",
        occurred_at=_NOW + datetime.timedelta(hours=3),
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is not None
    assert evidence.delay.reason == "Customs hold"
    assert evidence.delay.exception_event is not None
    assert evidence.delay.exception_event.id == latest_exception.id
    assert evidence.delay.exception_event.details == "Customs hold confirmed"


@pytest.mark.asyncio
async def test_timeline_delay_evidence_absent_for_on_track_shipment(session: AsyncSession):
    shipment = await _make_shipment(session, status="in_transit")

    await _make_event(session, shipment.id, event_type="dispatched", occurred_at=_NOW)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is None


@pytest.mark.asyncio
async def test_timeline_delay_evidence_without_reason_is_not_invented(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="lost",
        delay_reason=None,
        actual_arrival_at=None,
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is None


@pytest.mark.asyncio
async def test_timeline_delay_evidence_without_supporting_event_has_no_exception_event(session: AsyncSession):
    shipment = await _make_shipment(
        session,
        status="damaged",
        delay_reason="Container damaged in transit",
        actual_arrival_at=None,
    )

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.delay is not None
    assert evidence.delay.reason == "Container damaged in transit"
    assert evidence.delay.exception_event is None


@pytest.mark.asyncio
async def test_procurement_relationships_returns_buyer_order_vendor_and_products(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    product_b = await _make_product(session, shipment.id, name="Widget B", quantity=2, unit="box")
    product_a = await _make_product(session, shipment.id, name="Widget A", quantity=1, unit="crate")

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert isinstance(evidence, ProcurementEvidence)
    assert evidence.shipment.id == shipment.id
    assert evidence.purchase_order is not None
    assert evidence.purchase_order.id == order.id
    assert evidence.purchase_order.order_number == order.order_number
    assert evidence.buyer is not None
    assert evidence.buyer.id == buyer.id
    assert evidence.buyer.name == buyer.name
    assert evidence.vendor.id == shipment.vendor_id
    assert [p.id for p in evidence.products] == [product_a.id, product_b.id]


@pytest.mark.asyncio
async def test_procurement_relationships_missing_order_is_explicit(session: AsyncSession):
    shipment = await _make_shipment(session)

    evidence = await lookup_procurement(session, shipment.tracking_code)

    assert evidence.purchase_order is None
    assert evidence.buyer is None
    assert evidence.vendor.id == shipment.vendor_id
    assert evidence.products == []


@pytest.mark.asyncio
async def test_procurement_relationships_excludes_sensitive_user_fields(session: AsyncSession):
    shipment = await _make_shipment(session)
    buyer = await _make_buyer(session)
    order = await _make_purchase_order(session, shipment.vendor_id, buyer.id)
    shipment.purchase_order_id = order.id
    await session.flush()

    evidence = await lookup_procurement(session, shipment.tracking_code)

    buyer_fields = vars(evidence.buyer)
    assert "email" not in buyer_fields
    assert "password_hash" not in buyer_fields
    vendor_fields = vars(evidence.vendor)
    assert "email" not in vendor_fields
    assert "contact" not in vendor_fields
