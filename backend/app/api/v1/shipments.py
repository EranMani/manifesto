from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.dependencies import require_role
from app.models.client import Client
from app.models.product import Product
from app.models.shipment import Shipment
from app.models.shipment_item import ShipmentItem
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

    if payload.client_id is not None:
        client_result = await db.execute(select(Client).where(Client.id == payload.client_id))
        if client_result.scalars().first() is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Client not found")

    for item in payload.items:
        result = await db.execute(
            select(Product).where(Product.id == item.product_id).with_for_update()
        )
        product = result.scalars().first()
        if product is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Product {item.product_id} not found",
            )
        if product.quantity < item.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient stock for product {product.name}: available {product.quantity}, requested {item.quantity}",
            )
        product.quantity -= item.quantity

    shipment = Shipment(**payload.model_dump(exclude={"items"}))
    db.add(shipment)
    await db.flush()

    for item in payload.items:
        db.add(ShipmentItem(shipment_id=shipment.id, product_id=item.product_id, quantity=item.quantity))

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
