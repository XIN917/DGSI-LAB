from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.core.database import get_db
from app.services.provider_service import ProviderService
from app.api.schemas import StockSchema
from pydantic import BaseModel, Field
from app.models.product import Stock

router = APIRouter()


class RestockRequest(BaseModel):
    quantity: int = Field(gt=0)

@router.get("/", response_model=List[StockSchema])
def get_stock(db: Session = Depends(get_db)):
    service = ProviderService(db)
    return service.get_stock()


@router.post("/restock/{product_id}", response_model=StockSchema)
def restock(product_id: int, body: RestockRequest, db: Session = Depends(get_db)):
    service = ProviderService(db)
    try:
        service.restock(product_id, body.quantity)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return db.query(Stock).filter(Stock.product_id == product_id).first()
