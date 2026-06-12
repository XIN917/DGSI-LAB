import typer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.services.provider_service import ProviderService
from app.services.seed import seed_provider_data
import uvicorn

app = typer.Typer(help="Provider Management CLI - Orchestrate supply, orders, and simulation time.")
orders_app = typer.Typer(help="Manage and view purchase orders received from manufacturers.")
day_app = typer.Typer(help="Control the simulated passage of time.")
price_app = typer.Typer(help="Manage product pricing and volume discount tiers.")

app.add_typer(orders_app, name="orders")
app.add_typer(day_app, name="day")
app.add_typer(price_app, name="price")

@app.command()
def seed():
    """
    Seed the provider database with initial data.
    
    Creates default products (PCBs, Motors, Extruders), initial stock levels,
    and standard pricing tiers. This should be run once before starting the simulation.
    """
    init_db()
    db = SessionLocal()
    try:
        seed_provider_data(db)
    finally:
        db.close()

@app.command()
def catalog():
    """
    List all products in the provider's catalog.
    
    Displays product IDs, names, lead times (in days), and all active
    pricing tiers (volume discounts).
    """
    db = SessionLocal()
    service = ProviderService(db)
    products = service.get_catalog()
    for p in products:
        typer.echo(f"ID: {p.id} | Name: {p.name} | Lead Time: {p.lead_time_days} days")
        for tier in p.pricing_tiers:
            typer.echo(f"  - Min Qty: {tier.min_quantity} | Unit Price: {tier.unit_price}€")
    db.close()

@app.command()
def stock():
    """
    Show current provider inventory levels.
    
    Lists the quantity available for every product in the catalog.
    """
    db = SessionLocal()
    service = ProviderService(db)
    stocks = service.get_stock()
    for s in stocks:
        typer.echo(f"Product ID: {s.product_id} | Quantity: {s.quantity}")
    db.close()

@orders_app.command("list")
def list_orders(status: str = None):
    """
    List all orders received by the provider.
    
    Optional: Filter by status (e.g., PENDING, CONFIRMED, SHIPPED, DELIVERED).
    """
    db = SessionLocal()
    service = ProviderService(db)
    orders = service.get_orders(status=status)
    for o in orders:
        typer.echo(f"ID: {o.id} | Buyer: {o.buyer} | Product ID: {o.product_id} | Qty: {o.quantity} | Status: {o.status}")
    db.close()

@orders_app.command("show")
def show_order(order_id: int):
    """
    Show detailed information for a specific order.
    
    Displays full order state, including pricing, status, and delivery dates.
    """
    db = SessionLocal()
    service = ProviderService(db)
    o = service.get_order(order_id)
    if o:
        typer.echo(f"ID: {o.id}")
        typer.echo(f"Buyer: {o.buyer}")
        typer.echo(f"Product ID: {o.product_id}")
        typer.echo(f"Quantity: {o.quantity}")
        typer.echo(f"Unit Price: {o.unit_price}€")
        typer.echo(f"Total Price: {o.total_price}€")
        typer.echo(f"Status: {o.status}")
        typer.echo(f"Placed Day: {o.placed_day}")
        typer.echo(f"Expected Delivery Day: {o.expected_delivery_day}")
    else:
        typer.echo("Order not found")
    db.close()

@app.command()
def restock(product_id: int, quantity: int):
    """
    Manually add stock to a product.
    
    Increments the current inventory level for the specified product ID.
    """
    db = SessionLocal()
    service = ProviderService(db)
    service.restock(product_id, quantity)
    typer.echo(f"Added {quantity} to product {product_id}")
    db.close()

@app.command()
def export(output: str = typer.Option("provider_state.json", help="Output JSON file path")):
    """
    Export the complete provider state to a JSON file.
    """
    from app.utils.json_export import export_full_state
    import json
    db = SessionLocal()
    try:
        state = export_full_state(db)
        with open(output, "w") as f:
            json.dump(state, f, indent=2)
        typer.echo(f"Exported state to {output}")
    finally:
        db.close()

@app.command("import")
def import_command(file: str = typer.Argument(..., help="JSON file to import")):
    """
    Import a provider state from a JSON file.
    WARNING: This will overwrite the current database!
    """
    from app.utils.json_export import import_full_state
    import json
    import os
    if not os.path.exists(file):
        typer.echo(f"File not found: {file}")
        return
    
    db = SessionLocal()
    try:
        with open(file, "r") as f:
            data = json.load(f)
        result = import_full_state(db, data)
        typer.echo(f"Imported state: {result}")
    except Exception as e:
        typer.echo(f"Import failed: {e}")
    finally:
        db.close()

@day_app.command("advance")
def day_advance():
    """
    Advance the simulated time by one day.
    
    This command processes all active orders, moving them through the
    fulfillment pipeline (PENDING -> CONFIRMED -> SHIPPED -> DELIVERED).
    """
    db = SessionLocal()
    service = ProviderService(db)
    new_day = service.advance_day()
    typer.echo(f"Advanced to day {new_day}")
    db.close()

@day_app.command("current")
def day_current():
    """
    Show the current simulation day.
    """
    db = SessionLocal()
    service = ProviderService(db)
    day = service.get_current_day()
    typer.echo(f"Current Day: {day}")
    db.close()

@price_app.command("set")
def set_price(product_id: int, min_quantity: int, unit_price: float):
    """
    Update or create a pricing tier for a product.
    
    Defines the unit price for a given minimum order quantity.
    """
    from decimal import Decimal
    db = SessionLocal()
    service = ProviderService(db)
    try:
        service.set_price(product_id, min_quantity, Decimal(str(unit_price)))
        typer.echo(f"Updated product {product_id} tier {min_quantity} to {unit_price}€")
    except Exception as e:
        typer.echo(f"Error: {e}")
    finally:
        db.close()

@app.command()
def serve(port: int = 8001):
    """
    Start the Provider REST API server.
    
    Default port is 8001. Use this to allow the manufacturer to place orders.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    app()
