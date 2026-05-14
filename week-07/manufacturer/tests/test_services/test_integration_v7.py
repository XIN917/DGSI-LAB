"""Tests for Week 7 integration features."""
import pytest
from decimal import Decimal
from datetime import datetime
from app.services.order_service import OrderService
from app.services.inventory_service import InventoryService
from app.models.product import ProductModel
from app.models.inventory import Inventory

def test_order_auto_fulfillment(db_session):
    """Test that orders are auto-fulfilled if finished stock is available."""
    # Setup: Create a product with finished stock
    product = ProductModel(id="P3D-Classic", name="Classic", wholesale_price=Decimal("1200"))
    inventory = Inventory(
        product_name="P3D-Classic",
        quantity=Decimal("10"),
        unit_type="finished"
    )
    db_session.add(product)
    db_session.add(inventory)
    db_session.commit()

    svc = OrderService(db_session)
    
    # Create order for 3 units
    order = svc.create("P3D-Classic", Decimal("3"), datetime.utcnow())
    
    # Verify order is delivered
    assert order.status == "delivered"
    assert order.quantity_produced == Decimal("3")
    assert order.delivery_day is not None
    
    # Verify inventory is reduced
    db_session.refresh(inventory)
    assert inventory.quantity == Decimal("7")

def test_production_adds_to_finished_stock(db_session):
    """Test that completing production adds to finished goods inventory."""
    # Setup: Create a product and a released order
    product = ProductModel(id="P3D-Pro", name="Pro", wholesale_price=Decimal("2000"))
    inventory = Inventory(
        product_name="P3D-Pro",
        quantity=Decimal("0"),
        unit_type="finished"
    )
    db_session.add(product)
    db_session.add(inventory)
    db_session.commit()

    svc = OrderService(db_session)
    # Manual creation with "pending" (since create might auto-fulfill if we are not careful, 
    # but here stock is 0 so it will be pending)
    order = svc.create("P3D-Pro", Decimal("5"), datetime.utcnow())
    assert order.status == "pending"
    
    # Release it (manual status change to skip BOM check in this simple test)
    order.status = "released"
    db_session.commit()
    
    # Produce units
    svc.produce_units(order.id, 5.0, datetime.utcnow().date(), current_day=2)
    
    # Verify order is delivered
    db_session.refresh(order)
    assert order.status == "delivered"
    assert order.delivery_day == 2
    
    # Verify inventory is increased
    db_session.refresh(inventory)
    assert inventory.quantity == Decimal("5")
