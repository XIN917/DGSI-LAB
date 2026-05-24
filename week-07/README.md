# DGSI Supply Chain Ecosystem (Week 7)

A multi-service supply chain simulator consisting of a parts **Provider**, a 3D printer **Manufacturer**, and a downstream **Retailer**.

## Project Structure

- **[Provider](./provider/README.md)**: Simulates a raw materials supplier (PCBs, Motors, etc.) with a REST API.
- **[Manufacturer](./manufacturer/README.md)**: Simulates a 3D printer factory. Manages BOMs, production lines, and wholesale fulfillment.
- **[Retailer](./retailer/README.md)**: Simulates a consumer store. Manages retail pricing, customer demand, and stock replenishment.

## Prerequisites

Before running the simulation in AI mode, ensure your environment is set up for **Claude Code**:

1.  **Installation**: Ensure the `claude` CLI is installed. See the [official documentation](https://docs.anthropic.com/en/docs/agents-and-tools/claude-code/overview#install-claude-code) for setup instructions.
2.  **Authentication**: The Turn Engine requires Claude to be authenticated. You can do this by running:
    ```bash
    claude auth login
    ```
3.  **Verify Setup**: Run the following command to confirm you are authenticated and ready:
    ```bash
    claude --print "ping"
    ```
    *Note: If you receive a "403 invalid api-key" error, ensure your login session is active or your `ANTHROPIC_API_KEY` environment variable is set.*

## Quick Start (Installation)

To set up the simulation environment (virtual environments and dependencies) for all three services, run:

```bash
chmod +x scripts/*.sh
./scripts/setup_envs.sh
```

## 🚀 Automated Simulation

The full supply chain lifecycle can be executed using the provided automation scripts:

1.  **Start all servers:**
    ```bash
    ./scripts/start_all.sh
    ```
2.  **Reset all services to Day 0:**
    ```bash
    ./scripts/reset_all.sh
    ```
3.  **Turn Engine (Agent Orchestration):**
    Run the turn-based simulation where the manufacturer agent (via Claude Code) makes operational decisions. Retailer and provider run as stubs. Replace `<days>` with the number of simulated days:
    ```bash
    # Run for 3 simulated days
    python3 turn_engine.py config/sim.json scenarios/smoke-test.json 3

    # Run with verbose output
    python3 turn_engine.py config/sim.json scenarios/smoke-test.json 3 -v
    ```
    Agent logs are saved to `logs/day-NNN-manufacturer.log`.
4.  **Deterministic Health Check:**
    Run a scripted, no-agent scenario to verify basic plumbing:
    ```bash
    ./scripts/test_scenario.sh
    ```
5.  **Stop all servers:**
    ```bash
    pkill -f 'cli serve'
    ```

## 🛠 Manual Simulation & Troubleshooting

For a detailed step-by-step guide on how to run a manual simulation, monitor logs, and verify agent outputs, see the **[Testing & Integration Guide](./docs/TESTING.md)**.

## Integration Progress

Track the Week 7 development and integration status in:
- **[Integration Log](./docs/INTEGRATION.md)**
