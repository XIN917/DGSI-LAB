# Provider Service — DGSI Week 8

Parts supplier service for the DGSI supply chain simulation. Runs on `:8001`.

## Setup

Run from the repo root — `scripts/setup_envs.sh` creates `provider/venv/` automatically:

```bash
./scripts/setup_envs.sh
```

Or manually:

```bash
cd provider
uv venv venv
source venv/bin/activate
uv pip install -r requirements.txt
uv pip install -e .
```

## Start

```bash
provider/venv/bin/provider-cli serve --port 8001
```

API docs: `http://localhost:8001/docs`

## CLI Commands

```bash
provider-cli day current
provider-cli catalog
provider-cli stock
provider-cli orders list [--status pending]
provider-cli orders show <id>
provider-cli restock <product> <quantity>
provider-cli price set <product> <tier> <price>
provider-cli seed
```

## Testing

```bash
cd provider
venv/bin/pytest tests/ -v
```

## Notes

- **Never call `day advance` directly** — the turn engine does that via `POST /api/day/advance`.
- Database: `provider/data/provider.db` (git-ignored).
- Seed data initialised by `provider-cli seed` (called automatically by `scripts/reset_all.sh`).
