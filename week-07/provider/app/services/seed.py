import json
from pathlib import Path
from sqlalchemy.orm import Session
from decimal import Decimal
from app.models.product import Product, PricingTier, Stock
from app.models.simulation import SimState
from app.core.database import SessionLocal, init_db

def seed_provider_data(db: Session):
    # Check if already seeded
    if db.query(Product).first():
        print("Provider data already seeded.")
        return

    seed_path = Path(__file__).parent.parent / "data" / "seed-provider.json"
    if not seed_path.exists():
        print(f"Seed file not found at {seed_path}")
        return

    with open(seed_path, "r") as f:
        data = json.load(f)

    for p_data in data["products"]:
        product = Product(
            id=p_data["id"],
            name=p_data["name"],
            description=p_data["description"],
            lead_time_days=p_data["lead_time_days"]
        )
        db.add(product)
        db.flush()

        for t_data in p_data["pricing_tiers"]:
            tier = PricingTier(
                product_id=product.id,
                min_quantity=t_data["min_quantity"],
                unit_price=Decimal(str(t_data["unit_price"]))
            )
            db.add(tier)

        stock = Stock(
            product_id=product.id,
            quantity=p_data["initial_stock"]
        )
        db.add(stock)
    
    # Sim State
    db.add(SimState(key="current_day", value="0"))
    
    db.commit()
    print("Provider data seeded successfully from JSON.")

if __name__ == "__main__":
    init_db()
    db = SessionLocal()
    try:
        seed_provider_data(db)
    finally:
        db.close()
