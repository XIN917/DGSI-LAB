"""Typer CLI for Provider app."""
import typer
from rich.console import Console
from rich.table import Table
from rich import print as rprint
from typing import Optional

app = typer.Typer()
catalog_app = typer.Typer()
orders_app = typer.Typer()
day_app = typer.Typer()

app.add_typer(catalog_app, name="catalog")
app.add_typer(orders_app, name="orders")
app.add_typer(day_app, name="day")

console = Console()


@catalog_app.callback(invoke_without_command=True)
def catalog():
    """List products with pricing tiers."""
    pass


@catalog_app.command("list")
def catalog_list():
    """List all products with pricing tiers."""
    from provider.app.services.catalog_service import get_all_products
    
    products = get_all_products()
    
    table = Table(title="Provider Catalog")
    table.add_column("ID", style="cyan")
    table.add_column("Product", style="green")
    table.add_column("Lead Time", style="yellow")
    table.add_column("Stock", style="magenta")
    table.add_column("Pricing Tiers", style="blue")
    
    for p in products:
        pricing = ", ".join([f"{t['min_quantity']}+: €{t['unit_price']:.2f}" for t in p.get("pricing", [])])
        table.add_row(
            str(p["id"]),
            p["name"],
            f"{p['lead_time_days']} days",
            str(p.get("stock", 0)),
            pricing,
        )
    
    console.print(table)


@catalog_app.command("show")
def catalog_show(product_name: str):
    """Show details of a specific product."""
    from provider.app.services.catalog_service import get_product_by_name
    
    product = get_product_by_name(product_name)
    if not product:
        rprint(f"[red]Product '{product_name}' not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"\n[bold green]{product['name']}[/bold green]")
    rprint(f"Description: {product.get('description', 'N/A')}")
    rprint(f"Lead Time: {product['lead_time_days']} days")
    rprint(f"Stock: {product.get('stock', 0)}")
    
    rprint("\n[bold]Pricing Tiers:[/bold]")
    for tier in product.get("pricing", []):
        rprint(f"  {tier['min_quantity']}+ units: €{tier['unit_price']:.2f}")


@orders_app.callback(invoke_without_command=True)
def orders():
    """Manage orders."""
    pass


@orders_app.command("list")
def orders_list(status: Optional[str] = None):
    """List all orders, optionally filtered by status."""
    from provider.app.services.order_service import get_orders
    
    order_list = get_orders(status=status)
    
    if not order_list:
        rprint("[yellow]No orders found[/yellow]")
        return
    
    table = Table(title=f"Orders{f' - {status}' if status else ''}")
    table.add_column("ID", style="cyan")
    table.add_column("Buyer", style="green")
    table.add_column("Product ID", style="yellow")
    table.add_column("Qty", style="magenta")
    table.add_column("Total", style="blue")
    table.add_column("Placed", style="white")
    table.add_column("Expected", style="white")
    table.add_column("Status", style="red")
    
    for o in order_list:
        table.add_row(
            str(o["id"]),
            o["buyer"],
            str(o["product_id"]),
            str(o["quantity"]),
            f"€{o['total_price']:.2f}",
            str(o["placed_day"]),
            str(o["expected_delivery_day"]),
            o["status"],
        )
    
    console.print(table)


@orders_app.command("show")
def orders_show(order_id: int):
    """Show details of a specific order."""
    from provider.app.services.order_service import get_order
    
    order = get_order(order_id)
    if not order:
        rprint(f"[red]Order {order_id} not found[/red]")
        raise typer.Exit(1)
    
    rprint(f"\n[bold]Order #{order['id']}[/bold]")
    rprint(f"Buyer: {order['buyer']}")
    rprint(f"Product ID: {order['product_id']}")
    rprint(f"Quantity: {order['quantity']}")
    rprint(f"Unit Price: €{order['unit_price']:.2f}")
    rprint(f"Total Price: €{order['total_price']:.2f}")
    rprint(f"Placed Day: {order['placed_day']}")
    rprint(f"Expected Delivery: Day {order['expected_delivery_day']}")
    rprint(f"Shipped Day: {order.get('shipped_day', 'N/A')}")
    rprint(f"Delivered Day: {order.get('delivered_day', 'N/A')}")
    rprint(f"Status: [bold]{order['status']}[/bold]")


@day_app.callback(invoke_without_command=True)
def day():
    """Manage simulation day."""
    pass


@day_app.command("current")
def day_current():
    """Show current simulation day."""
    from provider.app.services.order_service import get_current_day
    
    current = get_current_day()
    rprint(f"\n[bold]Current Day:[/bold] {current}")


@day_app.command("advance")
def day_advance():
    """Advance simulation by one day."""
    from provider.app.services.order_service import advance_day
    
    result = advance_day()
    rprint(f"\n[bold green]Day advanced![/bold green]")
    rprint(f"Previous Day: {result['previous_day']}")
    rprint(f"Current Day: {result['current_day']}")
    rprint(f"Orders Shipped: {result['orders_shipped']}")
    rprint(f"Orders Delivered: {result['orders_delivered']}")


@app.command("stock")
def stock_show():
    """Show current inventory levels."""
    from provider.app.services.catalog_service import get_stock_levels
    
    stocks = get_stock_levels()
    
    table = Table(title="Current Stock")
    table.add_column("Product ID", style="cyan")
    table.add_column("Product Name", style="green")
    table.add_column("Quantity", style="yellow")
    
    for s in stocks:
        table.add_row(
            str(s["product_id"]),
            s["product_name"],
            str(s["quantity"]),
        )
    
    console.print(table)


@app.command("price")
def price_set():
    """Update a price tier (use subcommands)."""
    rprint("[yellow]Use: provider-cli price set <product_id> <min_quantity> <price>[/yellow]")


@app.command("restock")
def restock_product(product: str, quantity: int):
    """Add stock to a product."""
    from provider.app.services.catalog_service import add_stock
    
    success = add_stock(product, quantity)
    if success:
        rprint(f"[green]Added {quantity} to {product}[/green]")
    else:
        rprint(f"[red]Product '{product}' not found[/red]")
        raise typer.Exit(1)


@app.command("export")
def export_state():
    """Dump state to JSON."""
    from provider.app.services.export_import import export_state
    
    result = export_state()
    rprint(f"[green]State exported to {result}[/green]")


@app.command("import")
def import_state(file: str):
    """Load state from JSON."""
    from provider.app.services.export_import import import_state
    
    result = import_state(file)
    rprint(f"[green]State imported from {file}[/green]")


@app.command("serve")
def serve(port: int = 8001):
    """Start the REST API server."""
    import subprocess
    import os
    
    rprint(f"[green]Starting Provider API on port {port}...[/green]")
    
    # Set the port environment variable
    env = os.environ.copy()
    env["PROVIDER_PORT"] = str(port)
    
    # Run uvicorn
    subprocess.run(
        ["uvicorn", "provider.app.main:app", "--host", "0.0.0.0", "--port", str(port)],
        env=env,
    )


def main():
    app()


if __name__ == "__main__":
    main()