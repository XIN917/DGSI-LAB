# DGSI Week 7 - Project Context

> This file is the single source of truth for any AI assistant (Claude, Gemini, etc.) picking up this project.
> Read this before doing anything else.

## What This Is

A turn-based supply chain simulation with three decoupled services:

| Service | Port | Role |
|---|---|---|
| Provider | 8001 | Raw materials supplier |
| Manufacturer | 8002 | 3D printer factory |
| Retailer | 8003 | Consumer store |

Services communicate only via REST. No shared databases. Each service has its own SQLite DB in its own `data/` subdirectory (`manufacturer/data/`, `retailer/data/`, `provider/data/`).

## Quick Start

```bash
# 1. Reset to clean Day 0 state (stops services, wipes DBs, re-seeds, restarts)
./scripts/reset_all.sh

# 2. Run simulation (N days)
python3 turn_engine.py config/sim.json scenarios/smoke-test.json 3
```

## Scripts

| Script | What it does |
|---|---|
| `./scripts/setup_envs.sh` | Create venvs and install deps for all services |
| `./scripts/start_all.sh` | Launch all three services in background |
| `./scripts/reset_all.sh` | Stop services, delete all `.db` files, re-seed, restart |
| `./scripts/test_scenario.sh` | Deterministic (no-agent) health check |
| `pkill -f 'cli serve'` | Stop all services |

**Important**: `reset_all.sh` must stop running services before deleting DBs. If services are running when DBs are deleted, they keep file handles open to the old (deleted) inodes — the server and CLI end up reading/writing different files silently. Always use `reset_all.sh` rather than deleting DBs manually.

## Turn Engine (`turn_engine.py`)

Orchestrates one simulated day:
1. Read scenario signal for the day
2. Inject customer orders into retailer (stochastic demand generator)
3. Run each role's agent or stub
4. Advance all services to next day

**Invocation:**
```bash
python3 turn_engine.py config/sim.json scenarios/smoke-test.json <days> [-v]
```

**Agent call (manufacturer only for Week 7):**
```bash
claude --print --dangerously-skip-permissions --allowedTools Bash \
  --model claude-haiku-4-5-20251001 "<prompt>"
```

Key implementation decisions:
- `--dangerously-skip-permissions`: required because subprocess has no TTY — without it the agent blocks silently waiting for interactive approval
- `shell=True` with explicit `PATH=/opt/homebrew/bin:...`: symlink resolution fails when `cwd` changes; shell=True lets the shell find `claude` the same way the terminal does
- `stdin=subprocess.DEVNULL`: prevents subprocess blocking on stdin
- **Pre-fetch optimisation**: turn engine runs all read-only CLI commands (`stock`, `sales orders`, `capacity`, `production status`, `price list`, `purchase list`, `suppliers list`) before calling the agent and injects the output into the prompt. Agent skips assessment and goes straight to decisions. Cuts execution from ~70s to ~25s.
- **Prompt notes injection**: turn engine appends role-specific runtime notes to the prompt (e.g. Day 1 price freeze, supplier name reminder). This guards against known agent failure modes without modifying the skill file.
- **UI**: uses `rich` library for formatted output (panels, rules, colour). `Live`/`Spinner` was removed — it interfered with subprocess TTY detection causing hangs.

## Agent Skills

- Skill files live in `skills/` (centralised, not per-service)
- Week 7 scope: **manufacturer only** — `skills/manufacturer-manager.md`
- Retailer and provider are stubs (`"skill": null` in `config/sim.json`)
- **Do not modify skill files** — they are provided by the professor. Runtime guardrails go in the turn engine prompt instead.

### `skills/manufacturer-manager.md` — verified complete

Covers: role, available commands, DO NOT rules, 5-step decision framework, market signal interpretation, summary requirement.

**Price floor hardcoded**: minimum wholesale prices are P3D-Classic €163, P3D-Pro €246 (BOM material cost + 15%). These are explicit in the skill file because `price list` does not expose component costs — the agent cannot calculate the floor itself.

## Config Files

- `config/sim.json` — service URLs, paths, skill assignments
- `scenarios/smoke-test.json` — steady-state scenario, demand modifier 1.0, days 1–10

## Simulation Timing Rules

All services follow **"Increment then Process"** on day advance:
1. Increment day counter
2. Advance simulation date
3. Process logic for the new day
4. Persist and return

Day counters must stay in lock-step. The turn engine calls `POST /api/day/advance` on all services at the end of each turn.

## Agent Log Location

```
logs/day-001-manufacturer.log
logs/day-002-manufacturer.log
...
```

Logs are cleared on every `reset_all.sh` run.

## Verified Agent Behaviour (Smoke Test)

| Day | Sales orders | Price action |
|-----|-------------|--------------|
| 1 | Active (Retailer API fixed) | Prices held — no history yet |
| 2 | Active | Prices held — 1 day below threshold, rule not met |
| 3 | Active | P3D-Classic €1200 → €1140 (−5%); P3D-Pro held at €246 floor |

*Note: Sales orders are now correctly injected into the Retailer via the fixed `/api/customer-orders` JSON endpoint.*

## Week 7 Integration Fixes (Final Audit)

- **Missing CLI**: Created `retailer/retailer-cli` to match ecosystem patterns.
- **API Alignment**: Updated Retailer `create_customer_order` to support JSON payloads (customer, model, quantity) to match `turn_engine.py` demand generation. Removed trailing slashes from all routes to ensure direct `200 OK` responses.
- **Path Correction**: Updated `turn_engine.py` to use the PRD-mandated `/api/customer-orders` path.
- **Deterministic Verification**: Validated full supply chain loop using `scripts/test_scenario.sh`.

## Week 8 Notes

- Retailer agent needed: stub never places POs → full production-release loop not exercised until Week 8
- Stochastic demand: `generate_customer_orders` uses `random.gauss()` with no fixed seed — add `seed` to scenario file and call `random.seed()` if reproducibility is needed
- Claude auth: if `ANTHROPIC_API_KEY` / `ANTHROPIC_BASE_URL` point to an external provider (e.g. DashScope), CLI fails with 403 — run `unset ANTHROPIC_API_KEY` before simulating

## Final Review Checklist (Week 7)

- [x] All three services start and serve APIs
- [x] Turn engine runs deterministic (stub) mode without errors (Verified via `test_scenario.sh`)
- [x] Manufacturer skill file exists and is complete (`skills/manufacturer-manager.md`)
- [x] Turn engine runs with manufacturer agent (Note: verified prior to usage limit)
- [x] Agent output captured in `logs/day-NNN-manufacturer.log`
- [x] Agent verified: pricing, purchasing, reasoning logged correctly
- [x] `retailer-cli` created and verified
- [x] `report.md` rewritten as 3–4 page deliverable
- [x] REST isolation audit passed — all cross-service calls via httpx, isolated SQLite DBs
