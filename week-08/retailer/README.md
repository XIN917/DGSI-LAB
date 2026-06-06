# Retailer Service — DGSI Week 8

Retail store service for the DGSI supply chain simulation. Runs on `:8003`.

## Setup

Run from the repo root — `scripts/setup_envs.sh` creates `retailer/venv/` automatically:

```bash
./scripts/setup_envs.sh
```

Or manually:

```bash
cd retailer
uv venv venv
source venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
```

## Start

```bash
retailer/venv/bin/retailer-cli serve --port 8003
```

API docs: `http://localhost:8003/docs`

## CLI Commands

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
retailer-cli init
```

## Testing

```bash
cd retailer
venv/bin/pytest tests/ -v

# Focused delivery-sync regression test (run before full scenario runs):
venv/bin/pytest tests/test_services/test_purchase_order_sync.py
```

## Notes

- **Never call `day advance` directly** — the turn engine does that via `POST /api/day/advance`.
- Database: `retailer/data/retailer.db` (git-ignored).
- `pytest` is included in `requirements.txt` — use `retailer/venv/bin/pytest`, not `.venv/bin/pytest`.
