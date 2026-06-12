"""Verification tests for Phase 2 simulation logic."""
import pytest
from decimal import Decimal
from datetime import datetime, date
from sqlalchemy.orm import Session

from app.services.simulation_engine import SimulationEngine
from app.services.order_service import OrderService
from app.services.inventory_service import InventoryService
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.purchase_order import PurchaseOrder, Supplier, SupplierProduct
from app.models.order import ManufacturingOrder
from app.models.event import EventLog

@pytest.fixture
def sim_engine(db_session: Session):
    return SimulationEngine(db_session)

@pytest.fixture
def order_svc(db_session: Session):
    return OrderService(db_session)

@pytest.fixture
def inv_svc(db_session: Session):
    return InventoryService(db_session)

def setup_test_data(db: Session):
    """Setup a product with BOM and some initial inventory."""
    # Product Model
    model = ProductModel(id="P3D-Test", name="Test Printer", assembly_time_days=1)
    db.add(model)
    
    # BOM: 1 Frame, 1 Motor per unit
    db.add(BOMItem(model_id="P3D-Test", material_name="Frame", quantity_required=Decimal("1")))
    db.add(BOMItem(model_id="P3D-Test", material_name="Motor", quantity_required=Decimal("1")))
    
    # Inventory
    db.add(Inventory(product_name="Frame", quantity=Decimal("100"), reserved_quantity=Decimal("0")))
    db.add(Inventory(product_name="Motor", quantity=Decimal("100"), reserved_quantity=Decimal("0")))
    
    # Supplier for PO test
    supplier = Supplier(id=1, name="Test Supplier", lead_time_days=3)
    db.add(supplier)
    db.commit()

def test_po_delivery_logic(sim_engine, db_session):
    setup_test_data(db_session)
    
    # Create a PO due today
    po = PurchaseOrder(
        supplier_id=1,
        product_name="Frame",
        quantity_ordered=Decimal("50"),
        quantity_delivered=Decimal("0"),
        unit_cost=Decimal("10.00"),
        status="pending",
        order_date=datetime.combine(sim_engine.current_date, datetime.min.time()),
        expected_delivery=datetime.combine(sim_engine.current_date, datetime.min.time())
    )
    db_session.add(po)
    db_session.commit()
    
    initial_qty = db_session.query(Inventory).filter(Inventory.product_name == "Frame").first().quantity
    
    # Advance day
    result = sim_engine.advance_day()
    
    # Check PO delivery
    db_session.refresh(po)
    assert po.status == "delivered"
    assert po.quantity_delivered == Decimal("50")
    
    # Check inventory increased
    new_qty = db_session.query(Inventory).filter(Inventory.product_name == "Frame").first().quantity
    assert new_qty == initial_qty + Decimal("50")
    
    # Check event generated
    assert any(e["type"] == "po_arrived" for e in result["events_generated"])

def test_demand_generation_logic(sim_engine, db_session):
    setup_test_data(db_session)
    
    # Advance day
    result = sim_engine.advance_day()
    
    # Check demand generated (1-3 orders)
    demand_events = [e for e in result["events_generated"] if e["type"] == "demand_generated"]
    assert 1 <= len(demand_events) <= 3
    
    # Check orders created in DB
    orders = db_session.query(ManufacturingOrder).all()
    assert len(orders) == len(demand_events)

def test_production_and_capacity_logic(sim_engine, order_svc, db_session):
    setup_test_data(db_session)
    sim_engine.update_capacity(10) # Set capacity to 10
    
    # Create and release an order for 15 units
    order = order_svc.create("P3D-Test", Decimal("15"), sim_engine.current_date)
    success, error = order_svc.release(order.id)
    assert success is True
    
    # Check initial reservations
    frame_inv = db_session.query(Inventory).filter(Inventory.product_name == "Frame").first()
    assert frame_inv.reserved_quantity == Decimal("15")
    
    # Day 1: Should produce 10 units (capacity limit)
    result = sim_engine.advance_day()
    db_session.refresh(order)
    assert order.quantity_produced == Decimal("10")
    assert order.status == "released"
    
    # Check inventory consumption
    db_session.refresh(frame_inv)
    assert frame_inv.quantity == Decimal("90") # 100 - 10
    assert frame_inv.reserved_quantity == Decimal("5") # 15 - 10
    
    # Day 2: Should produce remaining 5 units
    result = sim_engine.advance_day()
    db_session.refresh(order)
    assert order.quantity_produced == Decimal("15")
    assert order.status == "completed"
    
    # Check inventory consumption final
    db_session.refresh(frame_inv)
    assert frame_inv.quantity == Decimal("85") # 90 - 5
    assert frame_inv.reserved_quantity == Decimal("0") # 5 - 5

def test_inventory_snapshot_logic(sim_engine, db_session):
    setup_test_data(db_session)
    
    # Advance day
    result = sim_engine.advance_day()
    
    # Check snapshot event
    assert any(e["type"] == "inventory_snapshot" for e in result["events_generated"])
    
    # Check EventLog entry
    snapshot_log = db_session.query(EventLog).filter(EventLog.event_type == "inventory_snapshot").first()
    assert snapshot_log is not None
    assert "Frame" in snapshot_log.details
