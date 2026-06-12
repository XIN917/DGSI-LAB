# DGSI Provider App

A parts supplier simulator that communicates over REST.

## Features
- REST API for catalog, stock, and orders.
- Typer-based CLI for manual control and simulation.
- Shared service layer for business logic.
- Day-based simulation engine.

## Installation
```bash
cd provider
pip install -r requirements.txt
```

## Usage
### Start the API
```bash
python main.py serve --port 8001
```

### CLI Commands
```bash
python cli.py catalog
python cli.py stock
python cli.py orders list
python cli.py day advance
```
