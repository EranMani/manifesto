import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Product
from app.models.purchase_order import PurchaseOrder, PurchaseOrderStatus
from app.models.shipment import Shipment, ShipmentStatus
from app.models.user import User
from app.models.vendor import Vendor


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
class ProcurementEvidence:
    shipment: ShipmentEvidence
    purchase_order: PurchaseOrderEvidence | None
    buyer: BuyerEvidence | None
    vendor: VendorEvidence
    products: list[ProductEvidence]


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
    )


class RAGLogistics:
    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError
