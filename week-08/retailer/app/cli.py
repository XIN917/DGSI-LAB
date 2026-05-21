import typer
from typing import Optional
import asyncio
import sys
import os
import uvicorn

# Add the project root to sys.path to allow running without PYTHONPATH=.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.retailer_service import RetailerService
from app.core.database import init_db

app = typer.Typer(help="Retailer Management CLI - Manage customer demand, inventory, and simulation time.")
day_app = typer.Typer(help="Control the simulated passage of time.")
customers_app = typer.Typer(help="Manage customer orders.")
purchase_app = typer.Typer(help="Manage manufacturer purchase orders.")
price_app = typer.Typer(help="Manage retail prices.")
app.add_typer(day_app, name="day")
app.add_typer(customers_app, name="customers")
app.add_typer(purchase_app, name="purchase")
app.add_typer(price_app, name="price")

service = RetailerService()


async def ensure_db() -> None:
    await init_db()


@app.command()
def init() -> None:
    """Initialize the retailer database."""
    try:
        asyncio.run(init_db())
        typer.echo("✅ Database initialized successfully")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)


@app.command()
def catalog() -> None:
    """List available finished printer SKUs and retail prices."""
    async def _catalog():
        try:
            await ensure_db()
            catalog_items = await service.get_catalog()
            typer.echo("Available Products:")
            for item in catalog_items:
                typer.echo(
                    f"  {item.sku}: {item.name} - "
                    f"Retail: ${item.retail_price} | "
                    f"Wholesale: ${item.wholesale_price}"
                )
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)

    asyncio.run(_catalog())


@app.command()
def inventory() -> None:
    """Display current finished goods inventory."""
    async def _inventory():
        try:
            await ensure_db()
            items = await service.list_inventory()
            if not items:
                typer.echo("No inventory found.")
                return

            typer.echo("Inventory:")
            for item in items:
                typer.echo(
                    f"  {item.sku}: on hand {item.quantity_on_hand}, "
                    f"reserved {item.quantity_reserved}, retail ${item.retail_price}"
                )
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)

    asyncio.run(_inventory())


@app.command("stock")
def stock_alias() -> None:
    """Alias for inventory."""
    inventory()


@app.command("customer-orders")
def customer_orders_command(
    action: str = typer.Argument(..., help="Action: create or list"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    customer_name: Optional[str] = typer.Option(None, help="Customer name"),
) -> None:
    """Manage customer orders."""
    async def _customer_orders():
        if action == "list":
            try:
                await ensure_db()
                orders = await service.list_customer_orders()
                if not orders:
                    typer.echo("No customer orders found.")
                    return

                typer.echo("Customer Orders:")
                for order in orders:
                    status = getattr(order.status, "value", order.status)
                    typer.echo(
                        f"  ID {order.id}: {order.quantity} x {order.sku} - "
                        f"Status: {status} - ${order.retail_price}"
                    )
            except Exception as e:
                typer.echo(f"Error: {e}", err=True)

        elif action == "create":
            if not sku or not quantity:
                typer.echo("Error: sku and quantity required for create action", err=True)
                return

            try:
                await ensure_db()
                order = await service.create_customer_order(
                    sku, quantity, customer_name
                )
                typer.echo(f"Created customer order ID {order.id} for {quantity} x {sku}")
            except Exception as e:
                typer.echo(f"Error: {e}", err=True)
        else:
            typer.echo("Invalid action. Use 'create' or 'list'", err=True)

    asyncio.run(_customer_orders())


@customers_app.command("orders")
def customers_orders_alias() -> None:
    """Alias for customer order listing."""
    customer_orders_command("list")


@customers_app.command("order")
def customers_order_alias(
    action: str = typer.Argument("list", help="Action: create or list"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    customer_name: Optional[str] = typer.Option(None, help="Customer name"),
) -> None:
    """Alias for customer order management."""
    customer_orders_command(action, sku=sku, quantity=quantity, customer_name=customer_name)


@app.command("purchase-orders")
def purchase_orders_command(
    action: str = typer.Argument(..., help="Action: create, list, or sync"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    po_id: Optional[int] = typer.Option(None, help="PO ID for sync action"),
) -> None:
    """Manage purchase orders with manufacturer."""
    async def _purchase_orders():
        if action == "list":
            try:
                await ensure_db()
                orders = await service.list_purchase_orders()

                if not orders:
                    typer.echo("No purchase orders found.")
                    return

                typer.echo("Purchase Orders:")
                for order in orders:
                    typer.echo(
                        f"  ID {order.id}: {order.quantity} x {order.sku} - "
                        f"Manufacturer ID: {order.manufacturer_po_id} - Status: {order.status}"
                    )
            except Exception as e:
                typer.echo(f"Error: {e}")

        elif action == "create":
            if not sku or not quantity:
                typer.echo("Error: sku and quantity required for create action")
                return

            try:
                await ensure_db()
                result = await service.create_purchase_order(sku, quantity)
                typer.echo(
                    "Created purchase order "
                    f"ID {result['id']} with manufacturer order "
                    f"{result['manufacturer_po_id']}: {quantity} x {sku} "
                    f"({result['status']})"
                )
            except Exception as e:
                typer.echo(f"Error: {e}")

        elif action == "sync":
            if not po_id:
                typer.echo("Error: po_id required for sync action")
                return

            try:
                await ensure_db()
                result = await service.sync_purchase_order(po_id)
                typer.echo(f"✅ PO {po_id} synced. Status: {result['status']}")
            except Exception as e:
                typer.echo(f"❌ Error: {e}")

        else:
            typer.echo("Invalid action. Use 'create', 'list', or 'sync'")

    asyncio.run(_purchase_orders())


@purchase_app.command("list")
def purchase_list_alias() -> None:
    """Alias for purchase order listing."""
    purchase_orders_command("list")


@purchase_app.command("create")
def purchase_create_alias(
    sku: str = typer.Option(..., help="SKU to order"),
    quantity: int = typer.Option(..., help="Quantity to order"),
) -> None:
    """Alias for creating a manufacturer purchase order."""
    purchase_orders_command("create", sku=sku, quantity=quantity)


@day_app.command("current")
def day_current_cmd() -> None:
    """Show current simulated day."""
    async def _day_current():
        try:
            await ensure_db()
            current_day = await service.get_current_day()
            typer.echo(f"Current simulated day: {current_day}")
        except Exception as e:
            typer.echo(f"Error: {e}")

    asyncio.run(_day_current())


@day_app.command("advance")
def day_advance_cmd() -> None:
    """Advance the simulation by one day."""
    async def _day_advance():
        try:
            await ensure_db()
            result = await service.advance_day()
            typer.echo(result["message"])
        except Exception as e:
            typer.echo(f"Error: {e}")

    asyncio.run(_day_advance())


@app.command()
def pricing(
    sku: str = typer.Argument(..., help="SKU to update"),
    price: float = typer.Argument(..., help="New retail price"),
) -> None:
    """Set retail price for a SKU (must be at least 15% above wholesale)."""
    async def _pricing():
        try:
            await ensure_db()
            item = await service.set_retail_price(sku, price)
            typer.echo(f"✅ Updated {sku} price to ${item.retail_price}")
        except Exception as e:
            typer.echo(f"❌ Error: {e}")

    asyncio.run(_pricing())


@price_app.command("set")
def price_set_alias(
    sku: str = typer.Argument(..., help="SKU to update"),
    price: float = typer.Argument(..., help="New retail price"),
) -> None:
    """Alias for pricing."""
    pricing(sku, price)


@price_app.command("list")
def price_list_alias() -> None:
    """List retail prices."""
    catalog()


@app.command("fulfill")
def fulfill_alias() -> None:
    """Process backorders with current stock."""
    async def _fulfill():
        await ensure_db()
        await service.process_backorders()
        typer.echo("Processed backorders.")

    asyncio.run(_fulfill())


@app.command("backorder")
def backorder_alias() -> None:
    """List backordered customer orders."""
    async def _backorders():
        await ensure_db()
        orders = await service.list_customer_orders()
        for order in orders:
            if str(order.status) == "backordered":
                typer.echo(f"ID {order.id}: {order.quantity} x {order.sku} - Status: {order.status}")

    asyncio.run(_backorders())


@app.command()
def serve(port: int = typer.Option(8003, "--port", "-p", help="Port to run the Retailer REST API on.")):
    """Start the Retailer REST API server."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    app()
