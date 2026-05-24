from fastapi import FastAPI
from app.api.endpoints import orders, purchase, day, catalog
from app.core.database import init_db


def create_app() -> FastAPI:
    # Synchronous initialization
    init_db()
    
    app = FastAPI(title="DGSI Retailer App")

    app.include_router(orders.router, prefix="/api/customer-orders", tags=["Customer Orders"])
    app.include_router(purchase.router, prefix="/api/purchase-orders", tags=["Purchase Orders"])
    app.include_router(day.router, prefix="/api/day", tags=["Simulation Day"])
    app.include_router(catalog.router, prefix="/api", tags=["Catalog & Inventory"])
    return app


app = create_app()
