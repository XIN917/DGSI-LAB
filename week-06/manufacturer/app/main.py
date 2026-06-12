"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.api.endpoints import auth, config, inventory, orders, purchase_orders, simulation, events, import_export

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="3D Printer Production Simulator API — manage inventory, orders, and production cycles.",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(auth.router)
app.include_router(config.router)
app.include_router(inventory.router)
app.include_router(orders.router)
app.include_router(purchase_orders.router)
app.include_router(simulation.router)
app.include_router(events.router)
app.include_router(import_export.router)


@app.on_event("startup")
async def startup():
    """Initialize database and seed if enabled."""
    init_db()
    if settings.SEED_SAMPLE_DATA:
        from app.services.seed import initialize_seed_data
        initialize_seed_data()


@app.get("/")
def root():
    """Root endpoint."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs": "/docs",
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
