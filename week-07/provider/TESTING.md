# CLI Testing Guide

This guide provides a step-by-step walkthrough for testing all CLI commands for both the **Manufacturer** and **Provider** applications.

## 0. Reset & Setup

To start from a clean state, run the following commands:

```bash
# Delete existing databases and re-seed
rm manufacturer/app/data/simulation.db provider/app/data/provider.db
manufacturer/manufacturer-cli seed
provider/provider-cli seed
```

### Start Servers
Open two terminal windows (or run in background) to start the REST APIs:

**Terminal 1 (Provider)**
```bash
provider/provider-cli serve
```

**Terminal 2 (Manufacturer)**
```bash
manufacturer/manufacturer-cli serve
```

---

## 1. Provider CLI Commands

The Provider manages inventory and sales to manufacturers.

### Check Initial State
```bash
# View current simulation day
provider/provider-cli day current

# View current stock levels
provider/provider-cli stock

# View product catalog and pricing
provider/provider-cli catalog
```

### Manage Pricing & Stock
```bash
# Add a new pricing tier (Product 1, Min Qty 100, Price 25.0)
provider/provider-cli price set 1 100 25.0

# Verify catalog change
provider/provider-cli catalog

# Manually restock a product (Add 50 to Product 1)
provider/provider-cli restock 1 50

# Verify stock increase
provider/provider-cli stock
```

### Advance Time
```bash
# Advance one day
provider/provider-cli day advance
```

---

## 2. Manufacturer CLI Commands

The Manufacturer manages production and purchases from external suppliers.

### Check Initial State
```bash
# View current simulation day
manufacturer/manufacturer-cli day current

# List configured external suppliers
manufacturer/manufacturer-cli suppliers list
```

### Remote Supplier Interaction
```bash
# Fetch catalog from the Provider (ChipSupply Co)
manufacturer/manufacturer-cli suppliers catalog "ChipSupply Co"
```

### Purchase Management
```bash
# Place a new purchase order (PO)
manufacturer/manufacturer-cli purchase create --supplier "ChipSupply Co" --product "PCB Main Board" --qty 50

# List all purchase orders and check status
manufacturer/manufacturer-cli purchase list
```

---

## 3. End-to-End Integration Scenario

Test the full lifecycle of a purchase order across both applications.

1.  **Day 0 (Manufacturer)**: Place an order.
    ```bash
    manufacturer/manufacturer-cli purchase create --supplier "ChipSupply Co" --product "PCB Main Board" --qty 50
    ```
2.  **Day 0 (Provider)**: Verify order is received.
    ```bash
    provider/provider-cli orders list
    # Note the ID (e.g., ID: 1)
    provider/provider-cli orders show 1
    ```
3.  **Advance Time**: Both apps must advance for the order to progress.
    *   **Day 1**: 
        *   `provider/provider-cli day advance` -> Order becomes `CONFIRMED`.
        *   `manufacturer/manufacturer-cli day advance` -> Syncs status.
    *   **Day 2**: 
        *   `provider/provider-cli day advance`
        *   `manufacturer/manufacturer-cli day advance`
    *   **Day 4 (Delivery)**: 
        *   Advance Provider until status is `DELIVERED`.
        *   Advance Manufacturer. The items will be added to the local inventory.

Verify final inventory in Manufacturer:
```bash
# (Note: Requires checking DB or potentially a dashboard as CLI might not show detailed inventory yet)
# Check manufacturer/manufacturer-cli purchase list to see "delivered" status.
manufacturer/manufacturer-cli purchase list
```
