# DGSI Week 6 - Project Instructions

## Shared Logic
- **REST as a Contract**: Neither app trusts the other's internals. Communicate only via REST.
- **Simulated Time**: A human advances each app one at a time. Day logic must be consistent.
- **Event Logs**: Every state change must be logged in the `events` table in the respective app.

## Provider App Requirements
- Port: `8001`
- Database: `provider.db`
- CLI: `provider-cli`
- REST API: FastAPI with Swagger at `/docs`
- Shared Service Layer: Typer CLI and FastAPI share the same `services/` logic.
- **State Management**: Use `provider-cli export` and `provider-cli import <file>` for JSON state management.

## Manufacturer App Adaptation
- Port: `8002` (from Week 5)
- Config: Add `providers` array in config.
- CLI: Add `suppliers` and `purchase` command groups.
- Simulation: Poll Provider during `day_advance`.

## Port Management
- Provider: `8001`
- Manufacturer: `8002`

## 5-Day Scenario Checklist
1. **Day 0**: Manufacturer orders 50 PCBs from Provider.
2. **Day 1-3**: Both apps advance. Order moves through state machine.
3. **Day 4**: Provider marks order as DELIVERED. Manufacturer polls, adds to inventory.
4. **Verification**: Check both DBs for matching events.
