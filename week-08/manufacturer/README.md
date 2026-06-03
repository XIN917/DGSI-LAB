# Manufacturer Service — DGSI Week 8

3D printer factory service for the DGSI supply chain simulation. Runs on `:8002`.

## Setup

Run from the repo root — `scripts/setup_envs.sh` creates `manufacturer/venv/` automatically:

```bash
./scripts/setup_envs.sh
```

Or manually:

```bash
cd manufacturer
uv venv venv
source venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
```

## Start

```bash
manufacturer/venv/bin/manufacturer-cli serve --port 8002
```

API docs: `http://localhost:8002/docs`

## CLI Commands

```bash
manufacturer-cli day current
manufacturer-cli stock
manufacturer-cli sales orders
manufacturer-cli sales order <id>
manufacturer-cli production status
manufacturer-cli production release <order_id>
manufacturer-cli capacity
manufacturer-cli suppliers list
manufacturer-cli suppliers catalog <name>
manufacturer-cli purchase list
manufacturer-cli purchase create --supplier <name> --product <id> --qty <n>
manufacturer-cli price list
manufacturer-cli price set <model> <price>
manufacturer-cli seed
```

## Testing

```bash
cd manufacturer
venv/bin/pytest tests/ -v

# Focused delivery-sync regression test (run before full scenario runs):
venv/bin/pytest tests/test_api/test_day_advance.py -W error
```

## Notes

- **Never call `day advance` directly** — the turn engine does that via `POST /api/day/advance`.
- `manufacturers/providers.json` must exist and point to `http://127.0.0.1:8001` — tracked in git.
- Database: `manufacturer/data/manufacturer.db` (git-ignored).
- Auth endpoints were removed in the Week 8 refactor — do not re-add them.
