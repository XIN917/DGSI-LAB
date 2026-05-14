import httpx
from typing import List, Dict, Optional
from decimal import Decimal

class ProviderClient:
    def __init__(self, base_url: str):
        self.base_url = base_url.rstrip("/")

    def get_catalog(self) -> List[Dict]:
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/api/catalog/")
            response.raise_for_status()
            return response.json()

    def place_order(self, buyer: str, product_id: int, quantity: int) -> Dict:
        with httpx.Client() as client:
            payload = {
                "buyer": buyer,
                "product_id": product_id,
                "quantity": quantity
            }
            response = client.post(f"{self.base_url}/api/orders/", json=payload)
            response.raise_for_status()
            return response.json()

    def get_order_status(self, order_id: int) -> Dict:
        with httpx.Client() as client:
            response = client.get(f"{self.base_url}/api/orders/{order_id}")
            response.raise_for_status()
            return response.json()
