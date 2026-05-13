"""SimPy simulation environment setup."""

import simpy
from typing import Optional
from datetime import datetime


class SimulationEnvironment:
    """Manages the SimPy simulation environment."""

    def __init__(self):
        self.env = simpy.Environment()
        self.current_day: int = 1
        self.running: bool = False
        self.production_capacity: int = 10  # printers per day
        self._day_processes: dict[int, simpy.Process] = {}

    def reset(self):
        """Reset the simulation environment to day 1."""
        self.env = simpy.Environment()
        self.current_day = 1
        self.running = False
        self._day_processes.clear()

    def advance_day(self):
        """Advance the simulation by one day (called from outside SimPy)."""
        self.current_day += 1
        return self.current_day

    @property
    def day(self) -> int:
        """Get the current simulated day."""
        return self.current_day

    @property
    def is_running(self) -> bool:
        """Check if simulation is currently running."""
        return self.running


# Global simulation environment instance
sim_env = SimulationEnvironment()


def get_sim_env() -> SimulationEnvironment:
    """Get the global simulation environment."""
    return sim_env
