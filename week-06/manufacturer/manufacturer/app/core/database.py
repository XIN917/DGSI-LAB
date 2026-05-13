"""Database configuration and initialization."""
import os
from pathlib import Path
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# Database path - can be overridden by environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    f"sqlite:///{Path(__file__).parent.parent / 'data' / 'simulation.db'}"
)

# Ensure data directory exists
if "sqlite" in DATABASE_URL:
    db_path = Path(DATABASE_URL.replace("sqlite:///", ""))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
    echo=os.getenv("SQL_DEBUG", "").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass


def get_db():
    """Dependency for FastAPI routes - yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database, creating all tables."""
    from app.models import user, product, inventory, order, purchase_order, event, simulation  # noqa: F401
    Base.metadata.create_all(bind=engine)
    _upgrade_sqlite_schema()


def _upgrade_sqlite_schema():
    """Apply small additive SQLite upgrades for existing local databases."""
    if not DATABASE_URL.startswith("sqlite"):
        return

    with engine.begin() as connection:
        columns = {
            row[1]
            for row in connection.execute(text("PRAGMA table_info(purchase_orders)"))
        }
        if not columns:
            return

        if "provider_name" not in columns:
            connection.execute(
                text("ALTER TABLE purchase_orders ADD COLUMN provider_name VARCHAR(100)")
            )
        if "provider_order_id" not in columns:
            connection.execute(
                text("ALTER TABLE purchase_orders ADD COLUMN provider_order_id INTEGER")
            )
