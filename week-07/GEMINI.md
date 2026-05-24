> **Current project context is in `CLAUDE.md`. Read that first. This file is the historical record of earlier development steps.**

# DGSI Week 7 - Project Mandates

## Core Architecture
- **Multi-Service Supply Chain**: The ecosystem consists of three decoupled services:
  - **Provider** (Port 8001): Raw materials and components.
  - **Manufacturer** (Port 8002): Production and wholesale fulfillment.
  - **Retailer** (Port 8003): Consumer demand and retail sales.
- **REST Communication**: Services communicate exclusively via REST APIs. No shared database access.
- **Persistence**: Each service uses its own SQLite database located in its respective `data/` directory.

## Simulation Timing (Turn-Based)
- **Starting Day**: All services must initialize the simulation at **Day 0**.
- **Advancement Logic**: All services must follow the **"Increment then Process"** pattern in their `day advance` implementation:
  1. Increment the current day counter.
  2. Advance the simulation date.
  3. Process logic for the *new* day (fulfillments, arrivals, demand).
  4. Persist and return the new day.
- **Synchronization**: The day counter must be kept in lock-step across all services during a simulation run.

## Development Conventions
- **Language**: Python 3.12+
- **Frameworks**: FastAPI (REST APIs), Typer (CLI), SQLAlchemy (ORM).
- **Environment**: Each service maintains its own virtual environment (`venv/`).
- **Tooling**: Prefer `uv` for dependency management where available, otherwise use `pip`.
- **Naming**: 
  - Models: `app/models/`
  - Business Logic: `app/services/`
  - REST Endpoints: `app/api/endpoints/`
  - CLI Interface: `app/cli.py`

## Operational Workflows
- **Setup**: Use `./scripts/setup_envs.sh` to create virtual environments and install dependencies for all services.
- **Initialization**: Use the `seed` (Provider/Manufacturer) or `init` (Retailer) CLI commands to reset simulation state.
- **Execution**: Use `scripts/start_all.sh` to launch background servers.
- **Turn Engine**: Use `python3 turn_engine.py config/sim.json scenarios/smoke-test.json <days>` to run a fully automated simulation.
- **Export/Import**: All services support `export` and `import` CLI commands for state persistence.
- **Logging**: Service logs are in `logs/*.log`. Agent decisions are in `logs/day-000-[role].log`.

## Service Features
### Manufacturer (Port 8002)
- Commands: `sales orders`, `production release`, `production status`, `capacity`, `price set/list`, `stock`.
- Logic: Fulfills retailer orders from finished goods or triggers production.

### Retailer (Port 8003)
- Commands: `catalog`, `inventory`, `customer-orders`, `purchase-orders`, `fulfill`, `backorder`, `pricing`.
- Logic: Backorders customer demand when low on stock and auto-fulfills when POs arrive.

### Provider (Port 8001)
- Commands: `catalog`, `orders`, `stock`, `day advance`.
- Logic: Supplier for manufacturer raw materials.

## Agent Skills
- **Skill Files**: Found in the central `skills/` directory (e.g., `skills/manufacturer-manager.md`). Agents should follow the decision frameworks defined therein.
- **Turn Engine**: Invokes agents via `claude --print --dangerously-skip-permissions --allowedTools Bash --model claude-haiku-4-5-20251001 <prompt>`. Only the manufacturer role calls Claude; retailer and provider remain stubs for Week 7.
- **Prompt optimisation**: The turn engine pre-fetches all read-only state (stock, sales orders, capacity, production status, price list, purchase list) and injects it into the prompt. The agent skips assessment commands and goes straight to decisions — reduces agent execution from ~70s to ~25s.
- **Skill price floor**: `skills/manufacturer-manager.md` hardcodes minimum wholesale prices (P3D-Classic €163, P3D-Pro €246) derived from BOM material cost + 15% margin, since `price list` does not expose component costs.
- **subprocess**: Uses `shell=True` with explicit `PATH=/opt/homebrew/bin:...` to ensure `claude` resolves correctly when cwd changes to a service subdirectory.

## Reset & Testing
- **Full reset**: `./scripts/reset_all.sh` — deletes all `.db` files then re-seeds. Must delete DBs first; `seed` uses `if not existing` guards and won't overwrite stale reservations otherwise.
- **Smoke test**: `python3 turn_engine.py config/sim.json scenarios/smoke-test.json 3` — 3 days, ~30s/day. Retailer/provider are stubs; manufacturer agent runs live.
- **Known test gap**: Retailer stub never places purchase orders with the manufacturer, so the agent sees zero sales orders. Production-release behaviour is not exercised in the smoke test. Verify pricing logic and purchasing decisions instead. Full production-release testing requires Week 8 retailer agent.

## Known Issues & Future Plans
- **Claude Authentication (VERIFIED)**: Claude Code integration is verified. Note: If `ANTHROPIC_API_KEY` or `ANTHROPIC_BASE_URL` are set in the environment (e.g., pointing to an external provider like DashScope), the CLI may fail with a 403 error. Unset these variables or ensure they point to Anthropic's native API to use Claude Code correctly.
- **Cross-Service Visibility**: The "Blind Service" mandate is strictly enforced; agents must only use their respective service's CLI/API.

## Final Review Plan
- [x] **Verify AI**: Run a 3-day agent simulation and verify decisions in `logs/`.
- [ ] **Sync Report**: Ensure `report.md` accurately reflects all core code implementations and Week 7 architecture.
- [ ] **Audit**: Final check of REST isolation and script functionality.
