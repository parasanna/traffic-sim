"""
Βασικός Πράκτορας (Base Agent module): Η αφηρημένη κλάση (Abstract) για όλα τα οχήματα.
Εδώ ορίζεται η βασική συμπεριφορά (κίνηση, βλάβες, ατυχήματα) που κληρονομούν όλοι οι τύποι οχημάτων.
"""
import random
from abc import ABC, abstractmethod
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict
from world import GridWorld, CellType, Direction, BuildingBlock, BlockCategory
from pathfinding import Pathfinder


class VehicleState(Enum):
    """Καταστάσεις λειτουργίας ενός οχήματος."""
    IDLE = auto()           # Ακίνητο (παρκαρισμένο ή περιμένει)
    MOVING = auto()         # Εν κινήσει (ακολουθεί μια διαδρομή)
    PARKED = auto()         # Παρκαρισμένο στον προορισμό του
    BROKEN_DOWN = auto()    # Ακινητοποιημένο λόγω βλάβης
    IN_ACCIDENT = auto()    # Ακινητοποιημένο λόγω ατυχήματος
    SERVICING = auto()      # Σταματημένο για δουλειά (π.χ. αδειάζει σκουπίδια)
    EXITING = auto()        # Αποχωρεί από τον χάρτη
    DESPAWNED = auto()      # Έχει βγει από την προσομοίωση (δεν υπάρχει πια)


class VehicleType(Enum):
    """Οι διάφοροι Τύποι Οχημάτων."""
    RESIDENT = "resident"       # P1 - Μόνιμος πληθυσμός (πορτοκαλί)
    TRANSIENT = "transient"     # P2 - Διερχόμενος πληθυσμός (κόκκινο)
    FOOD_TRUCK = "food_truck"   # Φορτηγό Τροφοδοσίας (γαλάζιο)
    GARBAGE_TRUCK = "garbage"   # Απορριμματοφόρο (πράσινο)


@dataclass
class MovementEpisode:
    """Ένα επεισόδιο κίνησης (δηλαδή η κίνηση με σταθερή ταχύτητα μέχρι την επόμενη στάση)."""
    speed: int                   # Ταχύτητα (κελιά ανά tick) για αυτό το επεισόδιο
    path: List[Tuple[int, int]]  # Η διαδρομή (λίστα από κελιά) που μένει
    current_index: int = 0       # Σε ποιο βήμα της διαδρομής βρισκόμαστε


class BaseVehicle(ABC):
    """
    Η αφηρημένη (Abstract) βασική κλάση για όλα τα οχήματα της προσομοίωσης.
    Αναλαμβάνει την κίνηση στον χάρτη, τη διαχείριση καταστάσεων και τις βλάβες.
    Όλα τα άλλα οχήματα (Resident, Transient κλπ) "πατάνε" πάνω σε αυτήν (κληρονομικότητα).
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

        # Θέση (Συντεταγμένες)
        self.position: Optional[Tuple[int, int]] = None  # (γραμμή, στήλη)
        self.state: VehicleState = VehicleState.IDLE

        # Κίνηση και Ταχύτητα
        self.current_speed: int = 0
        self.max_speed: int = world.config.vehicle.max_speed
        self.min_speed: int = world.config.vehicle.min_speed
        self.current_path: Optional[List[Tuple[int, int]]] = None
        self.path_index: int = 0
        self.current_episode: Optional[MovementEpisode] = None

        # Στοιχεία Ταξιδιού
        self.origin: Optional[Tuple[int, int]] = None
        self.destination: Optional[Tuple[int, int]] = None
        self.journey_purpose: str = ""

        # Χρονόμετρα Γεγονότων
        self.breakdown_timer: int = 0
        self.accident_timer: int = 0

        # Στατιστικά για αυτό το συγκεκριμένο όχημα
        self.total_distance: int = 0
        self.total_trips: int = 0
        self.ticks_moving: int = 0
        self.ticks_waiting: int = 0

        # [ΜΕΤΡΙΚΕΣ] Καταγραφή χρόνων ταξιδιών
        self.trip_start_tick: int = 0        # Πότε ξεκίνησε το τρέχον ταξίδι
        self.trip_start_distance: int = 0    # Απόσταση στο ξεκίνημα (για μέτρηση μήκους)
        self.completed_trip_times: list = [] # Λίστα: [(χρόνος_ταξιδιού, απόσταση_ταξιδιού), ...]

    @abstractmethod
    def decide_action(self, current_tick: int, current_hour: int):
        """Κάθε παιδί-κλάση (π.χ. ResidentVehicle) αποφασίζει μόνη της τι θα κάνει σε κάθε Tick."""
        pass

    @abstractmethod
    def on_arrival(self):
        """Τι συμβαίνει μόλις το όχημα φτάσει στον προορισμό του."""
        pass

    def spawn(self, position: Tuple[int, int]) -> bool:
        """Εμφάνιση (Spawn) του οχήματος στον χάρτη (πλέγμα)."""
        if self.world.place_vehicle(position[0], position[1], self.vehicle_id):
            self.position = position
            self.state = VehicleState.IDLE
            return True
        return False

    def despawn(self):
        """Εξαφάνιση (Αφαίρεση) του οχήματος από τον χάρτη."""
        if self.position:
            self.world.remove_vehicle(self.position[0], self.position[1])
        self.position = None
        self.state = VehicleState.DESPAWNED

    def start_journey(self, destination: Tuple[int, int], purpose: str = "") -> bool:
        """Ξεκινάει ένα ταξίδι προς έναν προορισμό υπολογίζοντας τη διαδρομή."""
        if not self.position:
            return False

        # Εύρεση ιδανικής διαδρομής (A* Algorithm)
        path = self.pathfinder.find_path(self.position, destination)
        if not path:
            # Αν δεν βρει, δοκιμάζει πιο "χαλαρή" αναζήτηση
            path = self.pathfinder.find_path_relaxed(self.position, destination)
        if not path:
            return False

        self.current_path = path
        self.path_index = 0
        self.destination = destination
        self.journey_purpose = purpose
        self.state = VehicleState.MOVING

        # [ΜΕΤΡΙΚΕΣ] Καταγραφή στιγμής εκκίνησης
        self.trip_start_tick = getattr(self, '_current_tick', 0)
        self.trip_start_distance = self.total_distance

        # Ξεκινάει το πρώτο επεισόδιο κίνησης
        self._start_new_episode()
        return True

    def _start_new_episode(self):
        """Επιλέγει μια νέα τυχαία ταχύτητα για αυτό το τμήμα της διαδρομής."""
        speed = self.rng.randint(self.min_speed, self.max_speed)

        # Μείωση ταχύτητας αν υπάρχει καταιγίδα
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
        """Επιστρέφει πόσο πρέπει να φρενάρει αν πέτυχε καταιγίδα (ενημερώνεται από το engine)."""
        return getattr(self, '_storm_reduction', 0)

    def tick_move(self):
        """Εκτελεί την κίνηση του οχήματος για το τρέχον Tick."""
        # 1. Αν έχει βλάβη, απλά περιμένει να λήξει ο χρόνος
        if self.state == VehicleState.BROKEN_DOWN:
            self.breakdown_timer -= 1
            if self.breakdown_timer <= 0:
                self.state = VehicleState.MOVING
                self._start_new_episode()
            return

        # 2. Αν είχε ατύχημα, απλά περιμένει να λήξει ο χρόνος
        if self.state == VehicleState.IN_ACCIDENT:
            self.accident_timer -= 1
            if self.accident_timer <= 0:
                self.state = VehicleState.MOVING
                self._start_new_episode()
            return

        # 3. Αν δεν κινείται, δεν κάνει τίποτα
        if self.state != VehicleState.MOVING or not self.current_path:
            self.ticks_waiting += 1
            return

        # 4. Προσπαθεί να κινηθεί όσα κελιά του επιτρέπει η ταχύτητά του (current_speed)
        cells_moved = 0
        for _ in range(self.current_speed):
            if self.path_index >= len(self.current_path) - 1:
                # Έφτασε στον προορισμό του
                self.state = VehicleState.IDLE
                self.on_arrival()
                self.total_trips += 1

                # [ΜΕΤΡΙΚΕΣ] Καταγραφή χρόνου & απόστασης ταξιδιού
                trip_duration = getattr(self, '_current_tick', 0) - self.trip_start_tick
                trip_distance = self.total_distance - self.trip_start_distance
                if trip_duration > 0:
                    self.completed_trip_times.append((trip_duration, trip_distance))

                return

            next_pos = self.current_path[self.path_index + 1]
            next_cell = self.world.get_cell(next_pos[0], next_pos[1])

            if next_cell:
                # [ΦΑΣΗ 5] Don't Block the Box
                # Αν είμαστε εκτός διασταύρωσης και πάμε να μπούμε σε μία, ελέγχουμε αν υπάρχει ελεύθερη έξοδος
                if self.position and not self.world.is_intersection(*self.position) and self.world.is_intersection(*next_pos):
                    exit_pos = None
                    for i in range(self.path_index + 1, len(self.current_path)):
                        if not self.world.is_intersection(*self.current_path[i]):
                            exit_pos = self.current_path[i]
                            break
                    if exit_pos:
                        exit_cell = self.world.get_cell(*exit_pos)
                        if exit_cell and exit_cell.is_occupied:
                            # Η έξοδος είναι μπλοκαρισμένη! Φρενάρει ΠΡΙΝ μπει στη διασταύρωση.
                            break

                # [ΦΑΣΗ 6] Έλεγχος Φαναριού
                # Αν πάμε να μπούμε σε διασταύρωση με κόκκινο, σταματάμε
                if self.position and hasattr(self, '_traffic_lights') and self._traffic_lights:
                    if not self._traffic_lights.can_pass(self.position, next_pos):
                        break  # Κόκκινο φανάρι!

                if not next_cell.is_occupied:
                    # Αν το επόμενο κελί είναι άδειο, προχωράει
                    if self.position:
                        self.world.remove_vehicle(self.position[0], self.position[1])
                    self.world.place_vehicle(next_pos[0], next_pos[1], self.vehicle_id)
                    self.position = next_pos
                    self.path_index += 1
                    cells_moved += 1
            else:
                # Αν βρει μπροστά του άλλο όχημα (Μποτιλιάρισμα/Εμπόδιο)
                # Δοκιμάζει Δυναμικό Προσπέρασμα (Overtaking)
                if self._attempt_overtake():
                    # Αν πέτυχε το προσπέρασμα, το path άλλαξε, οπότε θα κουνηθεί στο επόμενο loop
                    continue
                else:
                    # Αν απέτυχε, φρενάρει
                    break

        # 5. Καταγραφή Στατιστικών
        if cells_moved > 0:
            self.total_distance += cells_moved
            self.ticks_moving += 1
            self.ticks_waiting = 0  # Μηδενισμός αναμονής αφού κινήθηκε
        else:
            self.ticks_waiting += 1
            
            # Μηχανισμός Απεγκλωβισμού (Re-routing): 
            # Αν είναι μπλοκαρισμένο για πολλά ticks (π.χ. 15), προσπαθεί να βρει άλλη διαδρομή
            if self.ticks_waiting > 15 and self.destination:
                new_path = self.pathfinder.find_path_relaxed(self.position, self.destination)
                if new_path:
                    self.current_path = new_path
                    self.path_index = 0
                    self.ticks_waiting = 0  # Σταματάει να γκρινιάζει, βρήκε άλλη διέξοδο!

    def _attempt_overtake(self) -> bool:
        """
        [ΦΑΣΗ 1] Προσπαθεί να κάνει προσπέραση βγαίνοντας από τη λωρίδα του.
        Ελέγχει αν υπάρχει κενό διπλανό κελί δρόμου για να παρακάμψει το εμπόδιο.
        """
        if not self.position or not self.current_path:
            return False
            
        # Χρειάζεται να υπάρχουν τουλάχιστον 2 βήματα μπροστά για να κάνει την παράκαμψη
        if self.path_index + 2 >= len(self.current_path):
            return False
            
        curr_r, curr_c = self.position
        next1_r, next1_c = self.current_path[self.path_index + 1] # Το εμπόδιο
        next2_r, next2_c = self.current_path[self.path_index + 2] # Εκεί που θέλουμε να καταλήξουμε
        
        # Ελέγχει τα 4 διπλανά κελιά (πάνω, κάτω, αριστερά, δεξιά)
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            side_r, side_c = curr_r + dr, curr_c + dc
            
            # Αγνοεί το κελί που έχει το εμπόδιο
            if side_r == next1_r and side_c == next1_c:
                continue
                
            cell = self.world.get_cell(side_r, side_c)
            # Αν το διπλανό κελί είναι δρόμος και ΔΕΝ έχει όχημα πάνω του
            if cell and cell.cell_type == CellType.ROAD and not cell.is_occupied:
                # Ελέγχουμε αν από αυτό το 'side_cell' μπορούμε να πάμε στο 'next2'
                dist_to_next2 = abs(side_r - next2_r) + abs(side_c - next2_c)
                if dist_to_next2 == 1:
                    # Επιτυχία! Τροποποιούμε τη διαδρομή για να κάνει "ζικ-ζακ"
                    # Εισάγουμε το side_cell ως επόμενο βήμα
                    self.current_path.insert(self.path_index + 1, (side_r, side_c))
                    # Βγάζουμε το εμπόδιο από τη διαδρομή
                    self.current_path.pop(self.path_index + 2)
                    return True
                    
        return False

    def trigger_breakdown(self, duration: int):
        """Ενεργοποιεί κατάσταση Βλάβης στο όχημα."""
        self.state = VehicleState.BROKEN_DOWN
        self.breakdown_timer = duration
        self.current_speed = 0

    def trigger_accident(self, duration: int):
        """Ενεργοποιεί κατάσταση Ατυχήματος στο όχημα."""
        self.state = VehicleState.IN_ACCIDENT
        self.accident_timer = duration
        self.current_speed = 0

    def is_active(self) -> bool:
        """Ελέγχει αν το όχημα βρίσκεται ενεργό στον χάρτη (και όχι εξαφανισμένο/παρκαρισμένο)."""
        return self.state not in (VehicleState.DESPAWNED, VehicleState.PARKED)

    def __repr__(self) -> str:
        return (f"{self.vehicle_type.value}#{self.vehicle_id} "
                f"at {self.position} [{self.state.name}]")
