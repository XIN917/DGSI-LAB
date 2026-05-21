"""Tests for RetailerService business logic."""
import pytest

from app.services.retailer_service import RetailerService


class TestRetailerService:
    """Test RetailerService methods."""

    @pytest.mark.asyncio
    async def test_get_current_day(self, db_session, async_session_local):
        """Test retrieving current simulation day."""
        service = RetailerService(session_local=async_session_local)
        day = await service.get_current_day()
        assert day == 0

    @pytest.mark.asyncio
    async def test_set_current_day(self, db_session, async_session_local):
        """Test setting current simulation day."""
        service = RetailerService(session_local=async_session_local)
        await service.set_current_day(5)
        day = await service.get_current_day()
        assert day == 5

    @pytest.mark.asyncio
    async def test_get_catalog(self, db_session, async_session_local):
        """Test retrieving product catalog."""
        service = RetailerService(session_local=async_session_local)
        catalog = await service.get_catalog()
        assert len(catalog) == 2
        assert catalog[0].sku == "P3D-Classic"
        assert catalog[1].sku == "P3D-Pro"

    @pytest.mark.asyncio
    async def test_create_customer_order_fulfilled(self, db_session, async_session_local, sample_inventory):
        """Test creating customer order that can be fulfilled."""
        service = RetailerService(session_local=async_session_local)
        order = await service.create_customer_order("P3D-Classic", 2)

        assert order.sku == "P3D-Classic"
        assert order.quantity == 2
        assert order.status == "fulfilled"
        assert order.retail_price == 1500.0

    @pytest.mark.asyncio
    async def test_create_customer_order_backordered(self, db_session, async_session_local, sample_inventory):
        """Test creating customer order that gets backordered."""
        service = RetailerService(session_local=async_session_local)
        order = await service.create_customer_order("P3D-Pro", 10)  # Only 5 in stock

        assert order.sku == "P3D-Pro"
        assert order.quantity == 10
        assert order.status == "backordered"

    @pytest.mark.asyncio
    async def test_create_customer_order_rejects_non_positive_quantity(self, db_session, async_session_local, sample_inventory):
        """Negative demand must not increase inventory."""
        service = RetailerService(session_local=async_session_local)

        with pytest.raises(ValueError, match="Quantity must be positive"):
            await service.create_customer_order("P3D-Classic", -2)

        inventory = await service.get_inventory_item("P3D-Classic")
        assert inventory.quantity_on_hand == 10

    @pytest.mark.asyncio
    async def test_create_customer_order_rejects_unknown_sku(self, db_session, async_session_local, sample_inventory):
        service = RetailerService(session_local=async_session_local)

        with pytest.raises(ValueError, match="Unknown SKU"):
            await service.create_customer_order("NOPE", 1)

    @pytest.mark.asyncio
    async def test_create_customer_order_uses_catalog_price_when_inventory_missing(self, db_session, async_session_local):
        service = RetailerService(session_local=async_session_local)

        order = await service.create_customer_order("P3D-Classic", 1)

        assert order.status == "backordered"
        assert order.retail_price == 1500.0

    @pytest.mark.asyncio
    async def test_set_retail_price_rejects_non_positive_price(self, db_session, async_session_local, sample_inventory):
        service = RetailerService(session_local=async_session_local)

        with pytest.raises(ValueError, match="Price must be positive"):
            await service.set_retail_price("P3D-Classic", 0)

    @pytest.mark.asyncio
    async def test_set_retail_price_rejects_unknown_sku(self, db_session, async_session_local, sample_inventory):
        service = RetailerService(session_local=async_session_local)

        with pytest.raises(ValueError, match="Unknown SKU"):
            await service.set_retail_price("NOPE", 100)

    @pytest.mark.asyncio
    async def test_advance_day(self, db_session, async_session_local):
        """Test advancing simulation day."""
        service = RetailerService(session_local=async_session_local)
        result = await service.advance_day()

        assert "Advanced to day 1" in result["message"]

        day = await service.get_current_day()
        assert day == 1
