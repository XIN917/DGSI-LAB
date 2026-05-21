"""Shared test fixtures for Retailer App."""
import asyncio
import pytest
import pytest_asyncio
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from httpx import ASGITransport, AsyncClient

from app.models.database import Base
from app.models.database import (
    CustomerOrderDB,
    InventoryItemDB,
    PurchaseOrderDB,
    EventLogDB,
    SimStateDB,
)


@pytest.fixture(scope="function")
def db_path(tmp_path):
    return tmp_path / "test_retailer.db"


@pytest.fixture(scope="function")
def sync_engine(db_path):
    """Create a sync SQLite engine for each test."""
    eng = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    # Seed initial simulation state
    session = Session(eng)
    session.add(SimStateDB(key="current_day", value="0"))
    session.commit()
    session.close()
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture(scope="function")
def async_session_local(db_path):
    """Create an async session factory connected to the same test DB file."""
    engine = create_async_engine(f"sqlite+aiosqlite:///{db_path}", echo=False)
    local = sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
    yield local
    asyncio.run(engine.dispose())


@pytest.fixture(scope="function")
def db_session(sync_engine):
    """Provide a fresh DB session for each test."""
    session = Session(sync_engine)
    yield session
    session.rollback()
    session.close()


@pytest_asyncio.fixture
async def async_client():
    """Provide async HTTP client for API testing."""
    from app.main import create_app
    from app.core.database import init_db

    await init_db()
    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://testserver") as client:
        yield client


@pytest.fixture(scope="function")
def reset_db(db_session):
    """Reset database to clean state between tests."""
    # Clear all tables
    db_session.query(CustomerOrderDB).delete()
    db_session.query(PurchaseOrderDB).delete()
    db_session.query(InventoryItemDB).delete()
    db_session.query(EventLogDB).delete()
    db_session.query(SimStateDB).delete()
    # Reset sim state
    db_session.add(SimStateDB(key="current_day", value="0"))
    db_session.commit()


@pytest.fixture
def sample_inventory(db_session):
    """Create sample inventory for testing."""
    items = [
        InventoryItemDB(
            sku="P3D-Classic",
            quantity_on_hand=10,
            retail_price=1500.0,
            last_cost=1200.0,
        ),
        InventoryItemDB(
            sku="P3D-Pro",
            quantity_on_hand=5,
            retail_price=2500.0,
            last_cost=2000.0,
        ),
    ]
    for item in items:
        db_session.add(item)
    db_session.commit()
    return items
