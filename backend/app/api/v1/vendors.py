from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.dependencies import require_role
from app.models.user import User
from app.models.shipment import Shipment
from app.models.vendor import Vendor
from app.schemas.vendor import VendorCreate, VendorRead, VendorUpdate

router = APIRouter()


@router.get("", response_model=list[VendorRead])
async def list_vendors(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
) -> list[VendorRead]:
    result = await db.execute(select(Vendor))
    return result.scalars().all()


@router.get("/{vendor_id}", response_model=VendorRead)
async def get_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
) -> VendorRead:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    return vendor


@router.post("", response_model=VendorRead, status_code=status.HTTP_201_CREATED)
async def create_vendor(
    payload: VendorCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
) -> VendorRead:
    vendor = Vendor(
        name=payload.name,
        contact=payload.contact,
        email=payload.email,
        country=payload.country,
    )
    db.add(vendor)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.put("/{vendor_id}", response_model=VendorRead)
async def update_vendor(
    vendor_id: str,
    payload: VendorUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
) -> VendorRead:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(vendor, field, value)
    await db.commit()
    await db.refresh(vendor)
    return vendor


@router.delete("/{vendor_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_vendor(
    vendor_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role("admin", "manager")),
) -> None:
    result = await db.execute(select(Vendor).where(Vendor.id == vendor_id))
    vendor = result.scalars().first()
    if vendor is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor not found")
    child = await db.execute(select(Shipment).where(Shipment.vendor_id == vendor_id))
    if child.scalars().first() is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Vendor has existing shipments")
    await db.delete(vendor)
    await db.commit()
