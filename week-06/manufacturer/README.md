# Manufacturer App - Run Guide

This folder contains the manufacturer application for the 3D printer production simulator.
The actual Python app lives in `manufacturer/manufacturer/`.

## Goal

Run the manufacturer FastAPI backend and Streamlit dashboard, and connect the manufacturer to the provider service.

## Prerequisites

- Python 3.13 is recommended for this repo
- `python3.14` may fail to build `pydantic-core` on macOS
- `virtualenv` support via `python3.13 -m venv`
- `curl` or HTTP client for testing
- Provider service running separately on port `8001`

## Setup

1. Change into the app directory:

```bash
cd manufacturer/manufacturer
```

2. Create and activate a virtual environment:

```bash
python3.13 -m venv venv
source venv/bin/activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

## Configure Provider Integration

The manufacturer app calls the provider API through `PROVIDER_API_URL`.
By default, it uses:

```bash
http://localhost:8001
```

If your provider runs elsewhere, set the environment variable before starting the app:

```bash
export PROVIDER_API_URL="http://localhost:8001"
export PROVIDER_TIMEOUT_SECONDS=10
```

If you want, create a `.env` file in `manufacturer/manufacturer/` with:

```text
PROVIDER_API_URL=http://localhost:8001
PROVIDER_TIMEOUT_SECONDS=10
```

## Run the Manufacturer API

Start the FastAPI backend on port `8000`:

```bash
cd manufacturer/manufacturer
source venv/bin/activate
PYTHONPATH=. python -m uvicorn app.main:app --reload --port 8000
```

The API docs are available at:

- http://localhost:8000/docs

## Run the Dashboard

In a second terminal, activate the same venv and run:

```bash
cd manufacturer/manufacturer
source venv/bin/activate
PYTHONPATH=. streamlit run dashboard/pages.py
```

Then open:

- http://localhost:8501

## Connect to Provider

1. Start the provider service in its own terminal.
2. Ensure `PROVIDER_API_URL` points at the provider API.
3. Use the manufacturer endpoint to place provider orders:

```bash
curl -X POST http://localhost:8000/api/purchase-orders/from-provider \
  -H "Content-Type: application/json" \
  -d '{"product_id": 3, "quantity": 50}'
```

4. Advance the manufacturer simulation (this also polls provider order status):

```bash
curl -X POST http://localhost:8000/api/simulation/advance
```

## Notes

- The database initializes automatically on first run.
- `provider_order_id` and `provider_name` are used to track remote provider orders.
- If the provider is unavailable, `POST /api/purchase-orders/from-provider` returns HTTP 503.

## Troubleshooting

- If provider commands fail, verify the provider endpoint:

```bash
curl http://localhost:8001/api/catalog
```

- If the manufacturer dashboard does not load, make sure the backend is running and `PYTHONPATH=.` is set.

- The app expects the manufacturer FastAPI backend on `http://localhost:8000` by default.
