import asyncio
import datetime
import hashlib
import json
from pathlib import Path

from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.core.security import hash_password
from app.models.category import Category
from app.models.client import Client
from app.models.policy import PolicyChunk, PolicyDocument
from app.models.product import Product
from app.models.purchase_order import PurchaseOrder
from app.models.shipment import Shipment
from app.models.shipment_event import ShipmentEvent
from app.models.shipment_item import ShipmentItem
from app.models.user import User
from app.models.vendor import Vendor
from app.services.llm import EmbeddingService

DEMO_POLICIES_PATH = Path(__file__).parent / "app" / "data" / "demo_policies.json"

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

CLIENTS = [
    {"name": "Acme Corp", "contact": "John Smith", "email": "orders@acme.example", "country": "United States", "badge_color": "#ef4444"},
    {"name": "Global Trade Ltd", "contact": "Maria Chen", "email": "procurement@globaltrade.example", "country": "Singapore", "badge_color": "#3b82f6"},
    {"name": "Nordic Supply AS", "contact": "Erik Larsen", "email": "supply@nordicsupply.example", "country": "Norway", "badge_color": "#22c55e"},
    {"name": "Pacific Rim Imports", "contact": "Yuki Tanaka", "email": "imports@pacificrim.example", "country": "Japan", "badge_color": "#f59e0b"},
    {"name": "Sahara Logistics", "contact": "Ahmed Hassan", "email": "ops@saharalogistics.example", "country": "Egypt", "badge_color": "#8b5cf6"},
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

SHIPMENT_COUNT = 50
SHIPMENT_BASE_DATE = datetime.datetime(2026, 2, 2, tzinfo=datetime.timezone.utc)

ROUTES = [
    ("Los Angeles, US", "Chicago, US"),
    ("Shenzhen, CN", "Rotterdam, NL"),
    ("Mumbai, IN", "Hamburg, DE"),
    ("Mexico City, MX", "Dallas, US"),
    ("Toronto, CA", "New York, US"),
    ("Sao Paulo, BR", "Lisbon, PT"),
    ("Dubai, AE", "Mombasa, KE"),
    ("Tokyo, JP", "Vancouver, CA"),
    ("Hamburg, DE", "Casablanca, MA"),
    ("Singapore, SG", "Melbourne, AU"),
]

PRODUCT_CATALOG = [
    ("Steel Brackets", "box"),
    ("Laptop Docking Stations", "unit"),
    ("Packing Foam Sheets", "roll"),
    ("Industrial Gloves", "case"),
    ("LED Panel Lights", "unit"),
    ("Corrugated Boxes", "bundle"),
    ("Office Chairs", "unit"),
    ("Conveyor Belts", "unit"),
    ("Stainless Fasteners", "box"),
    ("Warehouse Shelving", "unit"),
    ("Printer Toner Cartridges", "case"),
    ("Pallet Wrap", "roll"),
]

# Each outcome's "events" entries are (event_type, day_offset_from_dispatch, location_role, details).
SHIPMENT_OUTCOMES = [
    dict(kind="delivered", status="delivered", delay_reason=None, status_reason=None, arrival_offset=6, events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None),
        ("departed", 0, "origin", None), ("arrived_hub", 3, "hub", None), ("delivered", 6, "destination", None),
    ]),
    dict(kind="in_transit", status="in_transit", delay_reason=None, status_reason=None, arrival_offset=None, events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None),
        ("departed", 0, "origin", None), ("arrived_hub", 3, "hub", None),
    ]),
    dict(kind="pending", status="pending", delay_reason=None, status_reason=None, arrival_offset=None, events=[
        ("ordered", -2, "origin", None),
    ]),
    dict(kind="weather_delay", status="delayed", arrival_offset=None,
         delay_reason="Severe weather conditions delayed transit",
         status_reason="Shipment is delayed due to weather conditions along the route", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("delay_reported", 4, "route", "Severe winter storm closed the transit corridor"),
    ]),
    dict(kind="customs_hold", status="delayed", arrival_offset=None,
         delay_reason="Shipment held for customs inspection",
         status_reason="Shipment is delayed due to customs clearance requirements", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("arrived_hub", 3, "hub", None), ("customs_hold", 4, "border", "Held pending customs documentation review"),
    ]),
    dict(kind="carrier_delay", status="delayed", arrival_offset=None,
         delay_reason="Carrier capacity shortage delayed pickup and transit",
         status_reason="Shipment is delayed due to carrier scheduling issues", events=[
        ("ordered", -7, "origin", None), ("dispatched", 2, "origin", None), ("departed", 2, "origin", None),
        ("delay_reported", 5, "route", "Carrier rescheduled the pickup due to a capacity shortage"),
    ]),
    dict(kind="vendor_delay", status="delayed", arrival_offset=None,
         delay_reason="Vendor production delay pushed back the shipment date",
         status_reason="Shipment is delayed due to vendor production issues", events=[
        ("ordered", -7, "origin", None),
        ("delay_reported", -1, "origin", "Vendor reported a production delay before dispatch"),
        ("dispatched", 3, "origin", None), ("departed", 3, "origin", None),
    ]),
    dict(kind="partial", status="partial", arrival_offset=6,
         delay_reason="Partial shipment due to inventory shortage at origin",
         status_reason="Only partial quantity was available for shipment", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("arrived_hub", 3, "hub", None),
        ("partial_delivery", 6, "destination", "Only part of the order quantity was available for shipment"),
    ]),
    dict(kind="damaged", status="damaged", arrival_offset=None,
         delay_reason="Cargo damaged in transit",
         status_reason="Cargo found damaged during hub inspection", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("arrived_hub", 3, "hub", None),
        ("damaged", 5, "hub", "Inspection found damaged packaging on arrival at the hub"),
    ]),
    dict(kind="cancelled", status="cancelled", arrival_offset=None,
         delay_reason="Order cancelled before dispatch",
         status_reason="Order was cancelled before dispatch", events=[
        ("ordered", -7, "origin", None), ("cancelled", -1, "origin", "Buyer cancelled the order before dispatch"),
    ]),
    dict(kind="returned", status="returned", arrival_offset=None,
         delay_reason="Recipient refused delivery; shipment returned to vendor",
         status_reason="Delivery refused by recipient; returning to origin", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("arrived_hub", 3, "hub", None), ("delivered", 6, "destination", None),
        ("returned", 8, "destination", "Recipient refused delivery; shipment returned to origin"),
    ]),
    dict(kind="lost", status="lost", arrival_offset=None,
         delay_reason="Shipment lost in transit; carrier investigation opened",
         status_reason="Shipment reported lost; investigation in progress", events=[
        ("ordered", -7, "origin", None), ("dispatched", 0, "origin", None), ("departed", 0, "origin", None),
        ("lost", 5, "route", "Carrier reported the shipment lost in transit and opened an investigation"),
    ]),
]


def purchase_order_number(index: int) -> str:
    return f"PO-2026-{index + 1:04d}"


def shipment_tracking_code(index: int) -> str:
    return f"SHP-{1001 + index:04d}"


def _event_location(role: str, origin: str, destination: str) -> str:
    if role == "origin":
        return origin
    if role == "destination":
        return destination
    if role == "hub":
        return f"{destination} regional hub"
    if role == "border":
        return f"{origin}/{destination} border crossing"
    if role == "route":
        return f"{origin} to {destination} route"
    return origin


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


async def _ensure_client(session, *, name: str, contact: str, email: str, country: str, badge_color: str) -> str:
    result = await session.execute(select(Client).where(Client.name == name))
    existing = result.scalar_one_or_none()
    if existing:
        return existing.id
    client = Client(name=name, contact=contact, email=email, country=country, badge_color=badge_color)
    session.add(client)
    await session.flush()
    return client.id


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


async def _ensure_shipment(
    session,
    *,
    tracking_code: str,
    vendor_id: str,
    client_id: str | None = None,
    origin: str,
    destination: str,
    status: str,
    dispatched_at: datetime.datetime,
    expected_arrival_at: datetime.datetime,
    actual_arrival_at: datetime.datetime | None,
    delay_reason: str | None,
    status_reason: str | None,
) -> tuple[str, bool]:
    result = await session.execute(select(Shipment).where(Shipment.tracking_code == tracking_code))
    existing = result.scalar_one_or_none()
    if existing:
        if client_id and not existing.client_id:
            existing.client_id = client_id
        return existing.id, False
    shipment = Shipment(
        tracking_code=tracking_code,
        vendor_id=vendor_id,
        client_id=client_id,
        origin=origin,
        destination=destination,
        status=status,
        dispatched_at=dispatched_at,
        expected_arrival_at=expected_arrival_at,
        actual_arrival_at=actual_arrival_at,
        delay_reason=delay_reason,
        status_reason=status_reason,
    )
    session.add(shipment)
    await session.flush()
    return shipment.id, True


def _add_product(session, *, category_id: str, name: str, unit: str, quantity: int) -> None:
    product = Product(category_id=category_id, name=name, unit=unit, quantity=quantity)
    session.add(product)
    return product


def _add_shipment_item(session, *, shipment_id: str, product_id: str, quantity: int) -> None:
    session.add(ShipmentItem(shipment_id=shipment_id, product_id=product_id, quantity=quantity))


def _add_shipment_event(
    session,
    *,
    shipment_id: str,
    event_type: str,
    occurred_at: datetime.datetime,
    location: str,
    details: str | None,
) -> None:
    session.add(
        ShipmentEvent(
            shipment_id=shipment_id,
            event_type=event_type,
            occurred_at=occurred_at,
            location=location,
            details=details,
        )
    )


def load_demo_policies() -> list[dict]:
    return json.loads(DEMO_POLICIES_PATH.read_text(encoding="utf-8"))


def _build_embedding_service() -> EmbeddingService:
    return EmbeddingService(
        provider=settings.EMBEDDING_PROVIDER,
        model=settings.EMBEDDING_MODEL or "",
        dimensions=settings.EMBEDDING_DIMENSIONS,
        openai_api_key=settings.OPENAI_API_KEY,
        ollama_base_url=settings.OLLAMA_BASE_URL,
        connect_timeout=settings.LLM_CONNECT_TIMEOUT,
        read_timeout=settings.LLM_READ_TIMEOUT,
        total_timeout=settings.LLM_TOTAL_TIMEOUT,
        max_retries=settings.LLM_MAX_RETRIES,
    )


async def _seed_policy_document(session, embeddings: EmbeddingService, policy: dict) -> None:
    sections = policy["sections"]
    contents = [section["content"] for section in sections]
    combined = "\n\n".join(contents)
    sha256 = hashlib.sha256(combined.encode("utf-8")).hexdigest()
    profile = embeddings.profile

    result = await session.execute(
        select(PolicyDocument).where(
            PolicyDocument.sha256 == sha256,
            PolicyDocument.embedding_provider == profile.provider,
            PolicyDocument.embedding_model == profile.model,
            PolicyDocument.embedding_dimensions == profile.dimensions,
            PolicyDocument.status == "ready",
        )
    )
    if result.scalars().first() is not None:
        return

    document = PolicyDocument(
        title=policy["title"],
        content_type="text/markdown",
        byte_size=len(combined.encode("utf-8")),
        sha256=sha256,
        status="processing",
        embedding_provider=profile.provider,
        embedding_model=profile.model,
        embedding_dimensions=profile.dimensions,
    )
    session.add(document)
    await session.flush()

    vectors = await embeddings.embed_documents(contents)

    for index, (section, vector) in enumerate(zip(sections, vectors)):
        session.add(
            PolicyChunk(
                document_id=document.id,
                chunk_index=index,
                content=section["content"],
                embedding=vector,
                section=section["section"],
            )
        )

    document.status = "ready"
    document.chunk_count = len(sections)


async def _seed_bundled_policies(session) -> None:
    embeddings = _build_embedding_service()
    try:
        for policy in load_demo_policies():
            await _seed_policy_document(session, embeddings, policy)
    finally:
        await embeddings.close()


async def seed() -> None:
    async with AsyncSessionLocal() as session:
        buyer_ids = [await _ensure_user(session, name="Admin", email=ADMIN_EMAIL, password="admin123", role="admin")]
        for manager in MANAGERS:
            buyer_ids.append(await _ensure_user(session, password="manager123", **manager))

        vendor_ids = [await _ensure_vendor(session, **vendor) for vendor in VENDORS]
        client_ids = [await _ensure_client(session, **c) for c in CLIENTS]

        category_ids = []
        for category_name in CATEGORIES:
            category_ids.append(await _ensure_category(session, name=category_name))

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

        for index in range(SHIPMENT_COUNT):
            outcome = SHIPMENT_OUTCOMES[index % len(SHIPMENT_OUTCOMES)]
            origin, destination = ROUTES[index % len(ROUTES)]
            dispatched_at = SHIPMENT_BASE_DATE + datetime.timedelta(days=index * 2)
            expected_arrival_at = dispatched_at + datetime.timedelta(days=10)
            arrival_offset = outcome["arrival_offset"]
            actual_arrival_at = (
                dispatched_at + datetime.timedelta(days=arrival_offset) if arrival_offset is not None else None
            )

            shipment_id, created = await _ensure_shipment(
                session,
                tracking_code=shipment_tracking_code(index),
                vendor_id=vendor_ids[index % len(vendor_ids)],
                client_id=client_ids[index % len(client_ids)],
                origin=origin,
                destination=destination,
                status=outcome["status"],
                dispatched_at=dispatched_at,
                expected_arrival_at=expected_arrival_at,
                actual_arrival_at=actual_arrival_at,
                delay_reason=outcome["delay_reason"],
                status_reason=outcome["status_reason"],
            )
            if not created:
                continue

            product_count = 1 + (index % 4)
            for offset in range(product_count):
                product_name, unit = PRODUCT_CATALOG[(index + offset) % len(PRODUCT_CATALOG)]
                product = _add_product(
                    session,
                    category_id=category_ids[(index + offset) % len(category_ids)],
                    name=product_name,
                    unit=unit,
                    quantity=50 + ((index + offset) % 5) * 10,
                )
                await session.flush()
                _add_shipment_item(
                    session,
                    shipment_id=shipment_id,
                    product_id=product.id,
                    quantity=10 + ((index + offset) % 5) * 5,
                )

            for event_type, day_offset, role, details in outcome["events"]:
                _add_shipment_event(
                    session,
                    shipment_id=shipment_id,
                    event_type=event_type,
                    occurred_at=dispatched_at + datetime.timedelta(days=day_offset),
                    location=_event_location(role, origin, destination),
                    details=details,
                )

        await _seed_bundled_policies(session)

        await session.commit()
        print("Seed complete — procurement foundation, shipment scenario, and policy data ready")


if __name__ == "__main__":
    asyncio.run(seed())
