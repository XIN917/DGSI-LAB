"""API routes for printer models and BOM."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import PrinterModel, BOMItem
from app.schemas.orders import PrinterModelCreate, PrinterModelResponse, BOMItemCreate, BOMItemResponse

router = APIRouter(prefix="/models", tags=["Printer Models"])


@router.get("", response_model=List[PrinterModelResponse])
def list_models(db: Session = Depends(get_db)):
    """List all printer models."""
    return db.query(PrinterModel).all()


@router.post("", response_model=PrinterModelResponse)
def create_model(model: PrinterModelCreate, db: Session = Depends(get_db)):
    """Create a new printer model."""
    existing = db.query(PrinterModel).filter(PrinterModel.id == model.id).first()
    if existing:
        raise HTTPException(status_code=400, detail="Model already exists")

    db_model = PrinterModel(**model.model_dump())
    db.add(db_model)
    db.commit()
    db.refresh(db_model)
    return db_model


@router.get("/{model_id}", response_model=PrinterModelResponse)
def get_model(model_id: str, db: Session = Depends(get_db)):
    """Get a specific printer model."""
    model = db.query(PrinterModel).filter(PrinterModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")
    return model


@router.get("/{model_id}/bom", response_model=List[BOMItemResponse])
def get_model_bom(model_id: str, db: Session = Depends(get_db)):
    """Get BOM for a specific printer model."""
    model = db.query(PrinterModel).filter(PrinterModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    return db.query(BOMItem).filter(BOMItem.printer_model_id == model_id).all()


@router.post("/{model_id}/bom", response_model=BOMItemResponse)
def add_bom_item(model_id: str, item: BOMItemCreate, db: Session = Depends(get_db)):
    """Add a BOM item to a printer model."""
    model = db.query(PrinterModel).filter(PrinterModel.id == model_id).first()
    if not model:
        raise HTTPException(status_code=404, detail="Model not found")

    db_item = BOMItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item
