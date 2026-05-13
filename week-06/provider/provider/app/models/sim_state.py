"""Simulation state model for Provider app."""
from sqlalchemy import Column, String
from provider.app.db import Base


class SimState(Base):
    __tablename__ = "sim_state"

    key = Column(String, primary_key=True)
    value = Column(String, nullable=False)

    def to_dict(self):
        return {
            "key": self.key,
            "value": self.value,
        }