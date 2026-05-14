from typing import Callable, List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.core.database import AsyncSessionLocal
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
    def __init__(self, session_local: Callable[[], AsyncSession] = AsyncSessionLocal):
        self.manufacturer_client = ManufacturerClient()
        self.session_local = session_local

    async def get_current_day(self) -> int:
        async with self.session_local() as session:
            result = await session.execute(
                select(SimStateDB.value).where(SimStateDB.key == "current_day")
            )
            row = result.first()
            return int(row.value) if row else 0

    async def set_current_day(self, day: int) -> None:
        async with self.session_local() as session:
            result = await session.execute(
                select(SimStateDB).where(SimStateDB.key == "current_day")
            )
            row = result.first()
            if row:
                await session.execute(
                    update(SimStateDB)
                    .where(SimStateDB.key == "current_day")
                    .values(value=str(day))
                )
            else:
                session.add(SimStateDB(key="current_day", value=str(day)))
            await session.commit()

    async def list_customer_orders(self) -> List[CustomerOrder]:
        async with self.session_local() as session:
            result = await session.execute(select(CustomerOrderDB))
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

    async def list_purchase_orders(self) -> List[PurchaseOrder]:
        async with self.session_local() as session:
            result = await session.execute(select(PurchaseOrderDB).order_by(PurchaseOrderDB.id))
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

    async def create_purchase_order(self, sku: str, quantity: int) -> dict:
        current_day = await self.get_current_day()
        manufacturer_response = await self.manufacturer_client.place_order(sku, quantity)

        async with self.session_local() as session:
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
            session.add(po)
            await session.commit()
            await session.refresh(po)

        # Immediate inventory update if already delivered (auto-fulfillment)
        if po.status == "delivered":
            await self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
            po.received_day = current_day
            async with self.session_local() as session:
                session.add(po)
                await session.merge(po)
                await session.commit()

        await self.log_event(
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

    async def create_customer_order(
        self, sku: str, quantity: int, customer_name: str = None, notes: str = None
    ) -> CustomerOrder:
        current_day = await self.get_current_day()

        # Check inventory and fulfill or backorder
        inventory = await self.get_inventory_item(sku)
        if inventory and inventory.quantity_on_hand >= quantity:
            # Fulfill immediately
            status = OrderStatus.fulfilled
            fulfilled_day = current_day
            await self.reserve_inventory(sku, quantity)
        else:
            # Backorder
            status = OrderStatus.backordered
            fulfilled_day = None

        async with self.session_local() as session:
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
            session.add(new_order)
            await session.commit()
            await session.refresh(new_order)

            # Log event
            await self.log_event(
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

    async def get_inventory_item(self, sku: str) -> Optional[InventoryItem]:
        async with self.session_local() as session:
            result = await session.execute(
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

    async def list_inventory(self) -> List[InventoryItem]:
        async with self.session_local() as session:
            result = await session.execute(select(InventoryItemDB).order_by(InventoryItemDB.sku))
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

    async def reserve_inventory(self, sku: str, quantity: int) -> None:
        async with self.session_local() as session:
            await session.execute(
                update(InventoryItemDB)
                .where(InventoryItemDB.sku == sku)
                .values(
                    quantity_on_hand=InventoryItemDB.quantity_on_hand - quantity,
                    quantity_reserved=InventoryItemDB.quantity_reserved + quantity,
                )
            )
            await session.commit()

    async def set_retail_price(self, sku: str, price: float) -> InventoryItem:
        # Business Rule: Retail prices must be at least 15% above the Manufacturer wholesale price
        catalog = await self.get_catalog()
        wholesale_price = 0.0
        for item in catalog:
            if item.sku == sku:
                wholesale_price = item.wholesale_price or 0.0
                break
        
        if wholesale_price > 0 and price < wholesale_price * 1.15:
            raise ValueError(f"Price ${price} is below the minimum 15% markup over wholesale (${wholesale_price})")

        async with self.session_local() as session:
            result = await session.execute(
                select(InventoryItemDB).where(InventoryItemDB.sku == sku)
            )
            item = result.scalars().first()
            if not item:
                # If it doesn't exist in inventory, we create it (or it might be a new product from manufacturer)
                item = InventoryItemDB(sku=sku, quantity_on_hand=0, retail_price=price)
                session.add(item)
            else:
                item.retail_price = price
            
            await session.commit()
            
            current_day = await self.get_current_day()
            await self.log_event(
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

    async def get_catalog(self) -> List[ProductCatalogItem]:
        try:
            manufacturer_catalog = await self.manufacturer_client.get_catalog()
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
                inventory = await self.get_inventory_item(sku)
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

    async def advance_day(self) -> dict[str, str]:
        current_day = await self.get_current_day()
        new_day = current_day + 1
        await self.set_current_day(new_day)

        # 1. Check for deliveries first to increase stock
        await self.check_purchase_order_deliveries()
        
        # 2. Process backorders with new stock
        await self.process_backorders()

        await self.log_event(new_day, "day_advanced", "simulation", None, f"Advanced to day {new_day}")

        return {"message": f"Advanced to day {new_day}"}

    async def process_backorders(self) -> None:
        async with self.session_local() as session:
            # Get all backordered orders, oldest first
            result = await session.execute(
                select(CustomerOrderDB)
                .where(CustomerOrderDB.status == OrderStatus.backordered)
                .order_by(CustomerOrderDB.created_day, CustomerOrderDB.id)
            )
            backorders = result.scalars().all()
            current_day = await self.get_current_day()

            for order in backorders:
                inventory = await self.get_inventory_item(order.sku)
                if inventory and inventory.quantity_on_hand >= order.quantity:
                    # Fulfill it!
                    await self.reserve_inventory(order.sku, order.quantity)
                    
                    # Update order status
                    order.status = OrderStatus.fulfilled
                    order.fulfilled_day = current_day
                    
                    await self.log_event(
                        current_day,
                        "customer_order_fulfilled",
                        "customer_order",
                        order.id,
                        f"Backorder fulfilled for {order.quantity} x {order.sku}",
                    )
            
            await session.commit()

    async def check_purchase_order_deliveries(self) -> None:
        async with self.session_local() as session:
            # Get all pending purchase orders
            result = await session.execute(
                select(PurchaseOrderDB).where(PurchaseOrderDB.status == "pending")
            )
            pending_pos = result.scalars().all()
            current_day = await self.get_current_day()

            for po in pending_pos:
                try:
                    # Sync status with manufacturer
                    manufacturer_po = await self.manufacturer_client.get_order(po.manufacturer_po_id)
                    new_status = manufacturer_po.get("status")
                    
                    if new_status == "delivered" or (new_status == "shipped" and manufacturer_po.get("delivery_day", 999) <= current_day):
                        # Add to inventory
                        await self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
                        
                        po.status = "delivered"
                        po.received_day = current_day
                        
                        await self.log_event(
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
            
            await session.commit()

    async def receive_inventory(self, sku: str, quantity: int, cost: float) -> None:
        async with self.session_local() as session:
            result = await session.execute(
                select(InventoryItemDB).where(InventoryItemDB.sku == sku)
            )
            item = result.scalars().first()
            if item:
                item.quantity_on_hand += quantity
                item.last_cost = cost
            else:
                # Should normally exist if we are receiving it
                session.add(InventoryItemDB(
                    sku=sku, 
                    quantity_on_hand=quantity, 
                    retail_price=cost * 1.30, 
                    last_cost=cost
                ))
            await session.commit()

    async def sync_purchase_order(self, po_id: int) -> dict:
        async with self.session_local() as session:
            result = await session.execute(
                select(PurchaseOrderDB).where(PurchaseOrderDB.id == po_id)
            )
            po = result.scalars().first()
            if not po:
                raise ValueError(f"Purchase order {po_id} not found")

            if po.status == "delivered":
                return {"id": po.id, "status": po.status, "message": "Already delivered"}

            # Sync status with manufacturer
            try:
                manufacturer_po = await self.manufacturer_client.get_order(po.manufacturer_po_id)
                new_status = manufacturer_po.get("status")
                current_day = await self.get_current_day()

                if new_status == "delivered" or (new_status == "shipped" and manufacturer_po.get("delivery_day", 999) <= current_day):
                    # Add to inventory
                    await self.receive_inventory(po.sku, po.quantity, po.wholesale_unit_price)
                    
                    po.status = "delivered"
                    po.received_day = current_day
                    
                    await self.log_event(
                        current_day,
                        "purchase_order_received",
                        "purchase_order",
                        po.id,
                        f"Received {po.quantity} x {po.sku} from manufacturer (manual sync)",
                    )
                else:
                    po.status = new_status
                    po.expected_delivery_day = manufacturer_po.get("expected_delivery_day")
                
                await session.commit()
                return {"id": po.id, "status": po.status, "manufacturer_response": manufacturer_po}
            except Exception as e:
                raise Exception(f"Failed to sync with manufacturer: {e}")

    async def log_event(
        self, sim_day: int, event_type: str, entity_type: str, entity_id: Optional[int], details: str
    ) -> None:
        async with self.session_local() as session:
            event = EventLogDB(
                sim_day=sim_day,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                details=details,
            )
            session.add(event)
            await session.commit()
