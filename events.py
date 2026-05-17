"""
Μονάδα Συμβάντων (Events module): Διαχειρίζεται τα τυχαία γεγονότα του συστήματος.
Περιλαμβάνει τον Καιρό (Καταιγίδες/Κυκλώνες), τις Βλάβες, και τα Ατυχήματα.
"""
import random
import math
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, Set
from world import GridWorld, CellType, Direction
from agents.base_agent import BaseVehicle, VehicleState


@dataclass
class Storm:
    """Μία καταιγίδα που επηρεάζει μια κυκλική περιοχή στον χάρτη."""
    storm_id: int
    center: Tuple[int, int]   # (γραμμή, στήλη) - το κέντρο της καταιγίδας
    radius: int               # SR - η ακτίνα επιρροής της καταιγίδας
    speed_reduction: int      # VR - η μείωση ταχύτητας για τα οχήματα που είναι μέσα
    duration: int             # Πόσα Ticks απομένουν μέχρι να σταματήσει
    active: bool = True

    def affects_position(self, row: int, col: int) -> bool:
        """Ελέγχει αν μια συγκεκριμένη θέση βρίσκεται μέσα στην ακτίνα της καταιγίδας."""
        if not self.active:
            return False
        # Πυθαγόρειο θεώρημα για τον υπολογισμό της απόστασης
        dist = math.sqrt((row - self.center[0])**2 + (col - self.center[1])**2)
        return dist <= self.radius


class WeatherSystem:
    """Διαχειρίζεται τα καιρικά φαινόμενα (Καταιγίδες) στην προσομοίωση."""

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
        """Ενημερώνει τον καιρό σε κάθε tick (χρονικό βήμα) της προσομοίωσης."""
        # Ενημέρωση υπαρχουσών καταιγίδων
        for storm in self.storms:
            if storm.active:
                storm.duration -= 1
                if storm.duration <= 0:
                    storm.active = False # Η καταιγίδα τελείωσε

        # Καθαρισμός λίστας από ανενεργές καταιγίδες
        self.storms = [s for s in self.storms if s.active]

        # Πιθανή δημιουργία νέας καταιγίδας
        if len(self.storms) < self.max_storms:
            if self.rng.random() < self.storm_probability:
                self._spawn_storm()

    def _spawn_storm(self):
        """Δημιουργεί μια νέα καταιγίδα σε τυχαία θέση στο χάρτη."""
        row = self.rng.randint(0, self.world.rows - 1)
        col = self.rng.randint(0, self.world.cols - 1)
        duration = self.rng.randint(20, 100)  # Η καταιγίδα κρατάει από 20 έως 100 ticks

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
        """Επιστρέφει τη συνολική μείωση ταχύτητας για ένα όχημα σε αυτή τη θέση (λόγω καιρού)."""
        reduction = 0
        for storm in self.storms:
            if storm.affects_position(row, col):
                reduction = max(reduction, storm.speed_reduction)
        return reduction


class EventManager:
    """Διαχειρίζεται τα τυχαία γεγονότα κυκλοφορίας: Βλάβες (Breakdowns) και Ατυχήματα (Accidents)."""

    def __init__(self, world: GridWorld, rng: random.Random, simulation=None):
        self.world = world
        self.rng = rng
        self.config = world.config.events
        self.simulation = simulation

    def check_breakdown(self, vehicle: BaseVehicle) -> bool:
        """
        Ελέγχει αν το όχημα θα πάθει βλάβη.
        Πιθανότητα: PMF ανά tick.
        """
        # Αν έχει ήδη βλάβη, ατύχημα ή είναι παρκαρισμένο, αγνόησέ το
        if vehicle.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT,
                              VehicleState.PARKED, VehicleState.DESPAWNED):
            return False

        # ΦΑΣΗ 3: Δυναμική Πιθανότητα Βλάβης (Fatigue Factor)
        # Όσο πιο πολύ έχει ταξιδέψει, τόσο αυξάνεται η πιθανότητα!
        fatigue_factor = 1.0 + (vehicle.total_distance / 2000.0)
        actual_prob = self.config.breakdown_probability * fatigue_factor

        if self.rng.random() < actual_prob:
            duration = self.config.breakdown_duration

            # Εάν είναι όχημα εξυπηρέτησης (Φορτηγό Φαγητού / Απορριμματοφόρο) και είναι σε τετράγωνο
            # Η διάρκεια της βλάβης είναι ανάλογη του μεγέθους του τετραγώνου
            if vehicle.position:
                cell = self.world.get_cell(vehicle.position[0], vehicle.position[1])
                if cell:
                    # Ψάχνει τα γειτονικά κελιά για να δει αν υπάρχει οικοδομικό τετράγωνο
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
            
            # V2V: Broadcast hazard to other vehicles
            if self.simulation and vehicle.position:
                self.simulation.broadcast_hazard(vehicle.position)
                
            return True
        return False

    def check_accident(self, vehicle1: BaseVehicle, vehicle2: BaseVehicle) -> bool:
        """
        Ελέγχει αν δύο οχήματα θα τρακάρουν.
        Προϋποθέσεις για να συμβεί:
        1. Να είναι σε αντίθετες λωρίδες στον ίδιο δρόμο.
        2. Να βρίσκονται στις εσωτερικές λωρίδες (κοντά στο κέντρο του δρόμου).
        3. Να είναι σε γειτονιά Moore (δηλαδή το ένα δίπλα/διαγώνια στο άλλο).
        """
        if not vehicle1.position or not vehicle2.position:
            return False

        pos1 = vehicle1.position
        pos2 = vehicle2.position

        # Έλεγχος γειτονιάς Moore (Πρέπει να είναι δίπλα-δίπλα)
        if not self._in_moore_neighborhood(pos1, pos2):
            return False

        cell1 = self.world.get_cell(pos1[0], pos1[1])
        cell2 = self.world.get_cell(pos2[0], pos2[1])

        if not cell1 or not cell2:
            return False

        # Πρέπει να βρίσκονται στον ίδιο δρόμο
        if cell1.road_id is None or cell1.road_id != cell2.road_id:
            return False

        # Πρέπει να κινούνται σε αντίθετες κατευθύνσεις
        if (cell1.lane_direction and cell2.lane_direction and
                cell1.lane_direction == cell2.lane_direction.opposite):

            # Πρέπει να βρίσκονται στις λωρίδες δίπλα στο διαχωριστικό (κέντρο δρόμου)
            if self._lanes_adjacent_to_center(pos1, pos2, cell1.road_id):
                if self.rng.random() < self.config.accident_probability:
                    vehicle1.trigger_accident(self.config.accident_duration)
                    vehicle2.trigger_accident(self.config.accident_duration)
                    
                    # V2V: Broadcast hazard
                    if self.simulation:
                        self.simulation.broadcast_hazard(pos1)
                        
                    return True

        return False

    def _in_moore_neighborhood(self, pos1: Tuple[int, int],
                                pos2: Tuple[int, int]) -> bool:
        """Ελέγχει αν 2 θέσεις ανήκουν σε γειτονιά Moore (8 κατευθύνσεων)."""
        return (abs(pos1[0] - pos2[0]) <= 1 and
                abs(pos1[1] - pos2[1]) <= 1 and
                pos1 != pos2)

    def _lanes_adjacent_to_center(self, pos1: Tuple[int, int],
                                   pos2: Tuple[int, int],
                                   road_id: int) -> bool:
        """Ελέγχει αν δύο θέσεις είναι σε λωρίδες που συνορεύουν με το κέντρο του δρόμου."""
        road = self.world.roads.get(road_id)
        if not road:
            return False

        # Για δρόμους R1 (4 λωρίδες) και R2 (2 λωρίδες), οι κεντρικές λωρίδες συνορεύουν.
        # Απλοποίηση: Ελέγχουμε απλά αν τα κελιά είναι δίπλα το ένα στο άλλο (άρα συνορεύουν)
        return (abs(pos1[0] - pos2[0]) <= 1 and abs(pos1[1] - pos2[1]) <= 1)

    def _handle_breakdown_traffic(self, vehicle: BaseVehicle):
        """
        Χειρίζεται τις επιπτώσεις μιας βλάβης στην κυκλοφορία.
        - Σε δρόμους R3 (Μονόδρομους): Μπλοκάρει τελείως η κυκλοφορία από πίσω
        - Σε R1/R2: Τα οχήματα αναγκάζονται να αλλάξουν λωρίδα (ή ρεύμα)
        """
        if not vehicle.position:
            return

        cell = self.world.get_cell(vehicle.position[0], vehicle.position[1])
        if not cell or cell.road_id is None:
            return

        road = self.world.roads.get(cell.road_id)
        if not road:
            return

        # Στους μονόδρομους (R3), η κυκλοφορία μπλοκάρεται ολοσχερώς.
        # Αυτό το χειρίζεται αυτόματα το σύστημα κίνησης του κώδικα (tick_move)
        # αφού το κελί παραμένει "πιασμένο" και τα από πίσω οχήματα σταματούν.
