"""
Transient Vehicle: Represents passing-through traffic (P2).
Enters and exits via R1 roads, never parks.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, CellType
from pathfinding import Pathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class TransientVehicle(BaseVehicle):
    """
    Transient (P2) vehicle agent.
    
    Behavior:
    - Enters the area from R1 entry points at the border
    - Travels through the area, mainly using R1 roads
    - Exits from R1 exit points at the border
    - NEVER parks
    - Primarily uses R1, may use other roads in emergencies
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random):
        super().__init__(world, VehicleType.TRANSIENT, pathfinder, rng)
        self.entry_point: Optional[Tuple[int, int]] = None
        self.exit_point: Optional[Tuple[int, int]] = None

    def decide_action(self, current_tick: int, current_hour: int):
        """Transient vehicles are always moving toward exit."""
        if self.state == VehicleState.MOVING:
            return  # Already moving

        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return

        if self.state == VehicleState.IDLE and self.position:
            # If idle with no path, try to find exit
            if not self.current_path or self.path_index >= len(self.current_path):
                self._navigate_to_exit()

    def spawn_at_entry(self) -> bool:
        """Spawn at a random R1 entry point."""
        if not self.world.border_entries:
            return False

        # Try multiple entry points
        entries = list(self.world.border_entries)
        self.rng.shuffle(entries)

        for entry in entries:
            if self.spawn(entry):
                self.entry_point = entry
                self.origin = entry
                # Find an exit point (different from entry)
                self._select_exit_point()
                if self.exit_point:
                    self.start_journey(self.exit_point, "TRANSIT")
                return True

        return False

    def _select_exit_point(self):
        """Select an exit point, preferring one far from entry."""
        if not self.world.border_exits or not self.entry_point:
            return

        exits = list(self.world.border_exits)
        # Prefer exits far from entry point
        exits.sort(key=lambda e: -(abs(e[0] - self.entry_point[0]) +
                                     abs(e[1] - self.entry_point[1])))

        # Pick from top choices with some randomness
        top_n = max(1, len(exits) // 3)
        self.exit_point = self.rng.choice(exits[:top_n])
        self.destination = self.exit_point

    def _navigate_to_exit(self):
        """Try to navigate to the assigned exit point."""
        if not self.exit_point:
            self._select_exit_point()
        if self.exit_point:
            if not self.start_journey(self.exit_point, "TRANSIT"):
                # Failed to find path, try another exit
                self._select_exit_point()
                if self.exit_point:
                    self.start_journey(self.exit_point, "TRANSIT")

    def on_arrival(self):
        """Transient vehicle reached exit - despawn."""
        self.despawn()
        self.state = VehicleState.DESPAWNED
