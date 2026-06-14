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
from app.models.purchase_order import PurchaseOrder
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
