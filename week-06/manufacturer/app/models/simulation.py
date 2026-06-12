"""Simulation state persistence model."""
from sqlalchemy import Column, Integer, String, Text
from app.core.database import Base


class SimulationState(Base):
    """Singleton row tracking the current simulation state."""
    __tablename__ = "simulation_state"

    id = Column(Integer, primary_key=True, default=1)
    current_day = Column(Integer, nullable=False, default=1)
    current_date = Column(String(10), nullable=False, default="2026-04-01")
    demand_params = Column(Text, nullable=True)  # JSON: {"P3D-Classic": {"mean": 8, "variance": 3}, ...}
    capacity_per_day = Column(Integer, nullable=False, default=250)
    warehouse_capacity = Column(Integer, nullable=False, default=1000)

    def __repr__(self):
        return f"<SimulationState(day={self.current_day}, date='{self.current_date}')>"
