"""API route router."""

from fastapi import APIRouter

from app.api.orders import router as orders_router
from app.api.inventory import router as inventory_router
from app.api.models import router as models_router
from app.api.suppliers import router as suppliers_router
from app.api.purchasing import router as purchasing_router
from app.api.events import router as events_router
from app.api.simulation import router as simulation_router

api_router = APIRouter()

api_router.include_router(orders_router)
api_router.include_router(inventory_router)
api_router.include_router(models_router)
api_router.include_router(suppliers_router)
api_router.include_router(purchasing_router)
api_router.include_router(events_router)
api_router.include_router(simulation_router)

__all__ = ["api_router"]
