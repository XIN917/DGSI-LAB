"""Tests for day control API endpoints."""
import pytest


@pytest.mark.asyncio
class TestDayAPI:
    """Test day control endpoints."""

    async def test_get_current_day(self, async_client):
        """Test getting current simulation day."""
        response = await async_client.get("/api/day/current")
        assert response.status_code == 200
        data = response.json()
        assert "current_day" in data
        assert isinstance(data["current_day"], int)

    async def test_advance_day(self, async_client):
        """Test advancing simulation day."""
        response = await async_client.post("/api/day/advance")
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "Advanced to day" in data["message"]


@pytest.mark.asyncio
class TestCatalogAPI:
    """Test catalog and inventory endpoints."""

    async def test_get_catalog(self, async_client):
        """Test getting product catalog."""
        response = await async_client.get("/api/catalog")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert "sku" in data[0]
        assert "name" in data[0]

    async def test_get_inventory(self, async_client):
        """Test getting current inventory."""
        response = await async_client.get("/api/inventory")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)