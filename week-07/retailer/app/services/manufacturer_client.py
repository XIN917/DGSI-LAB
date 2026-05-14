import httpx
from typing import Dict, Any, Optional

from app.core.config import settings


class ManufacturerClient:
    VALID_SKUS = {"P3D-Classic", "P3D-Pro"}

    def __init__(self) -> None:
        self.base_url = str(settings.manufacturer_url).rstrip("/")
        self._access_token: Optional[str] = None

    async def _get_access_token(self, client: httpx.AsyncClient) -> str:
        if self._access_token:
            return self._access_token

        response = await client.post(
            f"{self.base_url}/api/auth/login",
            data={
                "username": settings.manufacturer_username,
                "password": settings.manufacturer_password,
            },
            timeout=30.0,
        )
        response.raise_for_status()
        self._access_token = response.json()["access_token"]
        return self._access_token

    async def _auth_headers(self, client: httpx.AsyncClient) -> Dict[str, str]:
        token = await self._get_access_token(client)
        return {"Authorization": f"Bearer {token}"}

    async def place_order(self, sku: str, quantity: int) -> Dict[str, Any]:
        """Place a purchase order with the manufacturer."""
        if sku not in self.VALID_SKUS:
            raise ValueError(f"Unknown SKU: {sku}")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/orders",
                    headers=await self._auth_headers(client),
                    json={"product_model": sku, "quantity": quantity},
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

    async def get_order(self, order_id: int) -> Dict[str, Any]:
        """Get purchase order details from manufacturer."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/orders/{order_id}",
                    headers=await self._auth_headers(client),
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get order from manufacturer: {e}")

    async def get_catalog(self) -> Dict[str, Any]:
        """Get product catalog from manufacturer."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/catalog",
                    headers=await self._auth_headers(client),
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get catalog from manufacturer: {e}")

    async def get_current_day(self) -> int:
        """Get current simulation day from manufacturer."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/api/day/current",
                    headers=await self._auth_headers(client),
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()
                return data.get("current_day", 0)
            except httpx.HTTPError as e:
                raise Exception(f"Failed to get current day from manufacturer: {e}")

    async def advance_day(self) -> Dict[str, Any]:
        """Advance simulation day in manufacturer."""
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/api/day/advance",
                    headers=await self._auth_headers(client),
                    timeout=30.0,
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                raise Exception(f"Failed to advance day in manufacturer: {e}")
