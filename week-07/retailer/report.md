### DGSI Week 7: Retailer App Report

**Author:** David Morais, Zixin Zhang, Zhipeng Lin and Zhehan Xiang

**Date:** May 14, 2026

**Subject:** Week 7 Challenge — Retailer Service and Integration Testing

---

#### 1. Objectives

This week focused on building the new `Retailer` service as a REST-capable application and validating its integration readiness through automated tests.

Key goals:

* Scaffold the retailer app with FastAPI endpoints, Typer CLI, SQLAlchemy async database support, and a manufacturer REST client.
* Implement support for customer orders, purchase orders, inventory tracking, and day advancement.
* Build test infrastructure for both sync and async SQLAlchemy flows.
* Validate business logic with retailer service tests.

---

#### 2. Architecture and Implementation

The retailer service was built with the following design:

* **FastAPI app** in `app/main.py` exposing retailer APIs.
* **Typer CLI** in `app/cli.py` for catalog inspection and order creation.
* **Async SQLAlchemy** models and session management in `app/models/database.py` and `app/core/database.py`.
* **Configuration** using `pydantic-settings` in `app/core/config.py`.
* **Manufacturer client** in `app/services/manufacturer_client.py` for REST integration.
* **Business logic** in `app/services/retailer_service.py` using injected async sessions.

The retailer service maintains its own database and progresses simulation time independently, while retaining the ability to query manufacturer data via HTTP.

---

#### 3. Testing Strategy

Tests were implemented in `retailer/tests/` with a focus on service-level validation and database correctness.

Important elements:

* `tests/conftest.py` creates a temporary SQLite file database and shared async session factory.
* Service tests exercise retailer day advancement, order creation, inventory fulfillment, and backordering logic.
* The tests validate that the `RetailerService` correctly updates simulation state and order behavior.

---

#### 4. Integration Scenario and Terminal Workflow

The retailer app is designed to interact with the manufacturer app through REST-based purchase orders and status polling.

The live command sequence was run from the local project virtual environments, not the global shell Python.

The retailer database was initialized first:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py init
```

Output:

```bash
✅ Database initialized successfully
```

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py catalog
```

Output:

```bash
Available Products:
  P3D-Classic: Classic 3D Printer - $1500.0
  P3D-Pro: Professional 3D Printer - $2500.0
```

Inventory is available through the CLI and backed by the local SQLite database:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py inventory
```

Output:

```bash
Inventory:
  P3D-Classic: on hand 3, reserved 2, retail $1500.0
  P3D-Pro: on hand 3, reserved 0, retail $2500.0
```

The retailer day command now runs against initialized simulation state:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py day-current
```

Output:

```bash
Current simulated day: 5
```

Customer orders can be listed from the local retailer database:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py customer-orders list
```

Output:

```bash
Customer Orders:
  ID 1: 2 x P3D-Classic - Status: fulfilled - $1500.0
```

With the manufacturer API running on `127.0.0.1:8002`, the retailer client authenticates with the manufacturer and creates a purchase order:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py purchase-orders create --sku P3D-Pro --quantity 1
```

Output:

```bash
Created purchase order ID 1 with manufacturer order 2: 1 x P3D-Pro (pending)
```

The retailer also persists the local purchase order record:

```bash
cd retailer
PYTHONPATH=. .venv/bin/python app/cli.py purchase-orders list
```

Output:

```bash
Purchase Orders:
  ID 1: 1 x P3D-Pro - Manufacturer ID: 2 - Status: pending
```

---

#### 5. Test Outputs

The latest full retailer test run produced the following results:

Command:

```bash
cd retailer && PYTHONPATH=. uv run pytest -q
```

Results:

* `10 passed`
* Warnings:
  * `uv` reports that `tool.uv.dev-dependencies` is deprecated in `pyproject.toml`.

This confirms the retailer service and API endpoint tests are functioning correctly for the current test coverage, including day control and catalog/inventory endpoints.

---

#### 6. Notes and Next Steps

* The previous live issues were fixed: CLI/API startup initializes the retailer database, and the manufacturer client now logs in before calling protected manufacturer endpoints.
* Purchase order creation now stores the retailer-side PO record after the manufacturer accepts the order.
* Additional integration tests should mock or launch the manufacturer API to verify authenticated purchase orders automatically in CI.
