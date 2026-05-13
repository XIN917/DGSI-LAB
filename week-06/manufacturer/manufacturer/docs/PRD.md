# Product Requirements Document: 3D Printer Production Simulator

**Version**: 1.0-draft
**Created**: 2026-03-26
**Deadline**: 2026-04-14
**Status**: In Progress

---

## Table of Contents

1. [Overview](#1-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Data Model](#3-data-model)
4. [Architecture](#4-architecture)
5. [API Specification](#5-api-specification)
6. [UI/UX Design](#6-uiux-design)
7. [Authentication & Security](#7-authentication--security)
8. [Development Plan](#8-development-plan)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment Guide](#10-deployment-guide)
11. [Appendices](#11-appendices)

---

## 1. Overview

### 1.1 Product Vision

A day-by-day production simulation system for factory planning, where users act as production planners managing inventory, purchasing, and manufacturing operations for a 3D printer factory.

### 1.2 Objectives

- Simulate realistic production cycles with bill of materials (BOM) management
- Enable strategic decision-making on order releases and purchase orders
- Track all events for historical analysis and reporting
- Provide REST API access to all functionality
- Support full game state persistence via JSON import/export

### 1.3 Success Criteria

- All functional requirements R0-R8 implemented
- Clean, documented code with >80% test coverage
- Docker deployment working on Windows, macOS, Linux
- Complete OpenAPI/Swagger documentation
- Working authentication system

---

## 2. Functional Requirements

### R0 — Initial Configuration

| ID | Requirement | Priority |
|----|-------------|----------|
| R0.1 | Define production plans with multiple printer models | Must Have |
| R0.2 | Configure BOM for each model (materials + quantities) | Must Have |
| R0.3 | Set assembly time per model (in days) | Must Have |
| R0.4 | Manage supplier catalog with price breaks (bulk discounts) | Must Have |
| R0.5 | Configure lead times for each supplier/product | Must Have |
| R0.6 | Set warehouse capacity limits | Must Have |
| R0.7 | Set daily production capacity (default <250 units/day) | Must Have |
| R0.8 | Option to start with pre-configured sample data or empty slate | Must Have |

### R1 — Demand Generation

| ID | Requirement | Priority |
|----|-------------|----------|
| R1.1 | Generate manufacturing orders at start of each simulated day | Must Have |
| R1.2 | Configurable demand parameters (mean, variance) per product model | Must Have |
| R1.3 | Support demand for both finished printers and raw materials | Must Have |

### R2 — Control Dashboard

| ID | Requirement | Priority |
|----|-------------|----------|
| R2.1 | Display pending manufacturing orders | Must Have |
| R2.2 | Show BOM breakdown for each order | Must Have |
| R2.3 | Display current inventory levels with visual indicators | Must Have |
| R2.4 | Show warehouse capacity usage | Must Have |
| R2.5 | Display pending/delivered purchase orders | Must Have |

### R3 — User Decisions

| ID | Requirement | Priority |
|----|-------------|----------|
| R3.1 | Release orders to production (with insufficient material handling) | Must Have |
| R3.2 | Create purchase orders (product, supplier, quantity, expected date) | Must Have |
| R3.3 | Bulk discounts applied automatically based on quantity tiers | Must Have |

### R4 — Event Simulation

| ID | Requirement | Priority |
|----|-------------|----------|
| R4.1 | Realistic raw material consumption during manufacturing | Must Have |
| R4.2 | Enforce daily production capacity limits | Must Have |
| R4.3 | Handle "waiting for materials" state when insufficient inventory | Must Have |
| R4.4 | Simulate partial PO deliveries (~5-10% rate realistically) | Must Have |
| R4.5 | PO arrivals according to supplier lead time | Must Have |

### R5 — Calendar Advance

| ID | Requirement | Priority |
|----|-------------|----------|
| R5.1 | "Advance Day" button triggers 24h simulation cycle | Must Have |
| R5.2 | Manual refresh required after each day advance | Must Have |
| R5.3 | Future enhancement: Optional real-time auto-refresh | Nice to Have |

### R6 — Event Log

| ID | Requirement | Priority |
|----|-------------|----------|
| R6.1 | Log order releases to production | Must Have |
| R6.2 | Log material consumption events | Must Have |
| R6.3 | Log PO creation and arrivals | Must Have |
| R6.4 | Log failed orders (insufficient materials) | Must Have |
| R6.5 | Daily inventory snapshots | Must Have |
| R6.6 | User actions audit trail | Must Have |

### R7 — JSON Import/Export

| ID | Requirement | Priority |
|----|-------------|----------|
| R7.1 | Export full game state (inventory, config, events) | Must Have |
| R7.2 | Import saved game state | Must Have |
| R7.3 | Validate imported JSON schema | Must Have |

### R8 — REST API

| ID | Requirement | Priority |
|----|-------------|----------|
| R8.1 | All UI functionality accessible via REST API | Must Have |
| R8.2 | OpenAPI/Swagger documentation auto-generated | Must Have |

---

## 3. Data Model

### 3.1 Core Entities

```sql
-- Printer models and their configurations
CREATE TABLE product_models (
    id TEXT PRIMARY KEY,              -- e.g., "P3D-Classic", "P3D-Pro"
    name TEXT NOT NULL,
    assembly_time_days INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bill of Materials for each model
CREATE TABLE bom_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    model_id TEXT NOT NULL REFERENCES product_models(id),
    material_name TEXT NOT NULL,       -- e.g., "kit_piezas", "pcb"
    quantity REQUIRED DECIMAL NOT NULL,
    pcb_ref TEXT                       -- Optional reference like "CTRL-V2"
);

-- Suppliers with pricing tiers
CREATE TABLE suppliers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    lead_time_days INTEGER NOT NULL,
    active BOOLEAN DEFAULT 1
);

-- Supplier products with bulk pricing
CREATE TABLE supplier_products (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_name TEXT NOT NULL,        -- Matches material_name in BOM
    base_unit_cost DECIMAL NOT NULL,
    packaging_unit TEXT,               -- e.g., "pallet", "box"
    packaging_qty INTEGER,             -- Units per package
    discount_tiers JSON                -- [{"min_qty": 1000, "discount_pct": 10}]
);

-- Current inventory state
CREATE TABLE inventory (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL UNIQUE,
    quantity DECIMAL NOT NULL DEFAULT 0,
    reserved_quantity DECIMAL NOT NULL DEFAULT 0,  -- Reserved for released orders
    unit_type TEXT                     -- "raw" or "finished"
);

-- Manufacturing orders
CREATE TABLE manufacturing_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_model TEXT NOT NULL REFERENCES product_models(id),
    quantity_needed INTEGER NOT NULL,
    quantity_produced INTEGER DEFAULT 0,
    status TEXT NOT NULL DEFAULT 'pending',  -- pending, released, waiting_materials, completed, failed
    created_date DATE NOT NULL,
    started_date DATE,
    completed_date DATE,
    failure_reason TEXT
);

-- Purchase orders
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_id INTEGER NOT NULL REFERENCES suppliers(id),
    product_name TEXT NOT NULL,
    quantity_ordered INTEGER NOT NULL,
    quantity_delivered INTEGER DEFAULT 0,
    unit_cost DECIMAL NOT NULL,
    order_date DATE NOT NULL,
    expected_delivery DATE NOT NULL,
    actual_delivery DATE,
    status TEXT NOT NULL DEFAULT 'pending'  -- pending, partial, delivered, cancelled
);

-- Event log (append-only)
CREATE TABLE event_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type TEXT NOT NULL,          -- order_released, material_consumed, po_created, po_arrived, failed_order, inventory_snapshot, user_action
    event_date DATE NOT NULL,
    details JSON NOT NULL,             -- Context-specific payload
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- System configuration
CREATE TABLE simulation_config (
    key TEXT PRIMARY KEY,
    value JSON NOT NULL
);

-- Users for authentication
CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT DEFAULT 'planner',       -- planner, admin
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### 3.2 JSON Schema Examples

**Production Plan Export/Import:**
```json
{
  "capacity_per_day": 10,
  "warehouse_capacity": 1000,
  "models": {
    "P3D-Classic": {
      "bom": {
        "kit_piezas": {"qty": 1},
        "pcb": {"qty": 1, "pcb_ref": "CTRL-V2"},
        "extrusor": {"qty": 1},
        "cables_conexion": {"qty": 2},
        "transformador_24v": {"qty": 1},
        "enchufe_schuko": {"qty": 1}
      },
      "assembly_time_days": 1
    },
    "P3D-Pro": {
      "bom": {
        "kit_piezas": {"qty": 1},
        "pcb": {"qty": 1, "pcb_ref": "CTRL-V3"},
        "extrusor": {"qty": 1},
        "sensor_autonivel": {"qty": 1},
        "cables_conexion": {"qty": 3},
        "transformador_24v": {"qty": 1},
        "enchufe_schuko": {"qty": 1}
      },
      "assembly_time_days": 2
    }
  }
}
```

**Full Game State Export:**
```json
{
  "version": "1.0",
  "exported_at": "2026-04-01T14:30:00Z",
  "config": { /* production plan */ },
  "inventory": [
    {"product_name": "kit_piezas", "quantity": 150, "unit_type": "raw"}
  ],
  "manufacturing_orders": [ /* array of orders */ ],
  "purchase_orders": [ /* array of POs */ ],
  "event_log": [ /* array of events */ ]
}
```

---

## 4. Architecture

### 4.1 System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                         Docker Container                         │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────┐     ┌──────────────┐     ┌──────────────┐   │
│  │   Streamlit  │◄───►│   FastAPI    │◄───┤   SQLite     │   │
│  │   Dashboard  │     │   REST API   │     │   Database   │   │
│  └──────┬───────┘     └──────┬───────┘     └──────────────┘   │
│         │                    │                                  │
│         │           ┌────────▼────────┐                        │
│         │           │  Business Logic │                        │
│         │           │   Layer (Python)│                        │
│         │           └────────┬────────┘                        │
│         │                    │                                  │
│         │           ┌────────▼────────┐                        │
│         │           │ Simulation Engine│                       │
│         │           │  (Day Cycle)    │                        │
│         └───────────┴─────────────────┘                        │
│                                                                  │
│  Ports: 8501 (Streamlit), 8000 (FastAPI)                       │
└─────────────────────────────────────────────────────────────────┘
```

### 4.2 Component Responsibilities

| Component | Responsibility |
|-----------|----------------|
| **Streamlit Dashboard** | UI rendering, user interaction, manual refresh trigger |
| **FastAPI REST API** | HTTP endpoints, request validation, OpenAPI docs |
| **Business Logic Layer** | Order processing, inventory management, PO logic |
| **Simulation Engine** | Day advancement, demand generation, capacity enforcement |
| **SQLite Database** | Persistent storage, ACID transactions |

### 4.3 Data Flow

```
User Action (Dashboard)
    ↓
HTTP Request → FastAPI Endpoint
    ↓
Pydantic Validation
    ↓
Business Logic Service
    ↓
Database Transaction (SQLite)
    ↓
Event Log Entry
    ↓
Response → Streamlit Update
```

### 4.4 Directory Structure

```
week-05/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry
│   ├── api/
│   │   ├── __init__.py
│   │   ├── endpoints/
│   │   │   ├── orders.py
│   │   │   ├── inventory.py
│   │   │   ├── purchase_orders.py
│   │   │   ├── simulation.py
│   │   │   ├── config.py
│   │   │   └── auth.py
│   │   └── dependencies.py     # DB sessions, auth
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py           # Environment variables
│   │   ├── security.py         # Password hashing, JWT
│   │   └── database.py         # DB connection
│   ├── models/
│   │   ├── __init__.py
│   │   ├── product.py
│   │   ├── inventory.py
│   │   ├── order.py
│   │   ├── purchase_order.py
│   │   ├── event.py
│   │   └── user.py
│   ├── schemas/
│   │   ├── __init__.py
│   │   # Pydantic request/response models
│   ├── services/
│   │   ├── __init__.py
│   │   ├── simulation_engine.py
│   │   ├── inventory_service.py
│   │   ├── order_service.py
│   │   └── purchase_order_service.py
│   └── utils/
│       ├── __init__.py
│       └── json_export.py
├── dashboard/
│   ├── __init__.py
│   ├── pages.py                # Streamlit page layout
│   └── components/             # Reusable Streamlit components
├── tests/
│   ├── __init__.py
│   ├── conftest.py             # Test fixtures
│   ├── test_api/
│   ├── test_services/
│   └── test_simulation/
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml
│   └── entrypoint.sh
├── migrations/
│   └── init.sql                # Initial schema
├── sample_data/
│   └── default_production_plan.json
├── pyproject.toml
├── requirements.txt
├── README.md
└── PRD.md
```

---

## 5. API Specification

### 5.1 Authentication Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/auth/login` | Login with username/password |
| POST | `/api/auth/logout` | Invalidate session |
| GET | `/api/auth/me` | Get current user info |

**Request: POST /api/auth/login**
```json
{
  "username": "planner",
  "password": "secure_password"
}
```

**Response: 200 OK**
```json
{
  "access_token": "eyJ...",
  "token_type": "bearer",
  "user": {
    "id": 1,
    "username": "planner",
    "role": "planner"
  }
}
```

### 5.2 Configuration Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/config` | Get production plan configuration |
| POST | `/api/config` | Set production plan (import from JSON) |
| GET | `/api/config/models` | List all product models |
| GET | `/api/config/models/{model_id}` | Get model details with BOM |
| POST | `/api/config/suppliers` | Add supplier |
| GET | `/api/config/suppliers` | List suppliers |

### 5.3 Inventory Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/inventory` | Get all inventory levels |
| GET | `/api/inventory/{product_name}` | Get specific item |
| POST | `/api/inventory/adjust` | Manual inventory adjustment |

**Response: GET /api/inventory**
```json
{
  "items": [
    {
      "product_name": "kit_piezas",
      "quantity": 150,
      "reserved_quantity": 20,
      "available": 130,
      "unit_type": "raw"
    }
  ],
  "warehouse_usage": {
    "used": 450,
    "capacity": 1000,
    "percentage": 45
  }
}
```

### 5.4 Manufacturing Order Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/orders` | List all manufacturing orders |
| GET | `/api/orders/pending` | List pending orders only |
| GET | `/api/orders/{order_id}` | Get order details with BOM |
| POST | `/api/orders` | Create manual order |
| POST | `/api/orders/{order_id}/release` | Release order to production |
| POST | `/api/orders/{order_id}/cancel` | Cancel order |

**Response: GET /api/orders/pending**
```json
{
  "orders": [
    {
      "id": 1,
      "product_model": "P3D-Classic",
      "quantity_needed": 10,
      "status": "pending",
      "created_date": "2026-04-01",
      "bom_breakdown": {
        "kit_piezas": {"required": 10, "available": 150, "sufficient": true},
        "pcb": {"required": 10, "available": 5, "sufficient": false}
      },
      "can_release": false,
      "missing_materials": ["pcb"]
    }
  ]
}
```

### 5.5 Purchase Order Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/purchase-orders` | List all POs |
| GET | `/api/purchase-orders/{po_id}` | Get PO details |
| POST | `/api/purchase-orders` | Create new PO |
| POST | `/api/purchase-orders/{po_id}/cancel` | Cancel PO |

**Request: POST /api/purchase-orders**
```json
{
  "supplier_id": 1,
  "product_name": "pcb",
  "quantity": 1000,
  "expected_delivery": "2026-04-10"
}
```

**Response: 201 Created**
```json
{
  "id": 5,
  "supplier_id": 1,
  "product_name": "pcb",
  "quantity_ordered": 1000,
  "quantity_delivered": 0,
  "unit_cost": 8.50,
  "total_cost": 8500.00,
  "order_date": "2026-04-01",
  "expected_delivery": "2026-04-10",
  "status": "pending"
}
```

### 5.6 Simulation Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/simulation/status` | Get current simulation day/state |
| POST | `/api/simulation/advance` | Advance to next day |
| GET | `/api/simulation/demand-params` | Get demand generation params |
| POST | `/api/simulation/demand-params` | Update demand params |

**Response: GET /api/simulation/status**
```json
{
  "current_day": 15,
  "current_date": "2026-04-15",
  "sim_start_date": "2026-04-01",
  "pending_orders_count": 8,
  "production_today": 45,
  "capacity_remaining": 205
}
```

**Response: POST /api/simulation/advance**
```json
{
  "previous_day": 14,
  "new_day": 15,
  "events_generated": [
    {"type": "demand_generated", "count": 5},
    {"type": "po_arrived", "po_id": 3},
    {"type": "order_completed", "order_id": 12}
  ]
}
```

### 5.7 Event Log Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/events` | List events (paginated, filterable) |
| GET | `/api/events/{event_id}` | Get event details |
| GET | `/api/events/export` | Export events as JSON |

**Query Params: GET /api/events**
- `page`: integer (default: 1)
- `page_size`: integer (default: 50)
- `event_type`: filter by type
- `from_date`: ISO date
- `to_date`: ISO date

### 5.8 Import/Export Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/export/full-state` | Export complete game state |
| POST | `/api/import/full-state` | Import complete game state |
| POST | `/api/import/production-plan` | Import production plan only |

---

## 6. UI/UX Design

### 6.1 Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────────┐
│  3D PRINTER PRODUCTION SIMULATOR          Day 15  |  User: planner ✕   │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│  ┌─────────────────────┬─────────────────────────┬───────────────────┐ │
│  │   INVENTORY PANEL   │    ORDERS PANEL         │   ACTIONS PANEL   │ │
│  │                     │                         │                   │ │
│  │  Warehouse: 45%/1000│  Pending Orders (8)     │  [+ New PO]       │ │
│  │                     │                         │                   │ │
│  │  ┌────────────────┐ │  ┌────────────────────┐ │  [+ Release All]  │ │
│  │  │ kit_piezas     │ │  │ Order #12          │ │                   │ │
│  │  │ ████░░░░ 150   │ │  │ P3D-Pro x5         │ │  ───────────────  │ │
│  │  │   (20 res)     │ │  │ Status: Waiting    │ │  SIMULATION       │ │
│  │  └────────────────┘ │  │ Missing: sensor... │ │                   │ │
│  │  ┌────────────────┐ │  └────────────────────┘ │  [Advance Day ▶]  │ │
│  │  │ pcb            │ │                         │                   │ │
│  │  │ ██░░░░░░   5   │ │  ┌────────────────────┐ │  Simulated Date:  │ │
│  │  │   (5 res) ⚠️   │ │  │ Order #13          │ │  2026-04-15       │ │
│  │  └────────────────┘ │  │ P3D-Classic x10    │ │                   │ │
│  │  ...                │ │  Status: Can Release │ │  [Reset Simulation]││
│  │                     │ └─────────────────────┘ │                   │ │
│  └─────────────────────┴─────────────────────────┴───────────────────┘ │
│                                                                         │
├─────────────────────────────────────────────────────────────────────────┤
│  RECENT EVENTS                                              [View All]  │
│  ─────────────────────────────────────────────────────────────────────  │
│  2026-04-15 08:00  Demand generated: 5 new orders                       │
│  2026-04-14 16:30  PO #3 arrived (partial: 500/1000 pcb)               │
│  2026-04-14 09:15  Order #11 completed (P3D-Classic x8)                │
└─────────────────────────────────────────────────────────────────────────┘
```

### 6.2 Key Screens

**Create Purchase Order Modal:**
```
┌─────────────────────────────────────────────┐
│  Create Purchase Order                      │
├─────────────────────────────────────────────┤
│  Supplier:     [Select supplier ▼]          │
│  Product:      [Select product ▼]           │
│  Quantity:     [__________] units           │
│              ──────────────────────────     │
│              Price Breaks Applied:          │
│              • 1-999: $10.00/unit           │
│              • 1000-4999: $9.00/unit        │
│              • 5000+: $8.00/unit            │
│              ──────────────────────────     │
│  Total: $45,000.00                          │
│  Est. Delivery: 2026-04-10 (9 days)         │
│                                             │
│         [Cancel]      [Create PO]           │
└─────────────────────────────────────────────┘
```

**Order BOM Breakdown Expandable:**
```
▶ Order #12 — P3D-Pro x5 (Expand to see BOM)
  ▼ Order #13 — P3D-Classic x10
    ├─ kit_piezas: 10 needed ✓ 150 available
    ├─ pcb: 10 needed ⚠️ 5 available (5 short)
    ├─ extrusor: 10 needed ✓ 50 available
    ├─ cables_conexion: 20 needed ✓ 100 available
    ├─ transformador_24v: 10 needed ✓ 30 available
    ├─ enchufe_schuko: 10 needed ✓ 25 available
    ─────────────────────────────────────────
    Status: Cannot release — missing materials
    Quick action: [Create PO for pcb]
```

### 6.3 Visual Indicators

| Element | Design |
|---------|--------|
| Sufficient inventory | Green bar, checkmark ✓ |
| Insufficient inventory | Red bar, warning ⚠️ |
| Pending order | Yellow badge |
| Released to production | Blue badge |
| Waiting materials | Orange badge |
| Completed | Green badge |
| Failed | Red badge |

### 6.4 Future Enhancements (Not in MVP)

- Real-time auto-refresh every 30 seconds
- Chart.js integration for inventory trends
- Export to PDF reports
- Multi-language support
- Mobile-responsive layout

---

## 7. Authentication & Security

### 7.1 Authentication Approach

Since this is a local/single-user simulator designed as a "real product," we'll implement:

- **Session-based authentication** using secure cookies
- **Single admin user** by default (extensible to multi-user)
- **JWT tokens** for API requests (stored in memory, not localStorage since same-origin)
- **Password hashing** with bcrypt

### 7.2 Security Considerations

- All passwords hashed with bcrypt (cost factor 12)
- Session timeout after 24 hours of inactivity
- CSRF protection on all state-changing endpoints
- Rate limiting on login endpoint (5 attempts per minute)
- SQL injection prevention via parameterized queries (SQLAlchemy)
- Input validation via Pydantic models

### 7.3 User Table Schema

See Section 3.1 for full schema. Default seeded user:
- Username: `admin`
- Password: Generated randomly on first run (displayed in logs)
- Role: `admin`

---

## 8. Development Plan

### Phase 1: Foundation (March 26-28)

**Milestone: Core infrastructure working**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #1 | Setup project structure (FastAPI + Streamlit + SQLite) | 4 |
| #2 | Database schema implementation with SQLAlchemy | 4 |
| #3 | Authentication system (login, session, JWT) | 6 |
| #4 | Docker configuration (multi-stage build, volumes) | 4 |
| #5 | Sample data seeding (default production plan) | 3 |

**Acceptance Criteria:**
- Container builds and runs successfully
- Can login via Streamlit interface
- Database initialized with schema
- Sample production plan loadable

### Phase 2: Core Simulation (March 29-31)

**Milestone: Simulation engine functional**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #6 | Demand generation service (configurable mean/variance) | 4 |
| #7 | Inventory service (consume, reserve, adjust) | 6 |
| #8 | Order service (create, release, process) | 6 |
| #9 | Purchase order service (create, track, deliver) | 6 |
| #10 | Event logging service | 3 |
| #11 | Simulation engine (day advancement cycle) | 6 |

**Acceptance Criteria:**
- Clicking "Advance Day" generates demand
- Orders can be released if materials available
- Materials consumed correctly per BOM
- POs arrive on scheduled dates
- All events logged

### Phase 3: REST API (April 1-3)

**Milestone: Full API coverage**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #12 | Auth endpoints (/api/auth/*) | 3 |
| #13 | Config endpoints (/api/config/*) | 4 |
| #14 | Inventory endpoints (/api/inventory/*) | 4 |
| #15 | Order endpoints (/api/orders/*) | 5 |
| #16 | PO endpoints (/api/purchase-orders/*) | 5 |
| #17 | Simulation endpoints (/api/simulation/*) | 4 |
| #18 | Event log endpoints (/api/events/*) | 3 |
| #19 | Import/export endpoints (/api/import/*, /api/export/*) | 4 |
| #20 | OpenAPI documentation verification | 2 |

**Acceptance Criteria:**
- All endpoints functional and tested
- Swagger UI accessible at /docs
- API matches specification in Section 5

### Phase 4: Dashboard UI (April 4-7)

**Milestone: Complete dashboard**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #21 | Main dashboard layout (3-panel design) | 4 |
| #22 | Inventory panel component | 3 |
| #23 | Orders panel with BOM breakdown | 5 |
| #24 | Actions panel (release, create PO) | 4 |
| #25 | PO creation modal/dialog | 4 |
| #26 | Event log ticker at bottom | 3 |
| #27 | Visual indicators (colors, progress bars) | 3 |
| #28 | Responsive adjustments | 2 |

**Acceptance Criteria:**
- Dashboard matches wireframe design
- All interactions work (release orders, create POs)
- Visual feedback for all states
- Clear indication of insufficient materials

### Phase 5: Import/Export & Polish (April 8-10)

**Milestone: Save/load functionality**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #29 | JSON export (full state) | 3 |
| #30 | JSON import with validation | 4 |
| #31 | Production plan import (R0.8) | 2 |
| #32 | Error handling and user feedback | 4 |
| #33 | Code cleanup and comments | 4 |

**Acceptance Criteria:**
- Export creates valid JSON matching schema
- Import validates and rejects invalid JSON
- State restored exactly after import
- Helpful error messages for bad imports

### Phase 6: Testing & Documentation (April 11-13)

**Milestone: Production-ready**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #34 | Unit tests for business logic (>80% coverage) | 8 |
| #35 | Integration tests for API endpoints | 6 |
| #36 | E2E tests for critical flows | 4 |
| #37 | README documentation | 3 |
| #38 | API documentation review | 2 |
| #39 | Bug fixes and edge cases | 6 |
| #40 | Final review and cleanup | 3 |

**Acceptance Criteria:**
- All tests passing
- Coverage report shows >80%
- README has setup instructions
- No known critical bugs

### Phase 7: Buffer & Final Review (April 14)

**Milestone: Delivery**

| Issue | Task | Estimated Hours |
|-------|------|-----------------|
| #41 | Contingency for unexpected issues | 8 |
| #42 | Final demonstration prep | 2 |

---

### Gantt Timeline

```
Week 1 (Mar 26-28)    Week 2 (Mar 29-31)    Week 3 (Apr 1-7)     Week 4 (Apr 8-14)
██████████            ████████████          ████████████████     ████████████
Phase 1: Foundation   Phase 2: Core         Phase 3+4: API+UI    Phase 5+6+7:
                        Simulation            (overlapping)        Polish, Tests, Delivery
```

---

## 9. Testing Strategy

### 9.1 Test Types

| Type | Tool | Coverage Target |
|------|------|-----------------|
| Unit | pytest | Services, business logic |
| Integration | pytest + TestClient | API endpoints |
| E2E | pytest + Streamlit testing | Critical user flows |

### 9.2 Test Structure

```
tests/
├── conftest.py                 # Shared fixtures (DB, auth)
├── test_services/
│   ├── test_inventory_service.py
│   ├── test_order_service.py
│   ├── test_purchase_order_service.py
│   └── test_simulation_engine.py
├── test_api/
│   ├── test_auth.py
│   ├── test_inventory.py
│   ├── test_orders.py
│   └── test_simulation.py
└── test_integration/
    ├── test_full_order_flow.py
    └── test_import_export.py
```

### 9.3 Key Test Scenarios

**Inventory Service:**
- Reserve materials for order
- Consume materials on production
- Release reservations on order cancel
- Prevent oversubscription

**Order Service:**
- Create order with valid model
- Calculate BOM requirements
- Check material availability
- Release order only if sufficient materials
- Mark as waiting_materials if insufficient

**Simulation Engine:**
- Generate demand within configured variance
- Advance day processes all pending POs
- Capacity limits enforced per day
- Events logged correctly

**Import/Export:**
- Export contains all state
- Import restores exact state
- Invalid JSON rejected with clear error
- Schema validation catches missing fields

---

## 10. Deployment Guide

### 10.1 Docker Setup

**Dockerfile:**
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY . .

# Expose ports
EXPOSE 8000 8501

# Entry point
CMD ["bash", "docker/entrypoint.sh"]
```

**docker-compose.yml:**
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8000:8000"   # FastAPI
      - "8501:8501"   # Streamlit
    volumes:
      - ./data:/app/data  # Persist SQLite database
    environment:
      - SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32)}
      - DATABASE_URL=sqlite:///data/simulation.db
```

**entrypoint.sh:**
```bash
#!/bin/bash
set -e

# Initialize database if not exists
if [ ! -f /app/data/simulation.db ]; then
    mkdir -p /app/data
    python -m app.core.database_init
fi

# Run both services
pip install &
streamlit run dashboard/pages.py &
uvicorn app.main:app --host 0.0.0.0 --port 8000

wait
```

### 10.2 Running Locally

```bash
# Clone repository
git clone <repo>
cd week-05

# Build and run with Docker Compose
docker compose up --build

# Access:
# - Dashboard: http://localhost:8501
# - API: http://localhost:8000
# - Swagger Docs: http://localhost:8000/docs
```

### 10.3 Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SECRET_KEY` | Yes* | Random | Cryptographic secret |
| `DATABASE_URL` | Yes* | sqlite:///data/simulation.db | Database connection |
| `SIMULATION_START_DATE` | No | 2026-04-01 | Initial simulation date |
| `DEFAULT_CAPACITY_PER_DAY` | No | 250 | Production capacity |

*Generated automatically on first run if not provided

---

## 11. Appendices

### Appendix A: Simulation Day Cycle

The "Advance Day" button triggers this sequence:

1. **Demand Generation** (R1)
   - For each product model, generate random demand based on configured mean/variance
   - Create manufacturing orders with status=pending

2. **PO Processing** (R4)
   - For all POs with expected_delivery = current_date
   - Apply partial delivery logic (~5-10% chance of partial)
   - Add delivered quantities to inventory

3. **Order Processing** (R4)
   - For all orders with status=released
   - Check if materials are available
   - If yes: consume materials, update quantity_produced
   - If no: mark as waiting_materials
   - Enforce daily capacity limit

4. **Event Logging** (R6)
   - Record all state changes to event_log table

5. **Daily Snapshot** (R6)
   - Take inventory snapshot for historical tracking

### Appendix B: Event Log Schema

```json
{
  "event_type": "order_released",
  "event_date": "2026-04-01",
  "details": {
    "order_id": 1,
    "product_model": "P3D-Classic",
    "quantity": 10,
    "materials_reserved": {
      "kit_piezas": 10,
      "pcb": 10,
      "extrusor": 10,
      "cables_conexion": 20,
      "transformador_24v": 10,
      "enchufe_schuko": 10
    }
  }
}
```

Supported event types:
- `demand_generated`
- `order_created`
- `order_released`
- `material_consumed`
- `order_completed`
- `order_failed`
- `po_created`
- `po_arrived`
- `po_partial_delivery`
- `inventory_adjusted`
- `inventory_snapshot`

### Appendix C: Future Enhancements

Not in MVP scope but noted for future iterations:

1. **Advanced Analytics Dashboard**
   - Production efficiency charts
   - Inventory turnover metrics
   - Cost analysis reports

2. **Scenario Planning**
   - Save multiple "what-if" scenarios
   - Compare outcomes before committing decisions

3. **Multi-User Collaboration**
   - Multiple planners with different roles
   - Audit trail per user action

4. **Real-Time Updates**
   - WebSocket connections for live dashboard updates
   - Push notifications for PO arrivals

5. **Mobile App**
   - Responsive design improvements
   - Native mobile clients

---

**END OF DOCUMENT**
