"""Integration tests for the C44 procurement foundation seed.

These tests run against a real PostgreSQL database (the docker-compose ``db``
service, resolved via DATABASE_URL inside the backend container) and require
migrations up to head to be applied before ``seed.seed()`` runs.

Covers:
- The seed creates the expected admin/manager buyers, vendors, categories,
  and purchase orders with deterministic identifiers.
- Purchase orders reference seeded buyers and vendors.
- Running the seed a second time creates no duplicates.
"""

from __future__ import annotations

import os

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import select
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

import seed
from app.core.database import engine as app_engine
from app.models.category import Category
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.user import User
from app.models.vendor import Vendor

DB_URL = os.environ.get(
    "DATABASE_URL", "postgresql+asyncpg://manifesto:manifesto@localhost:5432/manifesto"
)


@pytest.fixture(scope="module", autouse=True)
def _apply_head_migration():
    """Ensure all procurement/shipment tables exist before the seed runs."""
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
async def _reset_app_engine():
    """seed.seed() uses the app's module-level engine; each test runs in its
    own event loop, so dispose pooled connections from the prior loop first."""
    await app_engine.dispose()
    yield
    await app_engine.dispose()


async def _fetch_seeded_rows():
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
            async with session_factory() as session:
                users = {
                    u.email: u
                    for u in (
                        await session.execute(
                            select(User).where(
                                User.email.in_([seed.ADMIN_EMAIL, *(m["email"] for m in seed.MANAGERS)])
                            )
                        )
                    ).scalars()
                }
                vendors = {
                    v.name: v
                    for v in (
                        await session.execute(
                            select(Vendor).where(Vendor.name.in_([v["name"] for v in seed.VENDORS]))
                        )
                    ).scalars()
                }
                categories = {
                    c.name: c
                    for c in (
                        await session.execute(select(Category).where(Category.name.in_(seed.CATEGORIES)))
                    ).scalars()
                }
                order_numbers = [seed.purchase_order_number(i) for i in range(seed.PURCHASE_ORDER_COUNT)]
                orders = {
                    o.order_number: o
                    for o in (
                        await session.execute(
                            select(PurchaseOrder).where(PurchaseOrder.order_number.in_(order_numbers))
                        )
                    ).scalars()
                }
                return users, vendors, categories, orders
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_procurement_foundation_seed_creates_expected_entities():
    await seed.seed()

    users, vendors, categories, orders = await _fetch_seeded_rows()

    assert seed.ADMIN_EMAIL in users
    assert users[seed.ADMIN_EMAIL].role == "admin"
    for manager in seed.MANAGERS:
        assert manager["email"] in users
        assert users[manager["email"]].role == "manager"

    assert len(vendors) == len(seed.VENDORS)
    assert len(categories) == len(seed.CATEGORIES)
    assert len(orders) == seed.PURCHASE_ORDER_COUNT

    buyer_ids = {users[seed.ADMIN_EMAIL].id} | {users[m["email"]].id for m in seed.MANAGERS}
    vendor_ids = {v.id for v in vendors.values()}
    for order in orders.values():
        assert order.buyer_id in buyer_ids
        assert order.vendor_id in vendor_ids


@pytest.mark.asyncio
async def test_procurement_foundation_seed_is_idempotent():
    await seed.seed()
    first_users, first_vendors, first_categories, first_orders = await _fetch_seeded_rows()

    await seed.seed()
    second_users, second_vendors, second_categories, second_orders = await _fetch_seeded_rows()

    assert {u.id for u in first_users.values()} == {u.id for u in second_users.values()}
    assert {v.id for v in first_vendors.values()} == {v.id for v in second_vendors.values()}
    assert {c.id for c in first_categories.values()} == {c.id for c in second_categories.values()}
    assert {o.id for o in first_orders.values()} == {o.id for o in second_orders.values()}
    assert len(second_orders) == seed.PURCHASE_ORDER_COUNT


# Evidence event type expected for each exceptional outcome, alongside a non-null delay_reason.
EXCEPTIONAL_OUTCOME_EVENTS = {
    "weather_delay": "delay_reported",
    "customs_hold": "customs_hold",
    "carrier_delay": "delay_reported",
    "vendor_delay": "delay_reported",
    "partial": "partial_delivery",
    "damaged": "damaged",
    "cancelled": "cancelled",
    "returned": "returned",
    "lost": "lost",
}


async def _fetch_seeded_shipments():
    engine = create_async_engine(DB_URL, echo=False)
    try:
        async with engine.connect() as conn:
            session_factory = async_sessionmaker(bind=conn, expire_on_commit=False)
            async with session_factory() as session:
                tracking_codes = [seed.shipment_tracking_code(i) for i in range(seed.SHIPMENT_COUNT)]
                shipments = {
                    s.tracking_code: s
                    for s in (
                        await session.execute(
                            select(Shipment).where(Shipment.tracking_code.in_(tracking_codes))
                        )
                    ).scalars()
                }
                shipment_ids = [s.id for s in shipments.values()]
                products = (
                    await session.execute(select(Product).where(Product.shipment_id.in_(shipment_ids)))
                ).scalars().all()
                events = (
                    await session.execute(
                        select(ShipmentEvent)
                        .where(ShipmentEvent.shipment_id.in_(shipment_ids))
                        .order_by(ShipmentEvent.occurred_at)
                    )
                ).scalars().all()
                return shipments, products, events
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_shipment_scenarios_seed_creates_expected_entities():
    await seed.seed()

    shipments, products, events = await _fetch_seeded_shipments()

    assert len(shipments) == seed.SHIPMENT_COUNT

    statuses_seen = {s.status for s in shipments.values()}
    for outcome in seed.SHIPMENT_OUTCOMES:
        assert outcome["status"] in statuses_seen

    products_by_shipment: dict[str, list] = {}
    for product in products:
        products_by_shipment.setdefault(product.shipment_id, []).append(product)
    for shipment in shipments.values():
        assert 1 <= len(products_by_shipment.get(shipment.id, [])) <= 4

    events_by_shipment: dict[str, list] = {}
    for event in events:
        events_by_shipment.setdefault(event.shipment_id, []).append(event)
    for index in range(seed.SHIPMENT_COUNT):
        outcome = seed.SHIPMENT_OUTCOMES[index % len(seed.SHIPMENT_OUTCOMES)]
        shipment = shipments[seed.shipment_tracking_code(index)]
        shipment_events = events_by_shipment[shipment.id]
        assert len(shipment_events) == len(outcome["events"])
        timestamps = [e.occurred_at for e in shipment_events]
        assert timestamps == sorted(timestamps)

        if outcome["kind"] in EXCEPTIONAL_OUTCOME_EVENTS:
            assert shipment.delay_reason is not None
            event_types = {e.event_type for e in shipment_events}
            assert EXCEPTIONAL_OUTCOME_EVENTS[outcome["kind"]] in event_types


@pytest.mark.asyncio
async def test_shipment_scenarios_seed_is_idempotent():
    await seed.seed()
    first_shipments, first_products, first_events = await _fetch_seeded_shipments()

    await seed.seed()
    second_shipments, second_products, second_events = await _fetch_seeded_shipments()

    assert {s.id for s in first_shipments.values()} == {s.id for s in second_shipments.values()}
    assert len(second_shipments) == seed.SHIPMENT_COUNT
    assert len(second_products) == len(first_products)
    assert len(second_events) == len(first_events)
