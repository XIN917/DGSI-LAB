# API Reference — DGSI Turn Engine (`api_server.py`)

Base URL: `http://localhost:8000`  
Interactive docs: `http://localhost:8000/docs`  
CORS: open (`*`) — restrict in production.

> **Run persistence:** Run metadata is saved to `logs/runs.json` on every state change and reloaded on server start. `run_id`s survive server restarts. Any run that was `running` at shutdown is marked `interrupted` on reload.

---

## Simulation Control

### `POST /run`
Start a new simulation run. Returns immediately with a `run_id`; the simulation runs in a background thread.

**Request body (JSON):**
| Field | Type | Default | Description |
|---|---|---|---|
| `scenario` | string | `"calm-market"` | Scenario name (must match a file in `scenarios/`) |
| `days` | int | `15` | Total days to simulate |
| `start_day` | int | `1` | First day to run (use to resume a chunked run) |
| `model` | string | `"gemini-3.1-flash-lite"` | LLM model ID (see `GET /models`) |
| `config` | string | `"config/sim.json"` | Path to agent wiring config |
| `verbose` | bool | `false` | Full agent output (default: compact 3-line summary) |
| `full_skill_prompt` | bool | `false` | Send full skill markdown instead of compact role contracts |

**Response `201`:**
```json
{ "run_id": "550e8400-e29b-41d4-a716-446655440000" }
```

---

### `DELETE /run/{run_id}`
Cancel a running simulation. Best-effort — stops after the current day completes.

**Response `200`:**
```json
{ "run_id": "...", "status": "cancelled" }
```

**Errors:** `404` run not found, `409` run already finished/cancelled.

---

### `GET /run/{run_id}/stream`
SSE stream of live log lines. Connect with `EventSource` in the frontend.

**Response:** `text/event-stream`  
Each event is a plain log line: `data: <line>\n\n`  
Special events:
- `data: KEEPALIVE` — heartbeat every 60 s of silence
- `data: STREAM_END` — simulation finished; close the connection

---

### `GET /run/{run_id}/status`
Current status and metadata of a run.

**Response `200`:**
```json
{
  "run_id": "...",
  "status": "running | done | error | cancelled",
  "scenario": "holiday-rush",
  "days": 25,
  "model": "gemini-3.1-flash-lite",
  "elapsed_seconds": 42.3,
  "error": null,
  "result": { ... }   // only present when status == "done"
}
```

---

### `GET /runs`
List all runs in the current server session (active and historical).

**Response `200`:** Array of run summary objects (same fields as `/run/{id}/status` minus `error`/`result`).

---

## Scenario & Config

### `GET /scenarios`
List available scenario files.

**Response `200`:**
```json
[
  { "name": "calm-market",   "path": "scenarios/calm-market.json" },
  { "name": "holiday-rush",  "path": "scenarios/holiday-rush.json" }
]
```

---

### `GET /scenarios/{name}`
Return the full content of a scenario file.

**Response `200`:** Raw scenario JSON object.  
**Errors:** `404` scenario not found.

---

### `GET /models`
List supported LLM model identifiers. Use this to build the model selector in the frontend.

**Response `200`:**
```json
[
  { "id": "gemini-3.1-flash-lite", "label": "Gemini 3.1 Flash Lite", "provider": "google",     "default": true  },
  { "id": "gemma-4-26b",           "label": "Gemma 4 26B",           "provider": "google",     "default": false },
  { "id": "gemini-2.5-flash",      "label": "Gemini 2.5 Flash",      "provider": "google",     "default": false },
  { "id": "gemini-2.5-pro",        "label": "Gemini 2.5 Pro",        "provider": "google",     "default": false },
  { "id": "gemini-2.0-flash",      "label": "Gemini 2.0 Flash",      "provider": "google",     "default": false },
  { "id": "claude-haiku-4-5-20251001", "label": "Claude Haiku 4.5",  "provider": "anthropic",  "default": false },
  { "id": "claude-sonnet-4-6",     "label": "Claude Sonnet 4.6",     "provider": "anthropic",  "default": false },
  { "id": "claude-opus-4-7",       "label": "Claude Opus 4.7",       "provider": "anthropic",  "default": false }
]
```

- `id` — value to pass in `POST /run` body as `model`
- `default: true` — pre-select this in the UI
- Google models require `GEMINI_API_KEY` in `.env`; Anthropic models require the `claude` CLI

---

## Run Data

All run-data endpoints read from archived SQLite snapshots and log files written at the **end** of a run. They return empty/partial data while the run is still in progress.

### `GET /run/{run_id}/logs?page=1&page_size=100`
Paginated agent log lines from all `logs/{scenario}/day-NNN.log` files.

**Query params:** `page` (default 1), `page_size` (default 100).

**Response `200`:**
```json
{
  "run_id": "...",
  "page": 1,
  "page_size": 100,
  "total": 4820,
  "lines": ["=== DAY 1 ...", "$ ./retailer-cli stock", ...]
}
```

---

### `GET /run/{run_id}/kpis`
Daily KPI rows from `logs/{scenario}/run.csv` for this run's scenario.

> **Note:** `logs/{scenario}/run.csv` is cleared at the start of every fresh run of that scenario. This endpoint returns meaningful data only for the latest completed run of a given scenario.

**Response `200`:** Array of objects with fields:
`scenario`, `day`, `demand_mod`, `supply_mod`, `lead_mod`, `price_sensitivity`, `events`, `orders_placed`, `fulfilled`, `backordered`, `stockout`, `fill_rate_pct`

---

### `GET /run/{run_id}/inventory`
Inventory-over-time data queried from archived SQLite databases.

**Response `200`:**
```json
{
  "provider":     [{ "sim_day": 1, "product": "frame_kit", "quantity": 490 }, ...],
  "manufacturer": [...],
  "retailer":     [...]
}
```

---

### `GET /run/{run_id}/prices`
Price history queried from archived SQLite databases.

**Response `200`:** Same shape as `/inventory` but with a `price` field instead of `quantity`.

---

## Charts

### `GET /run/{run_id}/charts`
List generated chart PNG files for this run.

**Response `200`:**
```json
[
  { "name": "scenario_events.png",         "path": "/run/{run_id}/charts/scenario_events.png" },
  { "name": "retailer_fulfillment.png",    "path": "/run/{run_id}/charts/retailer_fulfillment.png" },
  { "name": "manufacturer_stock.png",      "path": "/run/{run_id}/charts/manufacturer_stock.png" },
  { "name": "manufacturer_prices.png",     "path": "/run/{run_id}/charts/manufacturer_prices.png" },
  { "name": "manufacturer_utilisation.png","path": "/run/{run_id}/charts/manufacturer_utilisation.png" },
  { "name": "retailer_stock.png",          "path": "/run/{run_id}/charts/retailer_stock.png" },
  { "name": "retailer_prices.png",         "path": "/run/{run_id}/charts/retailer_prices.png" },
  { "name": "provider_stock.png",          "path": "/run/{run_id}/charts/provider_stock.png" },
  { "name": "provider_prices.png",         "path": "/run/{run_id}/charts/provider_prices.png" }
]
```

---

### `GET /run/{run_id}/charts/{filename}`
Serve a chart PNG directly (use as `<img src="...">` in the frontend).

**Response `200`:** `image/png`  
**Errors:** `404` chart not found.

---

## Services

### `GET /services/status`
Check whether the three simulation services are reachable.

**Response `200`:**
```json
{
  "provider":     { "url": "http://127.0.0.1:8001", "up": true,  "status_code": 200 },
  "manufacturer": { "url": "http://127.0.0.1:8002", "up": true,  "status_code": 200 },
  "retailer":     { "url": "http://127.0.0.1:8003", "up": false, "error": "Connection refused" }
}
```

---

## Typical Frontend Flow

```
1. GET /models          → build model dropdown, pre-select default:true entry
2. GET /scenarios       → build scenario dropdown
3. POST /run            → get run_id
4. EventSource /run/{id}/stream  → show live log lines
5. poll GET /run/{id}/status     → detect "done" or "error"
6. GET /run/{id}/kpis   → render KPI table / fill-rate chart
7. GET /run/{id}/charts → list PNGs
8. <img> /run/{id}/charts/{filename} → embed charts
```
