"""Database seeding functionality."""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.purchase_order import Supplier, SupplierProduct
from app.core.security import get_password_hash


def load_production_plan() -> dict:
    """Load the default production plan from JSON."""
    plan_path = Path(__file__).parent.parent.parent / "sample_data" / "default_production_plan.json"
    with open(plan_path) as f:
        return json.load(f)


def seed_default_admin(db: Session) -> User:
    """Create default admin user if not exists."""
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        return existing

    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),  # Change in production!
        role="admin"
    )
    db.add(admin)
    db.commit()
    return admin


def initialize_seed_data(db: Session = None):
    """Initialize database with sample data."""
    from app.core.database import SessionLocal
    if db is None:
        db = SessionLocal()

    try:
        plan = load_production_plan()

        # Seed product models and BOMs
        for model_id, model_data in plan["models"].items():
            existing = db.query(ProductModel).filter(ProductModel.id == model_id).first()
            if not existing:
                model = ProductModel(
                    id=model_id,
                    name=model_data["name"],
                    assembly_time_days=model_data["assembly_time_days"]
                )
                db.add(model)

            # Add BOM items
            for material, bom_info in model_data["bom"].items():
                existing_bom = db.query(BOMItem).filter(
                    BOMItem.model_id == model_id,
                    BOMItem.material_name == material
                ).first()
                if not existing_bom:
                    bom_item = BOMItem(
                        model_id=model_id,
                        material_name=material,
                        quantity_required=Decimal(str(bom_info["qty"])),
                        pcb_ref=bom_info.get("pcb_ref")
                    )
                    db.add(bom_item)

        # Seed suppliers and their products
        for supplier_data in plan["suppliers"]:
            existing = db.query(Supplier).filter(Supplier.id == supplier_data["id"]).first()
            if not existing:
                supplier = Supplier(
                    id=supplier_data["id"],
                    name=supplier_data["name"],
                    lead_time_days=supplier_data["lead_time_days"],
                    active=True
                )
                db.add(supplier)

                for product_data in supplier_data["products"]:
                    sup_product = SupplierProduct(
                        supplier_id=supplier_data["id"],
                        product_name=product_data["name"],
                        base_unit_cost=Decimal(str(product_data["base_cost"])),
                        packaging_unit=product_data.get("packaging"),
                        packaging_qty=product_data.get("pack_qty"),
                        discount_tiers=json.dumps(product_data.get("tiers", []))
                    )
                    db.add(sup_product)

        # Seed initial inventory
        for product_name, inv_data in plan["initial_inventory"].items():
            existing = db.query(Inventory).filter(Inventory.product_name == product_name).first()
            if not existing:
                # Set a realistic max capacity (default 250 or specific to part)
                max_cap = 250
                if "motor" in product_name: max_cap = 500
                if "kit" in product_name: max_cap = 200
                if "sensor" in product_name: max_cap = 300
                
                inventory = Inventory(
                    product_name=product_name,
                    quantity=Decimal(str(inv_data["qty"])),
                    reserved_quantity=Decimal("0"),
                    max_capacity=Decimal(str(max_cap)),
                    unit_type=inv_data.get("type", "raw")
                )
                db.add(inventory)

        # Seed default admin user
        seed_default_admin(db)

        # Seed default simulation state (singleton)
        from app.models.simulation import SimulationState
        from app.core.config import get_settings
        settings = get_settings()
        existing_state = db.query(SimulationState).first()
        if not existing_state:
            import json as _json
            state = SimulationState(
                current_day=1,
                current_date=settings.SIMULATION_START_DATE,
                demand_params=_json.dumps({
                    "P3D-Classic": {"mean": 8, "variance": 3},
                    "P3D-Pro": {"mean": 5, "variance": 2}
                }),
                capacity_per_day=settings.DEFAULT_CAPACITY_PER_DAY,
                warehouse_capacity=settings.DEFAULT_WAREHOUSE_CAPACITY
            )
            db.add(state)

        db.commit()

    except Exception as e:
        db.rollback()
        raise e
