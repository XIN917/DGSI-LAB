"""Simulation API schema definitions."""

from pydantic import BaseModel
from typing import Optional, Dict, Any, List


class SimulationStatusResponse(BaseModel):
    current_day: int
    running: bool


class SimulationAdvanceResponse(BaseModel):
    new_day: int
    deliveries_processed: int
    orders_generated: int
    production_completed: List[Dict[str, Any]]
    capacity_used: Dict[str, int]
    total_produced: int
    inventory_updates: List[Dict[str, Any]]
    shortages_detected: List[Dict[str, Any]]


class SimulationResetResponse(BaseModel):
    success: bool
    message: str


class ProductionStatsResponse(BaseModel):
    pending_orders: int
    released_orders: int
    completed_today: int
    queue_quantity: int
    daily_capacity: Dict[str, int]


class InventoryShortageResponse(BaseModel):
    material: str
    required: float
    available: float
    shortage: float


class LowStockAlertResponse(BaseModel):
    material_type: str
    current_stock: float
    future_requirement: float
    shortfall: float
    severity: str
