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
    from app.models.product import Product
    db = SessionLocal()
    service = ProviderService(db)
    stocks = service.get_stock()
    for s in stocks:
        name = db.query(Product).filter(Product.id == s.product_id).first()
        label = name.name if name else str(s.product_id)
        typer.echo(f"Product: {label} | Quantity: {s.quantity}")
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
    from app.models.product import Product
    for o in orders:
        name = db.query(Product).filter(Product.id == o.product_id).first()
        label = name.name if name else str(o.product_id)
        typer.echo(f"ID: {o.id} | Buyer: {o.buyer} | Product: {label} | Qty: {o.quantity} | Status: {o.status}")
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
def restock(product: str, quantity: int):
    """
    Manually add stock to a product.

    PRODUCT is the product name (e.g. pcb, motor, extruder).
    Increments the current inventory level for the named product.
    """
    from app.models.product import Product
    db = SessionLocal()
    service = ProviderService(db)
    p = db.query(Product).filter(Product.name.ilike(product)).first()
    if not p:
        typer.echo(f"Error: product '{product}' not found")
        db.close()
        raise typer.Exit(1)
    service.restock(p.id, quantity)
    typer.echo(f"Added {quantity} to {p.name}")
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
def set_price(product: str, tier: int, price: float):
    """
    Update or create a pricing tier for a product.

    PRODUCT is the product name (e.g. pcb, motor, extruder).
    TIER is the minimum order quantity that activates this price.
    PRICE is the unit price in euros.
    """
    from decimal import Decimal
    from app.models.product import Product
    db = SessionLocal()
    service = ProviderService(db)
    p = db.query(Product).filter(Product.name.ilike(product)).first()
    if not p:
        typer.echo(f"Error: product '{product}' not found")
        db.close()
        raise typer.Exit(1)
    try:
        service.set_price(p.id, tier, Decimal(str(price)))
        typer.echo(f"Updated {p.name} tier {tier} to {price}€")
    except Exception as e:
        typer.echo(f"Error: {e}")
    finally:
        db.close()

@app.command()
def export(file: str = typer.Argument(..., help="Path to save the JSON export")):
    """Export the complete provider state to a JSON file."""
    db = SessionLocal()
    try:
        from app.utils.json_export import export_full_state
        import json
        state = export_full_state(db)
        with open(file, "w") as f:
            json.dump(state, f, indent=2)
        typer.echo(f"✅ State exported to {file}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
    finally:
        db.close()

@app.command("import")
def import_command(file: str = typer.Argument(..., help="Path to the JSON file to import")):
    """Import a provider state from a JSON file (OVERWRITES CURRENT DATA)."""
    db = SessionLocal()
    try:
        import json
        import os
        if not os.path.exists(file):
            typer.echo(f"❌ Error: File {file} not found")
            return
        
        with open(file, "r") as f:
            data = json.load(f)
            
        from app.utils.json_export import import_full_state
        import_full_state(db, data)
        typer.echo(f"✅ State imported from {file}")
    except Exception as e:
        typer.echo(f"❌ Error: {e}")
    finally:
        db.close()

@app.command()
def serve(port: int = typer.Option(8001, "--port", "-p", help="Port to run the Provider REST API on.")):
    """
    Start the Provider REST API server.
    
    Default port is 8001. Use this to allow the manufacturer to place orders.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=False)

if __name__ == "__main__":
    app()
