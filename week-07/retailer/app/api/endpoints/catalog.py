from fastapi import APIRouter
from typing import List

from app.models.product import ProductCatalogItem, InventoryItem
from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/catalog", response_model=List[ProductCatalogItem])
async def get_catalog():
    """Get the product catalog with retail prices."""
    return await service.get_catalog()


@router.get("/inventory", response_model=List[InventoryItem])
async def get_inventory():
    """Get current inventory levels."""
    return await service.list_inventory()
