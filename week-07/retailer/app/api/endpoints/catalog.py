from fastapi import APIRouter, HTTPException
from typing import List

from app.models.product import ProductCatalogItem, InventoryItem
from app.services.retailer_service import RetailerService

router = APIRouter()
service = RetailerService()


@router.get("/catalog", response_model=List[ProductCatalogItem])
async def get_catalog():
    """Get the product catalog with retail prices."""
    return await service.get_catalog()


@router.patch("/{sku}/price", response_model=InventoryItem)
async def update_retail_price(sku: str, price: float):
    """Update the retail price for a SKU."""
    try:
        return await service.set_retail_price(sku, price)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/inventory", response_model=List[InventoryItem])
async def get_inventory():
    """Get current inventory levels."""
    return await service.list_inventory()
