# Provider App - Parts Supplier for 3D Printer Manufacturing

A FastAPI-based provider app that supplies components to the manufacturer. This service operates independently on port 8001 and manages its own inventory, pricing, and orders.

## Installation & Setup

It is recommended to use a virtual environment, similar to the manufacturer app.

### 1. Create and Activate Virtual Environment

```bash
cd provider
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Install core dependencies
pip install -r requirements.txt

# Install the package in editable mode to enable the 'provider-cli' command
pip install -e .
```

### 3. Initialize Database

The provider requires a seeded database to function correctly.

```bash
# Initialize and seed the provider.db
PYTHONPATH=. python -m provider.app.seed
```

## Running the Application

### Start the API Server

You can start the server using the CLI:

```bash
provider-cli serve --port 8001
```

If the package is not installed as an editable local package, you can run the CLI module directly:

```bash
PYTHONPATH=. python -m provider.app.cli serve --port 8001
```

Or directly via uvicorn:

```bash
PYTHONPATH=. uvicorn provider.app.main:app --host 0.0.0.0 --port 8001
```

The API documentation will be available at `http://localhost:8001/docs`.

## CLI Usage

The `provider-cli` command is the primary way to interact with the provider's internal state.

| Category | Command | Description |
|----------|---------|-------------|
| **Server** | `provider-cli serve` | Start the REST API server |
| **Catalog** | `provider-cli catalog list` | List all products with pricing tiers |
| **Stock** | `provider-cli stock` | Show current inventory levels |
| **Orders** | `provider-cli orders list` | List all orders (filter with `--status`) |
| | `provider-cli orders show <id>` | Show detailed order information |
| **Sim** | `provider-cli day current` | Show current simulation day |
| | `provider-cli day advance` | Advance simulation by one day |
| **Admin** | `provider-cli restock <id> <qty>` | Manually add stock to a product |
| | `provider-cli export` | Export database state to JSON |
| | `provider-cli import <file>` | Import database state from JSON |

## API Endpoints

The provider exposes a REST API for the manufacturer to consume:

- `GET /api/catalog` - Get product list and quantity-based pricing
- `GET /api/stock` - Check real-time inventory
- `POST /api/orders` - Place a new purchase order
- `GET /api/orders/{id}` - Track order status (pending, confirmed, shipped, delivered)
- `GET /api/day/current` - Get current simulation day
- `POST /api/day/advance` - Advance the provider simulation state

## Data Model

- **Products**: 11 core 3D printer components (frame kits, PCBs, motors, etc.)
- **Pricing**: Tiered pricing based on order quantity.
- **Lead Time**: Each product has a fixed lead time (in days) before delivery.
- **Order Lifecycle**: `pending` → `confirmed` → `shipped` → `delivered`.

## Configuration

- **Default Port**: 8001
- **Database**: `provider.db` (SQLite)
- **Environment Variables**: Can be configured in a `.env` file (see `provider/app/core/config.py` for options if implemented).
