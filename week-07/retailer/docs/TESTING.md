# Retailer App Testing Guide

This guide provides comprehensive testing strategies for the Retailer App, including unit tests, integration tests, CLI testing, and end-to-end supply chain scenarios.

## Table of Contents

1. [Testing Overview](#1-testing-overview)
2. [Setup & Prerequisites](#2-setup--prerequisites)
3. [Running Tests](#3-running-tests)
4. [CLI Testing Guide](#4-cli-testing-guide)
5. [End-to-End Supply Chain Testing](#5-end-to-end-supply-chain-testing)
6. [Troubleshooting](#6-troubleshooting)

---

## 1. Testing Overview

- **Unit Tests**: Business logic and pricing rules (`tests/test_services/`).
- **Integration Tests**: API endpoints and DB state (`tests/test_api/`).
- **CLI Tests**: Manual verification of `retailer-cli`.

---

## 2. Setup & Prerequisites

Choose your preferred environment manager:

### Option A: Using `uv` (Recommended)
```bash
cd retailer
uv sync
uv run retailer-cli init
```
*Note: When using `uv`, you should prefix execution commands with `uv run` unless you manually activate the environment via `source .venv/bin/activate`.*

### Option B: Using standard `venv`
```bash
cd retailer
python3 -m venv venv
source venv/bin/activate
pip install -e .
retailer-cli init
```

---

## 3. Running Tests

### If using `uv`:
```bash
# Run all tests
uv run pytest tests/

# Run specific business logic tests
uv run pytest tests/test_services/test_business_logic.py
```

### If using `venv`:
```bash
# Ensure environment is active: source venv/bin/activate
pytest tests/
```

---

## 4. CLI Testing Guide

To test the CLI while the API is running, use two terminal tabs.

### Terminal 1: Start the API
*   **uv**: `uv run uvicorn app.main:app --reload --port 8003`
*   **venv**: `uvicorn app.main:app --reload --port 8003`

### Terminal 2: Run CLI Commands
*   **uv**: `uv run retailer-cli <command>`
*   **venv**: `retailer-cli <command>`

#### Common Commands:
```bash
# Display catalog & inventory
retailer-cli catalog
retailer-cli inventory

# Customer Orders
retailer-cli customer-orders list
retailer-cli customer-orders create --sku P3D-Classic --quantity 2

# Purchase Orders & Simulation
retailer-cli purchase-orders list
retailer-cli day-advance
retailer-cli pricing P3D-Classic 1600.0
```

---

## 5. End-to-End Supply Chain Testing

### Setup All Three Apps

| App | Terminal Command (uv) | Default Port |
|-----|-----------------------|--------------|
| **Provider** | `uv run provider-cli serve` | 8001 |
| **Manufacturer** | `uv run uvicorn app.main:app --port 8002` | 8002 |
| **Retailer** | `uv run uvicorn app.main:app --port 8003` | 8003 |

#### Scenario: Order to Delivery
1.  **Retailer**: Place PO (`retailer-cli purchase-orders create ...`)
2.  **Simulation**: Advance days in all apps (`retailer-cli day-advance`)
3.  **Retailer**: Check inventory (`retailer-cli inventory`) to see arrival of goods.
4.  **Retailer**: Customer orders now fulfill automatically from new stock.

---

## 6. Troubleshooting

### Command not found: `retailer-cli`
- **uv**: Run `uv sync` to register the script. Use `uv run retailer-cli`.
- **venv**: Run `pip install -e .` and ensure `source venv/bin/activate` is run in the current terminal.

### Database Errors
Reset the database:
```bash
rm retailer.db
retailer-cli init  # (Add uv run if using uv)
```
