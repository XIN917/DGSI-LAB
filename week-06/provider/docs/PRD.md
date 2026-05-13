# Product Requirements Document (PRD)

## Week 6: Provider App + Manufacturer Integration

**Date:** 30 April 2026  
**Version:** 1.0  
**Status:** Draft

---

## 1. Overview

### 1.1 Purpose

This PRD defines the requirements for building the **Provider App** (a parts supplier) and extending the existing **Manufacturer App** (from Week 5) to enable communication between two separate services over a REST API.

### 1.2 Scope

| Component | Description |
|-----------|-------------|
| **Provider App** | New - Parts supplier that sells components to the manufacturer |
| **Manufacturer App** | Extend - Week 5 factory app with outbound API calls |
| **Integration** | REST API contract between provider and manufacturer |

### 1.3 Goals

By the end of Week 6, the system must demonstrate:
1. Two independent apps running on different ports (8001/8002)
2. Manufacturer can query provider's catalog and place purchase orders
3. Order lifecycle works: pending → shipped → delivered
4. Inventory updates correctly when orders arrive
5. Event logs maintain audit trail in both databases

---

## 2. Architecture

### 2.1 System Diagram

```
┌─────────────────────┐      ┌─────────────────────┐
│   Provider App      │      │ Manufacturer App   │
│   (Port 8001)       │      │   (Port 8002)      │
│                     │      │                     │
│  ┌───────────────┐  │ HTTP │ ┌───────────────┐  │
│  │   REST API    │◄─┼──────┼─►│  HTTP Client  │  │
│  │  /api/catalog │  │      │  │ (httpx)       │  │
│  │  /api/orders  │  │      │  └───────────────┘  │
│  │  /api/stock   │  │      │                     │
│  │  /api/day/*   │  │      │ ┌───────────────┐  │
│  └───────────────┘  │      │ │  Purchase     │  │
│         │           │      │ │  Order Track  │  │
│  ┌───────────────┐  │      │ └───────────────┘  │
│  │  SQLite DB    │  │      │         │           │
│  │  - products   │  │      │ ┌───────────────┐  │
│  │  - pricing    │  │      │ │  SQLite DB    │  │
│  │  - stock      │  │      │ │  (extended)   │  │
│  │  - orders     │  │      │ └───────────────┘  │
│  │  - events     │  │      │                     │
│  └───────────────┘  │      │                     │
└─────────────────────┘      └─────────────────────┘
```

### 2.2 Technology Stack

| Layer | Provider App | Manufacturer App (Extended) |
|-------|--------------|------------------------------|
| **Backend** | Python 3.11, FastAPI | Python 3.11, FastAPI (existing) |
| **ORM** | SQLAlchemy | SQLAlchemy (existing) |
| **Database** | SQLite (provider.db) | SQLite (manufacturer.db) |
| **CLI** | Typer | Typer (extended) |
| **HTTP Client** | — | httpx |
| **UI** | None (CLI + API) | Streamlit (existing) |

### 2.3 Directory Structure

```
week-6/
├── provider/                    # NEW: Provider app
│   ├── provider/
│   │   ├── app/
│   │   │   ├── __init__.py
│   │   │   ├── main.py          # FastAPI entry point
│   │   │   ├── api/
│   │   │   │   ├── dependencies.py
│   │   │   │   └── endpoints/
│   │   │   │       ├── catalog.py
│   │   │   │       ├── orders.py
│   │   │   │       ├── stock.py
│   │   │   │       └── simulation.py
│   │   │   ├── models/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── product.py
│   │   │   │   ├── pricing_tier.py
│   │   │   │   ├── stock.py
│   │   │   │   ├── order.py
│   │   │   │   └── event.py
│   │   │   ├── services/
│   │   │   │   ├── __init__.py
│   │   │   │   ├── catalog_service.py
│   │   │   │   ├── order_service.py
│   │   │   │   └── simulation_service.py
│   │   │   ├── cli.py           # Typer CLI
│   │   │   ├── db.py            # Database setup
│   │   │   └── seed.py          # Seed data loader
│   │   ├── requirements.txt
│   │   ├── pyproject.toml
│   │   └── seed_data/
│   │       └── seed-provider.json
│   │
│   └── docs/
│       └── PRD.md               # This document
│
├── manufacturer/                # EXISTING: Extended
│   └── ...
│
└── docs/
    └── (shared documentation)
```

---

## 3. Data Model

### 3.1 Provider Database Schema

```sql
-- Products catalog
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    lead_time_days INTEGER NOT NULL
);

-- Pricing tiers (quantity-based discounts)
CREATE TABLE pricing_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL,
    min_quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Current stock levels
CREATE TABLE stock (
    product_id INTEGER PRIMARY KEY,
    quantity INTEGER NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Orders from buyers
CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer TEXT NOT NULL,
    product_id INTEGER NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    placed_day INTEGER NOT NULL,
    expected_delivery_day INTEGER NOT NULL,
    shipped_day INTEGER,
    delivered_day INTEGER,
    status TEXT NOT NULL,
    FOREIGN KEY (product_id) REFERENCES products(id)
);

-- Event audit trail
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_day INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    detail TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simulation state
CREATE TABLE sim_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 3.2 Order Status State Machine

```
┌──────────┐    ┌───────────┐    ┌──────────┐    ┌────────────┐
│ pending  │───►│ confirmed │───►│ shipped  │───►│ delivered  │
└──────────┘    └───────────┘    └──────────┘    └────────────┘
     │               │                │                │
     │               │                │                │
  Order just    Stock confirmed   Shipped from     Arrived at
  placed        and ready to      provider         buyer
                ship
```

### 3.3 Manufacturer Extended Schema

```sql
-- Track purchase orders placed with providers
CREATE TABLE purchase_orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider_name TEXT NOT NULL,
    provider_order_id INTEGER,  -- Reference to provider's order
    product_id TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    placed_day INTEGER NOT NULL,
    expected_delivery_day INTEGER NOT NULL,
    delivered_day INTEGER,
    status TEXT NOT NULL,  -- pending, delivered
    FOREIGN KEY (product_id) REFERENCES products(id)
);
```

---

## 4. Functional Requirements

### 4.1 Provider App Features

#### 4.1.1 CLI Commands

| Command | Description |
|---------|-------------|
| `provider-cli catalog list` | List all products with pricing tiers |
| `provider-cli stock show` | Show current inventory levels |
| `provider-cli orders list [--status <status>]` | List all orders, optionally filtered |
| `provider-cli orders show <order_id>` | Show order details |
| `provider-cli price set <product> <tier> <price>` | Update a price tier |
| `provider-cli restock <product> <quantity>` | Add stock (simulate upstream delivery) |
| `provider-cli day advance` | Advance simulation by one day |
| `provider-cli day current` | Show current simulation day |
| `provider-cli export` | Dump state to JSON |
| `provider-cli import <file>` | Load state from JSON |
| `provider-cli serve --port 8001` | Start the REST API server |

#### 4.1.2 REST API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/catalog` | Get products with pricing tiers |
| GET | `/api/stock` | Get current inventory |
| POST | `/api/orders` | Place a purchase order |
| GET | `/api/orders` | List orders (optional `?status=pending`) |
| GET | `/api/orders/{id}` | Get order details |
| POST | `/api/day/advance` | Advance one day |
| GET | `/api/day/current` | Get current day |

#### 4.1.3 Business Logic

1. **Price Calculation**: When an order is placed, calculate price based on quantity tier breaks
2. **Lead Time**: Expected delivery = current_day + lead_time_days
3. **Day Advance**:
   - Transition pending → confirmed (if stock available)
   - Transition confirmed → shipped → delivered (if expected_delivery reached)
   - Increment current_day
   - Log all transitions to events table

### 4.2 Manufacturer App Extensions

#### 4.2.1 New CLI Commands

| Command | Description |
|---------|-------------|
| `manufacturer-cli suppliers list` | List configured providers |
| `manufacturer-cli suppliers catalog <name>` | Show catalog from a provider |
| `manufacturer-cli purchase create --supplier <name> --product <id> --qty <n>` | Create purchase order |
| `manufacturer-cli purchase list` | List purchase orders |

#### 4.2.2 New API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/suppliers` | List configured providers |
| GET | `/api/suppliers/{name}/catalog` | Get provider's catalog |
| POST | `/api/purchase-orders` | Create purchase order with provider |
| GET | `/api/purchase-orders` | List purchase orders |

#### 4.2.3 Purchase Order Polling

On each `day advance`:
1. Query all pending purchase orders
2. For each, call provider API: `GET /api/orders/{id}`
3. If status is `delivered`, add parts to local inventory and update status

---

## 5. Product Catalog

### 5.1 Provider Products (Matching Manufacturer BOM)

| Product ID | Description | Lead Time | Pricing Tiers |
|------------|-------------|-----------|---------------|
| `frame_kit` | Standard frame kit | 3 days | 1-9: €28.50, 10-99: €27.08, 100+: €25.65 |
| `frame_kit_pro` | Professional frame kit | 3 days | 1-9: €48.00, 10-49: €45.60, 50+: €42.24 |
| `pcb_control` | Control board PCB | 5 days | 1-9: €22.00, 10-99: €20.90, 100+: €18.04 |
| `stepper_motor` | Stepper motor | 2 days | 1-9: €15.00, 10-99: €13.50, 100+: €12.00 |
| `hotend` | Standard hotend | 4 days | 1-9: €35.00, 10-49: €31.50, 50+: €28.00 |
| `hotend_pro` | Professional hotend | 4 days | 1-9: €55.00, 10-49: €49.50, 50+: €44.00 |
| `bed_heater` | Heated bed element | 3 days | 1-9: €20.00, 10-99: €18.00, 100+: €16.00 |
| `power_supply` | Power supply unit | 5 days | 1-9: €18.50, 10-49: €17.58, 50+: €16.65 |
| `extruder_kit` | Standard extruder kit | 3 days | 1-9: €15.00, 10-99: €13.80, 100+: €12.00 |
| `dual_extruder_kit` | Dual extruder kit | 3 days | 1-9: €32.00, 10-49: €29.76, 50+: €26.56 |
| `filament_sensor` | Filament sensor | 2 days | 1-9: €12.00, 10-99: €10.80, 100+: €9.60 |

### 5.2 Initial Stock Levels

| Product | Initial Stock |
|---------|---------------|
| frame_kit | 500 |
| frame_kit_pro | 200 |
| pcb_control | 300 |
| stepper_motor | 500 |
| hotend | 250 |
| hotend_pro | 150 |
| bed_heater | 300 |
| power_supply | 250 |
| extruder_kit | 300 |
| dual_extruder_kit | 150 |
| filament_sensor | 200 |

---

## 6. API Contract

### 6.1 Provider API Specification

#### POST /api/orders

**Request:**
```json
{
  "buyer": "manufacturer",
  "product_id": "pcb_control",
  "quantity": 50
}
```

**Response (201):**
```json
{
  "id": 1,
  "buyer": "manufacturer",
  "product_id": "pcb_control",
  "quantity": 50,
  "unit_price": 20.90,
  "total_price": 1045.00,
  "placed_day": 1,
  "expected_delivery_day": 6,
  "shipped_day": null,
  "delivered_day": null,
  "status": "pending"
}
```

#### GET /api/orders/{id}

**Response (200):**
```json
{
  "id": 1,
  "buyer": "manufacturer",
  "product_id": "pcb_control",
  "quantity": 50,
  "unit_price": 20.90,
  "total_price": 1045.00,
  "placed_day": 1,
  "expected_delivery_day": 6,
  "shipped_day": 5,
  "delivered_day": 6,
  "status": "delivered"
}
```

### 6.2 Error Handling

| Status Code | Description |
|-------------|-------------|
| 400 | Bad Request (invalid product, quantity) |
| 404 | Order not found |
| 500 | Internal server error |
| 503 | Provider unavailable |

---

## 7. Configuration

### 7.1 Provider Config (config.json)

```json
{
  "provider": {
    "name": "ChipSupply Co",
    "port": 8001,
    "database": "provider.db"
  }
}
```

### 7.2 Manufacturer Config (config.json)

```json
{
  "manufacturer": {
    "port": 8002,
    "providers": [
      {
        "name": "ChipSupply Co",
        "url": "http://localhost:8001"
      }
    ]
  }
}
```

### 7.3 Environment Variables

```
PROVIDER_PORT=8001
MANUFACTURER_PORT=8002
PROVIDER_DB=provider.db
MANUFACTURER_DB=manufacturer.db
```

---

## 8. Verification Scenario

### 8.1 5-Day Manual Test Scenario

**Setup (Day 0):**
- Provider has 500 `pcb_control` at €20.90 (tier 10-99) with 5-day lead time
- Manufacturer has 5 `pcb_control` in inventory
- Both apps on day 0

**Day 1:**
```bash
# Query provider catalog
manufacturer-cli suppliers catalog "ChipSupply Co"

# Place order for 50 PCBs
manufacturer-cli purchase create --supplier "ChipSupply Co" --product pcb_control --qty 50

# Verify order shows pending with expected delivery day 6
provider-cli orders show 1
```

**Days 2-3:**
```bash
# Advance both apps
provider-cli day advance
manufacturer-cli day advance

# Verify order still in flight
provider-cli orders list
```

**Day 4:**
```bash
# Provider ships/delivers order
provider-cli day advance

# Manufacturer polls and receives delivery
manufacturer-cli day advance

# Verify inventory updated
manufacturer-cli stock show

# Should show 55 PCBs total
```

**Day 5:**
- Place second order, verify repeatability

### 8.2 Verification Checklist

- [ ] Provider app starts on port 8001
- [ ] Manufacturer app starts on port 8002
- [ ] `provider-cli catalog list` returns all products
- [ ] `provider-cli stock show` returns stock levels
- [ ] `manufacturer-cli suppliers catalog "ChipSupply Co"` works
- [ ] `manufacturer-cli purchase create` creates order in provider
- [ ] Order lifecycle: pending → confirmed → shipped → delivered
- [ ] Manufacturer inventory updates on delivery
- [ ] Event logs in both databases are consistent
- [ ] JSON export/import works for both apps
- [ ] Swagger docs at `/docs` are complete

---

## 9. Non-Functional Requirements

### 9.1 Performance

- API response time < 500ms for catalog queries
- Order creation < 200ms
- Day advance processing < 1 second

### 9.2 Reliability

- Network errors must be logged and surfaced clearly
- No silent failures - all errors return meaningful messages
- Database transactions must be atomic

### 9.3 Security

- No API keys in source code
- `.env` files in `.gitignore`
- Provide `.env.example` with placeholder values

---

## 10. Deliverables

### 10.1 Code

- `provider/` folder with complete app
- Extended `manufacturer/` with new CLI commands and API endpoints
- Seed data JSON files
- Updated README.md

### 10.2 Documentation

- This PRD
- Updated CLAUDE.md reflecting new architecture
- API documentation via Swagger at `/docs`

### 10.3 Testing

- Manual 5-day scenario runs end-to-end
- Event logs verify consistent story

---

## 11. Out of Scope (Week 7-8)

- Retailer app (Week 7)
- Turn engine (Week 7)
- LLM agents (Week 7-8)
- Market signals (Week 8)

---

## 12. Dependencies

### 12.1 Provider Requirements

```
fastapi>=0.109.0
uvicorn>=0.27.0
sqlalchemy>=2.0.0
pydantic>=2.0.0
typer>=0.9.0
httpx>=0.26.0
python-dotenv>=1.0.0
```

### 12.2 Manufacturer Extensions

- Add `httpx` to existing dependencies
- No other new dependencies required

---

**Document History**

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 30 April 2026 | GitHub Copilot | Initial draft |