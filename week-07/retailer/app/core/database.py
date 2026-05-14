from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import settings


database_url = settings.database_url
engine: AsyncEngine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db() -> None:
    """Initialize the database and create all tables."""
    from app.models.database import Base
    import os
    from urllib.parse import urlparse

    # Ensure the database directory exists
    if settings.database_url.startswith("sqlite"):
        db_path = settings.database_url.split("///")[-1]
        db_dir = os.path.dirname(db_path)
        if db_dir:
            os.makedirs(db_dir, exist_ok=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Seed sim_state with current_day if not exists
    async with AsyncSessionLocal() as session:
        from app.models.database import SimStateDB
        from sqlalchemy import select
        
        result = await session.execute(
            select(SimStateDB).where(SimStateDB.key == "current_day")
        )
        row = result.first()
        if not row:
            session.add(SimStateDB(key="current_day", value="0"))
            await session.commit()
        
        # Initialize inventory
        result = await session.execute(
            select(SimStateDB).where(SimStateDB.key == "inventory_initialized")
        )
        row = result.first()
        if not row:
            from app.models.database import InventoryItemDB
            session.add(InventoryItemDB(sku="P3D-Classic", quantity_on_hand=5, retail_price=1500.0))
            session.add(InventoryItemDB(sku="P3D-Pro", quantity_on_hand=3, retail_price=2500.0))
            session.add(SimStateDB(key="inventory_initialized", value="1"))
            await session.commit()
