from fastapi import FastAPI
from app.core.database import init_db
from app.api.endpoints import catalog, stock, orders, day

app = FastAPI(title="Provider API", version="1.0.0")

# Initialize database on startup
@app.on_event("startup")
def startup_event():
    init_db()

# Include routers
app.include_router(catalog.router, prefix="/api/catalog", tags=["catalog"])
app.include_router(stock.router, prefix="/api/stock", tags=["stock"])
app.include_router(orders.router, prefix="/api/orders", tags=["orders"])
app.include_router(day.router, prefix="/api/day", tags=["day"])

@app.get("/")
def read_root():
    return {"message": "Welcome to the Provider API"}
