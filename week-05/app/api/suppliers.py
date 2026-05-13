"""Suppliers API endpoints."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Supplier, SupplierProduct
from app.schemas.orders import SupplierCreate, SupplierResponse, SupplierProductCreate, SupplierProductResponse

router = APIRouter(prefix="/suppliers", tags=["Suppliers"])


@router.get("", response_model=List[SupplierResponse])
def list_suppliers(db: Session = Depends(get_db)):
    """List all suppliers."""
    return db.query(Supplier).all()


@router.post("", response_model=SupplierResponse)
def create_supplier(supplier: SupplierCreate, db: Session = Depends(get_db)):
    """Create a new supplier."""
    existing = db.query(Supplier).filter(Supplier.id == supplier.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Supplier already exists")

    db_supplier = Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier


@router.get("/{supplier_id}")
def get_supplier(supplier_id: str, db: Session = Depends(get_db)):
    """Get a specific supplier with their products."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")
    return supplier


@router.get("/{supplier_id}/products", response_model=List[SupplierProductResponse])
def get_supplier_products(supplier_id: str, db: Session = Depends(get_db)):
    """Get all products offered by a supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    return db.query(SupplierProduct).filter(SupplierProduct.supplier_id == supplier_id).all()


@router.post("/{supplier_id}/products", response_model=SupplierProductResponse)
def add_product(supplier_id: str, product: SupplierProductCreate, db: Session = Depends(get_db)):
    """Add a product to a supplier's catalog."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=404, detail="Supplier not found")

    db_product = SupplierProduct(**product.model_dump())
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product
