"""
Events module: Weather (storms), breakdowns, and accidents.
"""
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from world import GridWorld, CellType, Direction
from agents.base_agent import BaseVehicle, VehicleState


@dataclass
class Storm:
    """A storm affecting a circular area on the grid."""
    storm_id: int
    center: Tuple[int, int]   # (row, col)
    radius: int               # SR - effect radius
    speed_reduction: int      # VR - speed reduction
    duration: int             # Ticks remaining
    active: bool = True

    def affects_position(self, row: int, col: int) -> bool:
        """Check if a position is within the storm's radius."""
        if not self.active:
            return False
        dist = math.sqrt((row - self.center[0])**2 + (col - self.center[1])**2)
        return dist <= self.radius


class WeatherSystem:
    """Manages weather events (storms) in the simulation."""

    def __init__(self, world: GridWorld, rng: random.Random):
        self.world = world
        self.rng = rng
        self.storms: List[Storm] = []
        self._next_storm_id = 0
        self.max_storms = world.config.weather.max_storms
        self.storm_radius = world.config.weather.storm_radius
        self.speed_reduction = world.config.weather.storm_speed_reduction
        self.storm_probability = world.config.weather.storm_probability

    def tick(self):
        """Update weather each tick."""
        # Update existing storms
        for storm in self.storms:
            if storm.active:
                storm.duration -= 1
                if storm.duration <= 0:
                    storm.active = False

        # Remove inactive storms
        self.storms = [s for s in self.storms if s.active]

        # Maybe spawn new storm
        if len(self.storms) < self.max_storms:
            if self.rng.random() < self.storm_probability:
                self._spawn_storm()

    def _spawn_storm(self):
        """Spawn a new storm at a random position."""
        row = self.rng.randint(0, self.world.rows - 1)
        col = self.rng.randint(0, self.world.cols - 1)
        duration = self.rng.randint(20, 100)  # Storm lasts 20-100 ticks

        storm = Storm(
            storm_id=self._next_storm_id,
            center=(row, col),
            radius=self.storm_radius,
            speed_reduction=self.speed_reduction,
            duration=duration
        )
        self.storms.append(storm)
        self._next_storm_id += 1

    def get_speed_reduction_at(self, row: int, col: int) -> int:
        """Get total speed reduction at a position from all storms."""
        reduction = 0
        for storm in self.storms:
            if storm.affects_position(row, col):
                reduction = max(reduction, storm.speed_reduction)
        return reduction


class EventManager:
    """Manages random events: breakdowns and accidents."""

    def __init__(self, world: GridWorld, rng: random.Random):
        self.world = world
        self.rng = rng
        self.config = world.config.events

    def check_breakdown(self, vehicle: BaseVehicle) -> bool:
        """
        Check if a vehicle has a breakdown.
        Probability: PMF per tick.
        """
        if vehicle.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT,
                              VehicleState.PARKED, VehicleState.DESPAWNED):
            return False

        if self.rng.random() < self.config.breakdown_probability:
            duration = self.config.breakdown_duration

            # If it's a service vehicle (FOOD/COLLECTION) at a block,
            # duration is proportional to block area
            if vehicle.position:
                cell = self.world.get_cell(vehicle.position[0], vehicle.position[1])
                if cell:
                    # Check nearby blocks for service vehicle breakdown
                    for neighbor in self.world.get_neighbors(
                            vehicle.position[0], vehicle.position[1]):
                        if neighbor.block:
                            from agents.base_agent import VehicleType
                            if vehicle.vehicle_type in (VehicleType.FOOD_TRUCK,
                                                         VehicleType.GARBAGE_TRUCK):
                                duration = int(
                                    self.config.service_breakdown_factor *
                                    neighbor.block.area
                                )
                            break

            vehicle.trigger_breakdown(duration)
            self._handle_breakdown_traffic(vehicle)
            return True
        return False

    def check_accident(self, vehicle1: BaseVehicle, vehicle2: BaseVehicle) -> bool:
        """
        Check if two vehicles have an accident.
        Conditions:
        1. Opposite lanes on same road
        2. Adjacent to road center
        3. In Moore neighborhood of each other
        Probability: PA when conditions met.
        """
        if not vehicle1.position or not vehicle2.position:
            return False

        pos1 = vehicle1.position
        pos2 = vehicle2.position

        # Check Moore neighborhood
        if not self._in_moore_neighborhood(pos1, pos2):
            return False

        cell1 = self.world.get_cell(pos1[0], pos1[1])
        cell2 = self.world.get_cell(pos2[0], pos2[1])

        if not cell1 or not cell2:
            return False

        # Must be on same road
        if cell1.road_id is None or cell1.road_id != cell2.road_id:
            return False

        # Must be in opposite directions
        if (cell1.lane_direction and cell2.lane_direction and
                cell1.lane_direction == cell2.lane_direction.opposite):

            # Must be adjacent to road center (lanes touching)
            if self._lanes_adjacent_to_center(pos1, pos2, cell1.road_id):
                if self.rng.random() < self.config.accident_probability:
                    vehicle1.trigger_accident(self.config.accident_duration)
                    vehicle2.trigger_accident(self.config.accident_duration)
                    return True

        return False

    def _in_moore_neighborhood(self, pos1: Tuple[int, int],
                                pos2: Tuple[int, int]) -> bool:
        """Check if two positions are in Moore neighborhood (8-connected)."""
        return (abs(pos1[0] - pos2[0]) <= 1 and
                abs(pos1[1] - pos2[1]) <= 1 and
                pos1 != pos2)

    def _lanes_adjacent_to_center(self, pos1: Tuple[int, int],
                                   pos2: Tuple[int, int],
                                   road_id: int) -> bool:
        """Check if two positions are in lanes adjacent to road center."""
        road = self.world.roads.get(road_id)
        if not road:
            return False

        # For R1 (4 wide) and R2 (2 wide), the center lanes are adjacent
        # This is a simplification - check if they're in adjacent columns/rows
        return (abs(pos1[0] - pos2[0]) <= 1 and abs(pos1[1] - pos2[1]) <= 1)

    def _handle_breakdown_traffic(self, vehicle: BaseVehicle):
        """
        Handle traffic effects of a breakdown.
        - On R3 (one-way): blocks traffic for the duration
        - On R1/R2: vehicles can use opposite lane
        """
        if not vehicle.position:
            return

        cell = self.world.get_cell(vehicle.position[0], vehicle.position[1])
        if not cell or cell.road_id is None:
            return

        road = self.world.roads.get(cell.road_id)
        if not road:
            return

        # R3 one-way streets get completely blocked
        # (vehicles behind will need to wait or re-route)
        # This is handled naturally by the movement system -
        # the broken vehicle blocks the cell
