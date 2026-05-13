"""Daily Advance Cycle - processes all simulation events for a day."""

from typing import Dict, Any, List
from sqlalchemy.orm import Session

from app.models import (
    PurchaseOrder, PurchaseOrderStatus, InventoryLog,
    ManufacturingOrder, OrderStatus, PrinterModel
)
from app.services.event_logger import EventLogger
from app.services.demand_generator import get_demand_generator
from app.services.production_engine import get_production_engine
from app.services.inventory_manager import get_inventory_manager


class DailyCycleProcessor:
    """Processes all simulation events when advancing to a new day."""

    def __init__(self):
        self.events_processed: Dict[str, int] = {}

    def process_day_advance(self, db: Session, new_day: int, config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Process all events for advancing to a new day.

        Sequence:
        1. Process purchase order deliveries arriving today
        2. Generate new demand orders
        3. Process production completion
        4. Check for shortages and warnings
        5. Update statistics

        Args:
            db: Database session
            new_day: The day we're advancing to
            config: Optional configuration override

        Returns:
            Dict with processing results
        """
        results = {
            "new_day": new_day,
            "deliveries_processed": 0,
            "orders_generated": 0,
            "production_completed": [],
            "inventory_updates": [],
            "shortages_detected": [],
            "warnings": [],
        }

        # Step 1: Process purchase order deliveries
        arrivals = (
            db.query(PurchaseOrder)
            .filter(
                PurchaseOrder.expected_arrival == new_day,
                PurchaseOrder.status == PurchaseOrderStatus.PENDING,
            )
            .all()
        )

        inventory_mgr = get_inventory_manager()

        for po in arrivals:
            po.status = PurchaseOrderStatus.DELIVERED
            po.actual_arrival = new_day

            # Update inventory using the inventory manager
            result = inventory_mgr.receive_material(db, po.material_type, po.quantity, new_day)

            if result["success"]:
                results["inventory_updates"].append({
                    "material": po.material_type,
                    "old_quantity": result["old_quantity"],
                    "new_quantity": result["new_quantity"],
                })
            else:
                results["warnings"].append({
                    "type": "delivery_failed",
                    "po_id": po.id,
                    "reason": result.get("error"),
                })

            results["deliveries_processed"] += 1

        # Step 2: Generate new demand orders
        printer_models = db.query(PrinterModel).all()
        model_ids = [m.id for m in printer_models]

        if model_ids:
            demand_gen = get_demand_generator()
            if config:
                demand_config = config.get("demand_generation", {})
                demand_gen.set_config(demand_config)

            generated_orders = demand_gen.generate_orders_for_day(db, new_day, model_ids)
            results["orders_generated"] = len(generated_orders)

        # Step 3: Process production completion
        production_engine = get_production_engine()
        production_results = production_engine.process_production(db, new_day, config)

        results["production_completed"] = production_results.get("orders_completed", [])
        results["capacity_used"] = production_results.get("capacity_used", {})
        results["total_produced"] = production_results.get("total_produced", 0)

        # Step 4: Detect shortages for pending orders
        shortages = inventory_mgr.detect_shortages(db)
        results["shortages_detected"] = shortages

        # Log shortage events
        for shortage in shortages:
            EventLogger.log_inventory_shortage(
                db, new_day,
                shortage["material"],
                shortage["required"],
                shortage["available"]
            )

        # Commit all changes
        db.commit()

        # Reset counters
        self.events_processed = {
            "deliveries": results["deliveries_processed"],
            "orders_created": results["orders_generated"],
            "orders_completed": len(results["production_completed"]),
        }

        return results

    def reset(self):
        """Reset processor state."""
        self.events_processed.clear()


# Global instance
daily_processor = DailyCycleProcessor()


def get_daily_processor() -> DailyCycleProcessor:
    """Get the global daily cycle processor."""
    return daily_processor
