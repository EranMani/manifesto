import asyncio
import datetime

from sqlalchemy import select

from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.purchase_order import PurchaseOrder
from app.models.user import User
from app.models.vendor import Vendor

ADMIN_EMAIL = "admin@manifesto.local"

MANAGERS = [
    {"name": "Morgan Reyes", "email": "morgan.reyes@manifesto.local", "role": "manager"},
    {"name": "Priya Nair", "email": "priya.nair@manifesto.local", "role": "manager"},
]

VENDORS = [
    {"name": "Atlas Components", "contact": "Dana Kim", "email": "sales@atlascomponents.example", "country": "United States"},
    {"name": "Brightline Logistics", "contact": "Carlos Vega", "email": "orders@brightlinelogistics.example", "country": "Mexico"},
    {"name": "Cedar Grove Supplies", "contact": "Liu Wei", "email": "contact@cedargrovesupplies.example", "country": "Canada"},
    {"name": "Delta Pack Materials", "contact": "Sofia Rossi", "email": "info@deltapackmaterials.example", "country": "Italy"},
    {"name": "Everwell Equipment", "contact": "Tariq Aziz", "email": "sales@everwellequipment.example", "country": "United Arab Emirates"},
    {"name": "Falcon Freight Co", "contact": "Anna Schmidt", "email": "ops@falconfreightco.example", "country": "Germany"},
    {"name": "Granite Hardware", "contact": "James O'Brien", "email": "orders@granitehardware.example", "country": "Ireland"},
    {"name": "Horizon Textiles", "contact": "Mei Tanaka", "email": "sales@horizontextiles.example", "country": "Japan"},
]

CATEGORIES = [
    "Electronics",
    "Office Supplies",
    "Furniture",
    "Packaging",
    "Raw Materials",
    "Maintenance",
]

PURCHASE_ORDER_STATUSES = ["approved", "approved", "fulfilled", "draft"]
PURCHASE_ORDER_COUNT = 20


def purchase_order_number(index: int) -> str:
    return f"PO-2026-{index + 1:04d}"


def _purchase_order_dates(index: int) -> tuple[datetime.datetime, datetime.datetime]:
    ordered_at = datetime.datetime(2026, 1, 5, tzinfo=datetime.timezone.utc) + datetime.timedelta(days=index * 3)
    requested_delivery_at = ordered_at + datetime.timedelta(days=14)
    return ordered_at, requested_delivery_at


async def _ensure_user(session, *, name: str, email: str, password: str, role: str) -> str:
    result = await session.execute(select(User).where(User.email == email))
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id
    user = User(name=name, email=email, password_hash=hash_password(password), role=role)
    session.add(user)
    await session.flush()
    return user.id


async def _ensure_vendor(session, *, name: str, contact: str, email: str, country: str) -> str:
    result = await session.execute(select(Vendor).where(Vendor.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id
    vendor = Vendor(name=name, contact=contact, email=email, country=country)
    session.add(vendor)
    await session.flush()
    return vendor.id


async def _ensure_category(session, *, name: str) -> str:
    result = await session.execute(select(Category).where(Category.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id
    category = Category(name=name)
    session.add(category)
    await session.flush()
    return category.id


async def _ensure_purchase_order(
    session,
    *,
    order_number: str,
    vendor_id: str,
    buyer_id: str,
    ordered_at: datetime.datetime,
    requested_delivery_at: datetime.datetime,
    status: str,
) -> None:
    result = await session.execute(select(PurchaseOrder).where(PurchaseOrder.order_number == order_number))
    existing = result.scalar_one_or_none()
    if existing:
        return
    order = PurchaseOrder(
        order_number=order_number,
        vendor_id=vendor_id,
        buyer_id=buyer_id,
        ordered_at=ordered_at,
        requested_delivery_at=requested_delivery_at,
        status=status,
    )
    session.add(order)
    await session.flush()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        buyer_ids = [await _ensure_user(session, name="Admin", email=ADMIN_EMAIL, password="admin123", role="admin")]
        for manager in MANAGERS:
            buyer_ids.append(await _ensure_user(session, password="manager123", **manager))

        vendor_ids = [await _ensure_vendor(session, **vendor) for vendor in VENDORS]

        for category_name in CATEGORIES:
            await _ensure_category(session, name=category_name)

        for index in range(PURCHASE_ORDER_COUNT):
            ordered_at, requested_delivery_at = _purchase_order_dates(index)
            await _ensure_purchase_order(
                session,
                order_number=purchase_order_number(index),
                vendor_id=vendor_ids[index % len(vendor_ids)],
                buyer_id=buyer_ids[index % len(buyer_ids)],
                ordered_at=ordered_at,
                requested_delivery_at=requested_delivery_at,
                status=PURCHASE_ORDER_STATUSES[index % len(PURCHASE_ORDER_STATUSES)],
            )

        await session.commit()
        print("Seed complete — procurement foundation data ready")


if __name__ == "__main__":
    asyncio.run(seed())
