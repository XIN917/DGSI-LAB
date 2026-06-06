"""Tests for retailer purchase-order delivery synchronization."""

from app.models.database import InventoryItemDB, PurchaseOrderDB
from app.services.retailer_service import RetailerService


def test_released_purchase_order_is_still_synced_and_received(db_session):
    db_session.add(
        InventoryItemDB(
            sku="P3D-Classic",
            quantity_on_hand=0,
            retail_price=1500.0,
            last_cost=1200.0,
        )
    )
    db_session.add(
        PurchaseOrderDB(
            manufacturer_po_id=42,
            sku="P3D-Classic",
            quantity=12,
            wholesale_unit_price=1200.0,
            retail_unit_price=1500.0,
            status="released",
            placed_day=0,
        )
    )
    db_session.commit()

    service = RetailerService(db_session)
    service.manufacturer_client.get_order = lambda order_id: {
        "id": order_id,
        "status": "delivered",
        "delivery_day": 1,
    }

    service.check_purchase_order_deliveries()

    po = db_session.query(PurchaseOrderDB).one()
    inventory = db_session.query(InventoryItemDB).one()

    assert po.status == "delivered"
    assert po.received_day == 0
    assert inventory.quantity_on_hand == 12
