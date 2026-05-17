"""
Transient Vehicle (Διερχόμενο Όχημα): Αντιπροσωπεύει τη διερχόμενη κυκλοφορία (P2).
Τα οχήματα αυτά μπαίνουν από την άκρη του χάρτη (R1 είσοδοι), διασχίζουν την πόλη
και βγαίνουν από την άλλη πλευρά (R1 έξοδοι). Δεν παρκάρουν ποτέ.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, CellType
from pathfinding import Pathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class TransientVehicle(BaseVehicle):
    """
    Όχημα Διερχόμενου Πληθυσμού (P2).
    
    Συμπεριφορά:
    - Μπαίνει στην περιοχή από τα σημεία εισόδου των μεγάλων δρόμων (R1) στα όρια του χάρτη.
    - Διασχίζει την περιοχή χρησιμοποιώντας κυρίως τους δρόμους R1 (λεωφόρους).
    - Αποχωρεί από τα σημεία εξόδου R1 στα όρια του χάρτη.
    - ΠΟΤΕ δεν παρκάρει.
    - Σε περιπτώσεις ανάγκης (π.χ. μποτιλιάρισμα), μπορεί να χρησιμοποιήσει στενότερους δρόμους.
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random):
        super().__init__(world, VehicleType.TRANSIENT, pathfinder, rng)
        self.entry_point: Optional[Tuple[int, int]] = None  # Σημείο Εισόδου
        self.exit_point: Optional[Tuple[int, int]] = None   # Σημείο Εξόδου
        self.spawn_tick: int = 0                             # [ΜΕΤΡΙΚΕΣ] Πότε μπήκε στον χάρτη
        self.despawn_tick: int = 0                           # [ΜΕΤΡΙΚΕΣ] Πότε βγήκε από τον χάρτη
        self.transit_time: int = 0                           # [ΜΕΤΡΙΚΕΣ] Χρόνος Εξόδου - Χρόνος Εισόδου

    def decide_action(self, current_tick: int, current_hour: int):
        """
        Τα διερχόμενα οχήματα βρίσκονται πάντα σε κίνηση προς την έξοδο.
        Ελέγχει απλά αν πρέπει να υπολογίσει νέα διαδρομή.
        """
        if self.state == VehicleState.MOVING:
            return  # Ήδη οδηγεί προς τα έξω

        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return  # Δεν μπορεί να κάνει τίποτα

        if self.state == VehicleState.IDLE and self.position:
            # Αν κάθεται άπραγο και δεν έχει διαδρομή, προσπαθεί να βρει δρόμο για την έξοδο
            if not self.current_path or self.path_index >= len(self.current_path):
                self._navigate_to_exit()

    def spawn_at_entry(self) -> bool:
        """Εμφάνιση (Spawn) σε ένα τυχαίο σημείο εισόδου (R1) στα όρια της πόλης."""
        if not self.world.border_entries:
            return False

        # Δοκιμάζει τυχαία σημεία εισόδου μέχρι να βρει κάποιο ελεύθερο (που να μην έχει άλλο αμάξι)
        entries = list(self.world.border_entries)
        self.rng.shuffle(entries)

        for entry in entries:
            if self.spawn(entry):
                self.entry_point = entry
                self.origin = entry
                self.spawn_tick = getattr(self, '_current_tick', 0)  # [ΜΕΤΡΙΚΕΣ]
                # Μόλις μπει, διαλέγει αμέσως από ποια έξοδο θα βγει
                self._select_exit_point()
                if self.exit_point:
                    self.start_journey(self.exit_point, "TRANSIT")
                return True

        return False

    def _select_exit_point(self):
        """Επιλέγει ένα σημείο εξόδου, προτιμώντας συνήθως ένα που είναι μακριά από την είσοδο."""
        if not self.world.border_exits or not self.entry_point:
            return

        exits = list(self.world.border_exits)
        # Ταξινομεί τις εξόδους έτσι ώστε οι πιο μακρινές (Manhattan distance) να είναι πρώτες
        exits.sort(key=lambda e: -(abs(e[0] - self.entry_point[0]) +
                                     abs(e[1] - self.entry_point[1])))

        # Διαλέγει μια τυχαία έξοδο από το 33% των πιο μακρινών εξόδων (για ποικιλία)
        top_n = max(1, len(exits) // 3)
        self.exit_point = self.rng.choice(exits[:top_n])
        self.destination = self.exit_point

    def _navigate_to_exit(self):
        """Προσπαθεί να βρει διαδρομή προς την επιλεγμένη έξοδο."""
        if not self.exit_point:
            self._select_exit_point()
        if self.exit_point:
            if not self.start_journey(self.exit_point, "TRANSIT"):
                # Αν απέτυχε να βρει δρόμο, δοκιμάζει να διαλέξει άλλη έξοδο
                self._select_exit_point()
                if self.exit_point:
                    self.start_journey(self.exit_point, "TRANSIT")

    def on_arrival(self):
        """Καλείται όταν το όχημα φτάσει στην έξοδο - Εξαφανίζεται (Despawn) από τον χάρτη."""
        # [ΜΕΤΡΙΚΕΣ] Καταγραφή χρόνου εξόδου
        self.despawn_tick = getattr(self, '_current_tick', 0)
        self.transit_time = self.despawn_tick - self.spawn_tick
        self.despawn()
        self.state = VehicleState.DESPAWNED
