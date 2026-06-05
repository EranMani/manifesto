import structlog
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.admin import router as admin_router
from app.api.v1.auth import router as auth_router
from app.api.v1.products import router as product_router
from app.api.v1.shipments import router as shipment_router
from app.api.v1.vendors import router as vendor_router

logger = structlog.get_logger()

app = FastAPI(title="Manifesto", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def health():
    return {"status": "ok"}

# routers registered below
app.include_router(auth_router, prefix="/auth", tags=["auth"])
app.include_router(admin_router, prefix="/api/v1/admin", tags=["admin"])
app.include_router(vendor_router, prefix="/api/v1/vendors", tags=["vendors"])
app.include_router(shipment_router, prefix="/api/v1/shipments", tags=["shipments"])
app.include_router(product_router, prefix="/api/v1/products", tags=["products"])
