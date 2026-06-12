"""Full flow integration test via API (Simplified)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from decimal import Decimal

from app.main import app
from app.core.database import get_db, engine, Base
from app.services.seed import initialize_seed_data


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
    """Create fresh database for each test."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    initialize_seed_data(session)
    yield session
    session.rollback()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def token(client):
    """Get a valid authentication token."""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]


def test_fast_production_cycle_api(client, token):
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Create a Manufacturing Order for P3D-Classic (10 units - fits in stock)
    response = client.post(
        "/api/orders",
        json={"product_model": "P3D-Classic", "quantity": 10},
        headers=headers
    )
    assert response.status_code == 201
    order_id = response.json()["id"]

    # 2. Release the order (should succeed immediately)
    response = client.post(f"/api/orders/{order_id}/release", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "released"

    # 3. Advance Day (should produce all 10 units)
    response = client.post("/api/simulation/advance", headers=headers)
    assert response.status_code == 200
    
    # 4. Verify completion
    response = client.get(f"/api/orders/{order_id}", headers=headers)
    assert response.json()["status"] == "completed"
    assert response.json()["quantity_produced"] == 10.0

    # 5. Verify Export/Import logic
    response = client.get("/api/export/full-state", headers=headers)
    assert response.status_code == 200
    state = response.json()
    assert state["simulation_state"]["current_day"] == 2
    
    # Try importing it back
    response = client.post("/api/import/full-state", json=state, headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "imported"
