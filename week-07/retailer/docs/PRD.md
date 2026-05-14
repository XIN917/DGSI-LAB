# Product Requirements Document: Retailer App

**Version**: 1.0-draft
**Created**: 2026-05-14
**Status**: In Progress

---

## Table of Contents

1. [Overview](#1-overview)
2. [Functional Requirements](#2-functional-requirements)
3. [Data Model](#3-data-model)
4. [Integration and API](#4-integration-and-api)
5. [User Experience](#5-user-experience)
6. [Business Rules](#6-business-rules)
7. [Architecture](#7-architecture)
8. [Development Plan](#8-development-plan)
9. [Testing Strategy](#9-testing-strategy)
10. [Deployment](#10-deployment)
11. [Appendices](#11-appendices)

---

## 1. Overview

### 1.1 Product Vision

The Retailer App is the downstream node in the DGSI supply chain. It acts as a retail operator that purchases finished 3D printers from the Manufacturer, maintains finished goods inventory, receives customer orders, fulfills demand with available stock, manages backorders, and advances simulation days in sync with the central turn engine.

### 1.2 Objectives

- Provide a retailer-facing REST API and CLI for full operational control.
- Support customer order entry, fulfillment, backorder management, and shipment tracking.
- Enforce retail pricing rules by applying minimum profit margins above the Manufacturer wholesale price.
- Integrate with the Manufacturer App using REST endpoints for purchase orders and fulfillment updates.
- Maintain independent persistence, event logging, and JSON state import/export.

### 1.3 Success Criteria

- Retailer functionality is delivered via both REST API and CLI.
- All customer orders are logged and either fulfilled or correctly backordered.
- Purchase orders for finished goods are created, tracked, and updated from Manufacturer responses.
- Day advancement endpoints align with the existing Provider and Manufacturer simulation interface.
- All state transitions are recorded in an event log for auditing.

---

## 2. Functional Requirements

### R0 — Setup & Configuration

| ID | Requirement | Priority |
|----|-------------|----------|
| R0.1 | Support local SQLite persistence for retailer state | Must Have |
| R0.2 | Allow configurable application port, database path, and manufacturer endpoint | Must Have |
| R0.3 | Support JSON import/export of full retailer state | Must Have |
| R0.4 | Provide CLI and REST interfaces matching Provider and Manufacturer patterns | Must Have |
| R0.5 | Allow multiple retailer instances with separate config files and ports | Must Have |

### R1 — Customer Order Management

| ID | Requirement | Priority |
|----|-------------|----------|
| R1.1 | Create customer orders for finished printer SKUs | Must Have |
| R1.2 | Track order status: `pending`, `fulfilled`, `backordered`, `cancelled` | Must Have |
| R1.3 | Fulfill orders automatically from finished goods inventory when available | Must Have |
| R1.4 | Backorder orders when stock is insufficient | Must Have |
| R1.5 | Auto-fulfill backorders when inventory arrives on subsequent simulated days | Must Have |

### R2 — Inventory & Pricing

| ID | Requirement | Priority |
|----|-------------|----------|
| R2.1 | Maintain finished goods inventory levels | Must Have |
| R2.2 | Record inventory receipts from manufacturer purchase orders | Must Have |
| R2.3 | Set retail prices per product SKU | Must Have |
| R2.4 | Enforce a minimum markup of 15% above wholesale price | Must Have |
| R2.5 | Allow recommended markup of 30% while preserving minimum margin | Nice to Have |

### R3 — Procurement from Manufacturer

| ID | Requirement | Priority |
|----|-------------|----------|
| R3.1 | Place purchase orders to the Manufacturer via REST | Must Have |
| R3.2 | Track manufacturer PO status and expected delivery dates | Must Have |
| R3.3 | Receive fulfillment notifications or poll the Manufacturer for PO updates | Must Have |
| R3.4 | Add delivered finished goods to local stock automatically | Must Have |

### R4 — Simulation Day Control

| ID | Requirement | Priority |
|----|-------------|----------|
| R4.1 | Expose `/api/day/current` to return current simulated day | Must Have |
| R4.2 | Expose `/api/day/advance` to advance the retailer state by one day | Must Have |
| R4.3 | Ensure day advancement is consistent with the central turn engine and other apps | Must Have |
| R4.4 | Update backorders and PO statuses on day advance | Must Have |

### R5 — Event Logging

| ID | Requirement | Priority |
|----|-------------|----------|
| R5.1 | Record every state-changing event in an event log | Must Have |
| R5.2 | Log customer order creation, fulfillment, and backorder events | Must Have |
| R5.3 | Log purchase order creation, updates, and deliveries | Must Have |
| R5.4 | Log price changes and retail margin enforcement actions | Must Have |
| R5.5 | Log day advancement and inventory receipts | Must Have |

---

## 3. Data Model

### 3.1 Core Entities

- `CustomerOrder`
  - `id`
  - `sku`
  - `quantity`
  - `retail_price`
  - `status`
  - `created_day`
  - `fulfilled_day`
  - `backorder_date`
  - `customer_name`
  - `notes`

- `InventoryItem`
  - `id`
  - `sku`
  - `quantity_on_hand`
  - `quantity_reserved`
  - `retail_price`
  - `last_cost`

- `PurchaseOrder`
  - `id`
  - `manufacturer_po_id`
  - `sku`
  - `quantity`
  - `wholesale_unit_price`
  - `retail_unit_price`
  - `status`
  - `placed_day`
  - `expected_delivery_day`
  - `received_day`

- `EventLog`
  - `id`
  - `sim_day`
  - `event_type`
  - `entity_type`
  - `entity_id`
  - `details`
  - `created_at`

- `SimState`
  - `current_day`
  - `config` (manufacturer endpoint, port, markup settings)

---

## 4. Integration and API

### 4.1 Manufacturer Integration

The Retailer App integrates with the Manufacturer App using REST-only communication.

- `POST /api/purchase-orders` — create a PO to the Manufacturer
- `GET /api/purchase-orders` — list retail-to-manufacturer purchase orders
- `GET /api/purchase-orders/{id}` — get local PO details
- `POST /api/purchase-orders/{id}/sync` — refresh PO status from Manufacturer

### 4.2 Retail API

- `GET /api/catalog` — list finished printer SKUs and current retail prices
- `POST /api/customer-orders` — create a customer order
- `GET /api/customer-orders` — list customer orders
- `GET /api/customer-orders/{id}` — get customer order details
- `PATCH /api/customer-orders/{id}` — update order status or customer notes
- `GET /api/inventory` — view current finished goods inventory
- `PATCH /api/inventory/{sku}/price` — update retail price for a SKU
- `POST /api/day/advance` — advance simulated day
- `GET /api/day/current` — current simulation day
- `GET /api/events` — query event history
- `POST /api/exports` — export full retailer state as JSON
- `POST /api/imports` — import JSON state

### 4.3 CLI Commands

- `retailer-cli catalog`
- `retailer-cli inventory`
- `retailer-cli customer-orders create`
- `retailer-cli customer-orders list`
- `retailer-cli purchase-orders create`
- `retailer-cli purchase-orders sync`
- `retailer-cli pricing set <sku> <price>`
- `retailer-cli day current`
- `retailer-cli day advance`
- `retailer-cli export`
- `retailer-cli import`

---

## 5. User Experience

### 5.1 Persona

Retailer Manager

The Retailer Manager is responsible for daily operations: reviewing inventory, managing customer demand, placing manufacturer purchase orders, applying price changes, and advancing the simulation.

### 5.2 Typical Workflows

- Review inventory and backorders each morning.
- Create purchase orders to replenish finished printer stock.
- Enter customer orders and verify fulfillment status.
- Advance the simulation day and inspect event logs.
- Export current state for audit or import a saved scenario.

---

## 6. Business Rules

- Customer orders must be fulfilled from finished goods inventory when stock exists.
- If inventory is insufficient, customer orders are backordered automatically.
- Backorders are auto-fulfilled on future simulated days when stock arrives.
- Retail prices must be at least 15% above the Manufacturer wholesale price for that SKU.
- Recommended markup is 30%, but the system may permit lower prices only if they meet the 15% floor.
- All inter-app communication uses REST POST/GET endpoints.
- Every inventory, order, pricing, and shipment state change must be recorded in the event log.

---

## 7. Architecture

### 7.1 Application Layers

- `API` — FastAPI endpoints for retailer operations
- `CLI` — Typer commands for manual and scripted control
- `Services` — business logic, order lifecycle, pricing enforcement, manufacturer client
- `Models` — database entities and persistence
- `Core` — configuration, database connection, shared settings
- `Utilities` — JSON import/export, event logging helpers

### 7.2 Deployment

- The Retailer App runs independently on a configurable port (default `8003`).
- The system uses local SQLite for persistence.
- The Retailer App synchronizes simulated time via `/api/day/advance` and `/api/day/current`.
- Manufacturer integration is configured by endpoint URL in settings.

---

## 8. Development Plan

### Phase 1 — Retailer Core

- Implement basic database models and persistence.
- Implement event logging and simulation state storage.
- Implement customer order creation and inventory fulfillment/backorder behavior.

### Phase 2 — Manufacturer Integration

- Build REST client to place purchase orders with Manufacturer.
- Implement PO lifecycle tracking and delivery reconciliation.
- Add retail pricing enforcement logic.

### Phase 3 — API and CLI

- Implement FastAPI endpoints for customer orders, inventory, pricing, events, and day control.
- Implement Typer CLI commands.
- Add JSON import/export support.

### Phase 4 — Validation and Playback

- Validate application behavior with sample scenarios.
- Ensure event logs capture all transitions.
- Confirm compatibility with existing Provider and Manufacturer simulation interfaces.

---

## 9. Testing Strategy

- Unit tests for business rules, pricing validation, inventory allocation, and backorder fulfillment.
- Integration tests for REST endpoints, CLI flows, and JSON import/export.
- End-to-end scenario tests for day advancement, manufacturer order placement, and state synchronization.

---

## 10. Deployment

- Run locally with `uvicorn app.main:app --reload --port 8003`.
- Support containerization in later iterations.
- Use isolated configuration to run multiple retailer instances on different ports.

---

## 11. Appendices

### 11.1 Config Example

```json
{
  "retailer": {
    "port": 8003,
    "database": "retailer.db",
    "manufacturer_url": "http://localhost:8002",
    "minimum_markup_pct": 15,
    "recommended_markup_pct": 30
  }
}
```

### 11.2 Key REST Interaction

- Retailer → Manufacturer: `POST /api/purchase-orders`
- Retailer → Manufacturer: `GET /api/purchase-orders/{id}`
- Retailer → Manufacturer: `GET /api/day/current`
- Retailer → Manufacturer: `POST /api/day/advance`
