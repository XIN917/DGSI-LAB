import pytest
from app.services.retailer_service import RetailerService
from app.models.database import OrderStatus

@pytest.mark.asyncio
class TestBusinessLogic:
    async def test_pricing_markup_enforcement(self, db_session, async_session_local):
        service = RetailerService(session_local=async_session_local)
        
        # Wholesale for Classic is 1200.0 (from fallback catalog)
        # 1200 * 1.15 = 1380.0
        
        # Valid price
        await service.set_retail_price("P3D-Classic", 1400.0)
        item = await service.get_inventory_item("P3D-Classic")
        assert item.retail_price == 1400.0
        
        # Invalid price (below 15% markup)
        with pytest.raises(ValueError, match="below the minimum 15% markup"):
            await service.set_retail_price("P3D-Classic", 1300.0)

    async def test_backorder_auto_fulfillment(self, db_session, async_session_local):
        service = RetailerService(session_local=async_session_local)
        
        # Start with 0 stock for Pro
        async with async_session_local() as session:
            from app.models.database import InventoryItemDB
            from sqlalchemy import update
            await session.execute(
                update(InventoryItemDB).where(InventoryItemDB.sku == "P3D-Pro").values(quantity_on_hand=0)
            )
            await session.commit()
            
        # Create order (will be backordered)
        order = await service.create_customer_order("P3D-Pro", 5)
        assert order.status == OrderStatus.backordered
        
        # Receive stock
        await service.receive_inventory("P3D-Pro", 10, 2000.0)
        
        # Advance day (calls process_backorders)
        await service.advance_day()
        
        # Check order again
        orders = await service.list_customer_orders()
        updated_order = next(o for o in orders if o.id == order.id)
        assert updated_order.status == OrderStatus.fulfilled
        
        # Check inventory (10 - 5 = 5 left)
        item = await service.get_inventory_item("P3D-Pro")
        assert item.quantity_on_hand == 5
        assert item.quantity_reserved == 5
