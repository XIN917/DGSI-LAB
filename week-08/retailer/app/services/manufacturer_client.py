import httpx
from typing import Dict, Any, Optional

from app.core.config import settings


class ManufacturerClient:
    VALID_SKUS = {"P3D-Classic", "P3D-Pro"}

    def __init__(self) -> None:
        self.base_url = str(settings.manufacturer_url).rstrip("/")

    def place_order(self, sku: str, quantity: int, retailer_name: Optional[str] = None) -> Dict[str, Any]:
        """Place a purchase order with the manufacturer."""
        if sku not in self.VALID_SKUS:
            raise ValueError(f"Unknown SKU: {sku}")

        with httpx.Client() as client:
            try:
                response = client.post(
                    f"{self.base_url}/api/orders",
                    json={
                        "product_model": sku,
                        "quantity": quantity,
                        "retailer_name": retailer_name
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                order = response.json()
                return {
                    "id": order.get("id"),
                    "sku": sku,
                    "quantity": quantity,
                    "status": order.get("status"),
                    "manufacturer_order": order,
                    "message": f"Placed manufacturer order #{order.get('id')} for {quantity}x {sku}",
                }
            except httpx.HTTPError as e:
                raise Exception(f"Failed to place order with manufacturer: {e}")

    def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get purchase order details from manufacturer."""
        with httpx.Client() as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/orders/{order_id}",
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get order from manufacturer: {e}")

    def get_catalog(self) -> Dict[str, Any]:
        """Get product catalog from manufacturer."""
        with httpx.Client() as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/catalog",
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get catalog from manufacturer: {e}")

    def get_current_day(self) -> int:
        """Get current simulation day from manufacturer."""
        with httpx.Client() as client:
            try:
                response = client.get(
                    f"{self.base_url}/api/day/current",
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("current_day", 0)
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get current day from manufacturer: {e}")

    def advance_day(self) -> Dict[str, Any]:
        """Advance simulation day in manufacturer."""
        with httpx.Client() as client:
            try:
                response = client.post(
                    f"{self.base_url}/api/day/advance",
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to advance day in manufacturer: {e}")
