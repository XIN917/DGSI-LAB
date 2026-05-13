"""Integration tests for the full simulation flow."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.db import SessionLocal, init_db
from app.models import (
    PrinterModel, BOMItem, MaterialType, Supplier,
    SupplierProduct, InventoryLog, ManufacturingOrder, OrderStatus
)


@pytest.fixture
def client():
    """Create a test client with a clean database."""
    # Reset database for each test
    init_db()
    db = SessionLocal()
    # Clear existing data
    db.query(ManufacturingOrder).delete()
    db.query(InventoryLog).delete()
    db.query(SupplierProduct).delete()
    db.query(Supplier).delete()
    db.query(BOMItem).delete()
    db.query(PrinterModel).delete()
    db.query(MaterialType).delete()
    db.commit()
    db.close()

    client = TestClient(app)
    # Reset simulation state
    client.post("/api/simulation/reset")
    return client


def test_full_simulation_cycle(client):
    """Test a full simulation cycle: seed, advance, order, produce."""

    # 1. Seed initial data
    # Create Material
    mat_id = "test_filament"
    client.post("/api/models/materials", json={
        "id": mat_id,
        "name": "Test Filament",
        "unit": "spools"
    })

    # Create Printer Model
    model_id = "test_printer"
    client.post("/api/models", json={
        "id": model_id,
        "name": "Test Printer",
        "assembly_time_hours": 4,
        "daily_capacity": 5  # Small capacity to test partial completion
    })

    # Create BOM
    client.post(f"/api/models/{model_id}/bom", json={
        "id": "test_bom_1",
        "printer_model_id": model_id,
        "material_type": mat_id,
        "quantity_per_unit": 2.0
    })

    # Set initial inventory
    client.post("/api/inventory/logs", json={
        "id": "inv_1",
        "material_type": mat_id,
        "current_quantity": 100.0,
        "warehouse_capacity": 500
    })

    # 2. Advance day to generate demand
    # Make sure we generate at least one order by temporarily setting config
    # We'll just advance a few more days if needed
    orders = []
    days_advanced = 0
    while not orders and days_advanced < 5:
        resp = client.post("/api/simulation/advance")
        assert resp.status_code == 200
        days_advanced += 1
        resp = client.get("/api/orders")
        orders = resp.json()
    
    assert len(orders) > 0
    pending_order = next((o for o in orders if o["status"] == "PENDING"), None)
    assert pending_order is not None
    order_id = pending_order["id"]
    order_qty = pending_order["quantity"]
    current_day = 1 + days_advanced

    # 4. Release the order
    resp = client.put(f"/api/orders/{order_id}/release", json={"released_day": current_day})
    if resp.status_code != 200:
        print(f"Release failed: {resp.json()}")
    assert resp.status_code == 200

    # 5. Advance day to process production
    resp = client.post("/api/simulation/advance")
    assert resp.status_code == 200

    # 6. Check production progress
    resp = client.get(f"/api/orders/{order_id}")
    order_after = resp.json()

    # Model capacity is 5. If order_qty > 5, it should be PARTIAL.
    if order_qty > 5:
        assert order_after["status"] == "PARTIAL"
        assert order_after["completed_quantity"] == 5
    else:
        assert order_after["status"] == "COMPLETED"
        assert order_after["completed_quantity"] == order_qty

    # 7. Check inventory consumption
    # BOM is 2 per unit. Produced 5 (or order_qty if < 5).
    # Consumption = 5 * 2 = 10 (or order_qty * 2)
    consumed = min(order_qty, 5) * 2
    resp = client.get("/api/inventory")
    inventory = resp.json()
    mat_stock = next((i for i in inventory if i["material_type"] == mat_id), None)
    assert mat_stock["current_quantity"] == 100.0 - consumed


def test_export_import_cycle(client):
    """Test exporting and then importing the simulation state."""

    # 1. Seed some data
    client.post("/api/models/materials", json={
        "id": "mat_1",
        "name": "Mat 1",
        "unit": "units"
    })

    # 2. Advance a few days
    client.post("/api/simulation/advance")
    client.post("/api/simulation/advance")

    # 3. Export
    resp = client.get("/api/simulation/export")
    assert resp.status_code == 200
    export_data = resp.json()
    assert export_data["simulation_state"]["current_day"] == 3

    # 4. Modify something (reset)
    client.post("/api/simulation/reset")
    resp = client.get("/api/simulation/status")
    assert resp.json()["current_day"] == 1

    # 5. Import
    resp = client.post("/api/simulation/import", json=export_data)
    assert resp.status_code == 200

    # 6. Verify restoration
    resp = client.get("/api/simulation/status")
    assert resp.json()["current_day"] == 3
    resp = client.get("/api/models/materials")
    assert len(resp.json()) > 0
