"""FastAPI main application for Provider app."""
from fastapi import FastAPI
from provider.app.api.endpoints import catalog, orders, simulation

app = FastAPI(
    title="Provider App",
    description="Parts supplier API for 3D printer manufacturing",
    version="1.0.0",
)

# Include routers
app.include_router(catalog.router)
app.include_router(orders.router)
app.include_router(simulation.router)


@app.get("/")
def root():
    return {
        "name": "Provider App",
        "version": "1.0.0",
        "description": "Parts supplier for 3D printer manufacturing",
    }


@app.on_event("startup")
def startup_event():
    """Initialize database on startup."""
    from provider.app.db import init_db
    from provider.app.seed import load_seed_data
    
    try:
        init_db()
        load_seed_data()
    except Exception as e:
        print(f"Startup initialization: {e}")