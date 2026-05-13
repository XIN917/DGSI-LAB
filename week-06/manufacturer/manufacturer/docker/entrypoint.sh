#!/bin/bash
set -e

echo "Starting 3D Printer Production Simulator..."

mkdir -p /app/data

if [ ! -f /app/data/simulation.db ]; then
    echo "Initializing database..."
    PYTHONPATH=. python3 -c "
from app.core.database import engine, Base
from app.services.seed import initialize_seed_data
from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.purchase_order import Supplier, SupplierProduct, PurchaseOrder

Base.metadata.create_all(bind=engine)
initialize_seed_data()
print('Database initialized with sample data.')
"
fi

echo "Starting FastAPI server on port 8000..."
PYTHONPATH=. uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Starting Streamlit dashboard on port 8501..."
PYTHONPATH=. streamlit run dashboard/pages.py --server.address=0.0.0.0 --server.port=8501 &

wait
