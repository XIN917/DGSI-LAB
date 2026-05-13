# 3D Printer Factory Simulator

A discrete-event simulation system that models the day-by-day production cycle of a factory manufacturing 3D printers. The user acts as production planner, making decisions about what to manufacture and what raw materials to purchase, balancing demand, inventory levels, production capacity, and supplier lead times.

## Quick Start

### Prerequisites

- Python 3.11+
- pip

### Installation

```bash
# Install dependencies
pip install -r requirements.txt

# Seed the database with initial data
python app/utils/seed_data.py

# Run the API server
python run_api.py

# In another terminal, run the UI
python run_ui.py
```

### Access

- **API**: http://localhost:8000
- **Swagger Docs**: http://localhost:8000/docs
- **UI**: http://localhost:8501

## Project Structure

```
printer-factory-sim/
├── app/
│   ├── main.py           # FastAPI application
│   ├── config.py         # Configuration settings
│   ├── db.py             # Database configuration
│   ├── models/           # SQLAlchemy models (9 entities)
│   ├── schemas/          # Pydantic schemas
│   ├── api/              # API route handlers
│   ├── services/         # Business logic (4 managers + engines)
│   ├── simulation/       # SimPy simulation code
│   └── utils/            # Utilities
├── ui/                   # Streamlit dashboard
│   ├── dashboard.py      # Main dashboard
│   └── components/       # Chart components
├── config/               # Configuration files
├── data/                 # SQLite database
├── exports/              # JSON exports
├── tests/                # Unit tests
├── docs/                 # Documentation
├── run_api.py            # API launcher
└── run_ui.py             # UI launcher
```

## Features

### Core Simulation
- **Demand Generation**: Random customer orders with configurable parameters
- **Production Management**: Capacity-constrained production with FIFO queue processing
- **Inventory Tracking**: Real-time stock levels with shortage detection
- **Purchasing System**: Supplier management with lead time tracking

### Business Logic
- **BOM-based Material Consumption**: Orders consume materials based on Bill of Materials
- **Capacity Planning**: Per-model daily capacity enforcement
- **Shortage Detection**: Alerts when materials run low relative to pending demand
- **Event Logging**: Complete audit trail of all simulation events

### Dashboard UI
- Real-time order management with release/cancel actions
- Inventory visualization with shortage warnings
- Purchasing interface with cost estimation
- Production statistics and capacity overview
- Interactive charts for inventory, events, and production

## API Endpoints

See [Swagger Documentation](http://localhost:8000/docs) for full API reference.

### Key Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/models` | List printer models |
| `GET /api/orders` | List manufacturing orders |
| `PUT /api/orders/{id}/release` | Release order to production |
| `GET /api/inventory` | Current inventory levels |
| `POST /api/purchase-orders` | Create purchase order |
| `GET /api/simulation/advance` | Advance simulation day |
| `GET /api/simulation/production-stats` | Production statistics |
| `GET /api/simulation/shortages` | Material shortages |

## Data Model

| Entity | Purpose |
|--------|---------|
| PrinterModel | 3D printer models with capacity settings |
| BOMItem | Materials required per printer model |
| MaterialType | Raw material definitions |
| Supplier | Suppliers with lead times |
| SupplierProduct | Products offered by suppliers |
| ManufacturingOrder | Production orders with status tracking |
| PurchaseOrder | Purchase orders with delivery tracking |
| InventoryLog | Current stock levels |
| EventLog | Historical event records |

## Configuration

Edit `config/default_config.yaml` to customize:

- Simulation duration and warehouse capacity
- Demand generation parameters (mean orders, quantities)
- Production defaults (assembly time, capacity)
- Initial seed data (models, materials, suppliers, inventory)

## Development

### Running Tests

```bash
pytest
```

### Documentation

- [PRD](docs/PRD.md) - Product Requirements Document
- [CLAUDE.md](CLAUDE.md) - Project status and implementation notes

## Status

**Current Milestone**: ✅ Milestone 4 - Dashboard UI (Complete)

**Next**: Milestone 5 - Polish & Export (JSON import/export, integration tests)

## License

MIT
