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
1. **Navigate to the provider directory**:
   ```bash
   cd provider
   ```

2. **Set up a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

## Usage
### Start the API
```bash
PYTHONPATH=. uv run python main.py serve --port 8001
```

### CLI Commands
```bash
PYTHONPATH=. uv run python cli.py catalog
PYTHONPATH=. uv run python cli.py stock
PYTHONPATH=. uv run python cli.py orders list
PYTHONPATH=. uv run python cli.py day advance
```
