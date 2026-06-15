import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.shipment_event import ShipmentEvent, ShipmentEventType
from app.models.user import User
from app.models.vendor import Vendor

# Statuses for which a delay/exception explanation is expected.
EXCEPTION_STATUSES: frozenset[ShipmentStatus] = frozenset(
    {"delayed", "damaged", "partial", "cancelled", "returned", "lost"}
)

# Event types that can support a delay/exception explanation, ordered by
# nothing in particular here — selection picks the latest by (occurred_at, id).
EXCEPTION_EVENT_TYPES: frozenset[ShipmentEventType] = frozenset(
    {"delay_reported", "damaged", "partial_delivery", "cancelled", "returned", "lost"}
)


class ShipmentNotFoundError(Exception):
    """Raised when no shipment matches the normalized tracking code."""


@dataclass(frozen=True)
class ShipmentEvidence:
    id: str
    tracking_code: str
    status: ShipmentStatus
    origin: str
    destination: str
    dispatched_at: datetime.datetime
    expected_arrival_at: datetime.datetime
    actual_arrival_at: datetime.datetime | None
    delay_reason: str | None


@dataclass(frozen=True)
class VendorEvidence:
    id: str
    name: str
    country: str | None


@dataclass(frozen=True)
class BuyerEvidence:
    id: str
    name: str


@dataclass(frozen=True)
class PurchaseOrderEvidence:
    id: str
    order_number: str
    status: PurchaseOrderStatus
    ordered_at: datetime.datetime
    requested_delivery_at: datetime.datetime


@dataclass(frozen=True)
class ProductEvidence:
    id: str
    name: str
    description: str | None
    quantity: int
    unit: str | None


@dataclass(frozen=True)
class ShipmentEventEvidence:
    id: str
    event_type: ShipmentEventType
    occurred_at: datetime.datetime
    location: str
    details: str | None


@dataclass(frozen=True)
class DelayEvidence:
    reason: str
    exception_event: ShipmentEventEvidence | None


@dataclass(frozen=True)
class ProcurementEvidence:
    shipment: ShipmentEvidence
    purchase_order: PurchaseOrderEvidence | None
    buyer: BuyerEvidence | None
    vendor: VendorEvidence
    products: list[ProductEvidence]
    timeline: list[ShipmentEventEvidence]
    delay: DelayEvidence | None


def _shipment_evidence(shipment: Shipment) -> ShipmentEvidence:
    return ShipmentEvidence(
        id=shipment.id,
        tracking_code=shipment.tracking_code,
        status=shipment.status,
        origin=shipment.origin,
        destination=shipment.destination,
        dispatched_at=shipment.dispatched_at,
        expected_arrival_at=shipment.expected_arrival_at,
        actual_arrival_at=shipment.actual_arrival_at,
        delay_reason=shipment.delay_reason,
    )


async def _load_shipment(db: AsyncSession, tracking_code: str) -> Shipment:
    normalized = tracking_code.strip().upper()
    if not normalized:
        raise ShipmentNotFoundError("tracking code is blank")

    result = await db.execute(
        select(Shipment).where(Shipment.tracking_code == normalized)
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise ShipmentNotFoundError(f"no shipment found for tracking code {normalized!r}")

    return shipment


def _shipment_event_evidence(event: ShipmentEvent) -> ShipmentEventEvidence:
    return ShipmentEventEvidence(
        id=event.id,
        event_type=event.event_type,
        occurred_at=event.occurred_at,
        location=event.location,
        details=event.details,
    )


async def _load_timeline(db: AsyncSession, shipment_id: str) -> list[ShipmentEventEvidence]:
    events = (
        await db.execute(
            select(ShipmentEvent)
            .where(ShipmentEvent.shipment_id == shipment_id)
            .order_by(ShipmentEvent.occurred_at, ShipmentEvent.id)
        )
    ).scalars().all()
    return [_shipment_event_evidence(event) for event in events]


def _delay_evidence(
    shipment: Shipment, timeline: list[ShipmentEventEvidence]
) -> DelayEvidence | None:
    if shipment.status not in EXCEPTION_STATUSES:
        return None
    if not shipment.delay_reason:
        return None

    exception_event: ShipmentEventEvidence | None = None
    for event in timeline:
        if event.event_type in EXCEPTION_EVENT_TYPES:
            exception_event = event

    return DelayEvidence(reason=shipment.delay_reason, exception_event=exception_event)


async def lookup_shipment(db: AsyncSession, tracking_code: str) -> ShipmentEvidence:
    shipment = await _load_shipment(db, tracking_code)
    return _shipment_evidence(shipment)


async def lookup_procurement(db: AsyncSession, tracking_code: str) -> ProcurementEvidence:
    shipment = await _load_shipment(db, tracking_code)

    vendor = (
        await db.execute(select(Vendor).where(Vendor.id == shipment.vendor_id))
    ).scalar_one()

    purchase_order_evidence: PurchaseOrderEvidence | None = None
    buyer_evidence: BuyerEvidence | None = None
    if shipment.purchase_order_id is not None:
        purchase_order = (
            await db.execute(
                select(PurchaseOrder).where(PurchaseOrder.id == shipment.purchase_order_id)
            )
        ).scalar_one_or_none()
        if purchase_order is not None:
            purchase_order_evidence = PurchaseOrderEvidence(
                id=purchase_order.id,
                order_number=purchase_order.order_number,
                status=purchase_order.status,
                ordered_at=purchase_order.ordered_at,
                requested_delivery_at=purchase_order.requested_delivery_at,
            )
            buyer = (
                await db.execute(select(User).where(User.id == purchase_order.buyer_id))
            ).scalar_one_or_none()
            if buyer is not None:
                buyer_evidence = BuyerEvidence(id=buyer.id, name=buyer.name)

    products = (
        await db.execute(
            select(Product)
            .where(Product.shipment_id == shipment.id)
            .order_by(Product.name, Product.id)
        )
    ).scalars().all()

    timeline = await _load_timeline(db, shipment.id)

    return ProcurementEvidence(
        shipment=_shipment_evidence(shipment),
        purchase_order=purchase_order_evidence,
        buyer=buyer_evidence,
        vendor=VendorEvidence(id=vendor.id, name=vendor.name, country=vendor.country),
        products=[
            ProductEvidence(
                id=product.id,
                name=product.name,
                description=product.description,
                quantity=product.quantity,
                unit=product.unit,
            )
            for product in products
        ],
        timeline=timeline,
        delay=_delay_evidence(shipment, timeline),
    )


class RAGLogistics:
    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError
