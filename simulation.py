"""
Main Simulation Engine: Orchestrates the entire simulation.
Manages the tick loop, time zones, agent lifecycle, and events.
"""
import random
import time
import logging
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass, field

from config import SimulationConfig
from world import GridWorld, CellType, BlockCategory
from road_network import RoadNetworkGenerator
from blocks import BlockGenerator
from pathfinding import Pathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType
from agents.resident import ResidentVehicle
from agents.transient import TransientVehicle
from agents.food_truck import FoodTruck
from agents.garbage_truck import GarbageTruck
from events import WeatherSystem, EventManager

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SimulationStats:
    """Statistics collected during simulation."""
    total_ticks: int = 0
    total_trips_completed: int = 0
    total_breakdowns: int = 0
    total_accidents: int = 0
    total_storms: int = 0
    active_vehicles: int = 0
    food_delivered: float = 0.0
    pollution_collected: float = 0.0
    avg_trip_duration: float = 0.0
    vehicles_by_type: Dict[str, int] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            'total_ticks': self.total_ticks,
            'total_trips': self.total_trips_completed,
            'breakdowns': self.total_breakdowns,
            'accidents': self.total_accidents,
            'storms': self.total_storms,
            'active_vehicles': self.active_vehicles,
            'food_delivered': round(self.food_delivered, 1),
            'pollution_collected': round(self.pollution_collected, 1),
        }


class Simulation:
    """
    Main simulation engine.
    
    Orchestrates:
    - World generation (grid, roads, blocks)
    - Agent creation and lifecycle
    - Tick-based simulation loop
    - Time zone management
    - Weather and random events
    - Statistics collection
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.rng = random.Random(self.config.random_seed)

        # World
        self.world: Optional[GridWorld] = None
        self.pathfinder: Optional[Pathfinder] = None

        # Agents
        self.vehicles: Dict[int, BaseVehicle] = {}
        self.residents: List[ResidentVehicle] = []
        self.transients: List[TransientVehicle] = []
        self.food_trucks: List[FoodTruck] = []
        self.garbage_trucks: List[GarbageTruck] = []

        # Systems
        self.weather: Optional[WeatherSystem] = None
        self.event_manager: Optional[EventManager] = None

        # Time tracking
        self.current_tick: int = 0
        self.current_hour: int = 6  # Start at 6 AM
        self.current_zone_id: int = 1
        self.ticks_per_hour: int = self.config.world.ticks_per_hour
        self.day: int = 1

        # Statistics
        self.stats = SimulationStats()

        # Callbacks for visualization
        self._on_tick_callbacks = []
        self._on_zone_change_callbacks = []

        # State
        self.is_initialized = False
        self.is_running = False
        self.is_paused = False

    def initialize(self):
        """Initialize the world, generate roads/blocks, create agents."""
        logger.info("Initializing simulation world...")

        # Create world
        self.world = GridWorld(self.config)

        # Generate road network
        logger.info("Generating road network...")
        road_gen = RoadNetworkGenerator(self.world, self.config)
        road_gen.generate()
        logger.info(f"Generated {len(self.world.roads)} roads, "
                     f"{len(self.world.border_entries)} entries, "
                     f"{len(self.world.border_exits)} exits")

        # Generate building blocks
        logger.info("Generating building blocks...")
        block_gen = BlockGenerator(self.world, self.config)
        block_gen.generate()
        logger.info(f"Generated {len(self.world.blocks)} blocks")

        # Create pathfinder
        self.pathfinder = Pathfinder(self.world)

        # Create weather & event systems
        self.weather = WeatherSystem(self.world, self.rng)
        self.event_manager = EventManager(self.world, self.rng)

        # Create agents
        self._create_residents()
        self._create_service_fleets()

        self.is_initialized = True
        logger.info(f"Simulation initialized: {self.world}")
        logger.info(f"  Residents: {len(self.residents)}")
        logger.info(f"  Food trucks: {len(self.food_trucks)}")
        logger.info(f"  Garbage trucks: {len(self.garbage_trucks)}")

    def _create_residents(self):
        """Create permanent population (P1) vehicles."""
        residential_blocks = self.world.get_blocks_by_category(BlockCategory.RESIDENTIAL)
        if not residential_blocks:
            logger.warning("No residential blocks found!")
            return

        for i in range(self.config.population.permanent_population):
            vehicle = ResidentVehicle(self.world, self.pathfinder, self.rng)
            # Assign to a residential block (round-robin)
            home = residential_blocks[i % len(residential_blocks)]
            vehicle.assign_home(home)
            self.residents.append(vehicle)
            self.vehicles[vehicle.vehicle_id] = vehicle

    def _create_service_fleets(self):
        """Create FOOD and COLLECTION fleet vehicles."""
        # Food trucks
        for i in range(self.config.fleet.food_fleet_size):
            truck = FoodTruck(
                self.world, self.pathfinder, self.rng,
                self.config.fleet.food_capacity
            )
            truck.spawn_at_entry()
            self.food_trucks.append(truck)
            self.vehicles[truck.vehicle_id] = truck

        # Garbage trucks
        for i in range(self.config.fleet.collection_fleet_size):
            truck = GarbageTruck(
                self.world, self.pathfinder, self.rng,
                self.config.fleet.collection_capacity
            )
            truck.spawn_at_entry()
            self.garbage_trucks.append(truck)
            self.vehicles[truck.vehicle_id] = truck

    def tick(self):
        """Execute one simulation tick."""
        if not self.is_initialized:
            raise RuntimeError("Simulation not initialized. Call initialize() first.")

        self.current_tick += 1

        # Update time
        self._update_time()

        # 1. Weather update
        self.weather.tick()

        # 2. Update storm effects on vehicles
        self._apply_weather_effects()

        # 3. Spawn transient traffic based on zone probability
        self._manage_transient_traffic()

        # 4. All agents decide actions
        for vehicle in list(self.vehicles.values()):
            if vehicle.is_active() or vehicle.state == VehicleState.PARKED:
                vehicle.decide_action(self.current_tick, self.current_hour)

        # 5. Move all vehicles
        for vehicle in list(self.vehicles.values()):
            if vehicle.state == VehicleState.MOVING:
                vehicle.tick_move()
            elif vehicle.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
                vehicle.tick_move()  # Process timer countdown

        # 6. Check random events
        self._check_random_events()

        # 7. Update block resources
        self.world.update_block_resources()

        # 8. Cleanup despawned vehicles
        self._cleanup_despawned()

        # 9. Update statistics
        self._update_stats()

        # 10. Notify callbacks
        for callback in self._on_tick_callbacks:
            callback(self.current_tick, self.stats)

    def _update_time(self):
        """Update simulation time (hour and zone)."""
        ticks_in_hour = self.current_tick % self.ticks_per_hour
        if ticks_in_hour == 0 and self.current_tick > 0:
            self.current_hour = (self.current_hour + 1) % 24
            if self.current_hour == 0:
                self.day += 1
                logger.info(f"Day {self.day} starts")

        # Check zone change
        new_zone = self._get_zone_id(self.current_hour)
        if new_zone != self.current_zone_id:
            old_zone = self.current_zone_id
            self.current_zone_id = new_zone
            logger.info(f"Zone change: {old_zone} -> {new_zone} (hour {self.current_hour})")

            # Notify residents of zone change
            for resident in self.residents:
                resident.on_zone_change()

            for callback in self._on_zone_change_callbacks:
                callback(old_zone, new_zone)

    def _get_zone_id(self, hour: int) -> int:
        """Get zone ID for a given hour."""
        for zone in self.config.traffic.zones:
            if zone.start_hour <= hour < zone.end_hour:
                return zone.zone_id
            if zone.start_hour > zone.end_hour:
                if hour >= zone.start_hour or hour < zone.end_hour:
                    return zone.zone_id
        return 1

    def _apply_weather_effects(self):
        """Apply storm speed reduction to affected vehicles."""
        for vehicle in self.vehicles.values():
            if vehicle.position:
                reduction = self.weather.get_speed_reduction_at(
                    vehicle.position[0], vehicle.position[1]
                )
                vehicle._storm_reduction = reduction

    def _manage_transient_traffic(self):
        """Spawn and manage transient (P2) traffic."""
        # Get current zone's transient probability
        zone = None
        for z in self.config.traffic.zones:
            if z.zone_id == self.current_zone_id:
                zone = z
                break

        if not zone:
            return

        # Spawn new transients based on probability
        max_transients = self.config.population.transient_population
        active_transients = sum(1 for t in self.transients if t.is_active())

        if active_transients < max_transients:
            # Spawn multiple transients per tick for denser traffic
            spawn_prob = zone.transient_probability * 2.0 / self.ticks_per_hour
            # Try to spawn up to 5 per tick
            for _ in range(5):
                if active_transients >= max_transients:
                    break
                if self.rng.random() < spawn_prob:
                    t = TransientVehicle(self.world, self.pathfinder, self.rng)
                    if t.spawn_at_entry():
                        self.transients.append(t)
                        self.vehicles[t.vehicle_id] = t
                        active_transients += 1

    def _check_random_events(self):
        """Check for breakdowns and accidents."""
        active_vehicles = [v for v in self.vehicles.values()
                          if v.state == VehicleState.MOVING]

        # Check breakdowns
        for vehicle in active_vehicles:
            if self.event_manager.check_breakdown(vehicle):
                self.stats.total_breakdowns += 1

        # Check accidents (pairwise - only nearby vehicles)
        for i, v1 in enumerate(active_vehicles):
            if not v1.position:
                continue
            for v2 in active_vehicles[i+1:]:
                if not v2.position:
                    continue
                # Only check if nearby
                dist = (abs(v1.position[0] - v2.position[0]) +
                        abs(v1.position[1] - v2.position[1]))
                if dist <= 2:
                    if self.event_manager.check_accident(v1, v2):
                        self.stats.total_accidents += 1

    def _cleanup_despawned(self):
        """Remove despawned transient vehicles from tracking."""
        self.transients = [t for t in self.transients if t.state != VehicleState.DESPAWNED]
        # Remove from vehicles dict too
        despawned = [vid for vid, v in self.vehicles.items()
                    if v.state == VehicleState.DESPAWNED and
                    v.vehicle_type == VehicleType.TRANSIENT]
        for vid in despawned:
            del self.vehicles[vid]

    def _update_stats(self):
        """Update simulation statistics."""
        self.stats.total_ticks = self.current_tick
        self.stats.active_vehicles = sum(1 for v in self.vehicles.values()
                                          if v.is_active())
        self.stats.total_trips_completed = sum(v.total_trips for v in self.vehicles.values())
        self.stats.total_storms = len(self.weather.storms)

        # Count by type
        self.stats.vehicles_by_type = {}
        for v in self.vehicles.values():
            vtype = v.vehicle_type.value
            self.stats.vehicles_by_type[vtype] = (
                self.stats.vehicles_by_type.get(vtype, 0) + 1
            )

    def run(self, ticks: int = 1000, real_time: bool = False,
            tick_delay: float = 0.0):
        """
        Run the simulation for a number of ticks.
        
        Args:
            ticks: Number of ticks to run
            real_time: If True, add delays between ticks
            tick_delay: Delay in seconds between ticks (if real_time)
        """
        if not self.is_initialized:
            self.initialize()

        self.is_running = True
        logger.info(f"Starting simulation for {ticks} ticks...")

        try:
            for _ in range(ticks):
                if not self.is_running:
                    break
                while self.is_paused:
                    time.sleep(0.1)

                self.tick()

                if real_time and tick_delay > 0:
                    time.sleep(tick_delay)

                # Log progress every 100 ticks
                if self.current_tick % 100 == 0:
                    logger.info(f"Tick {self.current_tick}: "
                                 f"active={self.stats.active_vehicles}, "
                                 f"trips={self.stats.total_trips_completed}, "
                                 f"hour={self.current_hour}")

        except KeyboardInterrupt:
            logger.info("Simulation interrupted by user")
        finally:
            self.is_running = False

        logger.info(f"Simulation complete. Final stats: {self.stats.to_dict()}")
        return self.stats

    def pause(self):
        """Pause the simulation."""
        self.is_paused = True

    def resume(self):
        """Resume the simulation."""
        self.is_paused = False

    def stop(self):
        """Stop the simulation."""
        self.is_running = False

    def on_tick(self, callback):
        """Register a callback for each tick."""
        self._on_tick_callbacks.append(callback)

    def on_zone_change(self, callback):
        """Register a callback for zone changes."""
        self._on_zone_change_callbacks.append(callback)

    def get_grid_state(self) -> List[List[dict]]:
        """
        Get the current state of the grid for visualization.
        Returns a 2D array of cell state dictionaries.
        """
        state = []
        for r in range(self.world.rows):
            row = []
            for c in range(self.world.cols):
                cell = self.world.grid[r][c]
                cell_state = {
                    'type': cell.cell_type.name,
                    'occupied': cell.is_occupied,
                    'vehicle_id': cell.vehicle_id,
                    'road_id': cell.road_id,
                }
                if cell.block:
                    cell_state['block_id'] = cell.block.block_id
                    cell_state['block_category'] = cell.block.category.name
                if cell.lane_direction:
                    cell_state['direction'] = cell.lane_direction.name
                row.append(cell_state)
            state.append(row)
        return state

    def get_vehicle_positions(self) -> List[dict]:
        """Get positions of all active vehicles for visualization."""
        positions = []
        for vehicle in self.vehicles.values():
            if vehicle.position and vehicle.is_active():
                positions.append({
                    'id': vehicle.vehicle_id,
                    'type': vehicle.vehicle_type.value,
                    'row': vehicle.position[0],
                    'col': vehicle.position[1],
                    'state': vehicle.state.name,
                    'speed': vehicle.current_speed,
                })
        return positions
