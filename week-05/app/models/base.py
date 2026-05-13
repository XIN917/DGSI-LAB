"""Base model classes and mixins."""

from datetime import datetime
from sqlalchemy import Column, Integer, DateTime
from app.db import Base


class TimestampMixin:
    """Mixin to add timestamp columns to a model."""

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
