# Retailer App — Testing Guide

## Running Tests

```bash
cd retailer
venv/bin/pytest tests/ -v

# Focused delivery-sync regression test (run before full scenario runs):
venv/bin/pytest tests/test_services/test_purchase_order_sync.py
```

Always use `retailer/venv/bin/pytest`, not `.venv/bin/pytest`.

---

## Test Suites

| File | What it covers |
|---|---|
| `test_api/test_endpoints.py` | Day and catalog HTTP endpoints via async client |
| `test_services/test_retailer_service.py` | Core service methods: day counter, catalog, customer orders, advance |
| `test_services/test_business_logic.py` | 15% markup enforcement, backorder auto-fulfillment on stock arrival |
| `test_services/test_retailer_markup.py` | Markup rule unit test with mocked catalog |
| `test_services/test_purchase_order_sync.py` | PO sync runs until terminal state (pre-run regression) |

---

## Key Notes

- **Service is synchronous** — `RetailerService(db=session)`. Tests use the sync `db_session` fixture, not `async_session_local`.
- **Pricing tests mock `get_catalog`** — pricing enforcement calls the live manufacturer service to get wholesale prices. Tests mock this with the correct seed prices (Classic €195, Pro €290) so they don't require the manufacturer to be running.
- **Async API tests** (`test_endpoints.py`) use `aiosqlite` and `greenlet` — both installed via `requirements.txt`.
- **Never call `day advance` directly** in tests or manually — the turn engine does that via `POST /api/day/advance`.

---

## CLI Testing

Start the service first:

```bash
retailer/venv/bin/retailer-cli serve --port 8003
```

Then in another terminal:

```bash
retailer-cli day current
retailer-cli stock
retailer-cli customers orders
retailer-cli customers order <id>
retailer-cli fulfill <order_id>
retailer-cli backorder <order_id>
retailer-cli purchase list
retailer-cli purchase create <model> <qty>
retailer-cli price list
retailer-cli price set <model> <price>
```

---

## Troubleshooting

**`ModuleNotFoundError: No module named 'aiosqlite'`** — run `uv pip install --python venv/bin/python aiosqlite`.

**`No module named 'greenlet'`** — run `uv pip install --python venv/bin/python greenlet`.

**Database errors** — reset with `scripts/reset_all.sh` from the repo root, or delete `retailer/data/retailer.db` and run `retailer-cli init`.
