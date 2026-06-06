# CLI Testing Guide

This guide provides a step-by-step walkthrough for testing all CLI commands for both the **Manufacturer** and **Provider** applications.

## 0. Reset & Setup

To start from a clean state, use the reset script from the repo root:

```bash
./scripts/reset_all.sh
```

Or manually re-seed:

```bash
provider/venv/bin/provider-cli seed
manufacturer/venv/bin/manufacturer-cli seed
```

### Start Servers

Use the start script from the repo root:

```bash
./scripts/start_all.sh
```

Or individually:

**Terminal 1 (Provider)**
```bash
provider/venv/bin/provider-cli serve --port 8001
```

**Terminal 2 (Manufacturer)**
```bash
manufacturer/venv/bin/manufacturer-cli serve --port 8002
```

---

## 1. Provider CLI Commands

The Provider manages inventory and sales to manufacturers.

### Check Initial State
```bash
# View current simulation day
provider/venv/bin/provider-cli day current

# View current stock levels
provider/venv/bin/provider-cli stock

# View product catalog and pricing
provider/venv/bin/provider-cli catalog
```

### Manage Pricing & Stock
```bash
# Add a new pricing tier (Product 1, Min Qty 100, Price 25.0)
provider/venv/bin/provider-cli price set 1 100 25.0

# Verify catalog change
provider/venv/bin/provider-cli catalog

# Manually restock a product (Add 50 to Product 1)
provider/venv/bin/provider-cli restock 1 50

# Verify stock increase
provider/venv/bin/provider-cli stock
```

### Note on Day Advance
**Never call `day advance` directly** — the turn engine does that via `POST /api/day/advance`. Use `turn_engine.py` or the dashboard to advance days during a simulation.

---

## 2. Manufacturer CLI Commands

The Manufacturer manages production and purchases from external suppliers.

### Check Initial State
```bash
# View current simulation day
manufacturer/venv/bin/manufacturer-cli day current

# List configured external suppliers
manufacturer/venv/bin/manufacturer-cli suppliers list
```

### Remote Supplier Interaction
```bash
# Fetch catalog from the Provider (ChipSupply Co)
manufacturer/venv/bin/manufacturer-cli suppliers catalog "ChipSupply Co"
```

### Purchase Management
```bash
# Place a new purchase order (PO)
manufacturer/venv/bin/manufacturer-cli purchase create --supplier "ChipSupply Co" --product "PCB Main Board" --qty 50

# List all purchase orders and check status
manufacturer/venv/bin/manufacturer-cli purchase list
```

---

## 3. End-to-End Integration Scenario

Test the full lifecycle of a purchase order across both applications.

1.  **Day 0 (Manufacturer)**: Place an order.
    ```bash
    manufacturer/venv/bin/manufacturer-cli purchase create --supplier "ChipSupply Co" --product "PCB Main Board" --qty 50
    ```
2.  **Day 0 (Provider)**: Verify order is received.
    ```bash
    provider/venv/bin/provider-cli orders list
    # Note the ID (e.g., ID: 1)
    provider/venv/bin/provider-cli orders show 1
    ```
3.  **Advance Time**: Use `turn_engine.py` or `POST /api/day/advance` on each service — never call `day advance` via the CLI directly. After a few days the provider order status progresses `CONFIRMED` → `SHIPPED` → `DELIVERED` and the manufacturer inventory updates accordingly.

Verify final inventory in Manufacturer:
```bash
# (Note: Requires checking DB or potentially a dashboard as CLI might not show detailed inventory yet)
# Check manufacturer/venv/bin/manufacturer-cli purchase list to see "delivered" status.
manufacturer/venv/bin/manufacturer-cli purchase list
```
