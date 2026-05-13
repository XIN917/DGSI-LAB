"""Catalog endpoints for Provider app."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List

from provider.app.services.catalog_service import (
    get_all_products,
    get_product_by_name,
    get_stock_levels,
    update_price_tier,
    add_stock,
)

router = APIRouter(prefix="/api", tags=["catalog"])


class PriceUpdate(BaseModel):
    product_id: int
    min_quantity: int
    price: float


class RestockRequest(BaseModel):
    product: str
    quantity: int


@router.get("/catalog")
def list_catalog():
    """Get all products with pricing tiers."""
    return get_all_products()


@router.get("/stock")
def list_stock():
    """Get current inventory levels."""
    return get_stock_levels()


@router.post("/price/update")
def update_price(request: PriceUpdate):
    """Update a price tier."""
    success = update_price_tier(request.product_id, request.min_quantity, request.price)
    if not success:
        raise HTTPException(status_code=404, detail="Price tier not found")
    return {"success": True, "message": "Price updated"}


@router.post("/restock")
def restock(request: RestockRequest):
    """Add stock to a product."""
    success = add_stock(request.product, request.quantity)
    if not success:
        raise HTTPException(status_code=404, detail="Product not found")
    return {"success": True, "message": f"Added {request.quantity} to {request.product}"}


@router.get("/products/{product_name}")
def get_product(product_name: str):
    """Get a specific product by name."""
    product = get_product_by_name(product_name)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product