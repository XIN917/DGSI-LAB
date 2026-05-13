"""Seed database with initial data from config."""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy.orm import Session
from app.db import SessionLocal, init_db
from app.models import (
    PrinterModel, BOMItem, MaterialType, Supplier,
    SupplierProduct, InventoryLog, EventLog
)
from app.utils.config_loader import load_config


def seed_database():
    """Initialize database with default data."""
    # Ensure tables exist
    init_db()

    db = SessionLocal()

    try:
        # Load config
        config = load_config("config/default_config.yaml")

        # Seed printer models
        print("Seeding printer models...")
        for model_data in config.get("printer_models", []):
            existing = db.query(PrinterModel).filter(PrinterModel.id == model_data["id"]).first()
            if not existing:
                model = PrinterModel(**model_data)
                db.add(model)
                print(f"  Added printer model: {model.name}")

        # Seed materials
        print("Seeding material types...")
        for mat_data in config.get("materials", []):
            existing = db.query(MaterialType).filter(MaterialType.id == mat_data["id"]).first()
            if not existing:
                mat = MaterialType(**mat_data)
                db.add(mat)
                print(f"  Added material: {mat.name}")

        # Seed suppliers and their products
        print("Seeding suppliers...")
        for sup_data in config.get("suppliers", []):
            existing = db.query(Supplier).filter(Supplier.id == sup_data["id"]).first()
            if not existing:
                supplier = Supplier(id=sup_data["id"], name=sup_data["name"], lead_time_days=sup_data["lead_time_days"])
                db.add(supplier)
                print(f"  Added supplier: {supplier.name}")

                # Add products
                for prod_data in sup_data.get("products", []):
                    product_id = prod_data.get("id", f"{sup_data['id']}_{prod_data.get('material_type', 'product')}")
                    product = SupplierProduct(
                        id=product_id,
                        supplier_id=sup_data["id"],
                        **{k: v for k, v in prod_data.items() if k not in ["id"]}
                    )
                    db.add(product)
                    print(f"    Added product: {prod_data.get('material_type', 'unknown')}")

        # Seed inventory
        print("Seeding inventory...")
        warehouse_capacity = config.get("simulation", {}).get("warehouse_capacity", 500)
        for material_id, quantity in config.get("initial_inventory", {}).items():
            existing = db.query(InventoryLog).filter(InventoryLog.material_type == material_id).first()
            if not existing:
                inv = InventoryLog(
                    id=f"inv_{material_id}",
                    material_type=material_id,
                    current_quantity=quantity,
                    warehouse_capacity=warehouse_capacity
                )
                db.add(inv)
                print(f"  Added inventory: {material_id} = {quantity}")

        # Log initialization event
        event = EventLog(
            id="evt_init_start",
            day=config.get("simulation", {}).get("start_day", 1),
            timestamp=0.0,
            event_type="SIMULATION_INIT",
            category="SYSTEM",
            description="Database seeded with initial data",
        )
        db.add(event)

        db.commit()
        print("\n✅ Database seeding completed!")

    except Exception as e:
        db.rollback()
        print(f"\n❌ Error seeding database: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
