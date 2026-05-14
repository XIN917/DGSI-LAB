from pydantic import BaseModel
from typing import List, Optional
from decimal import Decimal
from datetime import datetime

class PricingTierSchema(BaseModel):
    min_quantity: int
    unit_price: Decimal

    class Config:
        from_attributes = True

class ProductSchema(BaseModel):
    id: int
    name: str
    description: Optional[str]
    lead_time_days: int
    pricing_tiers: List[PricingTierSchema]

    class Config:
        from_attributes = True

class StockSchema(BaseModel):
    product_id: int
    quantity: int

    class Config:
        from_attributes = True

class OrderCreateSchema(BaseModel):
    buyer: str
    product_id: int
    quantity: int

class OrderSchema(BaseModel):
    id: int
    buyer: str
    product_id: int
    quantity: int
    unit_price: Decimal
    total_price: Decimal
    placed_day: int
    expected_delivery_day: int
    shipped_day: Optional[int]
    delivered_day: Optional[int]
    status: str

    class Config:
        from_attributes = True

class DayAdvanceResponse(BaseModel):
    previous_day: int
    new_day: int
