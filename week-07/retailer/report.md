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
* **New**: Implement mandatory business rules including 15% minimum markup enforcement and backorder auto-fulfillment.
* **New**: Streamline developer workflow with a dedicated `retailer-cli` entry point and support for both `uv` and standard `venv`.

---

#### 2. Architecture and Implementation

The retailer service was built with the following design:

* **FastAPI app** in `app/main.py` exposing retailer APIs.
* **Streamlined CLI** in `app/cli.py` providing a global `retailer-cli` command.
* **Async SQLAlchemy** models and session management in `app/models/database.py` and `app/core/database.py`.
* **Manufacturer client** in `app/services/manufacturer_client.py` for REST integration and PO synchronization.
* **Advanced Business Logic** in `app/services/retailer_service.py`:
    * **Backorder Management**: Automated fulfillment of pending orders during day advancement when stock is received.
    * **Pricing Enforcement**: Validation logic that rejects retail prices failing to meet a 15% markup over wholesale.
    * **PO Reconciliation**: Automated status updates for pending manufacturer orders.

---

#### 3. Testing Strategy

Tests were implemented in `retailer/tests/` with a focus on service-level validation and business rule correctness.

Important elements:

* `tests/conftest.py`: Shared fixtures for temporary SQLite database and async session management.
* `tests/test_services/test_business_logic.py`: **New** tests specifically for pricing enforcement and backorder lifecycle.
* `tests/test_api/test_endpoints.py`: Validation of FastAPI routes for day control, catalog, and order management.

---

#### 4. Integration Scenario and Terminal Workflow

The retailer app is now fully installable, removing the need for `PYTHONPATH` hacks. The database is initialized via the CLI:

```bash
retailer-cli init
```

Output:
```bash
✅ Database initialized successfully
```

Product catalog and inventory are synced with the Manufacturer:

```bash
retailer-cli catalog
```

Output:
```bash
Available Products:
  P3D-Classic: Classic 3D Printer - $1500.0
  P3D-Pro: Professional 3D Printer - $2500.0
```

Retail pricing enforcement prevents setting invalid margins:

```bash
retailer-cli pricing P3D-Classic 1300.0
```

Output:
```bash
❌ Error: Price $1300.0 is below the minimum 15% markup over wholesale ($1200.0)
```

Simulation time and state transitions:

```bash
retailer-cli day-current
# Output: Current simulated day: 5

retailer-cli day-advance
# Output: Advanced to day 6 (Auto-fulfilled 2 backorders)
```

---

#### 5. Test Outputs

The latest full retailer test run confirms all core and business logic passes:

Command:
```bash
pytest tests/
```

Results:
```text
tests/test_api/test_endpoints.py ....                                    [ 33%]
tests/test_services/test_business_logic.py ..                            [ 50%]
tests/test_services/test_retailer_service.py ......                      [100%]

========================== 12 passed in 0.23s ===========================
```

---

#### 6. Notes and Final Status

* **Status**: Completed. All "Must Have" requirements from the PRD (including backorders and pricing) are implemented and tested.
* **Developer Experience**: The app now supports both `uv sync` and standard `pip install -e .` workflows.
* **Integration**: The `ManufacturerClient` is ready for full supply chain integration, featuring automatic token management and PO synchronization.
