# Retailer App Testing Guide

This guide provides comprehensive testing strategies for the Retailer App, including unit tests, integration tests, CLI testing, and end-to-end supply chain scenarios.

## Table of Contents

1. [Testing Overview](#1-testing-overview)
2. [Unit Testing](#2-unit-testing)
3. [Integration Testing](#3-integration-testing)
4. [CLI Testing Guide](#4-cli-testing-guide)
5. [End-to-End Supply Chain Testing](#5-end-to-end-supply-chain-testing)
6. [Performance Testing](#6-performance-testing)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. Testing Overview

The Retailer App testing strategy follows these principles:

- **Unit Tests**: Test individual functions and methods in isolation
- **Integration Tests**: Test API endpoints and service interactions
- **CLI Tests**: Manual testing of command-line interface functionality
- **E2E Tests**: Full supply chain scenarios across Provider → Manufacturer → Retailer

### Test Categories

| Test Type | Framework | Location | Purpose |
|-----------|-----------|----------|---------|
| Unit | pytest | `tests/test_services/` | Business logic validation |
| Integration | pytest + httpx | `tests/test_api/` | API endpoint testing |
| CLI | Manual | Terminal | User interface validation |
| E2E | Manual + Scripts | Multi-app | Supply chain workflows |

### Prerequisites

```bash
# Install test dependencies
cd retailer
uv sync

# Set up test database
PYTHONPATH=. uv run python -c "from app.core.database import engine; from app.models.database import Base; Base.metadata.create_all(bind=engine)"
```

---

## 2. Unit Testing

Unit tests focus on individual components without external dependencies.

### Running Unit Tests

```bash
# Run all tests
PYTHONPATH=. uv run pytest tests/

# Run specific test file
PYTHONPATH=. uv run pytest tests/test_services/test_retailer_service.py

# Run with coverage
PYTHONPATH=. uv run pytest --cov=app --cov-report=html tests/
```

### Key Test Areas

#### 2.1 RetailerService Tests

```python
# tests/test_services/test_retailer_service.py
import pytest
from app.services.retailer_service import RetailerService

class TestRetailerService:
    def test_create_customer_order_success(self, db_session):
        service = RetailerService()
        order = await service.create_customer_order("P3D-Classic", 2)
        assert order.quantity == 2
        assert order.sku == "P3D-Classic"
        assert order.status == "fulfilled"

    def test_create_customer_order_backorder(self, db_session):
        service = RetailerService()
        order = await service.create_customer_order("P3D-Pro", 100)  # Insufficient stock
        assert order.status == "backordered"

    def test_pricing_validation(self, db_session):
        service = RetailerService()
        # Test minimum markup enforcement
        with pytest.raises(ValueError):
            await service.set_retail_price("P3D-Classic", 100.0)  # Below wholesale
```

#### 2.2 ManufacturerClient Tests

```python
# tests/test_services/test_manufacturer_client.py
import pytest
from httpx import AsyncClient
from app.services.manufacturer_client import ManufacturerClient

class TestManufacturerClient:
    async def test_place_order_success(self, httpx_mock):
        client = ManufacturerClient()
        httpx_mock.add_response(json={"id": 123, "status": "pending"})

        result = await client.place_order("P3D-Classic", 5)
        assert result["id"] == 123
        assert result["status"] == "pending"

    async def test_get_order_status(self, httpx_mock):
        client = ManufacturerClient()
        httpx_mock.add_response(json={"id": 123, "status": "delivered"})

        result = await client.get_order(123)
        assert result["status"] == "delivered"
```

#### 2.3 Business Logic Tests

- **Fulfillment Logic**: Order fulfillment vs backordering
- **Pricing Rules**: Minimum markup validation (15% above wholesale)
- **Inventory Management**: Stock allocation and reservation
- **Event Logging**: All state changes recorded

---

## 3. Integration Testing

Integration tests verify API endpoints and database interactions.

### API Endpoint Tests

```python
# tests/test_api/test_orders.py
import pytest
from httpx import AsyncClient
from app.main import create_app

@pytest.mark.asyncio
class TestCustomerOrdersAPI:
    async def test_create_customer_order(self, async_client):
        response = await async_client.post(
            "/api/customer-orders/",
            json={"sku": "P3D-Classic", "quantity": 2}
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sku"] == "P3D-Classic"
        assert data["quantity"] == 2

    async def test_list_customer_orders(self, async_client):
        response = await async_client.get("/api/customer-orders/")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
```

### Database Integration Tests

```python
# tests/test_api/test_database_integration.py
@pytest.mark.asyncio
class TestDatabaseIntegration:
    async def test_order_persistence(self, db_session):
        # Create order via API
        response = await async_client.post(
            "/api/customer-orders/",
            json={"sku": "P3D-Classic", "quantity": 1}
        )

        # Verify in database
        from app.models.database import CustomerOrderDB
        order = db_session.query(CustomerOrderDB).first()
        assert order.sku == "P3D-Classic"
        assert order.quantity == 1
```

### Manufacturer Integration Tests

```python
# tests/test_api/test_manufacturer_integration.py
@pytest.mark.asyncio
class TestManufacturerIntegration:
    async def test_purchase_order_creation(self, httpx_mock):
        # Mock manufacturer response
        httpx_mock.add_response(json={"id": 456, "status": "pending"})

        response = await async_client.post(
            "/api/purchase-orders/",
            json={"sku": "P3D-Classic", "quantity": 10}
        )

        assert response.status_code == 200
        data = response.json()
        assert "manufacturer_po_id" in data
```

---

## 4. CLI Testing Guide

Manual testing of the Retailer CLI commands.

### Setup

```bash
# Start the retailer API (in separate terminal)
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8003

# Or run CLI commands directly
cd retailer
```

### 4.1 Catalog & Inventory Commands

```bash
# Display product catalog
PYTHONPATH=. uv run python app/cli.py catalog

# Expected output:
# Available Products:
#   P3D-Classic: Classic 3D Printer - $1500.0
#   P3D-Pro: Professional 3D Printer - $2500.0

# Check inventory (when implemented)
PYTHONPATH=. uv run python app/cli.py inventory
```

### 4.2 Customer Order Management

```bash
# List customer orders (initially empty)
PYTHONPATH=. uv run python app/cli.py customer-orders list

# Create a customer order
PYTHONPATH=. uv run python app/cli.py customer-orders create P3D-Classic 2

# List orders again (should show the new order)
PYTHONPATH=. uv run python app/cli.py customer-orders list

# Create another order (may backorder if insufficient stock)
PYTHONPATH=. uv run python app/cli.py customer-orders create P3D-Pro 50
```

### 4.3 Purchase Order Management

```bash
# List purchase orders from manufacturer
PYTHONPATH=. uv run python app/cli.py purchase-orders list

# Create purchase order to manufacturer
PYTHONPATH=. uv run python app/cli.py purchase-orders create P3D-Classic 20

# List orders again (should show pending PO)
PYTHONPATH=. uv run python app/cli.py purchase-orders list

# Sync PO status (when manufacturer API is running)
PYTHONPATH=. uv run python app/cli.py purchase-orders sync 1
```

### 4.4 Day Management

```bash
# Check current day
PYTHONPATH=. uv run python app/cli.py day current

# Advance to next day
PYTHONPATH=. uv run python app/cli.py day advance

# Verify day changed
PYTHONPATH=. uv run python app/cli.py day current
```

---

## 5. End-to-End Supply Chain Testing

Test the complete Provider → Manufacturer → Retailer workflow.

### 5.1 Setup All Three Apps

**Terminal 1: Provider**
```bash
cd provider
PYTHONPATH=. uv run python main.py serve --port 8001
```

**Terminal 2: Manufacturer**
```bash
cd manufacturer
PYTHONPATH=. uvicorn app.main:app --reload --port 8002
```

**Terminal 3: Retailer**
```bash
cd retailer
PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8003
```

### 5.2 Complete Order-to-Delivery Scenario

#### Day 0: Initial Setup
```bash
# Provider: Check initial state
provider/provider-cli day current  # Should be 0
provider/provider-cli stock

# Manufacturer: Check initial state
manufacturer/manufacturer-cli day current  # Should be 0

# Retailer: Check initial state
PYTHONPATH=. uv run python app/cli.py day current  # Should be 0
PYTHONPATH=. uv run python app/cli.py catalog
```

#### Day 0: Retailer Places Purchase Order
```bash
# Retailer orders printers from Manufacturer
PYTHONPATH=. uv run python app/cli.py purchase-orders create P3D-Classic 10

# Manufacturer should receive the order
manufacturer/manufacturer-cli purchase list  # Should show pending order
```

#### Day 1: Advance All Apps
```bash
# Advance all three apps
provider/provider-cli day advance
manufacturer/manufacturer-cli day advance
PYTHONPATH=. uv run python app/cli.py day advance
```

#### Day 2-4: Continue Advancement
```bash
# Continue advancing until manufacturer order is fulfilled
# (Lead time depends on manufacturer configuration)

# Check manufacturer order status
manufacturer/manufacturer-cli purchase list

# When manufacturer order is delivered, advance retailer
PYTHONPATH=. uv run python app/cli.py day advance
```

#### Day 5: Retailer Receives Stock
```bash
# Check retailer inventory (when implemented)
PYTHONPATH=. uv run python app/cli.py inventory

# Now retailer can fulfill customer orders
PYTHONPATH=. uv run python app/cli.py customer-orders create P3D-Classic 5
PYTHONPATH=. uv run python app/cli.py customer-orders list
```

### 5.3 Backorder Scenario

```bash
# Create customer order that exceeds available stock
PYTHONPATH=. uv run python app/cli.py customer-orders create P3D-Pro 100

# Verify it's backordered
PYTHONPATH=. uv run python app/cli.py customer-orders list

# Advance days and place more POs to manufacturer
# When stock arrives, backorders should auto-fulfill
PYTHONPATH=. uv run python app/cli.py day advance
PYTHONPATH=. uv run python app/cli.py customer-orders list  # Should show fulfilled
```

### 5.4 Pricing Validation

```bash
# Test pricing rules (when pricing commands are implemented)
# Attempt to set price below minimum markup - should fail
PYTHONPATH=. uv run python app/cli.py pricing set P3D-Classic 100.0  # Should reject

# Set valid price (30% markup)
PYTHONPATH=. uv run python app/cli.py pricing set P3D-Classic 1950.0  # Should accept
```

---

## 6. Performance Testing

### 6.1 Load Testing API Endpoints

```bash
# Use tools like locust or artillery for load testing
# Example: Test customer order creation under load

# Install artillery
npm install -g artillery

# Create test script (artillery.yml)
config:
  target: 'http://localhost:8003'
  phases:
    - duration: 60
      arrivalRate: 10
scenarios:
  - name: 'Create customer orders'
    requests:
      - post:
          url: '/api/customer-orders/'
          json:
            sku: 'P3D-Classic'
            quantity: 1
```

### 6.2 Database Performance

```python
# tests/test_performance.py
import time
import pytest

def test_bulk_order_creation(db_session):
    service = RetailerService()
    start_time = time.time()

    # Create 100 orders
    for i in range(100):
        await service.create_customer_order("P3D-Classic", 1)

    end_time = time.time()
    assert end_time - start_time < 5.0  # Should complete within 5 seconds
```

### 6.3 Memory Usage

```python
# Monitor memory usage during large operations
import psutil
import os

def test_memory_usage():
    process = psutil.Process(os.getpid())
    initial_memory = process.memory_info().rss

    # Perform memory-intensive operation
    # e.g., bulk order creation

    final_memory = process.memory_info().rss
    memory_increase = final_memory - initial_memory
    assert memory_increase < 50 * 1024 * 1024  # Less than 50MB increase
```

---

## 7. Troubleshooting

### 7.1 Common Issues

#### Database Connection Errors
```bash
# Reset database
rm retailer.db
PYTHONPATH=. uv run python -c "from app.core.database import engine; from app.models.database import Base; Base.metadata.create_all(bind=engine)"
```

#### Port Conflicts
```bash
# Check what's using ports
lsof -i :8003

# Change port in config or command
PYTHONPATH=. uv run uvicorn app.main:app --port 8004
```

#### Manufacturer Connection Issues
```bash
# Test manufacturer connectivity
curl http://localhost:8002/api/day/current

# Check manufacturer is running
ps aux | grep uvicorn
```

#### Import Errors
```bash
# Ensure virtual environment is activated
cd retailer
uv run python -c "import app.main"

# Check PYTHONPATH
PYTHONPATH=. uv run python -c "import sys; print(sys.path)"
```

### 7.2 Debug Mode

```bash
# Run with debug logging
PYTHONPATH=. UVICORN_LOG_LEVEL=debug uv run uvicorn app.main:app --reload

# Enable SQLAlchemy echo
# In config.py, set echo=True for database engine
```

### 7.3 Test Data Reset

```python
# tests/conftest.py - Add reset fixture
@pytest.fixture(scope="function")
def reset_db(db_session):
    """Reset database to clean state."""
    # Clear all tables
    db_session.query(CustomerOrderDB).delete()
    db_session.query(PurchaseOrderDB).delete()
    db_session.query(EventLogDB).delete()
    # Reset sim state
    db_session.query(SimStateDB).update({"value": "0"})
    db_session.commit()
```

---

## 8. Test Automation

### CI/CD Integration

```yaml
# .github/workflows/test.yml
name: Test Retailer App
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: astral-sh/setup-uv@v1
      - name: Install dependencies
        run: uv sync
      - name: Run tests
        run: uv run pytest --cov=app --cov-report=xml
      - name: Upload coverage
        uses: codecov/codecov-action@v3
```

### Pre-commit Hooks

```bash
# Install pre-commit
uv add --dev pre-commit

# Add to .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest
        name: Run tests
        entry: uv run pytest
        language: system
        pass_filenames: false
```

This testing guide ensures comprehensive coverage of the Retailer App functionality, from unit tests to full supply chain integration scenarios.