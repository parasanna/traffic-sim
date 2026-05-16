"""
Base Agent module: Abstract vehicle agent with common behavior.
All vehicle types inherit from BaseVehicle.
"""
import random
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from world import GridWorld, CellType, Direction, BuildingBlock, BlockCategory
from pathfinding import Pathfinder


class VehicleState(Enum):
    """Vehicle operational states."""
    IDLE = auto()           # Not moving (parked or waiting)
    MOVING = auto()         # Actively moving along path
    PARKED = auto()         # Parked at destination
    BROKEN_DOWN = auto()    # Immobilized due to breakdown
    IN_ACCIDENT = auto()    # Immobilized due to accident
    SERVICING = auto()      # At block, delivering/collecting
    EXITING = auto()        # Leaving the simulation area
    DESPAWNED = auto()      # Removed from simulation


class VehicleType(Enum):
    """Types of vehicles in the simulation."""
    RESIDENT = "resident"       # P1 - Permanent population
    TRANSIENT = "transient"     # P2 - Passing through
    FOOD_TRUCK = "food_truck"   # FOOD logistics
    GARBAGE_TRUCK = "garbage"   # COLLECTION


@dataclass
class MovementEpisode:
    """A single movement episode (constant speed until stop)."""
    speed: int               # cells/tick for this episode
    path: List[Tuple[int, int]]  # Remaining path
    current_index: int = 0   # Current position in path


class BaseVehicle(ABC):
    """
    Abstract base class for all vehicles in the simulation.
    Handles common movement, state management, and event handling.
    """

    _next_id = 0

    def __init__(self, world: GridWorld, vehicle_type: VehicleType,
                 pathfinder: Pathfinder, rng: random.Random):
        BaseVehicle._next_id += 1
        self.vehicle_id: int = BaseVehicle._next_id
        self.vehicle_type: VehicleType = vehicle_type
        self.world: GridWorld = world
        self.pathfinder: Pathfinder = pathfinder
        self.rng: random.Random = rng

        # Position
        self.position: Optional[Tuple[int, int]] = None  # (row, col)
        self.state: VehicleState = VehicleState.IDLE

        # Movement
        self.current_speed: int = 0
        self.max_speed: int = world.config.vehicle.max_speed
        self.min_speed: int = world.config.vehicle.min_speed
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self.current_episode: Optional[MovementEpisode] = None

        # Journey tracking
        self.origin: Optional[Tuple[int, int]] = None
        self.destination: Optional[Tuple[int, int]] = None
        self.journey_purpose: str = ""

        # Event tracking
        self.breakdown_timer: int = 0
        self.accident_timer: int = 0

        # Statistics
        self.total_distance: int = 0
        self.total_trips: int = 0
        self.ticks_moving: int = 0
        self.ticks_waiting: int = 0

    @abstractmethod
    def decide_action(self, current_tick: int, current_hour: int):
        """Decide what to do this tick (abstract - implemented by subclasses)."""
        pass

    @abstractmethod
    def on_arrival(self):
        """Called when vehicle reaches its destination."""
        pass

    def spawn(self, position: Tuple[int, int]) -> bool:
        """Spawn vehicle at a position on the grid."""
        if self.world.place_vehicle(position[0], position[1], self.vehicle_id):
            self.position = position
            self.state = VehicleState.IDLE
            return True
        return False

    def despawn(self):
        """Remove vehicle from the grid."""
        if self.position:
            self.world.remove_vehicle(self.position[0], self.position[1])
        self.position = None
        self.state = VehicleState.DESPAWNED

    def start_journey(self, destination: Tuple[int, int], purpose: str = "") -> bool:
        """Start a journey to a destination."""
        if not self.position:
            return False

        path = self.pathfinder.find_path(self.position, destination)
        if not path:
            # Try relaxed pathfinding
            path = self.pathfinder.find_path_relaxed(self.position, destination)
        if not path:
            return False

        self.current_path = path
        self.path_index = 0
        self.destination = destination
        self.journey_purpose = purpose
        self.state = VehicleState.MOVING

        # Start new movement episode with random speed
        self._start_new_episode()
        return True

    def _start_new_episode(self):
        """Start a new movement episode with random speed."""
        speed = self.rng.randint(self.min_speed, self.max_speed)

        # Apply weather effects
        storm_reduction = self._get_storm_speed_reduction()
        speed = max(1, speed - storm_reduction)

        self.current_speed = speed
        if self.current_path:
            remaining = self.current_path[self.path_index:]
            self.current_episode = MovementEpisode(
                speed=speed,
                path=remaining
            )

    def _get_storm_speed_reduction(self) -> int:
        """Check if vehicle is affected by storm. Returns speed reduction."""
        # This will be set by the simulation engine based on weather
        return getattr(self, '_storm_reduction', 0)

    def tick_move(self):
        """Execute one tick of movement."""
        if self.state == VehicleState.BROKEN_DOWN:
            self.breakdown_timer -= 1
            if self.breakdown_timer <= 0:
                self.state = VehicleState.MOVING
                self._start_new_episode()
            return

        if self.state == VehicleState.IN_ACCIDENT:
            self.accident_timer -= 1
            if self.accident_timer <= 0:
                self.state = VehicleState.MOVING
                self._start_new_episode()
            return

        if self.state != VehicleState.MOVING or not self.current_path:
            self.ticks_waiting += 1
            return

        # Move up to current_speed cells
        cells_moved = 0
        for _ in range(self.current_speed):
            if self.path_index >= len(self.current_path) - 1:
                # Reached destination
                self.state = VehicleState.IDLE
                self.on_arrival()
                self.total_trips += 1
                return

            next_pos = self.current_path[self.path_index + 1]
            next_cell = self.world.get_cell(next_pos[0], next_pos[1])

            if next_cell and not next_cell.is_occupied:
                # Move to next cell
                if self.position:
                    self.world.remove_vehicle(self.position[0], self.position[1])
                self.world.place_vehicle(next_pos[0], next_pos[1], self.vehicle_id)
                self.position = next_pos
                self.path_index += 1
                cells_moved += 1
            else:
                # Blocked - stop for this tick
                break

        if cells_moved > 0:
            self.total_distance += cells_moved
            self.ticks_moving += 1
        else:
            self.ticks_waiting += 1

    def trigger_breakdown(self, duration: int):
        """Trigger a vehicle breakdown."""
        self.state = VehicleState.BROKEN_DOWN
        self.breakdown_timer = duration
        self.current_speed = 0

    def trigger_accident(self, duration: int):
        """Trigger a vehicle accident."""
        self.state = VehicleState.IN_ACCIDENT
        self.accident_timer = duration
        self.current_speed = 0

    def is_active(self) -> bool:
        """Check if vehicle is currently active in the simulation."""
        return self.state not in (VehicleState.DESPAWNED, VehicleState.PARKED)

    def __repr__(self) -> str:
        return (f"{self.vehicle_type.value}#{self.vehicle_id} "
                f"at {self.position} [{self.state.name}]")
