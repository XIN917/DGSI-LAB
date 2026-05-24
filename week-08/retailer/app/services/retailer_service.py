from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, update

from app.models.database import (
    CustomerOrderDB,
    InventoryItemDB,
    PurchaseOrderDB,
    EventLogDB,
    SimStateDB,
    OrderStatus,
)
from app.models.order import CustomerOrder, PurchaseOrder
from app.models.product import InventoryItem, ProductCatalogItem
from app.services.manufacturer_client import ManufacturerClient


class RetailerService:
    def __init__(self, db: Session):
        self.manufacturer_client = ManufacturerClient()
        self.db = db

    def get_current_day(self) -> int:
        result = self.db.execute(
            select(SimStateDB.value).where(SimStateDB.key == "current_day")
        )
        row = result.first()
        return int(row.value) if row else 0

    def set_current_day(self, day: int) -> None:
        result = self.db.execute(
            select(SimStateDB).where(SimStateDB.key == "current_day")
        )
        row = result.first()
        if row:
            self.db.execute(
                update(SimStateDB)
                .where(SimStateDB.key == "current_day")
                .values(value=str(day))
            )
        else:
            self.db.add(SimStateDB(key="current_day", value=str(day)))
        self.db.commit()

    def list_customer_orders(self) -> List[CustomerOrder]:
        result = self.db.execute(select(CustomerOrderDB))
        orders = []
        for row in result.scalars():
            orders.append(
                CustomerOrder(
                    id=row.id,
                    sku=row.sku,
                    quantity=row.quantity,
                    retail_price=row.retail_price,
                    status=row.status,
                    created_day=row.created_day,
                    fulfilled_day=row.fulfilled_day,
                    customer_name=row.customer_name,
                    notes=row.notes,
                )
            )
        return orders

    def list_purchase_orders(self) -> List[PurchaseOrder]:
        result = self.db.execute(select(PurchaseOrderDB).order_by(PurchaseOrderDB.id))
        return [
            PurchaseOrder(
                id=row.id,
                manufacturer_po_id=row.manufacturer_po_id,
                sku=row.sku,
                quantity=row.quantity,
                wholesale_unit_price=row.wholesale_unit_price,
                status=row.status,
                placed_day=row.placed_day,
                expected_delivery_day=row.expected_delivery_day,
                received_day=row.received_day,
            )
            for row in result.scalars()
        ]

    def create_purchase_order(self, sku: str, quantity: int) -> dict:
        from app.core.config import settings
        current_day = self.get_current_day()
        manufacturer_response = self.manufacturer_client.place_order(
            sku, quantity, retailer_name=settings.name
        )

        po = PurchaseOrderDB(
            manufacturer_po_id=manufacturer_response.get("id"),
            sku=sku,
            quantity=quantity,
            wholesale_unit_price=manufacturer_response.get("unit_price", 0.0),
            retail_unit_price=0.0,
            status=manufacturer_response.get("status", "pending"),
            placed_day=current_day,
            expected_delivery_day=manufacturer_response.get("expected_delivery_day"),
        )
        self.db.add(po)
        self.db.commit()
        self.db.refresh(po)

        # Immediate inventory update if already delivered (auto-fulfillment)
        if po.status == "delivered":
            self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
            po.received_day = current_day
            self.db.add(po)
            self.db.commit()

        self.log_event(
            current_day,
            "purchase_order_created",
            "purchase_order",
            po.id,
            f"Created manufacturer order #{po.manufacturer_po_id} for {quantity} x {sku}",
        )

        return {
            "id": po.id,
            "manufacturer_po_id": po.manufacturer_po_id,
            "sku": po.sku,
            "quantity": po.quantity,
            "status": po.status,
            "message": "Purchase order created successfully",
            "manufacturer_response": manufacturer_response,
        }

    def create_customer_order(
        self, sku: str, quantity: int, customer_name: str = None, notes: str = None
    ) -> CustomerOrder:
        current_day = self.get_current_day()

        # Check inventory and fulfill or backorder
        inventory = self.get_inventory_item(sku)
        if inventory and inventory.quantity_on_hand >= quantity:
            # Fulfill immediately
            status = OrderStatus.fulfilled
            fulfilled_day = current_day
            self.reserve_inventory(sku, quantity)
        else:
            # Backorder
            status = OrderStatus.backordered
            fulfilled_day = None

        new_order = CustomerOrderDB(
            sku=sku,
            quantity=quantity,
            retail_price=inventory.retail_price if inventory else 0.0,
            status=status,
            created_day=current_day,
            fulfilled_day=fulfilled_day,
            customer_name=customer_name,
            notes=notes,
        )
        self.db.add(new_order)
        self.db.commit()
        self.db.refresh(new_order)

        # Log event
        self.log_event(
            current_day,
            "customer_order_created",
            "customer_order",
            new_order.id,
            f"Created order for {quantity} x {sku}, status: {status}",
        )

        return CustomerOrder(
            id=new_order.id,
            sku=new_order.sku,
            quantity=new_order.quantity,
            retail_price=new_order.retail_price,
            status=new_order.status,
            created_day=new_order.created_day,
            fulfilled_day=new_order.fulfilled_day,
            customer_name=new_order.customer_name,
            notes=new_order.notes,
        )

    def fulfill_customer_order(self, order_id: int) -> dict:
        result = self.db.execute(
            select(CustomerOrderDB).where(CustomerOrderDB.id == order_id)
        )
        order = result.scalars().first()
        if not order:
            raise ValueError(f"Order {order_id} not found")
        
        if order.status == OrderStatus.fulfilled:
            return {"id": order.id, "status": order.status, "message": "Already fulfilled"}

        inventory = self.get_inventory_item(order.sku)
        if not inventory or inventory.quantity_on_hand < order.quantity:
            raise ValueError(f"Insufficient stock to fulfill order {order_id}")

        current_day = self.get_current_day()
        self.reserve_inventory(order.sku, order.quantity)
        
        order.status = OrderStatus.fulfilled
        order.fulfilled_day = current_day
        self.db.commit()
        
        self.log_event(
            current_day,
            "customer_order_fulfilled_manual",
            "customer_order",
            order.id,
            f"Manually fulfilled order {order_id} for {order.quantity} x {order.sku}",
        )
        return {"id": order.id, "status": order.status}

    def backorder_customer_order(self, order_id: int) -> dict:
        result = self.db.execute(
            select(CustomerOrderDB).where(CustomerOrderDB.id == order_id)
        )
        order = result.scalars().first()
        if not order:
            raise ValueError(f"Order {order_id} not found")

        if order.status == OrderStatus.backordered:
            return {"id": order.id, "status": order.status, "message": "Already backordered"}

        order.status = OrderStatus.backordered
        order.fulfilled_day = None
        self.db.commit()
        
        current_day = self.get_current_day()
        self.log_event(
            current_day,
            "customer_order_backordered_manual",
            "customer_order",
            order.id,
            f"Manually backordered order {order_id}",
        )
        return {"id": order.id, "status": order.status}

    def get_inventory_item(self, sku: str) -> Optional[InventoryItem]:
        result = self.db.execute(
            select(InventoryItemDB).where(InventoryItemDB.sku == sku)
        )
        row = result.first()
        if row:
            item = row[0]
            return InventoryItem(
                sku=item.sku,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                retail_price=item.retail_price,
                last_cost=item.last_cost,
            )
        return None

    def list_inventory(self) -> List[InventoryItem]:
        result = self.db.execute(select(InventoryItemDB).order_by(InventoryItemDB.sku))
        return [
            InventoryItem(
                sku=item.sku,
                quantity_on_hand=item.quantity_on_hand,
                quantity_reserved=item.quantity_reserved,
                retail_price=item.retail_price,
                last_cost=item.last_cost,
            )
            for item in result.scalars()
        ]

    def reserve_inventory(self, sku: str, quantity: int) -> None:
        self.db.execute(
            update(InventoryItemDB)
            .where(InventoryItemDB.sku == sku)
            .values(
                quantity_on_hand=InventoryItemDB.quantity_on_hand - quantity,
                quantity_reserved=InventoryItemDB.quantity_reserved + quantity,
            )
        )
        self.db.commit()

    def set_retail_price(self, sku: str, price: float) -> InventoryItem:
        # Business Rule: Retail prices must be at least 15% above the Manufacturer wholesale price
        catalog = self.get_catalog()
        wholesale_price = 0.0
        for item in catalog:
            if item.sku == sku:
                wholesale_price = item.wholesale_price or 0.0
                break
        
        if wholesale_price > 0 and price < wholesale_price * 1.15:
            raise ValueError(f"Price ${price} is below the minimum 15% markup over wholesale (${wholesale_price})")

        result = self.db.execute(
            select(InventoryItemDB).where(InventoryItemDB.sku == sku)
        )
        item = result.scalars().first()
        if not item:
            # If it doesn't exist in inventory, we create it (or it might be a new product from manufacturer)
            item = InventoryItemDB(sku=sku, quantity_on_hand=0, retail_price=price)
            self.db.add(item)
        else:
            item.retail_price = price
        
        self.db.commit()
        
        current_day = self.get_current_day()
        self.log_event(
            current_day,
            "price_updated",
            "inventory",
            item.id,
            f"Updated price for {sku} to ${price}",
        )
        
        return InventoryItem(
            sku=item.sku,
            quantity_on_hand=item.quantity_on_hand,
            quantity_reserved=item.quantity_reserved,
            retail_price=item.retail_price,
            last_cost=item.last_cost,
        )

    def get_catalog(self) -> List[ProductCatalogItem]:
        try:
            manufacturer_catalog = self.manufacturer_client.get_catalog()
            # The manufacturer response structure might vary, but let's assume it's a list or has a 'products' key
            products = manufacturer_catalog if isinstance(manufacturer_catalog, list) else manufacturer_catalog.get("products", [])
            
            catalog = []
            for p in products:
                # Map manufacturer product to our catalog item
                # Manufacturer might call it 'model' or 'sku'
                sku = p.get("sku") or p.get("model") or p.get("product_model")
                name = p.get("name") or p.get("description") or sku
                wholesale_price = p.get("unit_price") or p.get("price") or 0.0
                
                # Get current retail price from our inventory if it exists
                inventory = self.get_inventory_item(sku)
                retail_price = inventory.retail_price if inventory else wholesale_price * 1.30
                
                catalog.append(ProductCatalogItem(
                    sku=sku,
                    name=name,
                    retail_price=retail_price,
                    wholesale_price=wholesale_price
                ))
            return catalog
        except Exception as e:
            # Fallback to hardcoded catalog if manufacturer is unreachable
            return [
                ProductCatalogItem(sku="P3D-Classic", name="Classic 3D Printer", retail_price=1500.0, wholesale_price=1200.0),
                ProductCatalogItem(sku="P3D-Pro", name="Professional 3D Printer", retail_price=2500.0, wholesale_price=2000.0),
            ]

    def advance_day(self) -> dict[str, str]:
        current_day = self.get_current_day()
        new_day = current_day + 1
        self.set_current_day(new_day)

        # 1. Check for deliveries first to increase stock
        self.check_purchase_order_deliveries()

        # 2. Process backorders with new stock
        self.process_backorders()

        # 3. Snapshot metrics
        self._snapshot_metrics(new_day)

        self.log_event(new_day, "day_advanced", "simulation", None, f"Advanced to day {new_day}")

        return {"message": f"Advanced to day {new_day}"}

    def _snapshot_metrics(self, sim_day: int) -> None:
        from app.models.metrics import RetailerMetrics
        from app.models.database import InventoryItemDB, CustomerOrderDB
        items = self.db.execute(select(InventoryItemDB)).scalars().all()
        for item in items:
            placed = self.db.execute(
                select(CustomerOrderDB).where(
                    CustomerOrderDB.sku == item.sku,
                    CustomerOrderDB.created_day == sim_day
                )
            ).scalars().all()
            fulfilled = [o for o in placed if o.status == OrderStatus.fulfilled]
            backordered = [o for o in placed if o.status == OrderStatus.backordered]
            self.db.add(RetailerMetrics(
                sim_day=sim_day,
                sku=item.sku,
                stock_quantity=item.quantity_on_hand,
                retail_price=item.retail_price,
                orders_placed=len(placed),
                orders_fulfilled=len(fulfilled),
                orders_backordered=len(backordered),
            ))
        self.db.commit()

    def process_backorders(self) -> None:
        # Get all backordered orders, oldest first
        result = self.db.execute(
            select(CustomerOrderDB)
            .where(CustomerOrderDB.status == OrderStatus.backordered)
            .order_by(CustomerOrderDB.created_day, CustomerOrderDB.id)
        )
        backorders = result.scalars().all()
        current_day = self.get_current_day()

        for order in backorders:
            inventory = self.get_inventory_item(order.sku)
            if inventory and inventory.quantity_on_hand >= order.quantity:
                # Fulfill it!
                self.reserve_inventory(order.sku, order.quantity)
                
                # Update order status
                order.status = OrderStatus.fulfilled
                order.fulfilled_day = current_day
                
                self.log_event(
                    current_day,
                    "customer_order_fulfilled",
                    "customer_order",
                    order.id,
                    f"Backorder fulfilled for {order.quantity} x {order.sku}",
                )
        
        self.db.commit()

    def check_purchase_order_deliveries(self) -> None:
        # Get all pending purchase orders
        result = self.db.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.status == "pending")
        )
        pending_pos = result.scalars().all()
        current_day = self.get_current_day()

        for po in pending_pos:
            try:
                # Sync status with manufacturer
                manufacturer_po = self.manufacturer_client.get_order(po.manufacturer_po_id)
                new_status = manufacturer_po.get("status")
                
                if new_status == "delivered" or (new_status == "shipped" and manufacturer_po.get("delivery_day", 999) <= current_day):
                    # Add to inventory
                    self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
                    
                    po.status = "delivered"
                    po.received_day = current_day
                    
                    self.log_event(
                        current_day,
                        "purchase_order_received",
                        "purchase_order",
                        po.id,
                        f"Received {po.quantity} x {po.sku} from manufacturer",
                    )
                else:
                    po.status = new_status
                    po.expected_delivery_day = manufacturer_po.get("expected_delivery_day")
                    
            except Exception as e:
                # Skip if manufacturer is down or PO not found
                continue
        
        self.db.commit()

    def receive_inventory(self, sku: str, quantity: int, cost: float) -> None:
        result = self.db.execute(
            select(InventoryItemDB).where(InventoryItemDB.sku == sku)
        )
        item = result.scalars().first()
        if item:
            item.quantity_on_hand += quantity
            item.last_cost = cost
        else:
            # Should normally exist if we are receiving it
            self.db.add(InventoryItemDB(
                sku=sku, 
                quantity_on_hand=quantity, 
                retail_price=cost * 1.30, 
                last_cost=cost
            ))
        self.db.commit()

    def sync_purchase_order(self, po_id: int) -> dict:
        result = self.db.execute(
            select(PurchaseOrderDB).where(PurchaseOrderDB.id == po_id)
        )
        po = result.scalars().first()
        if not po:
            raise ValueError(f"Purchase order {po_id} not found")

        if po.status == "delivered":
            return {"id": po.id, "status": po.status, "message": "Already delivered"}

        # Sync status with manufacturer
        try:
            manufacturer_po = self.manufacturer_client.get_order(po.manufacturer_po_id)
            new_status = manufacturer_po.get("status")
            current_day = self.get_current_day()

            if new_status == "delivered" or (new_status == "shipped" and manufacturer_po.get("delivery_day", 999) <= current_day):
                # Add to inventory
                self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
                
                po.status = "delivered"
                po.received_day = current_day
                
                self.log_event(
                    current_day,
                    "purchase_order_received",
                    "purchase_order",
                    po.id,
                    f"Received {po.quantity} x {po.sku} from manufacturer (manual sync)",
                )
            else:
                po.status = new_status
                po.expected_delivery_day = manufacturer_po.get("expected_delivery_day")
            
            self.db.commit()
            return {"id": po.id, "status": po.status, "manufacturer_response": manufacturer_po}
        except Exception as e:
            raise Exception(f"Failed to sync with manufacturer: {e}")

    def log_event(
        self, sim_day: int, event_type: str, entity_type: str, entity_id: Optional[int], details: str
    ) -> None:
        event = EventLogDB(
            sim_day=sim_day,
            event_type=event_type,
            entity_type=entity_type,
            entity_id=entity_id,
            details=details,
        )
        self.db.add(event)
        self.db.commit()
