"""JSON export/import utilities."""

import json
from pathlib import Path
from typing import Dict, Any, List, Type
from datetime import datetime
from sqlalchemy.orm import Session
from sqlalchemy import inspect

from app.models import (
    PrinterModel, BOMItem, MaterialType, Supplier,
    SupplierProduct, InventoryLog, ManufacturingOrder,
    PurchaseOrder, EventLog
)


def to_dict(model_instance):
    """Convert a SQLAlchemy model instance to a dictionary."""
    if model_instance is None:
        return None
    return {c.key: getattr(model_instance, c.key) for c in inspect(model_instance).mapper.column_attrs}


def export_state(data: Dict[str, Any], output_path: str = "exports/state_export.json") -> str:
    """Export simulation state to JSON file."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    export_data = {
        "exported_at": datetime.utcnow().isoformat(),
        "version": "1.0",
        **data,
    }

    with open(path, "w") as f:
        json.dump(export_data, f, indent=2, default=str)

    return str(path)


def import_state(input_path: str) -> Dict[str, Any]:
    """Import simulation state from JSON file."""
    path = Path(input_path)
    if not path.exists():
        raise FileNotFoundError(f"Import file not found: {input_path}")

    with open(path, "r") as f:
        data = json.load(f)

    # Validate version
    version = data.get("version", "unknown")
    if version != "1.0":
        raise ValueError(f"Incompatible import version: {version}")

    return data


def export_full_database(db: Session, sim_state: Dict[str, Any]) -> Dict[str, Any]:
    """
    Export all data from the database into a dictionary.

    Args:
        db: Database session
        sim_state: Current simulation state (current_day, running, etc.)

    Returns:
        Dictionary containing all database data
    """
    return {
        "simulation_state": sim_state,
        "printer_models": [to_dict(m) for m in db.query(PrinterModel).all()],
        "bom_items": [to_dict(m) for m in db.query(BOMItem).all()],
        "material_types": [to_dict(m) for m in db.query(MaterialType).all()],
        "suppliers": [to_dict(m) for m in db.query(Supplier).all()],
        "supplier_products": [to_dict(m) for m in db.query(SupplierProduct).all()],
        "inventory_logs": [to_dict(m) for m in db.query(InventoryLog).all()],
        "manufacturing_orders": [to_dict(m) for m in db.query(ManufacturingOrder).all()],
        "purchase_orders": [to_dict(m) for m in db.query(PurchaseOrder).all()],
        "event_logs": [to_dict(m) for m in db.query(EventLog).all()],
    }


def import_full_database(db: Session, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Import all data into the database from a dictionary.
    WARNING: This deletes all existing data.

    Args:
        db: Database session
        data: Dictionary containing database data

    Returns:
        New simulation state
    """
    # Delete all data in correct order to respect foreign keys
    db.query(EventLog).delete()
    db.query(ManufacturingOrder).delete()
    db.query(PurchaseOrder).all()
    db.query(PurchaseOrder).delete()
    db.query(InventoryLog).delete()
    db.query(SupplierProduct).delete()
    db.query(Supplier).delete()
    db.query(BOMItem).delete()
    db.query(PrinterModel).delete()
    db.query(MaterialType).delete()

    # Helper to bulk insert
    def bulk_insert(model_class: Type, items: List[Dict[str, Any]]):
        if not items:
            return
        for item in items:
            # Parse datetime strings back to datetime objects
            for key, value in item.items():
                if isinstance(value, str) and (key.endswith("_at") or "day" in key or "arrival" in key):
                    try:
                        # Only convert if it looks like an ISO format datetime
                        if "T" in value:
                            item[key] = datetime.fromisoformat(value)
                    except (ValueError, TypeError):
                        pass

            db.add(model_class(**item))

    # Import data in correct order
    bulk_insert(MaterialType, data.get("material_types", []))
    bulk_insert(PrinterModel, data.get("printer_models", []))
    bulk_insert(BOMItem, data.get("bom_items", []))
    bulk_insert(Supplier, data.get("suppliers", []))
    bulk_insert(SupplierProduct, data.get("supplier_products", []))
    bulk_insert(InventoryLog, data.get("inventory_logs", []))
    bulk_insert(PurchaseOrder, data.get("purchase_orders", []))
    bulk_insert(ManufacturingOrder, data.get("manufacturing_orders", []))
    bulk_insert(EventLog, data.get("event_logs", []))

    db.commit()

    return data.get("simulation_state", {"current_day": 1, "running": False})
