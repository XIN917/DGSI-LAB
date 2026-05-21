# DGSI Week 7: Terminal CLI Testing Guide

This guide provides a comprehensive walkthrough for testing the full supply chain integration: **Provider ↔ Manufacturer ↔ Retailer**.

---

## 🚀 Option 1: Automated Testing (Fastest)

We provide scripts to handle the boilerplate of starting servers and running the core scenario.

### 1. Start the Servers
This script launches all three services in the background and logs output to `.log` files.
```bash
./scripts/start_all.sh
```

### 2. Monitor Logs (Optional)
Open separate terminals to watch the activity:
- **Provider:** `tail -f logs/provider.log`
- **Manufacturer:** `tail -f logs/manufacturer.log`
- **Retailer:** `tail -f logs/retailer.log`

### 3. Run the Scenario
This script seeds databases, places orders, releases production, and advances time.
```bash
./scripts/test_scenario.sh
```

---

## 🛠 Option 2: Manual Testing

### 1. Environment Setup

Open **three** separate terminal windows to run the servers. Ensure you are in the project root (`week-07/`).

#### Terminal 1: Provider (Port 8001)
```bash
cd provider && source venv/bin/activate && provider-cli serve --port 8001
```

#### Terminal 2: Manufacturer (Port 8002)
```bash
cd manufacturer && source venv/bin/activate && manufacturer-cli serve --port 8002
```

#### Terminal 3: Retailer (Port 8003)
```bash
cd retailer && source venv/bin/activate && retailer-cli serve --port 8003
```

---

### 2. Initialization & Seed Data

In a **fourth terminal**, initialize all databases.

```bash
# 1. Initialize Provider (Parts Supplier)
./provider/venv/bin/provider-cli seed

# 2. Initialize Manufacturer (Factory)
./manufacturer/venv/bin/manufacturer-cli seed

# 3. Initialize Retailer (Store)
./retailer/venv/bin/retailer-cli init
```

---

### 3. Core Testing Scenario: The Full Lifecycle

Follow these steps in order using the **Fourth Terminal**.

#### Step A: Retailer Activity (Customer Demand)
1. **Check starting inventory:**
   ```bash
   ./retailer/venv/bin/retailer-cli inventory
   ```
2. **Create a Customer Order (causes a backorder):**
   ```bash
   ./retailer/venv/bin/retailer-cli customer-orders create --sku P3D-Classic --quantity 10
   ```
3. **Place a Purchase Order to Manufacturer:**
   ```bash
   ./retailer/venv/bin/retailer-cli purchase-orders create --sku P3D-Classic --quantity 10
   ```

#### Step B: Manufacturer Activity (Production)
1. **Check incoming Sales Orders:**
   ```bash
   ./manufacturer/venv/bin/manufacturer-cli sales orders
   ```
2. **Release order to production:**
   (Replace `<ID>` with the ID found in Step 1, e.g., `0001`)
   ```bash
   ./manufacturer/venv/bin/manufacturer-cli production release <ID>
   ```

#### Step C: Advance Time (Processing)
To "finish" the production and deliver the goods, advance the simulation in all three apps.

1. **Advance Provider:** `./provider/venv/bin/provider-cli day advance`
2. **Advance Manufacturer:** `./manufacturer/venv/bin/manufacturer-cli day advance`
3. **Advance Retailer:** `./retailer/venv/bin/retailer-cli day advance`

**Verification:**
- Run `./manufacturer/venv/bin/manufacturer-cli sales orders`. The order should now be `delivered`.
- Run `./retailer/venv/bin/retailer-cli inventory`. Stock should show 10 units `reserved` for the customer.

---

## 4. Testing Week 7 Special Features

### Scenario: Wholesale Price Adjustment
1. **Manufacturer sets a new price:**
   ```bash
   ./manufacturer/venv/bin/manufacturer-cli price set P3D-Classic 1500.00
   ```
2. **Retailer verifies the new catalog price:**
   ```bash
   ./retailer/venv/bin/retailer-cli catalog
   ```
3. **Retailer attempts to set a price below 15% markup:**
   ```bash
   ./retailer/venv/bin/retailer-cli pricing P3D-Classic 1600.00
   ```
   *Expected: ❌ Error. Minimum markup requires at least $1725 (1500 * 1.15).*

---

## 5. Summary of Key Verification Commands

| Command | Purpose |
| :--- | :--- |
| `retailer-cli catalog` | Check retailer prices and manufacturer wholesale prices. |
| `retailer-cli inventory` | Check retailer stock levels and reserved units. |
| `manufacturer-cli stock` | View factory inventory (raw materials + finished printers). |
| `manufacturer-cli sales orders` | View orders received from the retailer. |
| `manufacturer-cli price list` | View current wholesale prices set by the factory. |

---

## 6. Troubleshooting

- **"Address already in use" (Errno 48):** Stop all server processes with:
  ```bash
  pkill -f "cli serve"
  ```
- **"No such command 'production'":** Ensure you have updated the code in `manufacturer/app/cli.py` to include the `production` group.
- **"ModuleNotFoundError":** Ensure you are running commands using the venv path: `./[app]/venv/bin/[app]-cli`.
- **Database Mismatch:** If you see `no such column`, delete the `.db` file in the app's `data/` folder and re-run `seed` or `init`.
