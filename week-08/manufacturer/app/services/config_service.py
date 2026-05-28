"""Configuration service for product models and suppliers."""
from typing import List, Optional
from sqlalchemy.orm import Session

from app.models.product import ProductModel
from app.models.purchase_order import Supplier


class ConfigService:
    def __init__(self, db: Session):
        self.db = db

    def get_models(self) -> List[ProductModel]:
        return self.db.query(ProductModel).all()

    def get_model(self, model_id: str) -> Optional[ProductModel]:
        return self.db.query(ProductModel).filter(ProductModel.id == model_id).first()

    def get_suppliers(self) -> List[Supplier]:
        return self.db.query(Supplier).filter(Supplier.active == True).all()

    def add_supplier(self, name: str, lead_time_days: int) -> Supplier:
        supplier = Supplier(name=name, lead_time_days=lead_time_days, active=True)
        self.db.add(supplier)
        self.db.commit()
        self.db.refresh(supplier)
        return supplier
