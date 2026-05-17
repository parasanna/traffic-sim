"""
Κύρια Μηχανή Προσομοίωσης (Main Simulation Engine): Ενορχηστρώνει όλη την προσομοίωση.
Διαχειρίζεται τον χρόνο (ticks), τα οχήματα, τα γεγονότα, τον καιρό και τα στατιστικά.
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
from traffic_lights import TrafficLightSystem

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger(__name__)


@dataclass
class SimulationStats:
    """Στατιστικά που συλλέγονται κατά τη διάρκεια της προσομοίωσης."""
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
            'vehicles_by_type': self.vehicles_by_type,
        }


class Simulation:
    """
    Η Κύρια Μηχανή της Προσομοίωσης.
    
    Ελέγχει και ενορχηστρώνει τα πάντα:
    - Παραγωγή του Κόσμου (πλέγμα, δρόμοι, κτίρια)
    - Δημιουργία και κύκλος ζωής των Πρακτόρων (Οχήματα)
    - Τον κεντρικό βρόχο της προσομοίωσης (Tick-based loop)
    - Διαχείριση Ωρών και Ζωνών (Time zones)
    - Καιρό και τυχαία Γεγονότα (events)
    - Συλλογή Στατιστικών
    """

    def __init__(self, config: Optional[SimulationConfig] = None):
        self.config = config or SimulationConfig()
        self.rng = random.Random(self.config.random_seed)

        # Κόσμος και Πλοήγηση
        self.world: Optional[GridWorld] = None
        self.pathfinder: Optional[Pathfinder] = None

        # Πράκτορες (Οχήματα)
        self.vehicles: Dict[int, BaseVehicle] = {}
        self.residents: List[ResidentVehicle] = []
        self.transients: List[TransientVehicle] = []
        self.food_trucks: List[FoodTruck] = []
        self.garbage_trucks: List[GarbageTruck] = []

        # Υποσυστήματα
        self.weather: Optional[WeatherSystem] = None
        self.event_manager: Optional[EventManager] = None

        # Διαχείριση Χρόνου
        self.current_tick: int = 0
        self.current_hour: int = 6  # Η προσομοίωση ξεκινάει 06:00 το πρωί
        self.current_zone_id: int = 1
        self.ticks_per_hour: int = self.config.world.ticks_per_hour
        self.day: int = 1

        # Στατιστικά
        self.stats = SimulationStats()

        # Συναρτήσεις αναμονής (Callbacks) για ενημέρωση του Dashboard
        self._on_tick_callbacks = []
        self._on_zone_change_callbacks = []

        # Κατάσταση (State)
        self.is_initialized = False
        self.is_running = False
        self.is_paused = False

    def initialize(self):
        """Αρχικοποίηση: δημιουργεί το πλέγμα, τους δρόμους, τα κτίρια και τα οχήματα."""
        logger.info("Initializing simulation world...")

        # 1. Δημιουργία άδειου κόσμου
        self.world = GridWorld(self.config)

        # 2. Κατασκευή Οδικού Δικτύου
        logger.info("Generating road network...")
        road_gen = RoadNetworkGenerator(self.world, self.config)
        road_gen.generate()
        logger.info(f"Generated {len(self.world.roads)} roads, "
                     f"{len(self.world.border_entries)} entries, "
                     f"{len(self.world.border_exits)} exits")

        # 3. Κατασκευή Οικοδομικών Τετραγώνων (Κτίρια)
        logger.info("Generating building blocks...")
        block_gen = BlockGenerator(self.world, self.config)
        block_gen.generate()
        logger.info(f"Generated {len(self.world.blocks)} blocks")

        # 4. Ενεργοποίηση συστήματος εύρεσης διαδρομών (Pathfinder)
        self.pathfinder = Pathfinder(self.world)
        self.pathfinder.simulation = self  # Φάση 4: Πρόσβαση στα οχήματα για το Smart GPS

        # 5. Ενεργοποίηση Καιρού και Γεγονότων
        self.weather = WeatherSystem(self.world, self.rng)
        self.event_manager = EventManager(self.world, self.rng, simulation=self)

        # 5b. [ΦΑΣΗ 6] Σύστημα Φαναριών
        self.traffic_lights = TrafficLightSystem(self.world, cycle_duration=10)
        self.traffic_lights.detect_intersections()

        # 6. Δημιουργία Οχημάτων
        self._create_residents()
        self._create_service_fleets()

        self.is_initialized = True

        # 7. Σύνδεση φαναριών με τα οχήματα
        for vehicle in self.vehicles.values():
            vehicle._traffic_lights = self.traffic_lights

        logger.info(f"Simulation initialized: {self.world}")
        logger.info(f"  Residents: {len(self.residents)}")
        logger.info(f"  Food trucks: {len(self.food_trucks)}")
        logger.info(f"  Garbage trucks: {len(self.garbage_trucks)}")

    def _create_residents(self):
        """Δημιουργεί τον μόνιμο πληθυσμό (P1) και τον αναθέτει σε σπίτια (Residential)."""
        residential_blocks = self.world.get_blocks_by_category(BlockCategory.RESIDENTIAL)
        if not residential_blocks:
            logger.warning("No residential blocks found!")
            return

        for i in range(self.config.population.permanent_population):
            vehicle = ResidentVehicle(self.world, self.pathfinder, self.rng)
            # Αναθέτει το όχημα σε σπίτι (κυκλικά)
            home = residential_blocks[i % len(residential_blocks)]
            vehicle.assign_home(home)
            self.residents.append(vehicle)
            self.vehicles[vehicle.vehicle_id] = vehicle

    def _create_service_fleets(self):
        """Δημιουργεί τους στόλους εξυπηρέτησης: Food Trucks και Απορριμματοφόρα."""
        # Φορτηγά Τροφοδοσίας (Food trucks)
        for i in range(self.config.fleet.food_fleet_size):
            truck = FoodTruck(
                self.world, self.pathfinder, self.rng,
                self.config.fleet.food_capacity
            )
            truck.spawn_at_entry()
            self.food_trucks.append(truck)
            self.vehicles[truck.vehicle_id] = truck

        # Απορριμματοφόρα (Garbage trucks)
        for i in range(self.config.fleet.collection_fleet_size):
            truck = GarbageTruck(
                self.world, self.pathfinder, self.rng,
                self.config.fleet.collection_capacity
            )
            truck.spawn_at_entry()
            self.garbage_trucks.append(truck)
            self.vehicles[truck.vehicle_id] = truck

    def tick(self):
        """Εκτελεί ένα "βήμα" (Tick) της προσομοίωσης."""
        if not self.is_initialized:
            raise RuntimeError("Simulation not initialized. Call initialize() first.")

        self.current_tick += 1

        # 0. Ενημέρωση Ρολογιού & Ζώνης
        self._update_time()

        # 1. Ενημέρωση Καιρού
        self.weather.tick()

        # 2. Εφαρμογή επιπτώσεων καιρού (π.χ. μείωση ταχύτητας στα οχήματα)
        self._apply_weather_effects()

        # 2b. [ΦΑΣΗ 6] Ενημέρωση Φαναριών
        if hasattr(self, 'traffic_lights'):
            self.traffic_lights.tick()

        # 3. Σπορά διερχόμενης κίνησης (Transient Traffic) βάσει της πιθανότητας της Ζώνης (zone probability)
        self._manage_transient_traffic()

        # 4. Απόφαση: Όλα τα οχήματα σκέφτονται τι πρέπει να κάνουν τώρα
        for vehicle in list(self.vehicles.values()):
            if vehicle.is_active() or vehicle.state == VehicleState.PARKED:
                vehicle.decide_action(self.current_tick, self.current_hour)

        # 5. Κίνηση: Όλα τα οχήματα μετακινούνται ένα βήμα μπροστά (ή μειώνουν το χρόνο αναμονής)
        for vehicle in list(self.vehicles.values()):
            if vehicle.state == VehicleState.MOVING:
                vehicle.tick_move()
            elif vehicle.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
                vehicle.tick_move()  # Μείωση του χρονομέτρου για το πότε θα φύγει από το ατύχημα

        # 6. Έλεγχος Τυχαίων Γεγονότων (Τρακαρίσματα, Βλάβες)
        self._check_random_events()

        # 7. Ενημέρωση πόρων στα κτίρια (κατανάλωση φαγητού, δημιουργία σκουπιδιών)
        self.world.update_block_resources()

        # 8. Καθαρισμός των διερχόμενων οχημάτων που βγήκαν από το χάρτη
        self._cleanup_despawned()

        # 9. Ενημέρωση Στατιστικών
        self._update_stats()

        # 10. Ειδοποίηση του Dashboard (callbacks)
        for callback in self._on_tick_callbacks:
            callback(self.current_tick, self.stats)

    def _update_time(self):
        """Ενημερώνει την τρέχουσα ώρα και τη ζώνη δραστηριότητας."""
        ticks_in_hour = self.current_tick % self.ticks_per_hour
        if ticks_in_hour == 0 and self.current_tick > 0:
            self.current_hour = (self.current_hour + 1) % 24
            if self.current_hour == 0:
                self.day += 1
                logger.info(f"Day {self.day} starts")

        # Έλεγχος αν άλλαξε η Ζώνη (Zone)
        new_zone = self._get_zone_id(self.current_hour)
        if new_zone != self.current_zone_id:
            old_zone = self.current_zone_id
            self.current_zone_id = new_zone
            logger.info(f"Zone change: {old_zone} -> {new_zone} (hour {self.current_hour})")

            # Ειδοποίηση των κατοίκων για αλλαγή ζώνης (π.χ. πρέπει να πάνε στη δουλειά)
            for resident in self.residents:
                resident.on_zone_change()

            for callback in self._on_zone_change_callbacks:
                callback(old_zone, new_zone)

    def broadcast_hazard(self, hazard_pos: Tuple[int, int], radius: int = 15):
        """
        Επικοινωνία V2V (Vehicle-to-Vehicle). 
        Εκπέμπει σήμα κινδύνου σε όλα τα ενεργά οχήματα γύρω από ένα σημείο.
        Αν η διαδρομή ενός οχήματος περιλαμβάνει το προβληματικό σημείο, θα κάνει re-routing.
        """
        if not self.is_initialized:
            return
            
        from agents.base_agent import VehicleState
        
        for vehicle in self.vehicles.values():
            if not vehicle.position or not vehicle.current_path:
                continue
                
            # Αν το όχημα έχει ήδη βλάβη/ατύχημα, αγνόησέ το
            if vehicle.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
                continue
                
            # Έλεγχος απόστασης Manhattan από το όχημα
            dist_to_hazard = abs(vehicle.position[0] - hazard_pos[0]) + abs(vehicle.position[1] - hazard_pos[1])
            if dist_to_hazard <= radius:
                # Έλεγχος αν το σημείο βρίσκεται μέσα στη σχεδιασμένη διαδρομή του
                if hazard_pos in vehicle.current_path:
                    logger.info(f"V2V: Όχημα {vehicle.vehicle_id} έλαβε σήμα για κίνδυνο στο {hazard_pos}. Re-routing...")
                    # Βρίσκει νέα διαδρομή
                    if vehicle.destination:
                        new_path = vehicle.pathfinder.find_path_relaxed(vehicle.position, vehicle.destination, avoid_positions={hazard_pos})
                        if new_path:
                            vehicle.current_path = new_path
                            vehicle.path_index = 0


    def _get_zone_id(self, hour: int) -> int:
        """Επιστρέφει το Zone ID (π.χ. Πρωί, Απόγευμα, Βράδυ) για μια συγκεκριμένη ώρα."""
        for zone in self.config.traffic.zones:
            if zone.start_hour <= hour < zone.end_hour:
                return zone.zone_id
            # Αν η ζώνη περνάει τα μεσάνυχτα (π.χ. 23:00 - 06:00)
            if zone.start_hour > zone.end_hour:
                if hour >= zone.start_hour or hour < zone.end_hour:
                    return zone.zone_id
        return 1

    def _apply_weather_effects(self):
        """Εφαρμόζει τις μειώσεις ταχύτητας (λόγω καταιγίδας) στα οχήματα που περνούν από μέσα της."""
        for vehicle in self.vehicles.values():
            if vehicle.position:
                reduction = self.weather.get_speed_reduction_at(
                    vehicle.position[0], vehicle.position[1]
                )
                vehicle._storm_reduction = reduction

    def _manage_transient_traffic(self):
        """Ελέγχει και δημιουργεί την κίνηση των διερχόμενων οχημάτων (P2)."""
        zone = None
        for z in self.config.traffic.zones:
            if z.zone_id == self.current_zone_id:
                zone = z
                break

        if not zone:
            return

        # Μέγιστος αριθμός και τρέχων αριθμός
        max_transients = self.config.population.transient_population
        active_transients = sum(1 for t in self.transients if t.is_active())

        if active_transients < max_transients:
            # Πιθανότητα να δημιουργηθεί όχημα αυτό το tick (βάσει των ρυθμίσεων)
            spawn_prob = zone.transient_probability * 2.0 / self.ticks_per_hour
            # Προσπαθούμε να βάλουμε μέχρι 5 οχήματα σε κάθε tick
            for _ in range(5):
                if active_transients >= max_transients:
                    break
                if self.rng.random() < spawn_prob:
                    t = TransientVehicle(self.world, self.pathfinder, self.rng)
                    if t.spawn_at_entry():
                        self.transients.append(t)
                        self.vehicles[t.vehicle_id] = t
                        if hasattr(self, 'traffic_lights'):
                            t._traffic_lights = self.traffic_lights
                        active_transients += 1

    def _check_random_events(self):
        """Ελέγχει αν συνέβη κάποια Βλάβη ή κάποιο Ατύχημα."""
        active_vehicles = [v for v in self.vehicles.values()
                          if v.state == VehicleState.MOVING]

        # 1. Έλεγχος Βλαβών
        for vehicle in active_vehicles:
            if self.event_manager.check_breakdown(vehicle):
                self.stats.total_breakdowns += 1

        # 2. Έλεγχος Ατυχημάτων (Συγκρίνει ζεύγη κοντινών οχημάτων)
        for i, v1 in enumerate(active_vehicles):
            if not v1.position:
                continue
            for v2 in active_vehicles[i+1:]:
                if not v2.position:
                    continue
                
                # Υπολογισμός απόστασης (Manhattan Distance). Αν είναι > 2 δεν τρακάρουν
                dist = (abs(v1.position[0] - v2.position[0]) +
                        abs(v1.position[1] - v2.position[1]))
                if dist <= 2:
                    if self.event_manager.check_accident(v1, v2):
                        self.stats.total_accidents += 1

    def _cleanup_despawned(self):
        """Διαγράφει από τη μνήμη τα οχήματα που βγήκαν εκτός χάρτη για να ελαφρύνει ο υπολογιστής."""
        self.transients = [t for t in self.transients if t.state != VehicleState.DESPAWNED]
        despawned = [vid for vid, v in self.vehicles.items()
                    if v.state == VehicleState.DESPAWNED and
                    v.vehicle_type == VehicleType.TRANSIENT]
        for vid in despawned:
            del self.vehicles[vid]

    def _update_stats(self):
        """Ενημερώνει τα κεντρικά Στατιστικά της προσομοίωσης."""
        self.stats.total_ticks = self.current_tick
        self.stats.active_vehicles = sum(1 for v in self.vehicles.values()
                                          if v.is_active())
        self.stats.total_trips_completed = sum(v.total_trips for v in self.vehicles.values())
        self.stats.total_storms = len(self.weather.storms)

        # Μέτρημα ανά τύπο οχήματος
        self.stats.vehicles_by_type = {}
        for v in self.vehicles.values():
            vtype = v.vehicle_type.value
            self.stats.vehicles_by_type[vtype] = (
                self.stats.vehicles_by_type.get(vtype, 0) + 1
            )

    def run(self, ticks: int = 1000, real_time: bool = False,
            tick_delay: float = 0.0):
        """
        Τρέχει τον κεντρικό βρόχο (loop) της προσομοίωσης.
        
        Args:
            ticks: Αριθμός ticks που θα τρέξει συνολικά
            real_time: Αν είναι True, προσθέτει καθυστέρηση ανάμεσα στα ticks
            tick_delay: Καθυστέρηση σε δευτερόλεπτα
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

                # Τυπώνει πρόοδο στην κονσόλα κάθε 100 ticks
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
        """Παύση της προσομοίωσης."""
        self.is_paused = True

    def resume(self):
        """Συνέχιση της προσομοίωσης."""
        self.is_paused = False

    def stop(self):
        """Τερματισμός της προσομοίωσης."""
        self.is_running = False

    def on_tick(self, callback):
        """Εγγραφή συνάρτησης για εκτέλεση σε κάθε tick."""
        self._on_tick_callbacks.append(callback)

    def on_zone_change(self, callback):
        """Εγγραφή συνάρτησης για εκτέλεση όταν αλλάζει η ώρα/ζώνη."""
        self._on_zone_change_callbacks.append(callback)

    def get_grid_state(self) -> List[List[dict]]:
        """
        Επιστρέφει την τρέχουσα κατάσταση όλου του πλέγματος (δρόμοι, κτίρια, κλπ) 
        σε μορφή JSON για το Dashboard (Frontend).
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
        """Επιστρέφει τις συντεταγμένες όλων των οχημάτων (για να ζωγραφιστούν στον Browser)."""
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
