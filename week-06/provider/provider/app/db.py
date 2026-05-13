"""Database setup for Provider app."""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

Base = declarative_base()

# Database path - use environment or default
DB_PATH = os.environ.get("PROVIDER_DB", "provider.db")


def get_engine(echo: bool = False):
    """Create and return database engine."""
    engine = create_engine(f"sqlite:///{DB_PATH}", echo=echo)
    return engine


def get_session():
    """Create and return a database session."""
    engine = get_engine()
    Session = sessionmaker(bind=engine)
    return Session()


def init_db():
    """Initialize the database - create all tables."""
    from provider.app.models.product import Product
    from provider.app.models.pricing_tier import PricingTier
    from provider.app.models.stock import Stock
    from provider.app.models.order import Order
    from provider.app.models.event import Event
    from provider.app.models.sim_state import SimState

    engine = get_engine()
    Base.metadata.create_all(engine)
    return engine