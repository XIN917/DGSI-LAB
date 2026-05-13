"""Basic tests for the API."""

import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client."""
    return TestClient(app)


def test_root(client):
    """Test root endpoint."""
    response = client.get("/")
    assert response.status_code == 200
    assert "message" in response.json()


def test_health_check(client):
    """Test health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


def test_list_models_empty(client):
    """Test listing printer models (should be empty initially)."""
    response = client.get("/api/models")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_suppliers_empty(client):
    """Test listing suppliers (should be empty initially)."""
    response = client.get("/api/suppliers")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_orders_empty(client):
    """Test listing orders (should be empty initially)."""
    response = client.get("/api/orders")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_simulation_status(client):
    """Test simulation status endpoint."""
    response = client.get("/api/simulation/status")
    assert response.status_code == 200
    data = response.json()
    assert "current_day" in data
    assert "running" in data
