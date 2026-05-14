# 3D Printer Production Simulator — Phase 2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Implement the core simulation logic within the `SimulationEngine`, `OrderService`, and `InventoryService`.

**Business Logic Requirements:**
1.  **Demand Generation**: Simple random distribution (1-3 new orders per day).
2.  **Partial Production**: Factory processes units up to daily capacity. If an order is partially completed, it continues on the next shift.
3.  **Strict Reservations**: Materials are reserved at the time of order "Release". Production only proceeds if materials are already reserved, preventing mid-shift shortages.

---

## Task 1: Purchase Order (PO) Delivery Logic

**Files:**
- Modify: `app/services/simulation_engine.py` (implement `_process_purchase_orders`)

- [ ] **Step 1: Implement PO arrival logic**
  - Query all `PurchaseOrder` with status `pending` or `partial`.
  - Check if `expected_delivery` <= `self.current_date`.
  - For arriving POs:
    - Update `Inventory.quantity` for the product.
    - Update `PurchaseOrder.status` to `delivered`.
    - Create an `EventLog` entry of type `po_arrived`.

---

## Task 2: Order Processing & Capacity Management

**Files:**
- Modify: `app/services/simulation_engine.py` (implement `_process_manufacturing_orders`)
- Modify: `app/services/order_service.py` (add `produce_units` method)

- [ ] **Step 1: Add `produce_units` to `OrderService`**
  - Method should take `order_id` and `quantity_to_produce`.
  - Update `ManufacturingOrder.quantity_produced`.
  - If `quantity_produced` >= `quantity_needed`, set status to `completed` and set `completed_date`.
  - Consume materials from `Inventory` (moving from `reserved_quantity` to `quantity` subtraction) via `InventoryService.consume`.

- [ ] **Step 2: Implement `_process_manufacturing_orders` in `SimulationEngine`**
  - Get all orders with status `released`, sorted by `created_date` (FIFO).
  - Track remaining daily capacity (from `settings.CAPACITY_PER_DAY`).
  - For each order:
    - Calculate how many units can be produced today (min of `remaining_order_qty` and `remaining_capacity`).
    - Call `OrderService.produce_units`.
    - Create `EventLog` entries for production steps and order completion.
    - Subtract from `remaining_capacity`. Stop if capacity is 0.

---

## Task 3: Demand Generation Logic

**Files:**
- Modify: `app/services/simulation_engine.py` (implement `_generate_demand`)

- [ ] **Step 1: Implement random demand**
  - Generate a random number of new orders (1-3).
  - For each new order:
    - Randomly select a `ProductModel`.
    - Randomly select a quantity (e.g., 5-20 units).
    - Call `OrderService.create`.
    - Create `EventLog` entry of type `demand_generated`.

---

## Task 4: Inventory Snapshots & Event Logging

**Files:**
- Modify: `app/services/simulation_engine.py` (implement `_take_inventory_snapshot`)

- [ ] **Step 1: Implement daily snapshots**
  - Loop through all `Inventory` items.
  - Create an `EventLog` entry of type `inventory_snapshot` containing a JSON blob of the current state.

---

## Task 5: Verification & Unit Tests

**Files:**
- Create: `tests/test_services/test_phase_2_logic.py`

- [ ] **Step 1: Verify the full cycle**
  - Create a test that advances the day multiple times.
  - Assert that POs arrive on the correct day.
  - Assert that production correctly consumes capacity and materials.
  - Assert that demand is generated.
