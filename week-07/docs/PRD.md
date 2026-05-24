# Supply Chain Ecosystem PRD: Week 7

**Version**: 1.0 (Final Integration)
**Status**: Active
**AI Assistant**: Claude Code

---

## 1. Executive Summary

This project simulates a complete, end-to-end supply chain consisting of three independent services: a **Provider**, a **Manufacturer**, and a **Retailer**. The ecosystem models the lifecycle of 3D printers from raw material procurement to final consumer sale.

The primary goal of Week 7 is to complete the chain by adding the Retailer, synchronizing the simulation timing across all nodes, and introducing automated orchestration via a Turn Engine and AI agents (Claude Code).

---

## 2. Core Architecture

### 2.1 Service-Oriented Design
The system is composed of three decoupled Python services. Each service is "blind" to the others' databases and internal states, communicating exclusively via REST APIs.

| Service | Port | Role | Primary Entity |
| :--- | :--- | :--- | :--- |
| **Provider** | 8001 | Raw material supplier | Components (PCBs, Motors) |
| **Manufacturer** | 8002 | Factory & Wholesaler | 3D Printers (P3D-Classic, P3D-Pro) |
| **Retailer** | 8003 | Consumer storefront | Consumer Demand & Fulfillment |

### 2.2 Shared Principles
- **REST-Only Communication**: No shared database access.
- **Independent Persistence**: Each service uses its own SQLite database.
- **Unified Simulation Clock**: All services must be in the same "Simulated Day" to maintain consistency.
- **Auditability**: Every state-changing event is recorded in a local `event_log` table.
- **Persistence Portability**: Full state can be exported/imported via JSON for scenario playback.

---

## 3. Component Specifications

### 3.1 Provider (The Upstream)
- **Catalog**: Managed parts with lead times and volume-based pricing tiers.
- **Fulfillment**: Receives POs from the Manufacturer, tracks lead times, and marks orders as `delivered` once the simulated time has passed.
- **Inventory**: Simple stock management for raw materials.

### 3.2 Manufacturer (The Midstream)
- **Bill of Materials (BOM)**: Defines what parts are needed for each printer model.
- **Production Capacity**: Limited units per day (default: 250).
- **Dual Role**: 
  - **Buyer**: Purchases raw materials from the Provider.
  - **Seller**: Sells finished printers to the Retailer at wholesale prices.
- **Finished Goods**: Production logic moves completed units into a "finished goods" inventory for immediate retailer fulfillment.

### 3.3 Retailer (The Downstream)
- **Consumer Demand**: Generates random customer orders based on price elasticity and market signals.
- **Pricing Enforcement**: Must maintain a minimum 15% markup (recommended 30%) over Manufacturer wholesale prices.
- **Backorder Logic**: If stock is unavailable for a customer, the order is queued as a `backorder` and auto-fulfilled when new stock arrives from the Manufacturer.

---

## 4. Simulation Engine (Turn-Based)

### 4.1 Turn Orchestration
A central `turn_engine.py` script acts as the conductor for the entire ecosystem. Each turn (Simulated Day) follows a strict sequence:
1. **Market Signals**: Read external "signals" (e.g., demand modifiers) from a scenario file.
2. **Demand Injection**: Generate customer orders for each Retailer.
3. **Agent Decision Phase (Downstream-to-Upstream)**:
   - **Retailer Turn**: Decides how many printers to buy from the Manufacturer.
   - **Manufacturer Turn**: Decides how many parts to buy from the Provider and which orders to release to production.
   - **Provider Turn**: Processes shipments and adjusts prices.
   - *Rationale*: Downstream actors decide first so upstream actors can react to new demand within the same turn.
4. **Time Advancement**: Once all decisions are made, the engine sends a `/api/day/advance` request to all services.

### 4.2 Standardized Timing Logic
To prevent synchronization drift, all services must:
- Start at **Day 0**.
- Use **"Increment then Process"** logic: Increment the day counter *before* processing that day's arrivals, production, or demand.

---

## 5. Agent Skills (Claude Code Integration)

The system uses **Claude Code** to play operational roles.
- **Skill Files**: Markdown documents (e.g., `skills/manufacturer-manager.md`) that define the agent's role, available commands, and decision framework.
- **Execution**: The Turn Engine calls Claude Code via `subprocess.run(["claude", "--print", "--prompt", ...])` to perform a "no-human-in-the-loop" turn.
- **Constraints**: Agents are forbidden from advancing the day themselves; they only make operational decisions (ordering stock, releasing production, setting prices).

---

## 6. Operational Workflows

### 6.1 Lifecycle Management
- **`scripts/start_all.sh`**: Backgrounds all three API servers and initializes logs.
- **`turn_engine.py`**: Runs the multi-day simulation scenario.
- **`scripts/test_scenario.sh`**: A deterministic verification script for CI/CD and quick health checks.

### 6.2 Data Integrity
Each app provides:
- **`export <file>`**: Dumps the complete database state to JSON.
- **`import <file>`**: Wipes current state and restores from JSON.
- This allows researchers to "pause" the supply chain, analyze failure points, and "resume" or "branch" the simulation.

---

## 7. Success Criteria
- [x] Three apps running on independent ports.
- [x] Retailer successfully places orders with Manufacturer.
- [x] Manufacturer successfully places orders with Provider.
- [x] All three services advance days in lock-step.
- [x] Turn engine can run a 5+ day simulation with at least one Claude agent active.
- [x] Event logs across all apps tell a coherent, chronological story.
