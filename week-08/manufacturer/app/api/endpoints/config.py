"""Configuration API endpoints for product models and suppliers."""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.config_service import ConfigService
from app.services.provider_client import ProviderClient

router = APIRouter(prefix="/api/config", tags=["configuration"])


class BOMItemSchema(BaseModel):
    material_name: str
    quantity_required: float
    pcb_ref: str | None = None


class ProductModelSchema(BaseModel):
    id: str
    name: str
    assembly_time_days: int
    bom: List[BOMItemSchema] = []


class SupplierProductSchema(BaseModel):
    id: int
    product_name: str
    base_unit_cost: float
    packaging_unit: str | None = None
    packaging_qty: int | None = None
    discount_tiers: list = []


class SupplierSchema(BaseModel):
    id: int
    name: str
    lead_time_days: int
    active: bool
    products: List[SupplierProductSchema] = []


class ConfigResponse(BaseModel):
    models: List[ProductModelSchema]
    suppliers: List[SupplierSchema]


class NewSupplierRequest(BaseModel):
    name: str
    lead_time_days: int


@router.get("", response_model=ConfigResponse)
def get_config(db: Session = Depends(get_db)):
    """Get full production configuration (models, BOMs, suppliers)."""
    svc = ConfigService(db)
    return {
        "models": [_serialize_model(m) for m in svc.get_models()],
        "suppliers": [_serialize_supplier(s) for s in svc.get_suppliers()],
    }


@router.get("/models", response_model=List[ProductModelSchema])
def list_models(db: Session = Depends(get_db)):
    """List all product models."""
    svc = ConfigService(db)
    return [_serialize_model(m) for m in svc.get_models()]


@router.get("/models/{model_id}", response_model=ProductModelSchema)
def get_model(model_id: str, db: Session = Depends(get_db)):
    """Get a specific product model with its full BOM."""
    svc = ConfigService(db)
    model = svc.get_model(model_id)
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return _serialize_model(model)


@router.get("/suppliers", response_model=List[SupplierSchema])
def list_suppliers(db: Session = Depends(get_db)):
    """List all active suppliers with their product catalogs."""
    svc = ConfigService(db)
    return [_serialize_supplier(s) for s in svc.get_suppliers()]


@router.post("/suppliers", response_model=SupplierSchema, status_code=status.HTTP_201_CREATED)
def add_supplier(body: NewSupplierRequest, db: Session = Depends(get_db)):
    """Add a new supplier."""
    svc = ConfigService(db)
    supplier = svc.add_supplier(body.name, body.lead_time_days)
    return _serialize_supplier(supplier)


def _serialize_model(model) -> dict:
    return {
        "id": model.id,
        "name": model.name,
        "assembly_time_days": model.assembly_time_days,
        "bom": [
            {
                "material_name": item.material_name,
                "quantity_required": float(item.quantity_required),
                "pcb_ref": item.pcb_ref,
            }
            for item in model.bom_items
        ],
    }


def _serialize_supplier(supplier) -> dict:
    products = []
    if supplier.is_external and supplier.api_url:
        try:
            client = ProviderClient(supplier.api_url)
            external_catalog = client.get_catalog()
            for p in external_catalog:
                products.append({
                    "id": p["id"],
                    "product_name": p["name"],
                    "base_unit_cost": float(p["pricing_tiers"][-1]["unit_price"]) if p["pricing_tiers"] else 0.0,
                    "packaging_unit": "units",
                    "packaging_qty": 1,
                    "discount_tiers": [
                        {"min_qty": t["min_quantity"], "discount_pct": 0.0}
                        for t in p["pricing_tiers"]
                    ],
                })
        except Exception as e:
            print(f"Error fetching catalog for {supplier.name}: {e}")
    else:
        products = [
            {
                "id": p.id,
                "product_name": p.product_name,
                "base_unit_cost": float(p.base_unit_cost),
                "packaging_unit": p.packaging_unit,
                "packaging_qty": p.packaging_qty,
                "discount_tiers": json.loads(p.discount_tiers) if p.discount_tiers else [],
            }
            for p in supplier.products
        ]

    return {
        "id": supplier.id,
        "name": supplier.name,
        "lead_time_days": supplier.lead_time_days,
        "active": supplier.active,
        "products": products,
    }
