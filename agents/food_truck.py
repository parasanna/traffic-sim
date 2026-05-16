"""
Food Truck: Logistics supply vehicle ("FOOD").
Enters via R1, delivers food to target blocks (Market, Leisure).
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder, MultiTargetPathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class FoodTruck(BaseVehicle):
    """
    Food supply vehicle agent.
    
    Behavior:
    - Part of fleet M, carries M1 units of food
    - Targets: Market (3) and Leisure (4) blocks
    - Enters/exits via R1 entry/exit points
    - Operates 24h continuously
    - Parks next to block entry point (beside, not on road)
    - When food depleted, returns to exit to "reload" and re-enter
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random, capacity: int):
        super().__init__(world, VehicleType.FOOD_TRUCK, pathfinder, rng)
        self.capacity: int = capacity          # M1
        self.current_load: float = capacity    # Starts full
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

        if self.current_load <= 0:
            # Need to reload - exit and re-enter
            self._navigate_to_exit_for_reload()
            return

        if self.state == VehicleState.IDLE:
            # Find next block to supply
            self._find_next_target()

    def spawn_at_entry(self) -> bool:
        """Spawn at a random R1 entry point with full load."""
        if not self.world.border_entries:
            return False

        entries = list(self.world.border_entries)
        self.rng.shuffle(entries)

        for entry in entries:
            if self.spawn(entry):
                self.entry_point = entry
                self.current_load = self.capacity
                self._plan_delivery_route()
                return True
        return False

    def _plan_delivery_route(self):
        """Plan a route to visit blocks that need food."""
        # Get blocks that need food (Market and Leisure)
        target_categories = [BlockCategory.MARKET, BlockCategory.LEISURE]
        needy_blocks = []

        for cat in target_categories:
            for block in self.world.get_blocks_by_category(cat):
                if block.food_level < block.food_capacity * 0.5:
                    needy_blocks.append(block)

        # Sort by need (lowest food level first)
        needy_blocks.sort(key=lambda b: b.food_level / max(1, b.food_capacity))
        self.target_blocks = needy_blocks
        self.current_target_idx = 0

        # Start moving to first target
        if self.target_blocks:
            self._navigate_to_target(self.target_blocks[0])

    def _find_next_target(self):
        """Find the next block to deliver food to."""
        if self.current_target_idx < len(self.target_blocks):
            target = self.target_blocks[self.current_target_idx]
            self._navigate_to_target(target)
        else:
            # Re-plan route
            self._plan_delivery_route()
            if not self.target_blocks:
                # Nothing to deliver, wait
                self.state = VehicleState.IDLE

    def _navigate_to_target(self, block: BuildingBlock):
        """Navigate to a block's entry point for delivery."""
        dest = block.entry_point
        self.start_journey(dest, "FOOD_DELIVERY")

    def _navigate_to_exit_for_reload(self):
        """Navigate to an exit point to reload."""
        if self.world.border_exits:
            exit_point = self.rng.choice(self.world.border_exits)
            self.start_journey(exit_point, "RELOAD")

    def on_arrival(self):
        """Called when food truck reaches destination."""
        if self.journey_purpose == "FOOD_DELIVERY":
            # Start servicing the block
            self._start_service()
        elif self.journey_purpose == "RELOAD":
            # Reload and re-enter
            self.despawn()
            self.current_load = self.capacity
            self.state = VehicleState.IDLE
            # Will re-spawn next tick
            self.spawn_at_entry()

    def _start_service(self):
        """Start delivering food to the current block."""
        self.is_servicing = True
        self.state = VehicleState.SERVICING
        # Service time proportional to delivery amount
        self.service_timer = max(1, int(self.current_load * 0.1))

    def _service_tick(self):
        """Process one tick of food delivery service."""
        self.service_timer -= 1

        if self.current_target_idx < len(self.target_blocks):
            block = self.target_blocks[self.current_target_idx]
            # Deliver food
            deliver_amount = min(5.0, self.current_load)
            actually_delivered = block.deliver_food(deliver_amount)
            self.current_load -= actually_delivered

        if self.service_timer <= 0 or self.current_load <= 0:
            self.is_servicing = False
            self.current_target_idx += 1
            self.state = VehicleState.IDLE
