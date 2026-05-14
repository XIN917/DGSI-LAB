# DGSI Retailer App

A downstream retailer simulator for the DGSI supply chain. The Retailer App purchases finished printers from the Manufacturer, manages finished goods inventory, fulfills customer demand, enforces retail pricing rules, and advances simulation days in sync with the central turn engine.

## Features

- REST API and Typer CLI for all core operations
- Customer order intake, fulfillment, and backorder handling
- Purchase order placement to Manufacturer via REST
- Retail pricing management with enforced minimum profit margins
- Local SQLite persistence and event logging for auditability
- Standard simulation endpoints: `/api/day/current` and `/api/day/advance`

## Getting Started

### Prerequisites
- Python 3.11+

### Installation

Choose your preferred environment manager:

#### Option A: Using uv (Recommended)
```bash
cd retailer
uv sync
# Use 'uv run' for all subsequent commands
```

#### Option B: Using standard venv
```bash
cd retailer
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
pip install -e .
```

### Running the Application

Once installed (via `pip install -e .` or `uv sync`), you can run the commands. 
*Note: Prefix with `uv run` if using Option A without an active venv.*

1. **Initialize the database**:
   ```bash
   retailer-cli init
   ```

2. **Start the API**:
   ```bash
   uvicorn app.main:app --reload --port 8003
   ```

API docs will be available at `http://localhost:8003/docs`.

### CLI Commands

Use the `retailer-cli` command to interact with the simulation:

```bash
# Show product catalog & current inventory
retailer-cli catalog
retailer-cli inventory

# Manage Customer Orders
retailer-cli customer-orders list
retailer-cli customer-orders create --sku P3D-Classic --quantity 2

# Manage Simulation Day
retailer-cli day-current
retailer-cli day-advance

# Update Retail Pricing (Enforces 15% markup)
retailer-cli pricing P3D-Classic 1600.0
```

For more detailed testing scenarios, see [docs/TESTING.md](docs/TESTING.md).
