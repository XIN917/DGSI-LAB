from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
import asyncio

from app.core.config import settings


database_url = settings.database_url
engine: AsyncEngine = create_async_engine(database_url, echo=False)
AsyncSessionLocal = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def init_db(reset_day: bool = False) -> None:
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
    
    # Seed sim_state with current_day
    async with AsyncSessionLocal() as session:
        from app.models.database import SimStateDB
        from sqlalchemy import select, update
        
        result = await session.execute(
            select(SimStateDB).where(SimStateDB.key == "current_day")
        )
        if result.first():
            if reset_day:
                await session.execute(
                    update(SimStateDB).where(SimStateDB.key == "current_day").values(value="0")
                )
                await session.commit()
        else:
            session.add(SimStateDB(key="current_day", value="0"))
            await session.commit()
        
        # Initialize inventory if not exists
        result = await session.execute(
            select(SimStateDB).where(SimStateDB.key == "inventory_initialized")
        )
        if not result.first():
            from app.models.database import InventoryItemDB
            session.add(InventoryItemDB(sku="P3D-Classic", quantity_on_hand=5, retail_price=1500.0))
            session.add(InventoryItemDB(sku="P3D-Pro", quantity_on_hand=3, retail_price=2500.0))
            session.add(SimStateDB(key="inventory_initialized", value="1"))
            await session.commit()
