from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.dependencies import require_role
from app.models.shipment import Shipment
from app.models.vendor import Vendor
from app.schemas.shipment import ShipmentCreate, ShipmentRead

router = APIRouter()


@router.get("", response_model=list[ShipmentRead])
async def list_shipments(
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role("admin", "manager")),
):
    result = await db.execute(select(Shipment))
    return result.scalars().all()


@router.get("/{shipment_id}", response_model=ShipmentRead)
async def get_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role("admin", "manager")),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalars().first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    return shipment


@router.post("", response_model=ShipmentRead, status_code=status.HTTP_201_CREATED)
async def create_shipment(
    payload: ShipmentCreate,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role("admin", "manager")),
):
    vendor_result = await db.execute(select(Vendor).where(Vendor.id == payload.vendor_id))
    if vendor_result.scalars().first() is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    shipment = Shipment(**payload.model_dump())
    db.add(shipment)
    await db.commit()
    await db.refresh(shipment)
    return shipment


@router.delete("/{shipment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db),
    _: object = Depends(require_role("admin", "manager")),
):
    result = await db.execute(select(Shipment).where(Shipment.id == shipment_id))
    shipment = result.scalars().first()
    if shipment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Shipment not found")
    await db.delete(shipment)
    await db.commit()
