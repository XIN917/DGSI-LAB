import json
import typer
from pathlib import Path
from typing import List, Dict, Optional
from sqlalchemy.orm import Session
from decimal import Decimal
from datetime import datetime

from app.core.config import get_settings
from app.models.purchase_order import Supplier, PurchaseOrder
from app.services.provider_client import ProviderClient

class ExternalSupplierService:
    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()

    def get_configured_providers(self) -> List[Dict]:
        path = Path(self.settings.PROVIDERS_JSON_PATH)
        if not path.exists():
            return []
        with open(path, "r") as f:
            return json.load(f)

    def sync_providers(self):
        providers = self.get_configured_providers()
        for p in providers:
            supplier = self.db.query(Supplier).filter(Supplier.name == p["name"]).first()
            if not supplier:
                supplier = Supplier(
                    name=p["name"],
                    lead_time_days=0, # Will be updated or fetched from API if needed
                    is_external=True,
                    api_url=p["url"]
                )
                self.db.add(supplier)
            else:
                supplier.is_external = True
                supplier.api_url = p["url"]
        self.db.commit()

    def list_suppliers(self) -> List[Supplier]:
        return self.db.query(Supplier).filter(Supplier.is_external == True).all()

    def get_catalog(self, supplier_name: str) -> List[Dict]:
        supplier = self.db.query(Supplier).filter(Supplier.name == supplier_name, Supplier.is_external == True).first()
        if not supplier:
            raise ValueError(f"External supplier {supplier_name} not found")
        
        client = ProviderClient(supplier.api_url)
        return client.get_catalog()

    def place_order(self, supplier_name: str, product_ref: str | int, quantity: int) -> PurchaseOrder:
        supplier = self.db.query(Supplier).filter(Supplier.name == supplier_name, Supplier.is_external == True).first()
        if not supplier:
            raise ValueError(f"External supplier {supplier_name} not found")

        client = ProviderClient(supplier.api_url)
        # We need the product name from the catalog to match our local material name
        catalog = client.get_catalog()
        
        product = None
        if isinstance(product_ref, int):
            product = next((p for p in catalog if p["id"] == product_ref), None)
        else:
            # Flexible matching by name (case-insensitive partial match)
            product = next((p for p in catalog if product_ref.lower() in p["name"].lower()), None)
            
        if not product:
            raise ValueError(f"Product '{product_ref}' not found in supplier catalog")

        product_id = product["id"]
        # Place order on Provider API
        # The buyer name can be something like "Manufacturer App" or from config
        remote_order = client.place_order(buyer="Manufacturer App", product_id=product_id, quantity=quantity)

        # Map Provider status to local status
        # Provider: PENDING, CONFIRMED, InProgress, SHIPPED, DELIVERED
        # Local: pending, partial, delivered, cancelled
        local_status = "pending"
        if remote_order["status"] == "DELIVERED":
            local_status = "delivered"

        # Create local PO
        from app.services.simulation_engine import SimulationEngine
        from datetime import timedelta
        engine = SimulationEngine(self.db)
        current_dt = datetime.combine(engine.current_date, datetime.min.time())
        
        po = PurchaseOrder(
            supplier_id=supplier.id,
            product_name=product["name"].lower().replace(" ", "_"), # Simplified mapping for now
            quantity_ordered=Decimal(str(quantity)),
            quantity_delivered=Decimal("0"),
            unit_cost=Decimal(str(remote_order["unit_price"])),
            order_date=current_dt,
            expected_delivery=current_dt + timedelta(days=product["lead_time_days"]),
            status=local_status,
            external_id=remote_order["id"]
        )

        self.db.add(po)
        self.db.commit()
        self.db.refresh(po)
        return po

    def poll_orders(self):
        pending_orders = self.db.query(PurchaseOrder).join(Supplier).filter(
            Supplier.is_external == True,
            PurchaseOrder.status.in_(["pending", "partial", "shipped"]) # Added "shipped" to match Provider
        ).all()

        for po in pending_orders:
            supplier = self.db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
            client = ProviderClient(supplier.api_url)
            try:
                remote_order = client.get_order_status(po.external_id)
                if remote_order["status"] == "DELIVERED" and po.status != "delivered":
                    # Order arrived!
                    self._receive_order(po)
                elif remote_order["status"] == "SHIPPED":
                    po.status = "shipped"
                # Update other fields if necessary
            except Exception as e:
                print(f"Error polling order {po.id}: {e}")
        
        self.db.commit()

    def _receive_order(self, po: PurchaseOrder):
        from app.services.inventory_service import InventoryService
        from app.services.simulation_engine import SimulationEngine
        
        engine = SimulationEngine(self.db)
        inv_svc = InventoryService(self.db)
        
        # Match product name to local inventory
        material_name = po.product_name
        # Improved mapping for the scenario
        if "pcb" in material_name.lower():
            material_name = "pcb_control"
        elif "extruder" in material_name.lower():
            material_name = "extruder_kit"
        elif "motor" in material_name.lower():
            material_name = "stepper_motor"
        
        inventory = inv_svc.get_by_product(material_name)
        if not inventory:
            # Fallback if not found, but should exist from seed
            typer.echo(f"Warning: Material {material_name} not found in inventory.")
            return

        current_qty = inventory.quantity
        inv_svc.adjust(material_name, current_qty + po.quantity_ordered)
        
        po.quantity_delivered = po.quantity_ordered
        po.status = "delivered"
        po.actual_delivery = datetime.combine(engine.current_date, datetime.min.time())
        
        # Log event
        from app.models.event import EventLog
        event = EventLog(
            event_type="external_po_arrived",
            event_date=datetime.combine(engine.current_date, datetime.min.time()),
            details=f"Received {po.quantity_ordered} {material_name} from {po.supplier_id}"
        )
        self.db.add(event)
