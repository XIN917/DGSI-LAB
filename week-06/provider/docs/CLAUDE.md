# Provider ↔ Manufacturer Integration Guide

**Date:** 1 May 2026  
**Status:** Phase 2 Implementation Complete  
**Scope:** Manufacturer can now query provider API, place orders, and poll for delivery status

---

## Architecture

Two independent FastAPI services communicate via REST API:

```
┌─────────────────────┐          ┌──────────────────────┐
│   Provider App      │          │  Manufacturer App    │
│   (Port 8001)       │          │   (Port 8000/8501)   │
│                     │          │                      │
│  ┌─────────────────┐│          │ ┌──────────────────┐ │
│  │ REST API        ││◄─────────┼─┤ ProviderClient   │ │
│  │ /api/catalog    ││  httpx   │ │ (HTTP client)    │ │
│  │ /api/orders     ││          │ └──────────────────┘ │
│  │ /api/stock      ││          │                      │
│  │ /api/day/*      ││          │ ┌──────────────────┐ │
│  └─────────────────┘│          │ │ SimulationEngine │ │
│         │           │          │ │ (polls on day    │ │
│  ┌─────────────────┐│          │ │  advance)        │ │
│  │  SQLite DB      ││          │ └──────────────────┘ │
│  │  - products     ││          │                      │
│  │  - pricing      ││          │ ┌──────────────────┐ │
│  │  - stock        ││          │ │ SQLite DB        │ │
│  │  - orders       ││          │ │ + provider_order │ │
│  │  - events       ││          │ │   _id field      │ │
│  └─────────────────┘│          │ └──────────────────┘ │
│                     │          │                      │
└─────────────────────┘          └──────────────────────┘
```

---

## Implementation Details

### 1. ProviderClient Service

**File:** `manufacturer/app/services/provider_client.py`

Synchronous HTTP client using `httpx.Client()` for connection pooling.

**Methods:**
- `get_catalog()` - Fetch product list with pricing
- `get_stock()` - Check inventory levels
- `place_order(buyer, product_id, quantity)` - Create purchase order
- `get_order_status(order_id)` - Poll remote order status
- `get_current_day()` - Get provider's current simulation day
- `advance_day()` - Advance provider's day counter

**Error Handling:**
- All HTTP errors wrapped in `ProviderClientError` exception
- Errors logged with full context
- Consumer code must handle exceptions explicitly

### 2. Configuration

**File:** `manufacturer/app/core/config.py`

```python
PROVIDER_API_URL: str = "http://localhost:8001"  # Set via .env
PROVIDER_TIMEOUT_SECONDS: int = 10
```

**Usage:**
```bash
# Override via environment
export PROVIDER_API_URL="http://192.168.1.100:8001"
```

### 3. Dependency Injection

**File:** `manufacturer/app/api/dependencies.py`

```python
def get_provider_client() -> ProviderClient:
    settings = get_settings()
    return ProviderClient(
        base_url=settings.PROVIDER_API_URL,
        timeout=settings.PROVIDER_TIMEOUT_SECONDS,
    )
```

Used in endpoints and services via FastAPI `Depends()`.

### 4. Order Polling in Day Advance

**File:** `manufacturer/app/services/simulation_engine.py`

New method `_poll_provider_orders()` called in `advance_day()` before other processing:

```python
# Step 0: Poll provider for order status updates
provider_events = self._poll_provider_orders()
events.extend(provider_events)

# Step 1-4: Regular processing...
```

**Polling Logic:**
1. Query all pending POs with `provider_order_id` set
2. For each, call `provider.get_order_status(provider_order_id)`
3. If remote status is `delivered`:
   - Update local PO status to "delivered"
   - Add materials to local inventory
   - Log event
4. If remote status is `shipped`:
   - Update local PO status (no inventory yet)
5. Catch all exceptions - don't block day_advance

**Key Design Decision:** Network failures are logged but don't stop the simulation.

### 5. Purchase Order Schema Extension

**File:** `manufacturer/app/models/purchase_order.py`

New fields added:
```python
provider_name: Column(String(100), nullable=True)
provider_order_id: Column(Integer, nullable=True)
```

These track which provider an order came from and the remote order ID for polling.

### 6. Create PO from Provider Endpoint

**File:** `manufacturer/app/api/endpoints/purchase_orders.py`

New endpoint: `POST /api/purchase-orders/from-provider`

**Request:**
```json
{
  "product_id": 3,
  "quantity": 50
}
```

**Response:**
```json
{
  "id": 1,
  "supplier_id": 1,
  "supplier_name": null,
  "product_name": "provider_product_3",
  "quantity_ordered": 50.0,
  "quantity_delivered": 0.0,
  "unit_cost": 20.9,
  "total_cost": 1045.0,
  "order_date": "2026-05-01T00:00:00",
  "expected_delivery": "2026-05-06T00:00:00",
  "actual_delivery": null,
  "status": "pending"
}
```

**Process:**
1. Call `provider.place_order()` - creates remote order
2. Extract remote order ID from response
3. Create local PurchaseOrder with `provider_order_id` set
4. Log event for audit trail
5. Return PO details

**Error Handling:**
- `ProviderClientError` → HTTP 503 (Service Unavailable)
- Other errors → HTTP 500

---

## Integration Flow - 5-Day Scenario

### Day 1: Place Order

```bash
# Terminal 1: Provider API running on 8001
provider-cli serve --port 8001

# Terminal 2: Manufacturer API running on 8000
PYTHONPATH=. uvicorn app.main:app --reload --port 8000

# Terminal 3: Place purchase order with provider
curl -X POST http://localhost:8000/api/purchase-orders/from-provider \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer <token>" \
  -d '{"product_id": 3, "quantity": 50}'

# Expected: PO created locally with provider_order_id=1
```

### Days 2-5: Daily Cycle

```bash
# Advance manufacturer's day. This polls provider orders and advances
# the provider day once as part of the integration cycle.
curl -X POST http://localhost:8000/api/simulation/advance

# Check PO status at any point
curl http://localhost:8000/api/purchase-orders/1

# Verify inventory when delivered
curl http://localhost:8000/api/inventory
```

**Expected Timeline (with 5-day lead time):**
- Day 1: Order placed (pending)
- Day 4: Order ships (shipped)
- Day 6: Order arrives (delivered) → inventory updated automatically

---

## Testing Checklist

- [x] Provider API running on port 8001/temporary smoke-test port
- [x] Manufacturer API running on port 8000/temporary smoke-test port
- [x] `POST /api/purchase-orders/from-provider` creates order in provider
- [x] Remote order appears in `GET /api/orders` on provider side
- [x] Polling updates local PO status during day advance
- [x] Inventory increases when order status becomes "delivered"
- [ ] Event logs in both databases show consistent story
- [x] Network errors logged but don't crash day_advance
- [ ] Response times < 500ms for catalog queries

---

## Debugging

### Provider Client Not Connecting

Check configuration:
```bash
curl http://localhost:8001/api/catalog  # Verify provider is running
```

Check logs for timeout errors:
```bash
# Increase timeout if needed
export PROVIDER_TIMEOUT_SECONDS=20
```

### Orders Not Updating Status

Verify polling is running:
```python
# In SimulationEngine._poll_provider_orders() method
# Check logs for "Failed to poll" messages
```

Check remote order status:
```bash
curl http://localhost:8001/api/orders/1
```

### Schema Migration Issues

New fields `provider_order_id` and `provider_name` are nullable, so existing databases work.

If you need fresh state:
```bash
rm manufacturer.db
# App will reinitialize on next run
```

---

## Known Limitations

1. **Sync Only:** Uses `httpx.Client()` (sync), not async. Full async refactor out of scope.
2. **Single Provider:** Currently hardcoded to "ChipSupply Co". Multi-provider support deferred.
3. **No Retry Logic:** Network failures are logged but not retried. Acceptable for simulation context.
4. **Datetime Handling:** Provider uses simulation days (integers), manufacturer uses datetime. Conversion happens at boundary.

---

## Future Enhancements

- [ ] Add retry logic with exponential backoff
- [ ] Support multiple providers with configuration
- [ ] Dashboard widget showing provider order status
- [ ] Async refactor for better concurrency
- [ ] Provider authentication (API keys)
- [ ] Order cancellation propagation to provider
