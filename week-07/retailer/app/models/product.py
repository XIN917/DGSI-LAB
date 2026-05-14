from pydantic import BaseModel


class InventoryItem(BaseModel):
    sku: str
    quantity_on_hand: int
    quantity_reserved: int = 0
    retail_price: float
    last_cost: float | None = None


class ProductCatalogItem(BaseModel):
    sku: str
    name: str
    retail_price: float
    wholesale_price: float | None = None
