"""Configuration API endpoints for product models and suppliers."""
import json
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.purchase_order import Supplier, SupplierProduct

router = APIRouter(prefix="/api/config", tags=["configuration"])


# --- Pydantic schemas ---

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


# --- Endpoints ---

@router.get("", response_model=ConfigResponse)
def get_config(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get full production configuration (models, BOMs, suppliers)."""
    models = db.query(ProductModel).all()
    suppliers = db.query(Supplier).filter(Supplier.active == True).all()

    return {
        "models": [_serialize_model(m) for m in models],
        "suppliers": [_serialize_supplier(s) for s in suppliers],
    }


@router.get("/models", response_model=List[ProductModelSchema])
def list_models(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all product models."""
    models = db.query(ProductModel).all()
    return [_serialize_model(m) for m in models]


@router.get("/models/{model_id}", response_model=ProductModelSchema)
def get_model(
    model_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Get a specific product model with its full BOM."""
    model = db.query(ProductModel).filter(ProductModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail=f"Model '{model_id}' not found")
    return _serialize_model(model)


@router.get("/suppliers", response_model=List[SupplierSchema])
def list_suppliers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """List all active suppliers with their product catalogs."""
    suppliers = db.query(Supplier).filter(Supplier.active == True).all()
    return [_serialize_supplier(s) for s in suppliers]


class NewSupplierRequest(BaseModel):
    name: str
    lead_time_days: int


@router.post("/suppliers", response_model=SupplierSchema, status_code=status.HTTP_201_CREATED)
def add_supplier(
    body: NewSupplierRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a new supplier."""
    supplier = Supplier(
        name=body.name,
        lead_time_days=body.lead_time_days,
        active=True,
    )
    db.add(supplier)
    db.commit()
    db.refresh(supplier)
    return _serialize_supplier(supplier)


# --- Helpers ---

def _serialize_model(model: ProductModel) -> dict:
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


def _serialize_supplier(supplier: Supplier) -> dict:
    return {
        "id": supplier.id,
        "name": supplier.name,
        "lead_time_days": supplier.lead_time_days,
        "active": supplier.active,
        "products": [
            {
                "id": p.id,
                "product_name": p.product_name,
                "base_unit_cost": float(p.base_unit_cost),
                "packaging_unit": p.packaging_unit,
                "packaging_qty": p.packaging_qty,
                "discount_tiers": json.loads(p.discount_tiers) if p.discount_tiers else [],
            }
            for p in supplier.products
        ],
    }
