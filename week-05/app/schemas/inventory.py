"""Inventory API schema definitions."""

from pydantic import BaseModel, Field
from typing import Optional


class InventoryLogResponse(BaseModel):
    id: str
    material_type: str
    current_quantity: float
    warehouse_capacity: int

    class Config:
        from_attributes = True


class InventoryUpdate(BaseModel):
    current_quantity: float = Field(..., ge=0)
