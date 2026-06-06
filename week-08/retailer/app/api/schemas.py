from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    customer: str
    model: str
    quantity: int
    notes: Optional[str] = None
