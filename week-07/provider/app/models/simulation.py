from sqlalchemy import Column, String
from app.core.database import Base

class SimState(Base):
    __tablename__ = "sim_state"

    key = Column(String(50), primary_key=True)
    value = Column(String(100), nullable=False)
