# DGSI Provider App

A parts supplier simulator that communicates over REST.

## Features
- REST API for catalog, stock, and orders.
- Typer-based CLI for manual control and simulation.
- Shared service layer for business logic.
- Day-based simulation engine.

## Installation

### Prerequisites
- Python 3.11+

### Setup

Choose your preferred environment manager:

#### Option A: Using uv (Recommended)
```bash
cd provider
uv sync
# Use 'uv run' for all subsequent commands
```

#### Option B: Using standard venv
```bash
cd provider
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
```

## Usage

### Start the API
Using `uv`:
```bash
uv run python app/main.py serve --port 8001
```
Using `venv`:
```bash
python app/main.py serve --port 8001
```
API docs will be available at `http://localhost:8001/docs`.

### CLI Commands
You can use the `provider-cli` (after `pip install -e .`) or run the script directly:

```bash
# Using uv
uv run python app/cli.py catalog
uv run python app/cli.py stock

# Using venv (direct script)
python app/cli.py catalog
python app/cli.py stock
python app/cli.py orders list
python app/cli.py day advance
```

## Testing
Run the test suite using pytest:
```bash
# Using uv
uv run pytest

# Using venv
pytest
```
