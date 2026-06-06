# Product Requirements Document (PRD) - Week 6: Two Apps Talking

## 1. Overview
Week 6 of the DGSI Lab shifts from a single-process application to a distributed multi-service architecture. We will build a **Provider App** that acts as a parts supplier and integrate it with the existing **Manufacturer App** (from Week 5). These two applications will communicate over a REST API to simulate a simplified supply chain.

## 2. Goals
- Implement a standalone **Provider App** with its own database and state.
- Enable the **Manufacturer App** to purchase materials from the Provider via REST.
- Synchronize simulated time (days) across both applications.
- Maintain independent event logs in both apps for auditing.
- Prove cross-app communication works through a deterministic manual scenario.

---

## 3. Provider App Specification

The Provider App models a supplier that sells components (PCBs, extruders, etc.) to manufacturers.

### 3.1 Data Model
- **Products Catalog**: Available parts with descriptions.
- **Pricing Tiers**: Bulk discounts based on quantity (e.g., 1-9 units: 50€, 10-99 units: 35€).
- **Lead Times**: Days from order to delivery per product.
- **Stock Levels**: Current inventory of each product.
- **Orders**: Full history of purchase orders from manufacturers.
- **Simulated State**: Current simulated day.
- **Events**: Audit trail of all state changes.

### 3.2 Database Schema (SQLite)
```sql
CREATE TABLE products (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    lead_time_days INTEGER NOT NULL
);

CREATE TABLE pricing_tiers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER NOT NULL REFERENCES products(id),
    min_quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL
);

CREATE TABLE stock (
    product_id INTEGER PRIMARY KEY REFERENCES products(id),
    quantity INTEGER NOT NULL
);

CREATE TABLE orders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    buyer TEXT NOT NULL,
    product_id INTEGER NOT NULL REFERENCES products(id),
    quantity INTEGER NOT NULL,
    unit_price REAL NOT NULL,
    total_price REAL NOT NULL,
    placed_day INTEGER NOT NULL,
    expected_delivery_day INTEGER NOT NULL,
    shipped_day INTEGER,
    delivered_day INTEGER,
    status TEXT NOT NULL -- PENDING, CONFIRMED, SHIPPED, DELIVERED, REJECTED, CANCELLED
);

CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sim_day INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    entity_type TEXT,
    entity_id INTEGER,
    detail TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE sim_state (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);
```

### 3.3 REST Endpoints
- `GET /api/catalog`: List products with their pricing tiers.
- `GET /api/stock`: Show current provider inventory.
- `POST /api/orders`: Place a purchase order (Specs: product_id, quantity, buyer).
- `GET /api/orders`: List all orders (optional filter by status).
- `GET /api/orders/{id}`: Get specific order details.
- `POST /api/day/advance`: Advance simulated time by one day.
- `GET /api/day/current`: Get current simulated day.

### 3.4 CLI Commands (Typer/Click)
- `provider-cli catalog`: List products.
- `provider-cli stock`: Show inventory.
- `provider-cli orders list [--status]`: List orders.
- `provider-cli orders show <id>`: Order details.
- `provider-cli price set <prod> <tier> <val>`: Update pricing.
- `provider-cli restock <prod> <qty>`: Add stock.
- `provider-cli day advance`: Advance day.
- `provider-cli day current`: Show current day.
- `provider-cli export/import`: JSON state management.
- `provider-cli serve --port 8001`: Start API.

---

## 4. Manufacturer App Adaptation

The Week 5 Manufacturer App needs modest changes to interact with the new Provider.

### 4.1 Configuration
Add a configuration mechanism (JSON or ENV) to define external providers:
```json
{
  "manufacturer": {
    "port": 8002,
    "providers": [
      {"name": "ChipSupply Co", "url": "http://localhost:8001"}
    ]
  }
}
```

### 4.2 Outbound Calls
Implement a service layer to call the Provider's REST API:
- `manufacturer-cli suppliers list`: Query configured providers.
- `manufacturer-cli suppliers catalog <name>`: Show catalog from a specific provider.
- `manufacturer-cli purchase create --supplier <name> --product <id> --qty <n>`: Place an order.
- `manufacturer-cli purchase list`: Show orders placed with external providers.

### 4.3 Simulation Logic Updates
- **Tracking**: Store external purchase orders in the local DB with a status (PENDING, SHIPPED, DELIVERED).
- **Day Advance**: During `day_advance`, the Manufacturer must poll the Provider for each pending order's status. If an order is marked `DELIVERED` by the Provider, the Manufacturer adds the parts to its inventory and updates the local order status.
- **Simulated Time**: A human must advance BOTH apps manually.

---

## 5. Technical Stack
- **Language**: Python 3.11+
- **Web Framework**: FastAPI
- **CLI Framework**: Typer
- **Database**: SQLite (SQLAlchemy ORM)
- **HTTP Client**: HTTPX (for cross-app calls)
- **Validation**: Pydantic

---

## 6. Development Plan & Milestones

### Milestone 1: Provider Core
- [ ] Implement Provider database schema and models.
- [ ] Implement Provider service layer (orders, stock, time).
- [ ] Create `seed-provider.json` with initial data.

### Milestone 2: Provider Interfaces
- [ ] Implement Provider REST API endpoints.
- [ ] Implement Provider CLI commands.
- [ ] Verify Provider works standalone (CLI and Swagger).

### Milestone 3: Manufacturer Integration
- [ ] Add Provider configuration to Manufacturer.
- [ ] Implement REST client in Manufacturer to call Provider.
- [ ] Add `suppliers` and `purchase` commands to Manufacturer CLI.

### Milestone 4: Simulation & Sync
- [ ] Update Manufacturer's `day_advance` to poll Provider.
- [ ] Implement Order Lifecycle state machine in both apps.
- [ ] Verify arrival of parts in Manufacturer inventory.

### Milestone 5: The Manual Scenario
- [ ] Run the 5-day scenario: Order on Day 0, advance both apps, verify arrival on Day 4.
- [ ] Verify Event Logs in both databases tell a consistent story.
