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

    settings = get_settings()
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
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
    return {"message": "Successfully logged out"}


@router.get("/me")
def get_me(current_user: User = Depends(get_current_user)):
    """Get current authenticated user info."""
    return {
        "id": current_user.id,
        "username": current_user.username,
        "role": current_user.role
    }
