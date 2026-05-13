# 3D Printer Production Simulator Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete Phase 1 foundation (authentication, Docker, seed data) and begin core simulation services

**Architecture:** FastAPI backend with SQLAlchemy ORM, Streamlit frontend, SQLite database, Docker deployment. All state changes logged as events.

**Tech Stack:** Python 3.11, FastAPI, SQLAlchemy, Pydantic, Streamlit, JWT auth, bcrypt, Docker

---

## File Structure

### Existing (Already Created)
- `app/core/database.py` - DB connection, session management
- `app/core/config.py` - Settings from environment
- `app/core/security.py` - Password hashing, JWT (needs completion)
- `app/models/*.py` - All SQLAlchemy models defined
- `sample_data/default_production_plan.json` - Seed data
- `.github/ISSUE-*.md` - Issues #1-#42

### Files To Create

**Core:**
- `app/main.py` - FastAPI application entry point
- `app/api/dependencies.py` - DB session, auth dependencies
- `app/api/endpoints/auth.py` - Auth endpoints
- `app/services/seed.py` - Database seeding logic
- `app/services/simulation_engine.py` - Day advancement logic
- `app/services/inventory_service.py` - Inventory management
- `app/services/order_service.py` - Order processing
- `app/utils/json_export.py` - Import/export utilities

**Dashboard:**
- `dashboard/pages.py` - Main Streamlit dashboard
- `dashboard/components/__init__.py` - Reusable components

**Docker:**
- `docker/Dockerfile` - Multi-stage build
- `docker/docker-compose.yml` - Service orchestration
- `docker/entrypoint.sh` - Startup script

**Tests:**
- `tests/conftest.py` - Test fixtures
- `tests/test_services/*` - Service unit tests

---

## Phase 1 Tasks (Foundation)

### Task 1: Complete Authentication System

**Files:**
- Modify: `app/core/security.py:1-40` (already has basics, needs verification)
- Create: `app/api/dependencies.py`
- Create: `app/api/endpoints/auth.py`
- Create: `app/main.py`
- Test: `tests/test_api/test_auth.py`

#### Step 1: Verify security.py has all needed functions

Check current implementation:
```python
# Should have these in app/core/security.py:
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    # Implementation with JWT
    pass

def decode_access_token(token: str) -> Optional[dict]:
    # Decode and validate token
    pass
```

Run: `cat app/core/security.py` to verify exists

#### Step 2: Create auth dependencies

Create: `app/api/dependencies.py`

```python
"""Authentication dependencies for FastAPI routes."""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from jose import JWTError

from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db)
) -> User:
    """Get current authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    payload = decode_access_token(token)
    if payload is None:
        raise credentials_exception

    user_id: int = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user


def get_current_active_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Ensure user is active (placeholder for future inactive users support)."""
    return current_user
```

#### Step 3: Create auth endpoints

Create: `app/api/endpoints/auth.py`

```python
"""Authentication API endpoints."""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.database import get_db
from app.core.security import (
    verify_password,
    get_password_hash,
    create_access_token
)
from app.models.user import User
from app.api.dependencies import get_current_user
from app.services.seed import seed_default_admin

router = APIRouter(prefix="/api/auth", tags=["authentication"])

settings = get_settings()


@router.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    """Login endpoint - returns JWT access token."""
    # Get user by username
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=access_token_expires
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        }
    }


@router.post("/logout")
def logout(current_user: User = Depends(get_current_user)):
    """Logout endpoint (session-based, just invalidates client token)."""
    # In JWT system, client discards token server-side is optional
    return {"message": "Successfully logged out"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }
```

#### Step 4: Create main FastAPI app

Create: `app/main.py`

```python
"""FastAPI application entry point."""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.core.database import init_db
from app.api.endpoints import auth

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="3D Printer Production Simulator API",
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)


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
        "version": settings.APP_VERSION
    }


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}
```

#### Step 5: Write authentication test

Create: `tests/test_api/test_auth.py`

```python
"""Tests for authentication endpoints."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.core.database import get_db, engine, Base
from app.core.security import get_password_hash

# Override dependency for testing
@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def db_session():
    """Create fresh database for each test."""
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    yield session
    session.rollback()
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def test_user(db_session):
    """Create a test user."""
    from app.models.user import User
    user = User(
        username="testuser",
        password_hash=get_password_hash("password123"),
        role="admin"
    )
    db_session.add(user)
    db_session.commit()
    return user


def test_login_success(client, test_user):
    """Test successful login returns token."""
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert data["user"]["username"] == "testuser"


def test_login_invalid_credentials(client):
    """Test login fails with wrong credentials."""
    response = client.post(
        "/api/auth/login",
        data={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401


def test_get_me_requires_auth(client):
    """Test /api/auth/me requires authentication."""
    response = client.get("/api/auth/me")
    assert response.status_code == 401


def test_get_me_success(client, test_user, monkeypatch):
    """Test getting current user with valid token."""
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": test_user.id})

    response = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
```

#### Step 6: Run tests to verify

Run: `cd printer-factory-sim && pip install pytest pytest-asyncio httpx && pytest tests/test_api/test_auth.py -v`

Expected: Tests run, some may fail until implementation complete

#### Step 7: Commit

Run:
```bash
git add app/core/security.py app/api/dependencies.py app/api/endpoints/auth.py app/main.py tests/test_api/test_auth.py
git commit -m "feat(auth): implement authentication system (#3)"
```

---

### Task 2: Create Seed Service

**Files:**
- Create: `app/services/__init__.py`
- Create: `app/services/seed.py`
- Test: `tests/test_services/test_seed.py`

#### Step 1: Create services package

Create: `app/services/__init__.py`

```python
"""Services package."""
```

#### Step 2: Create seed service

Create: `app/services/seed.py`

```python
"""Database seeding functionality."""
import json
from pathlib import Path
from sqlalchemy.orm import Session
from decimal import Decimal

from app.models.user import User
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory
from app.models.supplier import Supplier, SupplierProduct
from app.core.security import get_password_hash


def load_production_plan() -> dict:
    """Load the default production plan from JSON."""
    plan_path = Path(__file__).parent.parent.parent / "sample_data" / "default_production_plan.json"
    with open(plan_path) as f:
        return json.load(f)


def seed_default_admin(db: Session) -> User:
    """Create default admin user if not exists."""
    existing = db.query(User).filter(User.username == "admin").first()
    if existing:
        return existing

    admin = User(
        username="admin",
        password_hash=get_password_hash("admin123"),  # Change in production!
        role="admin"
    )
    db.add(admin)
    db.commit()
    return admin


def initialize_seed_data(db: Session = None):
    """Initialize database with sample data."""
    from app.core.database import SessionLocal
    if db is None:
        db = SessionLocal()

    try:
        plan = load_production_plan()

        # Seed product models and BOMs
        for model_id, model_data in plan["models"].items():
            existing = db.query(ProductModel).filter(ProductModel.id == model_id).first()
            if not existing:
                model = ProductModel(
                    id=model_id,
                    name=model_data["name"],
                    assembly_time_days=model_data["assembly_time_days"]
                )
                db.add(model)

            # Add BOM items
            for material, bom_info in model_data["bom"].items():
                existing_bom = db.query(BOMItem).filter(
                    BOMItem.model_id == model_id,
                    BOMItem.material_name == material
                ).first()
                if not existing_bom:
                    bom_item = BOMItem(
                        model_id=model_id,
                        material_name=material,
                        quantity_required=Decimal(str(bom_info["qty"])),
                        pcb_ref=bom_info.get("pcb_ref")
                    )
                    db.add(bom_item)

        # Seed suppliers and their products
        for supplier_data in plan["suppliers"]:
            existing = db.query(Supplier).filter(Supplier.id == supplier_data["id"]).first()
            if not existing:
                supplier = Supplier(
                    id=supplier_data["id"],
                    name=supplier_data["name"],
                    lead_time_days=supplier_data["lead_time_days"],
                    active=True
                )
                db.add(supplier)

                for product_data in supplier_data["products"]:
                    sup_product = SupplierProduct(
                        supplier_id=supplier_data["id"],
                        product_name=product_data["name"],
                        base_unit_cost=Decimal(str(product_data["base_cost"])),
                        packaging_unit=product_data.get("packaging"),
                        packaging_qty=product_data.get("pack_qty"),
                        discount_tiers=json.dumps(product_data.get("tiers", []))
                    )
                    db.add(sup_product)

        # Seed initial inventory
        for product_name, inv_data in plan["initial_inventory"].items():
            existing = db.query(Inventory).filter(Inventory.product_name == product_name).first()
            if not existing:
                inventory = Inventory(
                    product_name=product_name,
                    quantity=Decimal(str(inv_data["qty"])),
                    reserved_quantity=Decimal("0"),
                    unit_type=inv_data.get("type", "raw")
                )
                db.add(inventory)

        db.commit()

    except Exception as e:
        db.rollback()
        raise e
```

Note: Need to create `app/models/supplier.py` if not separate:

Actually looking at PRD, Supplier/SupplierProduct/PurchaseOrder are in `app/models/purchase_order.py`. Update imports accordingly.

#### Step 3: Commit

Run:
```bash
git add app/services/ app/models/supplier.py 2>/dev/null || true
git commit -m "feat(seed): add database seeding service (#5)"
```

---

### Task 3: Create Docker Configuration

**Files:**
- Create: `docker/Dockerfile`
- Create: `docker/docker-compose.yml`
- Create: `docker/entrypoint.sh`
- Create: `.dockerignore`

#### Step 1: Create Dockerfile

Create: `docker/Dockerfile`

```dockerfile
# Build stage
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY ../requirements.txt .

# Install dependencies to virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir -r requirements.txt


# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd --create-home --shell /bin/bash appuser
USER appuser

# Copy application code
COPY --chown=appuser:appuser ../app ./app
COPY --chown=appuser:appuser ../dashboard ./dashboard
COPY --chown=appuser:appuser ../sample_data ./sample_data

# Create data directory for SQLite
RUN mkdir -p /app/data && chown appuser:appuser /app/data

# Expose ports
EXPOSE 8000 8501

# Copy entrypoint script
COPY --chown=appuser:appuser ../docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
```

#### Step 2: Create docker-compose.yml

Create: `docker/docker-compose.yml`

```yaml
version: '3.8'

services:
  simulator:
    build:
      context: ..
      dockerfile: docker/Dockerfile
    container_name: printer-factory-sim
    ports:
      - "8000:8000"  # FastAPI
      - "8501:8501"  # Streamlit
    volumes:
      - ./data:/app/data  # Persist SQLite database
    environment:
      - SECRET_KEY=${SECRET_KEY:-$(openssl rand -hex 32 2>/dev/null || cat /dev/urandom | tr -dc 'a-zA-Z0-9' | head -c 32)}
      - DATABASE_URL=sqlite:///app/data/simulation.db
      - SEED_SAMPLE_DATA=true
    restart: unless-stopped

networks:
  default:
    name: printer-factory-network
```

#### Step 3: Create entrypoint.sh

Create: `docker/entrypoint.sh`

```bash
#!/bin/bash
set -e

echo "Starting 3D Printer Production Simulator..."

# Ensure data directory exists
mkdir -p /app/data

# Initialize database if it doesn't exist
if [ ! -f /app/data/simulation.db ]; then
    echo "Initializing database..."
    python -c "
from app.core.database import engine, Base
from app.services.seed import initialize_seed_data, load_production_plan
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
uvicorn app.main:app --host 0.0.0.0 --port 8000 &

echo "Starting Streamlit dashboard on port 8501..."
streamlit run dashboard/pages.py --server.address=0.0.0.0 --server.port=8501 &

# Wait for both processes
wait
```

#### Step 4: Create .dockerignore

Create: `.dockerignore`

```
__pycache__
*.pyc
*.pyo
*.pyd
.Python
env/
venv/
.venv/
*.egg-info/
.eggs/
dist/
build/
.git/
.gitignore
*.md
!.dockerignore
.DS_Store
tests/
.docker/
data/*.db
*.log
.env.local
```

#### Step 5: Test Docker build

Run: `cd printer-factory-sim && docker compose -f docker/docker-compose.yml build`

Expected: Image builds successfully

#### Step 6: Commit

Run:
```bash
git add docker/ .dockerignore
git commit -m "feat(docker): add container configuration (#4)"
```

---

### Task 4: Implement Core Services Skeleton

Before full implementation, create the service layer structure.

#### Step 1: Create inventory service skeleton

Create: `app/services/inventory_service.py`

```python
"""Inventory management service."""
from decimal import Decimal
from sqlalchemy.orm import Session
from typing import List, Dict, Optional

from app.models.inventory import Inventory


class InventoryService:
    """Service for managing inventory."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[Inventory]:
        """Get all inventory items."""
        return self.db.query(Inventory).all()

    def get_by_product(self, product_name: str) -> Optional[Inventory]:
        """Get inventory item by product name."""
        return self.db.query(Inventory).filter(
            Inventory.product_name == product_name
        ).first()

    def get_available(self, product_name: str) -> Decimal:
        """Get available quantity (not reserved)."""
        inv = self.get_by_product(product_name)
        if not inv:
            return Decimal("0")
        return inv.quantity - inv.reserved_quantity

    def reserve(self, product_name: str, quantity: Decimal) -> bool:
        """Reserve materials for an order."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        available = inv.quantity - inv.reserved_quantity
        if available < quantity:
            return False

        inv.reserved_quantity += quantity
        self.db.commit()
        return True

    def consume(self, product_name: str, quantity: Decimal) -> bool:
        """Consume materials from inventory."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        # Can only consume what's not reserved (should be reserved first)
        available = inv.quantity - inv.reserved_quantity
        if available < quantity:
            return False

        inv.quantity -= quantity
        inv.reserved_quantity -= quantity
        self.db.commit()
        return True

    def release_reservation(self, product_name: str, quantity: Decimal) -> bool:
        """Release reserved materials back to available."""
        inv = self.get_by_product(product_name)
        if not inv:
            return False

        if inv.reserved_quantity < quantity:
            return False

        inv.reserved_quantity -= quantity
        self.db.commit()
        return True

    def adjust(self, product_name: str, new_quantity: Decimal) -> Inventory:
        """Manually adjust inventory quantity."""
        inv = self.get_by_product(product_name)
        if inv:
            inv.quantity = new_quantity
        else:
            inv = Inventory(
                product_name=product_name,
                quantity=new_quantity,
                reserved_quantity=Decimal("0"),
                unit_type="raw"
            )
            self.db.add(inv)

        self.db.commit()
        self.db.refresh(inv)
        return inv

    def get_warehouse_usage(self, capacity: int) -> Dict:
        """Get warehouse capacity usage."""
        total_used = sum(float(item.quantity) for item in self.get_all())
        return {
            "used": total_used,
            "capacity": capacity,
            "percentage": (total_used / capacity * 100) if capacity > 0 else 0
        }
```

#### Step 2: Create order service skeleton

Create: `app/services/order_service.py`

```python
"""Manufacturing order service."""
from datetime import datetime
from decimal import Decimal
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session

from app.models.order import ManufacturingOrder
from app.models.product import ProductModel, BOMItem
from app.models.inventory import Inventory


class OrderService:
    """Service for managing manufacturing orders."""

    def __init__(self, db: Session):
        self.db = db

    def get_all(self) -> List[ManufacturingOrder]:
        """Get all manufacturing orders."""
        return self.db.query(ManufacturingOrder).order_by(
            ManufacturingOrder.created_date.desc()
        ).all()

    def get_pending(self) -> List[ManufacturingOrder]:
        """Get pending orders."""
        return self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status == "pending"
        ).all()

    def get_by_id(self, order_id: int) -> Optional[ManufacturingOrder]:
        """Get order by ID."""
        return self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.id == order_id
        ).first()

    def create(self, product_model: str, quantity: Decimal, created_date: datetime) -> ManufacturingOrder:
        """Create a new manufacturing order."""
        order = ManufacturingOrder(
            product_model=product_model,
            quantity_needed=quantity,
            quantity_produced=Decimal("0"),
            status="pending",
            created_date=created_date
        )
        self.db.add(order)
        self.db.commit()
        self.db.refresh(order)
        return order

    def calculate_bom_requirements(self, order: ManufacturingOrder) -> Dict:
        """Calculate materials required for an order based on BOM."""
        model = self.db.query(ProductModel).filter(
            ProductModel.id == order.product_model
        ).first()

        if not model:
            return {}

        bom_items = self.db.query(BOMItem).filter(
            BOMItem.model_id == order.id
        ).all()

        requirements = {}
        qty_needed = float(order.quantity_needed)

        for item in bom_items:
            required = float(item.quantity_required) * qty_needed
            inventory = self.db.query(Inventory).filter(
                Inventory.product_name == item.material_name
            ).first()

            available = float(inventory.quantity - inventory.reserved_quantity) if inventory else 0

            requirements[item.material_name] = {
                "required": required,
                "available": available,
                "sufficient": available >= required,
                "shortage": max(0, required - available)
            }

        return requirements

    def can_release(self, order: ManufacturingOrder) -> Tuple[bool, List[str]]:
        """Check if order can be released (has all required materials)."""
        requirements = self.calculate_bom_requirements(order)
        missing = [
            mat for mat, req in requirements.items()
            if not req["sufficient"]
        ]
        return len(missing) == 0, missing

    def release(self, order_id: int) -> Tuple[bool, Optional[str]]:
        """Release order to production (reserves materials)."""
        from app.services.inventory_service import InventoryService

        order = self.get_by_id(order_id)
        if not order:
            return False, "Order not found"

        if order.status != "pending":
            return False, f"Order already in {order.status} status"

        can, missing = self.can_release(order)
        if not can:
            order.status = "waiting_materials"
            self.db.commit()
            return False, f"Missing materials: {', '.join(missing)}"

        # Reserve all materials
        bom_reqs = self.calculate_bom_requirements(order)
        inventory_svc = InventoryService(self.db)

        for material, req in bom_reqs.items():
            success = inventory_svc.reserve(material, Decimal(str(req["required"])))
            if not success:
                order.status = "waiting_materials"
                self.db.commit()
                return False, f"Failed to reserve {material}"

        order.status = "released"
        order.started_date = datetime.utcnow()
        self.db.commit()
        return True, None

    def cancel(self, order_id: int) -> bool:
        """Cancel order and release reserved materials."""
        from app.services.inventory_service import InventoryService

        order = self.get_by_id(order_id)
        if not order or order.status == "completed":
            return False

        # Release reservations
        inventory_svc = InventoryService(self.db)
        bom_reqs = self.calculate_bom_requirements(order)

        for material, req in bom_reqs.items():
            inventory_svc.release_reservation(material, Decimal(str(req["required"])))

        order.status = "cancelled"
        self.db.commit()
        return True
```

#### Step 3: Create simulation engine skeleton

Create: `app/services/simulation_engine.py`

```python
"""Simulation engine for day advancement."""
from datetime import datetime, timedelta
from typing import List, Dict
import random
from sqlalchemy.orm import Session

from app.models.event import EventLog
from app.models.order import ManufacturingOrder
from app.models.purchase_order import PurchaseOrder
from app.core.config import get_settings


class SimulationEngine:
    """Engine for running simulation day cycles."""

    def __init__(self, db: Session):
        self.db = db
        self.settings = get_settings()
        self.current_day = 1
        self.current_date = datetime.strptime(
            self.settings.SIMULATION_START_DATE, "%Y-%m-%d"
        ).date()

    def advance_day(self) -> Dict:
        """Advance simulation by one day."""
        events = []

        # Step 1: Process arriving POs
        po_events = self._process_purchase_orders()
        events.extend(po_events)

        # Step 2: Process manufacturing orders
        order_events = self._process_manufacturing_orders()
        events.extend(order_events)

        # Step 3: Generate new demand
        demand_events = self._generate_demand()
        events.extend(demand_events)

        # Step 4: Take inventory snapshot
        snapshot_event = self._take_inventory_snapshot()
        events.append(snapshot_event)

        # Increment day counter
        self.current_day += 1
        self.current_date += timedelta(days=1)

        return {
            "previous_day": self.current_day - 1,
            "new_day": self.current_day,
            "current_date": self.current_date.isoformat(),
            "events_generated": events
        }

    def _process_purchase_orders(self) -> List[Dict]:
        """Process purchase orders due today."""
        events = []
        return events  # TODO: Implement PO delivery logic

    def _process_manufacturing_orders(self) -> List[Dict]:
        """Process manufacturing orders within daily capacity."""
        events = []
        return events  # TODO: Implement order processing

    def _generate_demand(self) -> List[Dict]:
        """Generate new manufacturing orders based on demand parameters."""
        events = []
        return events  # TODO: Implement demand generation

    def _take_inventory_snapshot(self) -> Dict:
        """Take daily inventory snapshot."""
        # TODO: Implement snapshot
        return {
            "type": "inventory_snapshot",
            "date": self.current_date.isoformat()
        }

    def get_status(self) -> Dict:
        """Get current simulation status."""
        pending_count = self.db.query(ManufacturingOrder).filter(
            ManufacturingOrder.status.in_(["pending", "released"])
        ).count()

        return {
            "current_day": self.current_day,
            "current_date": self.current_date.isoformat(),
            "sim_start_date": self.settings.SIMULATION_START_DATE,
            "pending_orders_count": pending_count
        }
```

#### Step 4: Commit

Run:
```bash
git add app/services/inventory_service.py app/services/order_service.py app/services/simulation_engine.py
git commit -m "feat(services): add core service layer skeletons"
```

---

## Next Phase Preview

After completing Phase 1, proceed to:
- Phase 2: Full simulation engine implementation (demand generation, order processing, PO delivery)
- Phase 3: REST API endpoints
- Phase 4: Streamlit dashboard
- Phase 5: Import/export
- Phase 6: Testing
- Phase 7: Final review
