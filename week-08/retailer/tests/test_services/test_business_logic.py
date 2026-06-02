import pytest
from unittest.mock import patch
from app.services.retailer_service import RetailerService
from app.models.database import InventoryItemDB
from app.models.product import ProductCatalogItem
from sqlalchemy import update

_MOCK_CATALOG = [
    ProductCatalogItem(sku="P3D-Classic", name="Classic", retail_price=295.0, wholesale_price=195.0),
    ProductCatalogItem(sku="P3D-Pro",     name="Pro",     retail_price=435.0, wholesale_price=290.0),
]


class TestBusinessLogic:
    def test_pricing_markup_enforcement(self, db_session, sample_inventory):
        service = RetailerService(db=db_session)

        # Wholesale for Classic is €195 → minimum retail is €224.25
        with patch.object(RetailerService, "get_catalog", return_value=_MOCK_CATALOG):
            # Valid price (above 224.25)
            service.set_retail_price("P3D-Classic", 250.0)
            item = service.get_inventory_item("P3D-Classic")
            assert item.retail_price == 250.0

            # Invalid price (below 224.25)
            with pytest.raises(ValueError, match="below the minimum 15% markup"):
                service.set_retail_price("P3D-Classic", 200.0)

    def test_backorder_auto_fulfillment(self, db_session, sample_inventory):
        service = RetailerService(db=db_session)

        # Set Pro stock to 0
        db_session.execute(
            update(InventoryItemDB)
            .where(InventoryItemDB.sku == "P3D-Pro")
            .values(quantity_on_hand=0)
        )
        db_session.commit()

        # Create order (will be backordered)
        order = service.create_customer_order("P3D-Pro", 5)
        assert order.status == "backordered"

        # Receive stock and advance day (triggers process_backorders)
        service.receive_inventory("P3D-Pro", 10, 2000.0)
        service.advance_day()

        orders = service.list_customer_orders()
        updated = next(o for o in orders if o.id == order.id)
        assert updated.status == "fulfilled"

        item = service.get_inventory_item("P3D-Pro")
        assert item.quantity_on_hand == 5
