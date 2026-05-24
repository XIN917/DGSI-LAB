
from sqlalchemy.orm import Session
from app.core.database import SessionLocal
from app.models.order import ManufacturingOrder
from app.models.inventory import Inventory
from app.services.inventory_service import InventoryService
from app.services.simulation_engine import SimulationEngine
from decimal import Decimal

def fulfill_from_stock():
    db = SessionLocal()
    inv_svc = InventoryService(db)
    engine = SimulationEngine(db)
    
    # Get all pending or waiting orders
    orders = db.query(ManufacturingOrder).filter(
        ManufacturingOrder.status.in_(["pending", "waiting_materials"])
    ).order_by(ManufacturingOrder.created_date.asc()).all()
    
    for order in orders:
        inv = inv_svc.get_by_product(order.product_model)
        if inv and inv.unit_type == "finished" and inv.quantity >= order.quantity_needed:
            print(f"Fulfilling order {order.id} ({order.product_model}, Qty {order.quantity_needed}) from stock.")
            # Adjust stock
            inv_svc.adjust(order.product_model, inv.quantity - order.quantity_needed)
            
            # Update order
            order.status = "delivered"
            order.quantity_produced = order.quantity_needed
            order.delivery_day = engine.current_day
            db.commit()
        else:
            # print(f"Not enough stock for order {order.id} ({order.product_model})")
            pass
            
    db.close()

if __name__ == "__main__":
    fulfill_from_stock()
