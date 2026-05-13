"""HTTP client for communicating with the Provider API."""
import logging
from typing import Optional, Dict, Any, List
import httpx

logger = logging.getLogger(__name__)


class ProviderClientError(Exception):
    """Base exception for provider API errors."""
    pass


class ProviderClient:
    """Client for calling the Provider API endpoints."""

    def __init__(self, base_url: str, timeout: int = 10):
        """Initialize the provider client.

        Args:
            base_url: Base URL of provider API (e.g., http://localhost:8001)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.client = httpx.Client(timeout=timeout)

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def get_catalog(self) -> List[Dict[str, Any]]:
        """Fetch product catalog from provider.

        Returns:
            List of products with pricing tiers

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            response = self.client.get(f"{self.base_url}/api/catalog")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            msg = f"Failed to fetch catalog: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e

    def get_stock(self) -> Dict[str, int]:
        """Fetch current stock levels from provider.

        Returns:
            Dict mapping product_id to quantity

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            response = self.client.get(f"{self.base_url}/api/stock")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            msg = f"Failed to fetch stock: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e

    def place_order(
        self,
        buyer: str,
        product_id: int,
        quantity: int,
    ) -> Dict[str, Any]:
        """Place a purchase order with the provider.

        Args:
            buyer: Name of buyer (typically "manufacturer")
            product_id: ID of product to order
            quantity: Quantity to order

        Returns:
            Order response with order ID, status, pricing, expected delivery

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            payload = {
                "buyer": buyer,
                "product_id": product_id,
                "quantity": quantity,
            }
            response = self.client.post(
                f"{self.base_url}/api/orders",
                json=payload,
            )
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            msg = f"Failed to place order: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e

    def get_order_status(self, order_id: int) -> Dict[str, Any]:
        """Get the status of a provider order.

        Args:
            order_id: ID of order in provider system

        Returns:
            Order details including current status

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            response = self.client.get(f"{self.base_url}/api/orders/{order_id}")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            msg = f"Failed to fetch order status: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e

    def get_current_day(self) -> int:
        """Get the current simulation day from provider.

        Returns:
            Current day number

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            response = self.client.get(f"{self.base_url}/api/day/current")
            response.raise_for_status()
            data = response.json()
            return int(data.get("current_day", 0))
        except httpx.HTTPError as e:
            msg = f"Failed to fetch current day: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e

    def advance_day(self) -> Dict[str, Any]:
        """Advance the provider's simulation by one day.

        Returns:
            Day advancement result with counts of orders shipped/delivered

        Raises:
            ProviderClientError: If API call fails
        """
        try:
            response = self.client.post(f"{self.base_url}/api/day/advance")
            response.raise_for_status()
            return response.json()
        except httpx.HTTPError as e:
            msg = f"Failed to advance provider day: {e}"
            logger.error(msg)
            raise ProviderClientError(msg) from e
