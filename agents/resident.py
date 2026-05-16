"""
Resident Vehicle: Represents permanent population (P1) vehicles.
Follows daily activity patterns based on time zones.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


# Mapping from transition codes to (source_category, dest_category, purpose)
TRANSITION_MAP = {
    "Res->Off(W)": (BlockCategory.RESIDENTIAL, BlockCategory.OFFICE, "WORK"),
    "Res->Mar(W)": (BlockCategory.RESIDENTIAL, BlockCategory.MARKET, "WORK"),
    "Res->Lei(W)": (BlockCategory.RESIDENTIAL, BlockCategory.LEISURE, "WORK"),
    "Res->Oth(W)": (BlockCategory.RESIDENTIAL, BlockCategory.OTHER, "WORK"),
    "Res->Mar(F)": (BlockCategory.RESIDENTIAL, BlockCategory.MARKET, "FOOD"),
    "Res->Oth(O)": (BlockCategory.RESIDENTIAL, BlockCategory.OTHER, "OTHER"),
    "Off->Oth(O)": (BlockCategory.OFFICE, BlockCategory.OTHER, "OTHER"),
    "Res->Lei(L)": (BlockCategory.RESIDENTIAL, BlockCategory.LEISURE, "LEISURE"),
    "Off->Lei(L)": (BlockCategory.OFFICE, BlockCategory.LEISURE, "LEISURE"),
    "Mar->Lei(L)": (BlockCategory.MARKET, BlockCategory.LEISURE, "LEISURE"),
    "Oth->Lei(L)": (BlockCategory.OTHER, BlockCategory.LEISURE, "LEISURE"),
    "Mar->Oth(O)": (BlockCategory.MARKET, BlockCategory.OTHER, "OTHER"),
    "Lei->Oth(O)": (BlockCategory.LEISURE, BlockCategory.OTHER, "OTHER"),
    "Off->Res(S)": (BlockCategory.OFFICE, BlockCategory.RESIDENTIAL, "SLEEP"),
    "Mar->Res(S)": (BlockCategory.MARKET, BlockCategory.RESIDENTIAL, "SLEEP"),
    "Lei->Res(S)": (BlockCategory.LEISURE, BlockCategory.RESIDENTIAL, "SLEEP"),
    "Oth->Res(S)": (BlockCategory.OTHER, BlockCategory.RESIDENTIAL, "SLEEP"),
}


class ResidentVehicle(BaseVehicle):
    """
    Resident (P1) vehicle agent.
    
    Behavior:
    - Always starts and ends journeys at building blocks
    - Follows daily activity patterns (WORK, FOOD, LEISURE, SLEEP)
    - Parks inside blocks (disappears from road)
    - Never leaves the simulation area
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random):
        super().__init__(world, VehicleType.RESIDENT, pathfinder, rng)
        self.home_block: Optional[BuildingBlock] = None
        self.current_block: Optional[BuildingBlock] = None
        self.activity: str = "SLEEP"  # Current activity
        self.trips_this_zone: int = 0
        self.max_trips_per_zone: int = 3  # Allow multiple trips per zone
        self.idle_ticks: int = 0
        self.min_idle_before_trip: int = 5  # Min ticks parked before next trip

    def assign_home(self, block: BuildingBlock):
        """Assign a home (residential) block to this resident."""
        self.home_block = block
        self.current_block = block

    def decide_action(self, current_tick: int, current_hour: int):
        """
        Decide whether to start a trip based on current time zone.
        Uses the traffic probability tables to determine transitions.
        """
        if self.state == VehicleState.MOVING:
            return  # Already moving

        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return  # Can't move

        # Count idle time when parked
        if self.state == VehicleState.PARKED:
            self.idle_ticks += 1
            if self.idle_ticks < self.min_idle_before_trip:
                return  # Wait before next trip

        if self.trips_this_zone >= self.max_trips_per_zone:
            return  # Max trips reached for this zone

        # Find current zone
        zone = self._get_current_zone(current_hour)
        if not zone:
            return

        # Boost: each tick has a chance to start a trip
        # Use a per-tick probability derived from zone probability
        per_tick_boost = 0.15  # 15% chance each tick to try a transition
        if self.rng.random() > per_tick_boost:
            return

        # Check each possible transition for this zone
        for transition_code, probability in zone.transitions.items():
            if transition_code not in TRANSITION_MAP:
                continue

            source_cat, dest_cat, purpose = TRANSITION_MAP[transition_code]

            # Check if we're at the right source
            if self.current_block and self.current_block.category != source_cat:
                continue

            # Roll probability (boosted 3x for more visible traffic)
            if self.rng.random() < probability * 3.0:
                # Find destination block
                dest_block = self.world.get_random_block(dest_cat)
                if dest_block and dest_block.block_id != (
                        self.current_block.block_id if self.current_block else -1):
                    self._start_block_trip(dest_block, purpose)
                    self.trips_this_zone += 1
                    self.idle_ticks = 0
                    return

    def _start_block_trip(self, dest_block: BuildingBlock, purpose: str):
        """Start a trip from current block to destination block."""
        if not self.current_block:
            return

        # Spawn at current block's entry point
        entry = self.current_block.entry_point
        if self.spawn(entry):
            # Navigate to destination block's entry point
            dest_entry = dest_block.entry_point
            if self.start_journey(dest_entry, purpose):
                self.activity = purpose
            else:
                self.despawn()

    def on_arrival(self):
        """Called when resident reaches destination block."""
        if self.destination:
            # Find which block this destination belongs to
            dest_cell = self.world.get_cell(self.destination[0], self.destination[1])
            if dest_cell and dest_cell.block:
                self.current_block = dest_cell.block
            else:
                # Check nearby blocks
                for neighbor in self.world.get_neighbors(self.destination[0],
                                                          self.destination[1]):
                    if neighbor.block:
                        self.current_block = neighbor.block
                        break

        # Park (remove from road)
        self.despawn()
        self.state = VehicleState.PARKED

    def on_zone_change(self):
        """Called when time zone changes - reset trip counter."""
        self.trips_this_zone = 0

    def _get_current_zone(self, current_hour: int):
        """Get the current traffic zone based on hour."""
        for zone in self.world.config.traffic.zones:
            if zone.start_hour <= current_hour < zone.end_hour:
                return zone
            # Handle midnight wrap
            if zone.start_hour > zone.end_hour:
                if current_hour >= zone.start_hour or current_hour < zone.end_hour:
                    return zone
        return None
