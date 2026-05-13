# Project State

**Last Updated:** 1 May 2026 (post Phase 3 validation)

---

## Milestones

| Milestone | Status | Date Completed |
|-----------|--------|----------------|
| PRD created | ✅ Complete | 30 April 2026 |
| Provider app structure | ✅ Complete | 30 April 2026 |
| Database models | ✅ Complete | 30 April 2026 |
| Seed data (11 products) | ✅ Complete | 30 April 2026 |
| FastAPI endpoints | ✅ Complete | 30 April 2026 |
| Typer CLI | ✅ Complete | 30 April 2026 |
| Order lifecycle logic | ✅ Complete | 30 April 2026 |
| JSON export/import | ✅ Complete | 30 April 2026 |
| **Manufacturer API integration (httpx client)** | ✅ Complete | 1 May 2026 |
| **Manufacturer purchase order polling** | ✅ Complete | 1 May 2026 |
| **Provider integration documentation (CLAUDE.md)** | ✅ Complete | 1 May 2026 |
| Provider app testing | ✅ Complete | 1 May 2026 |
| 5-day manual scenario validation | ✅ Complete | 1 May 2026 |
| **Demo hardening and repeatability** | ⏳ Pending | — |

---

## Task Status

### Provider App Build

- [x] Create directory structure
- [x] Create database models (Product, PricingTier, Stock, Order, Event, SimState)
- [x] Create seed data with 11 products
- [x] Build FastAPI endpoints (catalog, orders, stock, day)
- [x] Build Typer CLI commands
- [x] Implement order lifecycle (pending → confirmed → shipped → delivered)
- [x] Add JSON export/import functionality
- [x] Create requirements.txt and pyproject.toml

### Manufacturer Integration (Week 6)

- [x] Manufacturer has Supplier and PurchaseOrder models
- [x] Manufacturer has purchase_orders API endpoints
- [x] Add httpx client to call provider API
- [x] Implement catalog fetch from provider (via ProviderClient)
- [x] Implement order placement against provider (POST /api/purchase-orders/from-provider)
- [x] Implement polling for order status updates (SimulationEngine._poll_provider_orders)
- [x] Add provider_order_id and provider_name fields to PurchaseOrder schema
- [x] Test end-to-end scenario

---

## Build Steps

### 1. Provider App Setup

```bash
cd /Users/xin/UPC/2025-Q2/DGSI/week-06/provider

# Create virtual environment (if needed)
python -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Initialize database
PYTHONPATH=. python -m provider.app.seed
```

### 2. Start Provider API

```bash
# Option 1: Direct uvicorn
PYTHONPATH=. uvicorn provider.app.main:app --host 0.0.0.0 --port 8001

# Option 2: Via CLI
PYTHONPATH=. python -m provider.app.cli serve --port 8001
```

### 3. Test Provider CLI

```bash
# List catalog
PYTHONPATH=. python -m provider.app.cli catalog list

# Show stock
PYTHONPATH=. python -m provider.app.cli stock

# Show current day
PYTHONPATH=. python -m provider.app.cli day current

# Advance day
PYTHONPATH=. python -m provider.app.cli day advance
```

### 4. Verify API Endpoints

```bash
# Test catalog
curl http://localhost:8001/api/catalog

# Test stock
curl http://localhost:8001/api/stock

# Test current day
curl http://localhost:8001/api/day/current

# Place order
curl -X POST http://localhost:8001/api/orders \
  -H "Content-Type: application/json" \
  -d '{"buyer": "manufacturer", "product_id": 3, "quantity": 50}'
```

---

## Current State

### Provider App
- **Status:** ✅ Running and tested (port 8001)
- **Database:** provider.db (11 products seeded)
- **API Endpoints:** All endpoints implemented and working
- **CLI Commands:** All commands implemented
- **Order Lifecycle:** pending → confirmed → shipped → delivered
- **Testing:** Manual via curl completed ✓

### Manufacturer App
- **Status:** ✅ Integrated with provider (port 8000 API / 8501 dashboard)
- **Provider Integration:** 
  - ✅ ProviderClient service created (HTTP client)
  - ✅ Configuration with PROVIDER_API_URL
  - ✅ Dependency injection registered
  - ✅ Order polling in day_advance()
  - ✅ POST /api/purchase-orders/from-provider endpoint
  - ✅ PurchaseOrder schema extended (provider_order_id, provider_name)
- **Next Action:** Demo hardening and repeatability

---

## Next Steps

**PHASE COMPLETE: Manufacturer ↔ Provider Integration**

**PHASE COMPLETE: End-to-End 5-Day Scenario Validation**

Validated on temporary local databases with Provider API on port 18011 and Manufacturer API on port 18010:
- Manufacturer placed `POST /api/purchase-orders/from-provider` successfully
- Provider order was created and reached `delivered`
- Provider shipped on day 4 and delivered on day 5, with provider current day at 6 after six manufacturer advances
- Manufacturer PO reached `delivered` with `actual_delivery` set to `2026-04-06`
- Manufacturer inventory gained `provider_product_3` quantity `50`

**PHASE 4: Demo Hardening and Repeatability** (Next)

- Create a single scripted demo command or documented checklist for the full flow
- Add an automated cross-service integration test if time allows
- Review event logs in both databases for a clean audit story
- Confirm the Streamlit/dashboard surface shows provider-backed POs clearly
- Prepare reset instructions for demo databases

### Scenario Overview

**Day 1:** Manufacturer places order with provider
- Call `POST /api/purchase-orders/from-provider` → order created in both systems
- Order status: pending (5-day lead time)

**Days 2-6:** Daily advancement with polling
- Each day: `POST /api/simulation/advance` on manufacturer
  - Triggers polling for remote order updates
  - Advances provider simulation day once
  - Checks if order status changed (pending → shipped → delivered)
  - Auto-adds inventory when delivered
- Do not also manually call `POST /api/day/advance` on provider during this flow, or the provider will advance twice per manufacturer day.

**Success Metrics:**
- [ ] Remote order appears in provider's order list
- [ ] Order transitions: pending → shipped → delivered
- [ ] Manufacturer inventory updates on delivery
- [ ] Event logs show consistent story across both databases
- [ ] No errors or network timeouts
- [ ] Scenario repeatable (place second order)

### Manual Test Commands

```bash
# Terminal 1: Provider API
cd provider && provider-cli serve --port 8001

# Terminal 2: Manufacturer API  
cd manufacturer && PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 3: Test commands
# 1. Place order from provider
curl -X POST http://localhost:8000/api/purchase-orders/from-provider \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"product_id": 3, "quantity": 50}'

# 2. Check provider's order (should appear)
curl http://localhost:8001/api/orders

# 3-6. Advance manufacturer daily and check statuses
# Manufacturer polling also advances the provider simulation day.
curl -X POST http://localhost:8000/api/simulation/advance

# Monitor: Check PO status and inventory
curl http://localhost:8000/api/purchase-orders/1
curl http://localhost:8000/api/inventory
```

### Documentation

- **Implementation Guide:** `/provider/docs/CLAUDE.md`
- **Architecture Diagram:** See CLAUDE.md
- **Integration Flow:** See CLAUDE.md (5-Day Scenario section)

---

## Notes

- Provider app follows the same architecture as manufacturer (FastAPI + SQLAlchemy + Typer)
- Order lifecycle: pending → confirmed → shipped → delivered
- Minimum lead time: 1 day (Ironclad Rule)
- Event logging enabled for audit trail
- **Integration:** Manufacturer uses httpx.Client (sync) for provider communication
- **Error Handling:** Network failures logged but don't block day_advance
- **Schema:** New fields (provider_order_id, provider_name) added to PurchaseOrder (nullable)
- **Configuration:** PROVIDER_API_URL can be overridden via environment variable
