"""
Resident Vehicle (Μόνιμος Κάτοικος): Αντιπροσωπεύει τα οχήματα του μόνιμου πληθυσμού (P1).
Ακολουθεί καθημερινά μοτίβα δραστηριοτήτων (π.χ. Σπίτι -> Δουλειά -> Σπίτι) ανάλογα με τη ζώνη ώρας.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


# Χάρτης Μεταβάσεων: Κωδικός -> (Κατηγορία_Αφετηρίας, Κατηγορία_Προορισμού, Σκοπός)
TRANSITION_MAP = {
    "Res->Off(W)": (BlockCategory.RESIDENTIAL, BlockCategory.OFFICE, "WORK"), # Σπίτι -> Γραφείο (Δουλειά)
    "Res->Mar(W)": (BlockCategory.RESIDENTIAL, BlockCategory.MARKET, "WORK"), # Σπίτι -> Αγορά (Δουλειά)
    "Res->Lei(W)": (BlockCategory.RESIDENTIAL, BlockCategory.LEISURE, "WORK"), # Σπίτι -> Διασκέδαση (Δουλειά)
    "Res->Oth(W)": (BlockCategory.RESIDENTIAL, BlockCategory.OTHER, "WORK"), # Σπίτι -> Άλλο (Δουλειά)
    "Res->Mar(F)": (BlockCategory.RESIDENTIAL, BlockCategory.MARKET, "FOOD"), # Σπίτι -> Αγορά (Ψώνια)
    "Res->Oth(O)": (BlockCategory.RESIDENTIAL, BlockCategory.OTHER, "OTHER"), # Σπίτι -> Άλλο (Διάφορα)
    "Off->Oth(O)": (BlockCategory.OFFICE, BlockCategory.OTHER, "OTHER"), # Γραφείο -> Άλλο (Διάφορα)
    "Res->Lei(L)": (BlockCategory.RESIDENTIAL, BlockCategory.LEISURE, "LEISURE"), # Σπίτι -> Διασκέδαση
    "Off->Lei(L)": (BlockCategory.OFFICE, BlockCategory.LEISURE, "LEISURE"), # Γραφείο -> Διασκέδαση
    "Mar->Lei(L)": (BlockCategory.MARKET, BlockCategory.LEISURE, "LEISURE"), # Αγορά -> Διασκέδαση
    "Oth->Lei(L)": (BlockCategory.OTHER, BlockCategory.LEISURE, "LEISURE"), # Άλλο -> Διασκέδαση
    "Mar->Oth(O)": (BlockCategory.MARKET, BlockCategory.OTHER, "OTHER"), # Αγορά -> Άλλο
    "Lei->Oth(O)": (BlockCategory.LEISURE, BlockCategory.OTHER, "OTHER"), # Διασκέδαση -> Άλλο
    "Off->Res(S)": (BlockCategory.OFFICE, BlockCategory.RESIDENTIAL, "SLEEP"), # Γραφείο -> Σπίτι (Ύπνος)
    "Mar->Res(S)": (BlockCategory.MARKET, BlockCategory.RESIDENTIAL, "SLEEP"), # Αγορά -> Σπίτι (Ύπνος)
    "Lei->Res(S)": (BlockCategory.LEISURE, BlockCategory.RESIDENTIAL, "SLEEP"), # Διασκέδαση -> Σπίτι (Ύπνος)
    "Oth->Res(S)": (BlockCategory.OTHER, BlockCategory.RESIDENTIAL, "SLEEP"), # Άλλο -> Σπίτι (Ύπνος)
}


class ResidentVehicle(BaseVehicle):
    """
    Όχημα Μόνιμου Κατοίκου (P1).
    
    Συμπεριφορά:
    - Ξεκινάει και καταλήγει πάντα σε Οικοδομικά Τετράγωνα (κτίρια).
    - Ακολουθεί καθημερινό πρόγραμμα (ΔΟΥΛΕΙΑ, ΦΑΓΗΤΟ, ΔΙΑΣΚΕΔΑΣΗ, ΥΠΝΟΣ).
    - Όταν φτάνει στον προορισμό του, παρκάρει μέσα στο κτίριο (εξαφανίζεται από το δρόμο).
    - Δεν φεύγει ποτέ εκτός του χάρτη της πόλης.
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random):
        super().__init__(world, VehicleType.RESIDENT, pathfinder, rng)
        self.home_block: Optional[BuildingBlock] = None       # Το "Σπίτι" του
        self.current_block: Optional[BuildingBlock] = None    # Το κτίριο που βρίσκεται τώρα
        self.activity: str = "SLEEP"                          # Η τρέχουσα δραστηριότητα (π.χ. Υπνος)
        self.trips_this_zone: int = 0                         # Πόσα ταξίδια έκανε σε αυτή τη ζώνη
        self.max_trips_per_zone: int = 3                      # Μέγιστα επιτρεπτά ταξίδια ανά ζώνη ώρας
        self.idle_ticks: int = 0                              # Πόση ώρα περιμένει παρκαρισμένος
        self.min_idle_before_trip: int = 5                    # Ελάχιστος χρόνος παραμονής (ticks) πριν ξαναβγεί

    def assign_home(self, block: BuildingBlock):
        """Ορίζει ένα σπίτι (Residential block) για αυτόν τον κάτοικο."""
        self.home_block = block
        self.current_block = block

    def decide_action(self, current_tick: int, current_hour: int):
        """
        Αποφασίζει αν θα ξεκινήσει ένα νέο ταξίδι, βάσει της τρέχουσας ώρας.
        Χρησιμοποιεί τον πίνακα πιθανοτήτων μεταβάσεων από το config.
        """
        if self.state == VehicleState.MOVING:
            return  # Ήδη οδηγεί, δεν κάνει κάτι νέο

        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return  # Έχει βλάβη/ατύχημα, δεν μπορεί να κουνηθεί

        # Μετράει πόσο χρόνο έχει μείνει παρκαρισμένος
        if self.state == VehicleState.PARKED:
            self.idle_ticks += 1
            if self.idle_ticks < self.min_idle_before_trip:
                return  # Περιμένει λίγο πριν ξαναφύγει

        if self.trips_this_zone >= self.max_trips_per_zone:
            return  # Έκανε ήδη αρκετά ταξίδια για αυτή τη ζώνη της ημέρας

        # Βρίσκει σε ποια ζώνη (zone) είμαστε τώρα (π.χ. 06:00 - 09:00)
        zone = self._get_current_zone(current_hour)
        if not zone:
            return

        # Πιθανότητα (ανά tick) να δοκιμάσει να κάνει ένα ταξίδι
        per_tick_boost = 0.15  # 15% πιθανότητα
        if self.rng.random() > per_tick_boost:
            return

        # Ελέγχει όλες τις πιθανές μεταβάσεις (transitions) για αυτή τη ζώνη
        for transition_code, probability in zone.transitions.items():
            if transition_code not in TRANSITION_MAP:
                continue

            source_cat, dest_cat, purpose = TRANSITION_MAP[transition_code]

            # Ελέγχει αν το τρέχον κτίριό του ταιριάζει με την Αφετηρία (Source)
            if self.current_block and self.current_block.category != source_cat:
                continue

            # "Ρίχνει το ζάρι" με βάση την πιθανότητα (x3 για να υπάρχει πιο πυκνή κίνηση)
            if self.rng.random() < probability * 3.0:
                # Βρίσκει ένα τυχαίο κτίριο-προορισμό με τη σωστή κατηγορία
                dest_block = self.world.get_random_block(dest_cat)
                if dest_block and dest_block.block_id != (
                        self.current_block.block_id if self.current_block else -1):
                    # Ξεκινάει το ταξίδι
                    self._start_block_trip(dest_block, purpose)
                    self.trips_this_zone += 1
                    self.idle_ticks = 0
                    return

    def _start_block_trip(self, dest_block: BuildingBlock, purpose: str):
        """Ξεκινάει το ταξίδι από το τρέχον κτίριο στο κτίριο-προορισμό."""
        if not self.current_block:
            return

        # Εμφάνιση (Spawn) του οχήματος στην "πόρτα" (entry point) του κτιρίου του
        entry = self.current_block.entry_point
        if self.spawn(entry):
            # Υπολογισμός διαδρομής (Navigation) προς την πόρτα του προορισμού
            dest_entry = dest_block.entry_point
            if self.start_journey(dest_entry, purpose):
                self.activity = purpose
            else:
                self.despawn() # Αν δεν βρεθεί δρόμος, ξαναπαρκάρει μέσα

    def on_arrival(self):
        """Καλείται όταν ο κάτοικος φτάσει στον προορισμό του."""
        if self.destination:
            # Βρίσκει σε ποιο κτίριο ανήκει αυτή η πόρτα
            dest_cell = self.world.get_cell(self.destination[0], self.destination[1])
            if dest_cell and dest_cell.block:
                self.current_block = dest_cell.block
            else:
                # Ψάχνει μήπως είναι σε διπλανό κελί
                for neighbor in self.world.get_neighbors(self.destination[0],
                                                          self.destination[1]):
                    if neighbor.block:
                        self.current_block = neighbor.block
                        break

        # Παρκάρει (εξαφανίζεται από τον δρόμο για να μην πιάνει χώρο)
        self.despawn()
        self.state = VehicleState.PARKED

    def on_zone_change(self):
        """Καλείται όταν αλλάζει η ζώνη της ώρας - Μηδενίζει τον μετρητή ταξιδιών."""
        self.trips_this_zone = 0

    def _get_current_zone(self, current_hour: int):
        """Επιστρέφει τη σωστή κυκλοφοριακή ζώνη ανάλογα με την ώρα."""
        for zone in self.world.config.traffic.zones:
            if zone.start_hour <= current_hour < zone.end_hour:
                return zone
            # Χειρισμός της περίπτωσης που η ζώνη περνάει τα μεσάνυχτα (π.χ. 22:00 - 02:00)
            if zone.start_hour > zone.end_hour:
                if current_hour >= zone.start_hour or current_hour < zone.end_hour:
                    return zone
        return None
