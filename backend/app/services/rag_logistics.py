import datetime
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.shipment import Shipment, ShipmentStatus


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


async def lookup_shipment(db: AsyncSession, tracking_code: str) -> ShipmentEvidence:
    normalized = tracking_code.strip().upper()
    if not normalized:
        raise ShipmentNotFoundError("tracking code is blank")

    result = await db.execute(
        select(Shipment).where(Shipment.tracking_code == normalized)
    )
    shipment = result.scalar_one_or_none()
    if shipment is None:
        raise ShipmentNotFoundError(f"no shipment found for tracking code {normalized!r}")

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


class RAGLogistics:
    async def query(self, text: str, top_k: int = 5) -> list[dict]:
        raise NotImplementedError
