import typer
from typing import Optional
import asyncio

from app.services.retailer_service import RetailerService
from app.core.database import init_db

app = typer.Typer()
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
    import asyncio

    async def _catalog():
        try:
            await ensure_db()
            catalog_items = await service.get_catalog()
            typer.echo("Available Products:")
            for item in catalog_items:
                typer.echo(f"  {item.sku}: {item.name} - ${item.retail_price}")
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


@app.command("customer-orders")
def customer_orders_command(
    action: str = typer.Argument(..., help="Action: create or list"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    customer_name: Optional[str] = typer.Option(None, help="Customer name"),
) -> None:
    """Manage customer orders."""
    import asyncio

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


@app.command("purchase-orders")
def purchase_orders_command(
    action: str = typer.Argument(..., help="Action: create, list, or sync"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    po_id: Optional[int] = typer.Option(None, help="PO ID for sync action"),
) -> None:
    """Manage purchase orders with manufacturer."""
    import asyncio

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
                typer.echo(f"Error: {e}", err=True)

        elif action == "create":
            if not sku or not quantity:
                typer.echo("Error: sku and quantity required for create action", err=True)
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
                typer.echo(f"Error: {e}", err=True)

        elif action == "sync":
            if not po_id:
                typer.echo("Error: po_id required for sync action", err=True)
                return

            typer.echo(f"Sync purchase order {po_id} - implementation pending")

        else:
            typer.echo("Invalid action. Use 'create', 'list', or 'sync'", err=True)

    asyncio.run(_purchase_orders())


@app.command()
def day_current() -> None:
    """Show current simulated day."""
    import asyncio

    async def _day_current():
        try:
            await ensure_db()
            current_day = await service.get_current_day()
            typer.echo(f"Current simulated day: {current_day}")
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)

    asyncio.run(_day_current())


@app.command()
def day_advance() -> None:
    """Advance the simulation by one day."""
    import asyncio

    async def _day_advance():
        try:
            await ensure_db()
            result = await service.advance_day()
            typer.echo(result["message"])
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)

    asyncio.run(_day_advance())


if __name__ == "__main__":
    app()
