"""
Garbage Truck: Pollution collection vehicle ("COLLECTION").
Enters via R1, collects pollution from ALL block types.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder, MultiTargetPathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class GarbageTruck(BaseVehicle):
    """
    Garbage collection vehicle agent.
    
    Behavior:
    - Part of fleet N, capacity N1 units
    - Targets: ALL block types (1-5)
    - Enters/exits via R1 entry/exit points
    - Operates 24h continuously
    - Parks next to block entry point
    - When full, returns to exit to "unload" and re-enter
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random, capacity: int):
        super().__init__(world, VehicleType.GARBAGE_TRUCK, pathfinder, rng)
        self.capacity: int = capacity          # N1
        self.current_load: float = 0.0         # Starts empty
        self.multi_pathfinder = MultiTargetPathfinder(world)
        self.target_blocks: List[BuildingBlock] = []
        self.current_target_idx: int = 0
        self.is_servicing: bool = False
        self.service_timer: int = 0

    def decide_action(self, current_tick: int, current_hour: int):
        """Decide what to do this tick."""
        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return

        if self.state == VehicleState.MOVING:
            return

        if self.is_servicing:
            self._service_tick()
            return

        if self.current_load >= self.capacity:
            # Full - need to unload
            self._navigate_to_exit_for_unload()
            return

        if self.state == VehicleState.IDLE:
            self._find_next_target()

    def spawn_at_entry(self) -> bool:
        """Spawn at a random R1 entry point with empty load."""
        if not self.world.border_entries:
            return False

        entries = list(self.world.border_entries)
        self.rng.shuffle(entries)

        for entry in entries:
            if self.spawn(entry):
                self.entry_point = entry
                self.current_load = 0.0
                self._plan_collection_route()
                return True
        return False

    def _plan_collection_route(self):
        """Plan a route to visit blocks that need collection."""
        dirty_blocks = []
        for block in self.world.blocks.values():
            if block.pollution_level > block.pollution_capacity * 0.3:
                dirty_blocks.append(block)

        # Sort by pollution level (highest first)
        dirty_blocks.sort(key=lambda b: -b.pollution_level)
        self.target_blocks = dirty_blocks
        self.current_target_idx = 0

        if self.target_blocks:
            self._navigate_to_target(self.target_blocks[0])

    def _find_next_target(self):
        """Find next block to collect from."""
        if self.current_target_idx < len(self.target_blocks):
            target = self.target_blocks[self.current_target_idx]
            self._navigate_to_target(target)
        else:
            self._plan_collection_route()
            if not self.target_blocks:
                self.state = VehicleState.IDLE

    def _navigate_to_target(self, block: BuildingBlock):
        """Navigate to a block's entry point for collection."""
        dest = block.entry_point
        self.start_journey(dest, "COLLECTION")

    def _navigate_to_exit_for_unload(self):
        """Navigate to an exit point to unload."""
        if self.world.border_exits:
            exit_point = self.rng.choice(self.world.border_exits)
            self.start_journey(exit_point, "UNLOAD")

    def on_arrival(self):
        """Called when garbage truck reaches destination."""
        if self.journey_purpose == "COLLECTION":
            self._start_service()
        elif self.journey_purpose == "UNLOAD":
            self.despawn()
            self.current_load = 0.0
            self.state = VehicleState.IDLE
            self.spawn_at_entry()

    def _start_service(self):
        """Start collecting pollution from current block."""
        self.is_servicing = True
        self.state = VehicleState.SERVICING
        self.service_timer = max(1, 5)  # Fixed service time

    def _service_tick(self):
        """Process one tick of pollution collection."""
        self.service_timer -= 1

        if self.current_target_idx < len(self.target_blocks):
            block = self.target_blocks[self.current_target_idx]
            remaining_capacity = self.capacity - self.current_load
            collected = block.collect_pollution(min(5.0, remaining_capacity))
            self.current_load += collected

        if self.service_timer <= 0 or self.current_load >= self.capacity:
            self.is_servicing = False
            self.current_target_idx += 1
            self.state = VehicleState.IDLE
