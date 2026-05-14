import typer
import sys
import os
from decimal import Decimal

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.services.external_supplier_service import ExternalSupplierService
from app.services.simulation_engine import SimulationEngine
import uvicorn

app = typer.Typer(help="Manufacturer Production Simulator CLI - Manage production, inventory, and external suppliers.")
suppliers_app = typer.Typer(help="Interact with external component providers.")
purchase_app = typer.Typer(help="Manage purchase orders for raw materials.")
day_app = typer.Typer(help="Control the simulated passage of time and sync with providers.")
price_app = typer.Typer(help="Manage wholesale prices for finished products.")
sales_app = typer.Typer(help="Manage retailer sales orders.")
production_app = typer.Typer(help="Manage production line and release orders.")

app.add_typer(suppliers_app, name="suppliers")
app.add_typer(purchase_app, name="purchase")
app.add_typer(day_app, name="day")
app.add_typer(price_app, name="price")
app.add_typer(sales_app, name="sales")
app.add_typer(production_app, name="production")

@app.callback()
def callback():
    """
    Initialize database before any command.
    Ensures the SQLite database and tables are created.
    """
    init_db()

@app.command()
def seed():
    """
    Seed the manufacturer database with initial data.
    
    Loads default materials, products, production lines, and initial 
    inventory levels. Required before running any simulation.
    """
    from app.services.seed import initialize_seed_data
    db = SessionLocal()
    try:
        initialize_seed_data(db)
        typer.echo("Manufacturer database seeded.")
    finally:
        db.close()

@suppliers_app.command("list")
def list_suppliers():
    """
    List all configured external suppliers.
    
    Reads from the local 'providers.json' configuration and syncs
    them with the database.
    """
    db = SessionLocal()
    service = ExternalSupplierService(db)
    service.sync_providers()
    suppliers = service.list_suppliers()
    for s in suppliers:
        typer.echo(f"Name: {s.name} | URL: {s.api_url}")
    db.close()

@suppliers_app.command("catalog")
def show_catalog(name: str):
    """
    Fetch and show the product catalog from a specific external supplier.
    
    Requires the supplier's name as an argument (e.g., "ChipSupply Co").
    Note: Use double quotes "" if the name contains spaces.
    """
    db = SessionLocal()
    service = ExternalSupplierService(db)
    try:
        catalog = service.get_catalog(name)
        for p in catalog:
            typer.echo(f"ID: {p['id']} | Name: {p['name']} | Lead Time: {p['lead_time_days']} days")
            for tier in p['pricing_tiers']:
                typer.echo(f"  - Min Qty: {tier['min_quantity']} | Unit Price: {tier['unit_price']}€")
    except Exception as e:
        typer.echo(f"Error: {e}")
    db.close()

@purchase_app.command("create")
def create_purchase(
    supplier: str = typer.Option(..., "--supplier", help="The name of the external supplier (e.g., 'ChipSupply Co')"),
    product: str = typer.Option(..., "--product", help="The Product ID or Name from the supplier's catalog"),
    qty: int = typer.Option(..., "--qty", help="The amount to purchase")
):
    """
    Place a new purchase order with an external supplier.
    
    This command communicates via REST to the provider's API. If successful,
    a local purchase order is created to track the delivery.
    """
    db = SessionLocal()
    service = ExternalSupplierService(db)
    try:
        po = service.place_order(supplier, product, qty)
        typer.echo(f"Placed PO #{po.id} (External ID: {po.external_id}) with {supplier}")
    except Exception as e:
        typer.echo(f"Error: {e}")
    db.close()

@purchase_app.command("list")
def list_purchases():
    """
    List all purchase orders (internal and external).
    
    Shows the current status of each order. External orders are marked with [EXT].
    """
    db = SessionLocal()
    from app.models.purchase_order import PurchaseOrder, Supplier
    pos = db.query(PurchaseOrder).join(Supplier).order_by(PurchaseOrder.id).all()
    for po in pos:
        supplier = db.query(Supplier).filter(Supplier.id == po.supplier_id).first()
        ext_flag = " [EXT]" if supplier.is_external else ""
        typer.echo(f"ID: {po.id:04d}{ext_flag} | Supplier: {supplier.name} | Product: {po.product_name} | Qty: {po.quantity_ordered:8.2f} | Status: {po.status:10}")
    db.close()

@day_app.command("advance")
def day_advance():
    """
    Advance the local simulation by one day.
    
    IMPORTANT: This command first polls all external suppliers via REST
    to update the status of pending purchase orders. If an order is marked
    as DELIVERED by the provider, it is automatically added to the local inventory.
    """
    db = SessionLocal()
    # First poll providers
    ext_service = ExternalSupplierService(db)
    ext_service.poll_orders()
    
    # Then advance day using SimulationEngine
    engine = SimulationEngine(db)
    result = engine.advance_day()
    typer.echo(f"Advanced from day {result['previous_day']} to {result['new_day']}")
    db.close()

@day_app.command("current")
def day_current():
    """
    Display the current simulation day and date.
    """
    db = SessionLocal()
    engine = SimulationEngine(db)
    status = engine.get_status()
    typer.echo(f"Current Day: {status['current_day']} ({status['current_date']})")
    db.close()

@price_app.command("list")
def list_prices():
    """List all finished product models and their current wholesale prices."""
    db = SessionLocal()
    from app.models.product import ProductModel
    models = db.query(ProductModel).all()
    for m in models:
        typer.echo(f"SKU: {m.id:15} | Name: {m.name:20} | Wholesale Price: {float(m.wholesale_price):>8.2f}€")
    db.close()

@price_app.command("set")
def set_price(sku: str, price: float):
    """Update the wholesale price for a specific product SKU."""
    db = SessionLocal()
    from app.models.product import ProductModel
    model = db.query(ProductModel).filter(ProductModel.id == sku).first()
    if not model:
        typer.echo(f"Error: SKU '{sku}' not found.")
        db.close()
        return
    model.wholesale_price = Decimal(str(price))
    db.commit()
    typer.echo(f"Updated {sku} wholesale price to {price:.2f}€")
    db.close()

@sales_app.command("orders")
def list_sales_orders():
    """List all sales orders (manufacturing orders)."""
    db = SessionLocal()
    from app.models.order import ManufacturingOrder
    orders = db.query(ManufacturingOrder).order_by(ManufacturingOrder.created_date.desc()).all()
    for o in orders:
        typer.echo(f"ID: {o.id:04d} | SKU: {o.product_model:12} | Qty: {float(o.quantity_needed):6.1f} | Status: {o.status:15} | Produced: {float(o.quantity_produced):6.1f}")
    db.close()

@production_app.command("release")
def release_production(order_id: int):
    """
    Release a pending sales order to production.
    
    This reserves the required raw materials based on the product BOM.
    If materials are insufficient, the order status changes to 'waiting_materials'.
    """
    db = SessionLocal()
    from app.services.order_service import OrderService
    service = OrderService(db)
    success, error = service.release(order_id)
    if success:
        typer.echo(f"Order #{order_id:04d} released to production.")
    else:
        typer.echo(f"Error: {error}")
    db.close()

@app.command()
def stock():
    """Show current inventory levels for raw materials and finished goods."""
    db = SessionLocal()
    from app.models.inventory import Inventory
    items = db.query(Inventory).order_by(Inventory.unit_type, Inventory.product_name).all()
    typer.echo(f"{'TYPE':10} | {'PRODUCT':20} | {'QTY':>8} | {'RESERVED':>8} | {'AVAILABLE':>10}")
    typer.echo("-" * 65)
    for item in items:
        typer.echo(f"{item.unit_type:10} | {item.product_name:20} | {float(item.quantity):8.2f} | {float(item.reserved_quantity):8.2f} | {item.available:10.2f}")
    db.close()

@app.command()
def serve(port: int = typer.Option(8002, "--port", "-p", help="Port to run the Manufacturer REST API on.")):
    """
    Start the Manufacturer REST API server.
    
    Default port is 8002. This allows access to the web dashboard and REST endpoints.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    init_db()
    app()
