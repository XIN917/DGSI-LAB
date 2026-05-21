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
- **Skill Files**: Found in each service's `docs/` directory (e.g., `manufacturer/docs/skills.md`). Agents should follow the decision frameworks defined therein.
- **Turn Engine**: The simulation is orchestrated by a turn engine that invokes agents via `claude --print [prompt]` and advances time once all decisions are made.

## Known Issues & Future Plans
- **Claude Authentication (PENDING)**: While the Claude Code integration is implemented in `turn_engine.py`, full end-to-end agent testing is pending local CLI authentication (`claude auth login`). Use the deterministic `test_scenario.sh` for integration verification until auth is complete.
- **Cross-Service Visibility**: The "Blind Service" mandate is strictly enforced; agents must only use their respective service's CLI/API.

## Final Review Plan
- [ ] **Verify AI**: Run a 3-day agent simulation and verify decisions in `logs/`.
- [ ] **Sync Report**: Ensure `report.md` accurately reflects all core code implementations and Week 7 architecture.
- [ ] **Audit**: Final check of REST isolation and script functionality.
