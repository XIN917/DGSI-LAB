# DGSI Supply Chain Ecosystem (Week 7)

A multi-service supply chain simulator consisting of a parts **Provider**, a 3D printer **Manufacturer**, and a downstream **Retailer**.

## Project Structure

- **[Provider](./provider/README.md)**: Simulates a raw materials supplier (PCBs, Motors, etc.) with a REST API.
- **[Manufacturer](./manufacturer/README.md)**: Simulates a 3D printer factory. Manages BOMs, production lines, and wholesale fulfillment.
- **[Retailer](./retailer/README.md)**: Simulates a consumer store. Manages retail pricing, customer demand, and stock replenishment.

## Quick Start (Installation)

To get started, you must set up the virtual environment for each service. From the root directory:

```bash
# Setup Provider
cd provider && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..

# Setup Manufacturer
cd manufacturer && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..

# Setup Retailer
cd retailer && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt && ./venv/bin/pip install -e . && cd ..
```

## 🚀 Automated Simulation

The full supply chain lifecycle can be executed using the provided automation scripts:

1.  **Start all servers:**
    ```bash
    ./scripts/start_all.sh
    ```
2.  **Run the core simulation scenario:**
    ```bash
    ./scripts/test_scenario.sh
    ```
    *This script handles database seeding, demand generation, production release, and time advancement automatically.*

## 🛠 Manual Simulation

For a detailed step-by-step guide on how to run a manual, day-by-day simulation and monitor logs across separate terminal windows, see the **[Testing & Integration Guide](./docs/TESTING.md)**.

## Integration Progress

Track the Week 7 development and integration status in:
- **[Integration Plan](./docs/retailer_integration_plan.md)**
- **[Integration Log](./docs/INTEGRATION.md)**
