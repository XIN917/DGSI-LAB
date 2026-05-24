from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from typing import List

from app.models.product import ProductCatalogItem, InventoryItem
from app.services.retailer_service import RetailerService
from app.core.database import get_db

router = APIRouter()


@router.get("/catalog", response_model=List[ProductCatalogItem])
def get_catalog(db: Session = Depends(get_db)):
    """Get the product catalog with retail prices."""
    service = RetailerService(db)
    return service.get_catalog()


@router.patch("/{sku}/price", response_model=InventoryItem)
def update_retail_price(sku: str, price: float, db: Session = Depends(get_db)):
    """Update the retail price for a SKU."""
    service = RetailerService(db)
    try:
        return service.set_retail_price(sku, price)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



@router.get("/inventory", response_model=List[InventoryItem])
def get_inventory(db: Session = Depends(get_db)):
    """Get current inventory levels."""
    service = RetailerService(db)
    return service.list_inventory()
