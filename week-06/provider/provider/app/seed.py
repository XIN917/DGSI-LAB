"""Seed data loader for Provider app."""
import json
import os
from pathlib import Path

from provider.app.db import get_session
from provider.app.models.product import Product
from provider.app.models.pricing_tier import PricingTier
from provider.app.models.stock import Stock
from provider.app.models.sim_state import SimState


def get_seed_file_path() -> str:
    """Get the path to the seed data file."""
    # Try multiple locations
    possible_paths = [
        "seed_data/seed-provider.json",
        "provider/seed_data/seed-provider.json",
        os.path.join(os.path.dirname(__file__), "..", "seed_data", "seed-provider.json"),
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # Default to the one in the repo
    return "seed_data/seed-provider.json"


def load_seed_data(session=None):
    """Load seed data into the database."""
    close_session = False
    if session is None:
        session = get_session()
        close_session = True
    
    try:
        seed_path = get_seed_file_path()
        with open(seed_path, "r") as f:
            seed_data = json.load(f)
        
        # Load products
        for product_data in seed_data.get("products", []):
            # Check if product already exists
            existing = session.query(Product).filter_by(name=product_data["name"]).first()
            if existing:
                continue
            
            # Create product
            product = Product(
                name=product_data["name"],
                description=product_data.get("description", ""),
                lead_time_days=product_data["lead_time_days"],
            )
            session.add(product)
            session.flush()  # Get the ID
            
            # Create pricing tiers
            for tier_data in product_data.get("pricing", []):
                tier = PricingTier(
                    product_id=product.id,
                    min_quantity=tier_data["min_qty"],
                    unit_price=tier_data["price"],
                )
                session.add(tier)
            
            # Create stock
            stock = Stock(
                product_id=product.id,
                quantity=product_data.get("initial_stock", 0),
            )
            session.add(stock)
        
        # Initialize sim state if not exists
        if not session.query(SimState).filter_by(key="current_day").first():
            sim_state = SimState(key="current_day", value="0")
            session.add(sim_state)
        
        session.commit()
        print(f"Seed data loaded successfully from {seed_path}")
        
    except Exception as e:
        session.rollback()
        print(f"Error loading seed data: {e}")
        raise
    finally:
        if close_session:
            session.close()


if __name__ == "__main__":
    from provider.app.db import init_db
    
    # Initialize database
    print("Initializing database...")
    init_db()
    
    # Load seed data
    print("Loading seed data...")
    load_seed_data()