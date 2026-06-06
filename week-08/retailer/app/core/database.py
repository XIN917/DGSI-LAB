import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Database URL from settings (strip aiosqlite if present)
DATABASE_URL = settings.database_url.replace("sqlite+aiosqlite", "sqlite")

# Ensure data directory exists
if "sqlite" in DATABASE_URL:
    db_path = DATABASE_URL.replace("sqlite:///", "")
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {},
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    """Dependency for FastAPI routes - yields a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(reset_day: bool = False) -> None:
    """Initialize the database, creating all tables."""
    from app.models.database import Base, SimStateDB, InventoryItemDB
    from app.models.metrics import RetailerMetrics  # noqa: F401
    from sqlalchemy import select, update

    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Seed sim_state with current_day
    with SessionLocal() as session:
        result = session.execute(
            select(SimStateDB).where(SimStateDB.key == "current_day")
        ).first()
        
        if result:
            if reset_day:
                session.execute(
                    update(SimStateDB).where(SimStateDB.key == "current_day").values(value="0")
                )
                session.commit()
        else:
            session.add(SimStateDB(key="current_day", value="0"))
            session.commit()
        
        # Initialize inventory if not exists
        result = session.execute(
            select(SimStateDB).where(SimStateDB.key == "inventory_initialized")
        ).first()
        
        if not result:
            session.add(InventoryItemDB(sku="P3D-Classic", quantity_on_hand=5, retail_price=295.0))
            session.add(InventoryItemDB(sku="P3D-Pro", quantity_on_hand=3, retail_price=435.0))
            session.add(SimStateDB(key="inventory_initialized", value="1"))
            session.commit()
