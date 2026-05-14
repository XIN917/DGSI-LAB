# DGSI Retailer App

A downstream retailer simulator for the DGSI supply chain. The Retailer App purchases finished printers from the Manufacturer, manages finished goods inventory, fulfills customer demand, enforces retail pricing rules, and advances simulation days in sync with the central turn engine.

## Features

- REST API and Typer CLI for all core operations
- Customer order intake, fulfillment, and backorder handling
- Purchase order placement to Manufacturer via REST
- Retail pricing management with enforced minimum profit margins
- Local SQLite persistence and event logging for auditability
- JSON import/export of full application state
- Standard simulation endpoints: `/api/day/current` and `/api/day/advance`

## Getting Started

### Prerequisites
- Python 3.11+

### Installation

1. **Navigate to the retailer directory**:
   ```bash
   cd retailer
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

### Running the Application

1. **Start the API**:
   ```bash
   PYTHONPATH=. uv run uvicorn app.main:app --reload --port 8003
   ```

API docs will be available at `http://localhost:8003/docs`.

### CLI Commands

```bash
# Show product catalog
PYTHONPATH=. uv run python app/cli.py catalog

# List customer orders
PYTHONPATH=. uv run python app/cli.py customer-orders list

# Create customer order
PYTHONPATH=. uv run python app/cli.py customer-orders create P3D-Classic 2

# Show current day
PYTHONPATH=. uv run python app/cli.py day current

# Advance to next day
PYTHONPATH=. uv run python app/cli.py day advance
```
