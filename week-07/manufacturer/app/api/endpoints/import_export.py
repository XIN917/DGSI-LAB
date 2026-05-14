"""Import/Export API endpoints for full game state."""
import json
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.api.dependencies import get_current_active_user
from app.models.user import User
from app.utils.json_export import export_full_state, import_full_state
from app.services.seed import load_production_plan, initialize_seed_data

router = APIRouter(prefix="/api", tags=["import-export"])


@router.get("/export/full-state")
def export_state(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Export complete game state as JSON (inventory, config, orders, events)."""
    return export_full_state(db)


@router.post("/import/full-state")
def import_state(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Import a complete game state.
    WARNING: Replaces all simulation data (users are preserved).
    """
    try:
        result = import_full_state(db, data)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Import failed: {str(e)}")
    return result


@router.post("/import/production-plan")
def import_production_plan(
    data: dict,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """
    Import a production plan (models, suppliers, initial inventory).
    Does NOT clear orders or events — only replaces configuration.
    """
    required_keys = {"models", "suppliers", "initial_inventory"}
    missing = required_keys - set(data.keys())
    if missing:
        raise HTTPException(status_code=422, detail=f"Missing required keys: {missing}")

    try:
        from app.models.product import ProductModel, BOMItem
        from app.models.purchase_order import Supplier, SupplierProduct
        from app.models.inventory import Inventory
        from decimal import Decimal

        # Merge models (upsert)
        for model_id, model_data in data["models"].items():
            existing = db.query(ProductModel).filter(ProductModel.id == model_id).first()
            if not existing:
                db.add(ProductModel(
                    id=model_id,
                    name=model_data["name"],
                    assembly_time_days=model_data.get("assembly_time_days", 1),
                ))
            for material, bom_info in model_data.get("bom", {}).items():
                existing_bom = db.query(BOMItem).filter(
                    BOMItem.model_id == model_id,
                    BOMItem.material_name == material,
                ).first()
                if not existing_bom:
                    db.add(BOMItem(
                        model_id=model_id,
                        material_name=material,
                        quantity_required=Decimal(str(bom_info["qty"])),
                        pcb_ref=bom_info.get("pcb_ref"),
                    ))

        # Merge suppliers
        for sup_data in data["suppliers"]:
            existing = db.query(Supplier).filter(Supplier.id == sup_data["id"]).first()
            if not existing:
                db.add(Supplier(
                    id=sup_data["id"],
                    name=sup_data["name"],
                    lead_time_days=sup_data["lead_time_days"],
                    active=True,
                ))
                for prod in sup_data.get("products", []):
                    db.add(SupplierProduct(
                        supplier_id=sup_data["id"],
                        product_name=prod["name"],
                        base_unit_cost=Decimal(str(prod["base_cost"])),
                        packaging_unit=prod.get("packaging"),
                        packaging_qty=prod.get("pack_qty"),
                        discount_tiers=json.dumps(prod.get("tiers", [])),
                    ))

        # Merge inventory
        for product_name, inv_data in data["initial_inventory"].items():
            existing = db.query(Inventory).filter(Inventory.product_name == product_name).first()
            if not existing:
                db.add(Inventory(
                    product_name=product_name,
                    quantity=Decimal(str(inv_data["qty"])),
                    reserved_quantity=Decimal("0"),
                    unit_type=inv_data.get("type", "raw"),
                ))

        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Plan import failed: {str(e)}")

    return {"status": "imported", "models": len(data["models"]), "suppliers": len(data["suppliers"])}
