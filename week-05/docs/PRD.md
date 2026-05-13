# Product Requirements Document: 3D Printer Production Simulator

## Overview

### Purpose
Build a discrete-event simulation system that models the day-by-day production cycle of a factory manufacturing 3D printers. The user acts as production planner, making decisions about what to manufacture and what raw materials to purchase, balancing demand, inventory levels, production capacity, and supplier lead times.

### Target User
Operations managers, supply chain students, and anyone interested in understanding production planning dynamics through interactive simulation.

### Key Value Proposition
- Hands-on learning tool for supply chain management concepts
- Visualizes the tension between demand, inventory, capacity, and lead times
- Provides immediate feedback on planning decisions

---

## Tech Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| Language | Python 3.11+ | Modern syntax, excellent ecosystem for simulation & data |
| Simulation Engine | SimPy | Discrete-event simulation, well-established, easy to extend |
| REST API | FastAPI + Pydantic | Auto-generated OpenAPI docs, type safety, async support |
| Dashboard UI | Streamlit | Rapid prototyping, matplotlib integration, no frontend required |
| Persistence | SQLite + JSON | Lightweight, portable, SQLite for transactions, JSON for export |
| Charts | matplotlib | Direct Streamlit integration, full customization |
| Version Control | Git + GitHub | Standard workflow, PR reviews, issue tracking |

---

## Data Model

### Core Entities

```
┌─────────────────────┐
│   PrinterModel      │
├─────────────────────┤
│ id: str             │
│ name: str           │
│ assembly_time: int  │  # hours to assemble one unit
│ daily_capacity: int │  # max units producible per day
└─────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│    BOMItem          │
├─────────────────────┤
│ id: str             │
│ printer_model_id: str FK
│ material_type: str  │
│ quantity_per_unit: float
└─────────────────────┘


┌─────────────────────┐
│   MaterialType      │
├─────────────────────┤
│ id: str             │
│ name: str           │
│ unit: str           │  # e.g., "kits", "units", "kg"
└─────────────────────┘
           │
           │ 1:N
           ▼
┌─────────────────────┐
│    Supplier         │
├─────────────────────┤
│ id: str             │
│ name: str           │
│ lead_time_days: int │
└─────────────────────┘
           │
           │ M:N (through SupplierProduct)
           ▼
┌─────────────────────┐
│  SupplierProduct    │
├─────────────────────┤
│ id: str             │
│ supplier_id: str FK │
│ material_type: str  │
│ price_per_unit: float
│ min_order_qty: int  │
│ packaging: str      │  # e.g., "pallet of 1000"
└─────────────────────┘


┌─────────────────────┐
│ ManufacturingOrder  │
├─────────────────────┤
│ id: str             │
│ printer_model_id: str FK
│ quantity: int       │
│ status: Enum        │  # PENDING, RELEASED, PARTIAL, COMPLETED, CANCELLED
│ created_day: int    │
│ released_day: int?  │
│ completed_day: int? │
└─────────────────────┘


┌─────────────────────┐
│   InventoryLog      │
├─────────────────────┤
│ id: str             │
│ material_type: str  │
│ current_quantity: float
│ warehouse_capacity: int │ (shared across all materials)
└─────────────────────┘


┌─────────────────────┐
│   PurchaseOrder     │
├─────────────────────┤
│ id: str             │
│ supplier_id: str FK │
│ material_type: str  │
│ quantity: float     │
│ order_day: int      │
│ expected_arrival: int│
│ actual_arrival: int?│
│ status: Enum        │  # PENDING, DELIVERED, CANCELLED
└─────────────────────┘


┌─────────────────────┐
│       Event         │
├─────────────────────┤
│ id: str             │
│ day: int            │
│ timestamp: float    │  # simulated time within day
│ event_type: str     │  # ORDER_CREATED, ORDER_RELEASED, etc.
│ category: str       │  # DEMAND, PRODUCTION, PURCHASING, INVENTORY
│ description: str    │
│ details: JSON       │  # flexible payload
└─────────────────────┘
```

### Entity Relationships Summary

- **PrinterModel** has many **BOMItem** entries defining required materials
- **MaterialType** can be supplied by multiple **Supplier** entities via **SupplierProduct**
- **ManufacturingOrder** references one **PrinterModel**, tracks production status
- **PurchaseOrder** references one **Supplier**, delivers one **MaterialType**
- **Event** log captures all state changes with historical context

---

## Architecture

### System Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    Presentation Layer                       │
│  ┌─────────────────┐         ┌───────────────────────────┐ │
│  │   Streamlit UI  │ ◄────►  │      REST API Client      │ │
│  └─────────────────┘         └───────────────────────────┘ │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      API Layer                              │
│  ┌─────────────────────────────────────────────────────────┐│
│  │              FastAPI Routes (with Pydantic)             ││
│  │  /api/orders  /api/inventory  /api/purchases  /api/sim ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic Layer                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ OrderManager │  │ ProdEngine   │  │ PurchaseManager  │  │
│  └──────────────┘  └──────────────┘  └──────────────────┘  │
│  ┌──────────────┐  ┌──────────────┐                        │
│  │ InventoryMgr │  │ EventLogger  │                        │
│  └──────────────┘  └──────────────┘                        │
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                    Simulation Engine                        │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   SimPy Environment                     ││
│  │  - DemandGenerator process                              ││
│  │  - ProductionProcess (capacity-limited)                 ││
│  │  - DeliveryProcess (lead-time based)                    ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                           │
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                      Data Layer                             │
│  ┌──────────────┐         ┌──────────────────────────────┐  │
│  │  SQLite DB   │ ◄──────► │   JSON Import/Export       │  │
│  └──────────────┘         └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### File Structure

```
printer-factory-sim/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app entry point
│   ├── config.py               # Configuration & environment vars
│   ├── models/                 # SQLAlchemy/SQLite models
│   │   ├── __init__.py
│   │   ├── base.py
│   │   ├── printer_model.py
│   │   ├── bom.py
│   │   ├── material.py
│   │   ├── supplier.py
│   │   ├── order.py
│   │   ├── inventory.py
│   │   └── event_log.py
│   ├── schemas/                # Pydantic schemas for API
│   │   ├── __init__.py
│   │   ├── orders.py
│   │   ├── inventory.py
│   │   ├── purchases.py
│   │   └── simulation.py
│   ├── services/               # Business logic
│   │   ├── __init__.py
│   │   ├── order_manager.py
│   │   ├── production_engine.py
│   │   ├── purchase_manager.py
│   │   ├── inventory_manager.py
│   │   ├── event_logger.py
│   │   └── demand_generator.py
│   ├── simulation/             # SimPy-specific code
│   │   ├── __init__.py
│   │   ├── environment.py
│   │   ├── processes.py
│   │   └── resources.py
│   ├── api/                    # API route handlers
│   │   ├── __init__.py
│   │   ├── orders.py
│   │   ├── inventory.py
│   │   ├── purchasing.py
│   │   ├── simulation.py
│   │   └── admin.py
│   └── utils/
│       ├── __init__.py
│       ├── json_export.py
│       └── validators.py
├── ui/
│   ├── __init__.py
│   ├── dashboard.py            # Main Streamlit app
│   ├── components/             # Reusable UI components
│   │   ├── order_panel.py
│   │   ├── inventory_panel.py
│   │   ├── purchasing_panel.py
│   │   ├── production_panel.py
│   │   └── charts.py
│   └── pages/                  # Additional Streamlit pages
│       └── logs.py
├── data/
│   └── database.db             # SQLite database (gitignored)
├── exports/                    # JSON export files (gitignored)
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_orders.py
│   ├── test_production.py
│   └── test_purchasing.py
├── config/
│   ├── default_config.yaml     # Default simulation parameters
│   └── initial_data.json       # Seed data for demo
├── requirements.txt
├── run_api.py                  # API server launcher
├── run_ui.py                   # Streamlit launcher
└── README.md
```

---

## API Endpoints

### Base URL: `http://localhost:8000`

#### Simulation Control

| Method | Endpoint | Description | Request/Response |
|--------|----------|-------------|------------------|
| GET | `/api/simulation/status` | Get current day, paused/running state | `{day: int, running: bool}` |
| POST | `/api/simulation/advance` | Advance simulation by one day | `{new_day: int}` |
| POST | `/api/simulation/reset` | Reset simulation to day 0 | `{success: bool}` |

#### Orders (R1, R2, R3)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders` | List all manufacturing orders |
| POST | `/api/orders` | Create manual manufacturing order |
| GET | `/api/orders/{id}` | Get order details with BOM breakdown |
| PUT | `/api/orders/{id}/release` | Release order to production |
| PUT | `/api/orders/{id}/cancel` | Cancel pending order |

#### Inventory (R2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/inventory` | Current stock levels for all materials |
| GET | `/api/inventory/{material}` | Detailed history for specific material |
| GET | `/api/inventory/capacity` | Warehouse capacity info |

#### Purchasing (R3, R4)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/suppliers` | List all suppliers |
| GET | `/api/suppliers/{id}/products` | Products available from supplier |
| POST | `/api/purchase-orders` | Create purchase order |
| GET | `/api/purchase-orders` | List all purchase orders |
| GET | `/api/purchase-orders/{id}` | Get purchase order details |

#### Bill of Materials (R0, R2)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/models` | List all printer models |
| GET | `/api/models/{id}/bom` | Get BOM for specific model |
| GET | `/api/bom/analyze` | Analyze material needs for order |

#### Events & Logs (R6)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | List events (filterable by date/type) |
| GET | `/api/events/timeline` | Timeline view for charts |

#### Import/Export (R7)

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/state` | Export full state as JSON |
| POST | `/api/import/state` | Import state from JSON |
| GET | `/api/export/events` | Export events as JSON |

#### Documentation

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/docs` | Swagger UI documentation |
| GET | `/openapi.json` | Raw OpenAPI spec |

---

## UI Layout (Streamlit)

### Main Dashboard (`ui/dashboard.py`)

```
┌─────────────────────────────────────────────────────────────────┐
│  ╔═══════════════════════════════════════════════════════════╗ │
│ ║         3D PRINTER FACTORY SIMULATOR                         ║ │
│  ╠═══════════════════════════════════════════════════════════╣ │
│  ║  📅 Simulated Day: [Day 5]                                 ║ │
│  ║  ⏹️ Status: Running  [Advance Day ▶]  [Reset ↻]           ║ │
│  ╚═══════════════════════════════════════════════════════════╝ │
├──────────────────────┬──────────────────────┬──────────────────┤
│ 📋 ORDERS PANEL      │ 💾 INVENTORY PANEL   │ 🛒 PURCHASING    │
│                      │                      │                  │
│ Pending Orders: 3    │ Material      Stock  │ Supplier: [▼]   │
│ ┌────────────────┐   │ ├──────────────┼────┤  Material: [▼]   │
│ │ Order #101     │   │ │ Filament-RGB │ 45 │                  │
│ │ Model: Pro X1  │   │ │ PrintBed-G1 │ 120│ Quantity: [____] │
│ │ Qty: 8         │   │ │ Nozzle-Cu   │  8 │                  │
│ │ Needs:         │   │ │ Motors-Nema │  5 │ [Issue PO Button]│
│ │  ├─Filament x48│   │ │ PCB-Board   │  3 │                  │
│ │  ├─Motor x8    │   │ └──────────────┴────┘                  │
│ │  └─PCB x8      │   │                                        │
│ │ [Release Order]│   │ ⚠️ Shortages:                          │
│ └────────────────┘   │   • Nozzle-Cu (need 40 for queue)     │
│                      │                                        │
│ ──────────────────── │ ─────────────────────────────────────  │
│                      │                                        │
│ 🏭 PRODUCTION PANEL  │ 📊 CHARTS                              │
│                      │                                        │
│ Daily Capacity: 10/10│ [Stock Levels Over Time]              │
│ In Progress: 3       │ [Completed Orders History]            │
│ Queue: 12            │                                        │
│ Today Completed: 0   │                                        │
│                      │                                        │
└──────────────────────┴──────────────────────┴──────────────────┘
```

### Pages

- **Dashboard**: Main control panel (above layout)
- **Event Log**: Filterable table of all simulation events
- **Reports**: Aggregate statistics and KPIs

---

## Configuration Parameters (R0)

### `config/default_config.yaml`

```yaml
simulation:
  start_day: 1
  total_days: 90
  warehouse_capacity: 500  # total storage units

demand_generation:
  mean_orders_per_day: 2.0
  variance_orders_per_day: 1.0
  min_order_quantity: 1
  max_order_quantity: 15
  order_quantity_mean: 8
  order_quantity_variance: 4

production:
  default_assembly_time_hours: 4
  default_daily_capacity: 10

supplier_defaults:
  standard_lead_time_days: 3
  min_order_quantity: 10

# Initial seed data (can be modified via import)
printer_models:
  - id: "pro_x1"
    name: "Pro X1"
    assembly_time_hours: 4
    daily_capacity: 10

materials:
  - id: "filament_rgb"
    name: "PLA Filament RGB"
    unit: "spools"
  - id: "printbed_g1"
    name: "Glass Print Bed 200mm"
    unit: "units"
  - id: "nozzle_cu"
    name: "Copper Nozzle"
    unit: "units"
  - id: "motor_nema17"
    name: "NEMA 17 Motor"
    unit: "units"
  - id: "pcb_board"
    name: "Control PCB Board"
    unit: "units"

suppliers:
  - id: "supplier_a"
    name: "Parts Direct"
    lead_time_days: 3
    products:
      - material: "filament_rgb"
        price_per_unit: 90.00
        packaging: "case of 20"
      - material: "nozzle_cu"
        price_per_unit: 15.00
        packaging: "box of 10"

initial_inventory:
  filament_rgb: 30
  printbed_g1: 50
  nozzle_cu: 20
  motor_nema17: 15
  pcb_board: 10
```

---

## Development Plan

### Milestone 1: Foundation (Week 1)
**Goal**: Working API with data models and basic CRUD operations

- [ ] Set up project structure and dependencies
- [ ] Implement data models (SQLAlchemy + SQLite)
- [ ] Create Pydantic schemas for API validation
- [ ] Build CRUD endpoints for:
  - Printer models & BOMs
  - Suppliers & products
  - Inventory management
- [ ] Unit tests for models and schemas

**Deliverable**: API returns initial configuration data, Swagger docs functional

---

### Milestone 2: Simulation Core (Week 2)
**Goal**: Working simulation engine with demand generation

- [ ] Implement SimPy environment setup
- [ ] Build demand generator (random order creation)
- [ ] Create ManufacturingOrder entity and management
- [ ] Implement daily advance cycle
- [ ] Event logging system
- [ ] API endpoints for simulation control

**Deliverable**: Can advance days, orders generated automatically, events logged

---

### Milestone 3: Production & Purchasing (Week 3)
**Goal**: Full production and purchasing workflows

- [ ] Production engine with capacity constraints
- [ ] BOM-based material consumption
- [ ] Purchase order workflow (create → track → deliver)
- [ ] Lead time implementation for deliveries
- [ ] Order status transitions (PENDING → RELEASED → COMPLETED)
- [ ] Shortage detection and handling

**Deliverable**: Complete business logic for all core workflows

---

### Milestone 4: Dashboard UI (Week 4)
**Goal**: Functional Streamlit dashboard

- [ ] Header with day display and controls
- [ ] Orders panel with BOM breakdown
- [ ] Inventory panel with shortage warnings
- [ ] Purchasing panel for placing orders
- [ ] Production panel showing capacity usage
- [ ] Charts for stock levels and completed orders

**Deliverable**: Interactive dashboard matching specified layout

---

### Milestone 5: Polish & Export (Week 5)
**Goal**: Complete all requirements including export/import

- [ ] JSON export/import functionality
- [ ] Event log viewing interface
- [ ] Edge case handling (over-commitment, capacity overflow)
- [ ] Integration tests
- [ ] Documentation updates
- [ ] Sample scenario walkthrough

**Deliverable**: Production-ready system with all R0-R8 requirements

---

## Implementation Phases Summary

| Phase | Duration | Key Deliverables |
|-------|----------|------------------|
| Foundation | Week 1 | Data models, API scaffolding, CRUD |
| Simulation Core | Week 2 | SimPy engine, demand generation, day cycle |
| Production & Purchasing | Week 3 | Full business logic, order workflows |
| Dashboard UI | Week 4 | Complete Streamlit interface |
| Polish & Export | Week 5 | Export/import, testing, documentation |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SimPy complexity | Start with simple discrete day loop, add SimPy processes incrementally |
| State consistency | Use transactions for multi-step operations, implement undo for imports |
| UI performance | Cache chart data, lazy load event history |
| Data migration | Version JSON export schema, provide migration utilities |

---

## Appendix A: Example Scenario Walkthrough

**Day 1:**
- Starting stock: 30 filament spools
- Capacity: 10 printers/day
- Generated orders: 8 units, 6 units
- User releases only the 8-unit order
- Production consumes 8 spools (22 remaining)
- No purchase needed

**Day 2:**
- New orders: 5 units, 7 units
- Stock alert triggered (only 22 spools, need 12 more plus buffer)
- User places PO: 20 spools from Supplier A @ $90/unit, lead time 3 days
- Expected arrival: Day 5

**Day 5:**
- PO arrives (+20 spools, stock now 34)
- Production resumes at full capacity
- Cycle continues...

---

## Appendix B: Success Criteria

- ✅ All R0-R8 functional requirements implemented
- ✅ API documented with OpenAPI/Swagger
- ✅ Dashboard matches specified layout
- ✅ Example scenario runs without errors
- ✅ Unit test coverage > 80%
- ✅ Clean code with comments and docstrings
- ✅ Cross-platform tested (Windows, macOS, Linux)
