# DGSI Week 7: Retailer Service Implementation & Full Integration Report

- **Author:** David Morais, Zixin Zhang, Zhipeng Lin and Zhehan Xiang
- **Date:** May 14, 2026
- **Repository:** [https://github.com/XIN917/DGSI-LAB](https://github.com/XIN917/DGSI-LAB)
- **Subject:** Week 7 Challenge — Retailer Development and Supply Chain Integration (Provider ↔ Manufacturer ↔ Retailer)

---

## 1. Executive Summary

This week focused on two primary deliverables: the **ground-up implementation of the new Retailer service** and the **end-to-end integration** of the complete three-tier supply chain. We have successfully connected the Parts Provider, the 3D Printer Manufacturer, and the newly built Retailer into a functional ecosystem. The system now supports a complete lifecycle: from customer demand at the retail storefront to automated production and raw material fulfillment.

## 2. Technical Stack & Service Map

| Service | Port | Primary Tech | Role |
| :--- | :--- | :--- | :--- |
| **Provider** | 8001 | FastAPI, SQLAlchemy | Raw Material Supply |
| **Manufacturer** | 8002 | FastAPI, SQLAlchemy, Typer | Production & Wholesale |
| **Retailer** | 8003 | FastAPI, Async SQLAlchemy, Typer | Consumer Sales & PO Management |

### **Supply Chain Flow Diagram**
![Supply Chain Flow](./docs/sequenceDiagram.png)

## 3. New Retailer Service Implementation

The Retailer service was developed as a modern REST-capable application to manage consumer-facing operations.

### **Architectural Highlights:**
- **FastAPI Framework:** Exposes REST endpoints for catalog sync, order management, and simulation control.
- **Async SQLAlchemy:** Implements a non-blocking database layer for high-concurrency simulation.
- **Retailer CLI:** A dedicated entry point (`retailer-cli`) for administrative tasks like initialization, inventory checks, and manual price setting.
- **Manufacturer REST Client:** A specialized client for secure communication and PO synchronization with the Manufacturer tier.

### **Advanced Business Logic:**
- **15% Minimum Markup Enforcement:** Logic that automatically rejects retail prices failing to meet the mandatory 15% margin over wholesale costs.
- **Backorder Management:** Automated fulfillment system that scans and fulfills pending customer orders immediately upon receiving new stock.
- **Auto-Sync Engine:** Polling logic that reconciles local purchase orders with the Manufacturer's production state during simulation day advancement.

## 4. The Integration Chain (Provider ↔ Manufacturer ↔ Retailer)

The integrated ecosystem ensures a seamless flow of data and goods across three independent services:

1.  **Parts Provider (Port 8001):** Sourcing for raw materials (PCBs, Motors, etc.).
2.  **3D Printer Manufacturer (Port 8002):** The production hub consuming materials and fulfilling wholesale printer orders.
3.  **Consumer Retailer (Port 8003):** The demand driver, managing retail pricing and customer fulfillment.

### **Integrated Workflow Improvements:**
- **Standardized Data Organization:** All services now utilize a top-level `data/` folder for persistence, ensuring the `app/` source folders remain immutable.
- **Unified Simulation Control:** All tiers share a consistent CLI pattern for time management (`day current`, `day advance`).
- **Decoupled REST Sync:** Real-time state synchronization is achieved through robust REST contracts rather than database sharing.

## 5. Automation & Developer Experience

To simplify the orchestration of three distributed services, we introduced a new automation suite:

- **`scripts/start_all.sh`:** A "one-click" startup script that manages background processes and redirects output to a unified `logs/` directory.
- **`scripts/test_scenario.sh`:** A full-chain automation script that executes the entire Week 7 scenario:
    1.  Seeds all three tiers.
    2.  Simulates a customer backorder at the Retailer.
    3.  Triggers a Manufacturer PO and production release.
    4.  Advances simulation time across all services.
    5.  Verifies the final fulfillment and inventory state.

## 6. Bug Fixes & Stability

Key technical hurdles resolved during the integration phase:
- **Manufacturer Schema Fix:** Resolved a missing `wholesale_price` column in the SQLite schema.
- **Production CLI:** Implemented the missing `production release` command to enable the production lifecycle.
- **Path Standardization:** Corrected directory-traversal bugs and moved all databases to clean, service-root `data/` folders.

## 7. Final Status

| Metric | Status | Verification |
| :--- | :--- | :--- |
| **Retailer App** | ✅ 100% | Unit & Integration tests passing (12/12) |
| **Integration Chain** | ✅ 100% | Full handshake verified via `test_scenario.sh` |
| **Automation** | ✅ 100% | Background server orchestration functional |
| **Documentation** | ✅ 100% | Updated README, TESTING, and INTEGRATION docs |

## 8. Known Issues

- **Bcrypt Version Warning:** A non-breaking `AttributeError: module 'bcrypt' has no attribute '__about__'` occurs in some environments during seeding. This is a known issue with the `passlib` library and Python 3.14+, but it does not affect database security or functionality.
- **Port Conflicts:** Rapid restarts can sometimes leave ports in a `TIME_WAIT` state, requiring a brief delay before using `./scripts/start_all.sh`.

---
**Testing Command:** `./scripts/test_scenario.sh`
**Documentation:** Refer to `docs/TESTING.md` for manual walkthroughs.
