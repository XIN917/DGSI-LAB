# 3D Printer Production Simulator (DGSI)

A day-by-day factory production planning simulator where you manage inventory, manufacturing orders, and supplier purchasing for a 3D printer factory.

## Overview

DGSI (Data-Dense Global Simulation Interface) is a simulation system designed to model realistic production cycles. Users act as production planners, making strategic decisions to keep the factory running efficiently while managing material shortages, lead times, and capacity limits.

### Key Features

*   **Simulation Engine**: Advance time day-by-day, generating random demand and processing deliveries.
*   **Inventory Management**: Track raw materials and finished goods with strict reservation logic.
*   **Manufacturing Orders**: Release orders to production, ensuring BOM (Bill of Materials) requirements are met.
*   **Purchase Orders**: Manage supplier relationships with automated bulk discounts and realistic lead times.
*   **Interactive Dashboard**: A professional, dark industrial Streamlit UI for monitoring and decision-making.
*   **REST API**: Fully functional FastAPI backend for programmatic control and integration.
*   **Persistence**: Export and import complete game states via JSON.

## Tech Stack

*   **Backend**: Python 3.11-3.13, FastAPI, SQLAlchemy (SQLite), Pydantic
*   **Frontend**: Streamlit 1.40 (Custom Dark Industrial Theme)
*   **Security**: JWT Authentication with bcrypt password hashing
*   **Infrastructure**: Docker & Docker Compose

## Getting Started

### Prerequisites

*   Python 3.11, 3.12, or 3.13
*   Docker & Docker Compose (optional, for containerized deployment)

> Python 3.14 is not supported by the currently pinned dependency set. In particular, `pydantic-core==2.23.4` builds through a PyO3 version that supports up to Python 3.13.

### Local Installation

1.  **Clone the repository**:
    ```bash
    git clone <repository-url>
    cd DGSI
    ```

2.  **Set up a virtual environment**:
    ```bash
    python3.11 -m venv venv  # or python3.12 / python3.13
    source venv/bin/activate  # On Windows: venv\Scripts\activate
    python -m pip install --upgrade pip
    ```

3.  **Install dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

4.  **Initialize the database**:
    The database initializes automatically on the first run of the API or Dashboard.

### Running the Application

1.  **Start the Backend (FastAPI)**:
    ```bash
    PYTHONPATH=. uvicorn app.main:app --reload --port 8000
    ```
    Access the API documentation at [http://localhost:8000/docs](http://localhost:8000/docs).

2.  **Start the Dashboard (Streamlit)**:
    ```bash
    PYTHONPATH=. streamlit run dashboard/pages.py
    ```
    Access the UI at [http://localhost:8501](http://localhost:8501).

### Default Credentials

*   **Username**: `admin`
*   **Password**: `admin123` (Note: Change this in production or via seed configuration)

## Docker Deployment

To run the entire stack using Docker:

```bash
docker compose -f docker/docker-compose.yml up --build
```

## Testing

Run the test suite using pytest:

```bash
pytest
```

If dependency installation fails while building `pydantic-core` and the log mentions `Python interpreter version (3.14)`, recreate the virtual environment with Python 3.11, 3.12, or 3.13 and reinstall `requirements.txt`.

## Directory Structure

*   `app/`: FastAPI backend (models, services, API endpoints)
*   `dashboard/`: Streamlit frontend components and layout
*   `docker/`: Containerization configuration
*   `docs/`: Implementation plans and PRD
*   `tests/`: Unit and integration tests
*   `sample_data/`: Default production plans and seed data
