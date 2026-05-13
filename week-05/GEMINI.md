# Project: 3D Printer Production Simulator

## What This Is
A discrete-event simulation system that models the day-by-day production cycle of a factory manufacturing 3D printers. The user acts as production planner, making decisions about what to manufacture and what raw materials to purchase, balancing demand, inventory levels, production capacity, and supplier lead times.

## Tech Stack
- Python 3.11+
- FastAPI + Pydantic for the REST API
- Streamlit for the dashboard UI
- SQLite for persistence
- SimPy for discrete event simulation
- matplotlib for charts

## Architecture
- **5-layer design**: Presentation (Streamlit) → API (FastAPI) → Business Logic (services/) → Simulation Engine (SimPy) → Data Layer (SQLAlchemy/SQLite)
- **API routes** in `app/api/` separated from **business logic** in `app/services/`
- **Models** defined with SQLAlchemy in `app/models/`
- **Schemas** defined with Pydantic in `app/schemas/`

## Data Model
| Entity | Description |
|--------|-------------|
| PrinterModel | 3D printer models that can be manufactured |
| BOMItem | Materials required per printer model |
| MaterialType | Raw material definitions |
| Supplier | Suppliers offering materials |
| SupplierProduct | Products offered by each supplier |
| ManufacturingOrder | Production orders with status tracking |
| PurchaseOrder | Purchase orders with delivery tracking |
| InventoryLog | Current stock levels |
| EventLog | Historical event records |

## Coding Conventions
- Use type hints everywhere
- Pydantic models for all API request/response schemas
- Keep API routes in separate files from business logic
- Write docstrings for public functions
- All configuration via environment variables or config files

## Current State

### ✅ Milestone 1: Foundation - COMPLETED
- [x] Project structure created (`app/`, `ui/`, `tests/`, `config/`, `data/`, `exports/`)
- [x] Dependencies defined (`requirements.txt`)
- [x] Configuration loader (`config/default_config.yaml`)
- [x] Database models implemented (all 9 entities)
- [x] Pydantic schemas for API validation
- [x] CRUD API endpoints:
  - `/api/models` - Printer models & BOMs
  - `/api/orders` - Manufacturing orders
  - `/api/inventory` - Inventory levels
  - `/api/suppliers` - Suppliers & products
  - `/api/purchase-orders` - Purchase orders
  - `/api/events` - Event logs
  - `/api/simulation` - Simulation control (advance, reset, status)
- [x] Seed data script (`app/utils/seed_data.py`)
- [x] Basic Streamlit placeholder (`ui/dashboard.py`)
- [x] Test framework setup (`tests/test_api.py`)
- [x] Documentation (README.md, CLAUDE.md updated)

### ✅ Milestone 2: Simulation Core - COMPLETED
- [x] SimPy environment setup (`app/simulation/environment.py`)
- [x] Demand generator with configurable parameters (`app/services/demand_generator.py`)
  - Poisson-like order generation around configurable mean
  - Configurable order quantity distribution
  - Automatic order creation when advancing days
- [x] Daily advance cycle processor (`app/services/daily_cycle.py`)
  - Process purchase order deliveries
  - Generate new demand orders
  - Update inventory automatically
- [x] Enhanced event logging (`app/services/event_logger.py`)
  - Order created/released/cancelled
  - Purchase order created/delivered
  - Production started/completed
  - Material consumed
  - Inventory shortage
  - Day advanced/reset
- [x] Simulation control API updated:
  - `POST /api/simulation/advance` - Processes full day cycle
  - `GET /api/simulation/config` - Returns current configuration
  - `POST /api/simulation/reset` - Resets simulation state

**Verified behavior:**
- Orders auto-generated on day advance (random quantities based on config)
- Purchase deliveries arrive on expected day and update inventory
- All events logged with timestamps and details
- 6 passing tests

### ✅ Milestone 3: Production & Purchasing - COMPLETED
- [x] **Order Manager** (`app/services/order_manager.py`)
  - Calculate BOM-based material requirements for orders
  - Check material availability before release
  - Release orders with automatic material consumption
  - Shortage detection for pending/released orders
  - Order lifecycle management (PENDING → RELEASED → COMPLETED)

- [x] **Production Engine** (`app/services/production_engine.py`)
  - Track production capacity per printer model
  - Process completed orders based on available capacity
  - FIFO queue processing for released orders
  - Production statistics and queue tracking

- [x] **Inventory Manager** (`app/services/inventory_manager.py`)
  - Stock level tracking and updates
  - Material receive from PO deliveries
  - Low stock alerts based on future requirements
  - Warehouse capacity utilization monitoring
  - Shortage detection for pending orders

- [x] **Purchase Manager** (`app/services/purchase_manager.py`)
  - Create purchase orders with supplier validation
  - Lead time calculation based on supplier settings
  - Minimum order quantity enforcement
  - Cost estimation for potential orders
  - PO cancellation workflow

- [x] Updated API endpoints:
  - `PUT /api/orders/{id}/release` - Release with material check and consumption
  - `GET /api/orders/{id}/check-release` - Pre-flight check for order release
  - `GET /api/simulation/production-stats` - Production capacity and queue stats
  - `GET /api/simulation/shortages` - Current material shortages
  - `GET /api/simulation/low-stock-alerts` - Future shortage warnings
  - `GET /api/purchase-orders/suppliers` - List all suppliers
  - `GET /api/purchase-orders/suppliers/{id}/products` - Available products
  - `POST /api/purchase-orders/estimate-cost` - Cost estimation

- [x] Integrated production into daily cycle:
  - Deliveries processed first
  - New demand generated
  - Production completed based on capacity
  - Shortages detected and logged

**Verified behavior:**
- Order release validates materials and consumes inventory
- Production completes orders respecting capacity limits
- Shortages detected when attempting to release orders
- Low stock alerts generated based on future requirements
- All services import correctly

### ✅ Milestone 4: Dashboard UI - COMPLETED
- [x] Header with day display and simulation controls (Advance Day, Reset)
- [x] Orders panel showing pending/released/completed orders with BOM breakdown
- [x] Release order button with material shortage validation
- [x] Inventory panel displaying current stock levels per material
- [x] Shortage warnings with detailed shortfall amounts
- [x] Purchasing panel with supplier/material selection dropdowns
- [x] Purchase order creation with cost estimation and lead time calculation
- [x] Production panel showing pending/released/completed counts
- [x] Daily capacity display per printer model
- [x] Inventory levels bar chart
- [x] Shortage visualization chart
- [x] Event timeline scatter plot
- [x] Production summary by model chart

**New files:**
- `ui/dashboard.py` - Main Streamlit dashboard with all panels
- `ui/components/charts.py` - Chart rendering components

**API integration:**
- All panels connected to backend API endpoints
- Real-time data refresh on actions
- Error handling for API failures

### 📋 Next: Milestone 5 - Polish & Export
- [ ] JSON export/import functionality
- [ ] Event log viewing interface (dedicated page)
- [ ] Edge case handling (over-commitment, capacity overflow)
- [ ] Integration tests
- [ ] Documentation updates
- [ ] Sample scenario walkthrough
