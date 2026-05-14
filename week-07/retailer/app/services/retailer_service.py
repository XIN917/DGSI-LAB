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

    async def get_catalog(self) -> List[ProductCatalogItem]:
        # For now, return hardcoded catalog - in real implementation would sync with manufacturer
        return [
            ProductCatalogItem(sku="P3D-Classic", name="Classic 3D Printer", retail_price=1500.0),
            ProductCatalogItem(sku="P3D-Pro", name="Professional 3D Printer", retail_price=2500.0),
        ]

    async def advance_day(self) -> dict[str, str]:
        current_day = await self.get_current_day()
        new_day = current_day + 1
        await self.set_current_day(new_day)

        # Process backorders and deliveries
        await self.process_backorders()
        await self.check_purchase_order_deliveries()

        await self.log_event(new_day, "day_advanced", "simulation", None, f"Advanced to day {new_day}")

        return {"message": f"Advanced to day {new_day}"}

    async def process_backorders(self) -> None:
        # Auto-fulfill backorders when inventory becomes available
        pass  # Implementation for backorder fulfillment

    async def check_purchase_order_deliveries(self) -> None:
        # Check with manufacturer for PO status updates
        pass  # Implementation for PO delivery checking

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
