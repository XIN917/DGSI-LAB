"""Full flow integration test via API."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, Base
from app.services.seed import initialize_seed_data
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Create fresh isolated in-memory database for each test."""
    from app.models import product, inventory, order, purchase_order, event, simulation, metrics  # noqa
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    initialize_seed_data(session)
    yield session
    session.rollback()
    session.close()
    engine.dispose()


def test_fast_production_cycle_api(client):
    # 1. Create a Manufacturing Order for P3D-Classic (10 units)
    response = client.post("/api/orders", json={"product_model": "P3D-Classic", "quantity": 10})
    assert response.status_code == 201
    order_id = response.json()["id"]

    # 2. Release the order
    response = client.post(f"/api/orders/{order_id}/release")
    assert response.status_code == 200
    assert response.json()["status"] == "released"

    # 3. Advance Day
    response = client.post("/api/simulation/advance")
    assert response.status_code == 200

    # 4. Verify completion
    response = client.get(f"/api/orders/{order_id}")
    assert response.json()["status"] == "delivered"
    assert response.json()["quantity_produced"] == 10.0

    # 5. Verify Export/Import logic
    response = client.get("/api/export/full-state")
    assert response.status_code == 200
    state = response.json()
    assert state["simulation_state"]["current_day"] == 1

    response = client.post("/api/import/full-state", json=state)
    assert response.status_code == 200
    assert response.json()["status"] == "imported"
