import typer
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, init_db
from app.services.external_supplier_service import ExternalSupplierService
from app.services.simulation_engine import SimulationEngine
import uvicorn

app = typer.Typer(help="Manufacturer Production Simulator CLI - Manage production, inventory, and external suppliers.")
suppliers_app = typer.Typer(help="Interact with external component providers.")
purchase_app = typer.Typer(help="Manage purchase orders for raw materials.")
day_app = typer.Typer(help="Control the simulated passage of time and sync with providers.")

app.add_typer(suppliers_app, name="suppliers")
app.add_typer(purchase_app, name="purchase")
app.add_typer(day_app, name="day")

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

@app.command()
def serve(port: int = 8002):
    """
    Start the Manufacturer REST API server.
    
    Default port is 8002. This allows access to the web dashboard and REST endpoints.
    """
    uvicorn.run("app.main:app", host="0.0.0.0", port=port, reload=True)

if __name__ == "__main__":
    init_db()
    app()
