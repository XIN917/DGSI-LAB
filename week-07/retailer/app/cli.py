import typer
from typing import Optional
from pathlib import Path
import json
import sys
import os
import uvicorn

# Add the project root to sys.path to allow running without PYTHONPATH=.
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.retailer_service import RetailerService
from app.core.database import init_db, SessionLocal

app = typer.Typer(help="Retailer Management CLI - Manage customer demand, inventory, and simulation time.")
day_app = typer.Typer(help="Control the simulated passage of time.")
app.add_typer(day_app, name="day")


def get_service():
    return RetailerService(SessionLocal())


@app.command()
def init() -> None:
    """Initialize the retailer database."""
    try:
        init_db(reset_day=True)
        typer.echo("✅ Database initialized successfully")
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)


@app.command()
def catalog() -> None:
    """List available finished printer SKUs and retail prices."""
    try:
        service = get_service()
        catalog_items = service.get_catalog()
        typer.echo("Available Products:")
        for item in catalog_items:
            typer.echo(
                f"  {item.sku}: {item.name} - "
                f"Retail: ${item.retail_price} | "
                f"Wholesale: ${item.wholesale_price}"
            )
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)


@app.command()
def inventory() -> None:
    """Display current finished goods inventory."""
    try:
        service = get_service()
        items = service.list_inventory()
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


@app.command("customer-orders")
def customer_orders_command(
    action: str = typer.Argument(..., help="Action: create or list"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    customer_name: Optional[str] = typer.Option(None, help="Customer name"),
) -> None:
    """Manage customer orders."""
    service = get_service()
    if action == "list":
        try:
            orders = service.list_customer_orders()
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
            order = service.create_customer_order(
                sku, quantity, customer_name
            )
            typer.echo(f"Created customer order ID {order.id} for {quantity} x {sku}")
        except Exception as e:
            typer.echo(f"Error: {e}", err=True)
    else:
        typer.echo("Invalid action. Use 'create' or 'list'", err=True)


@app.command("purchase-orders")
def purchase_orders_command(
    action: str = typer.Argument(..., help="Action: create, list, or sync"),
    sku: Optional[str] = typer.Option(None, help="SKU for create action"),
    quantity: Optional[int] = typer.Option(None, help="Quantity for create action"),
    po_id: Optional[int] = typer.Option(None, help="PO ID for sync action"),
) -> None:
    """Manage purchase orders with manufacturer."""
    service = get_service()
    if action == "list":
        try:
            orders = service.list_purchase_orders()

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
            result = service.create_purchase_order(sku, quantity)
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
            result = service.sync_purchase_order(po_id)
            typer.echo(f"✅ PO {po_id} synced. Status: {result['status']}")
        except Exception as e:
            typer.echo(f"❌ Error: {e}")

    else:
        typer.echo("Invalid action. Use 'create', 'list', or 'sync'")


@day_app.command("current")
def day_current_cmd() -> None:
    """Show current simulated day."""
    try:
        service = get_service()
        current_day = service.get_current_day()
        typer.echo(f"Current simulated day: {current_day}")
    except Exception as e:
        typer.echo(f"Error: {e}")


@day_app.command("advance")
def day_advance_cmd() -> None:
    """Advance the simulation by one day."""
    try:
        service = get_service()
        result = service.advance_day()
        typer.echo(result["message"])
    except Exception as e:
        typer.echo(f"Error: {e}")


@app.command()
def pricing(
    sku: str = typer.Argument(..., help="SKU to update"),
    price: float = typer.Argument(..., help="New retail price"),
) -> None:
    """Set retail price for a SKU (must be at least 15% above wholesale)."""
    try:
        service = get_service()
        item = service.set_retail_price(sku, price)
        typer.echo(f"✅ Updated {sku} price to ${item.retail_price}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")


@app.command()
def fulfill(order_id: int) -> None:
    """Manually fulfill a customer order from stock."""
    try:
        service = get_service()
        result = service.fulfill_customer_order(order_id)
        typer.echo(f"✅ Order {order_id} fulfilled. Status: {result['status']}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")


@app.command()
def backorder(order_id: int) -> None:
    """Manually mark a customer order as backordered."""
    try:
        service = get_service()
        result = service.backorder_customer_order(order_id)
        typer.echo(f"✅ Order {order_id} backordered. Status: {result['status']}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")


@app.command()
def export(file: Path = typer.Argument(..., help="Path to save the JSON export")) -> None:
    """Export the complete retailer state to a JSON file."""
    try:
        from app.core.database import SessionLocal
        from app.utils.json_export import export_full_state
        with SessionLocal() as session:
            state = export_full_state(session)
            file.write_text(json.dumps(state, indent=2))
            typer.echo(f"✅ State exported to {file}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")


@app.command("import")
def import_command(file: Path = typer.Argument(..., help="Path to the JSON file to import")) -> None:
    """Import a retailer state from a JSON file (OVERWRITES CURRENT DATA)."""
    try:
        if not file.exists():
            typer.echo(f"❌ Error: File {file} not found")
            return
        
        data = json.loads(file.read_text())
        from app.core.database import SessionLocal
        from app.utils.json_export import import_full_state
        with SessionLocal() as session:
            import_full_state(session, data)
            typer.echo(f"✅ State imported from {file}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")


@app.command()
def serve(port: int = typer.Option(8003, "--port", "-p", help="Port to run the Retailer REST API on.")):
    """Start the Retailer REST API server."""
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)


if __name__ == "__main__":
    app()
