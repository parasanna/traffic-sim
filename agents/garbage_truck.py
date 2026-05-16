"""
Garbage Truck (Απορριμματοφόρο): Όχημα καθαρισμού μόλυνσης/σκουπιδιών (Κατηγορία "COLLECTION").
Μπαίνει από δρόμους R1, μαζεύει σκουπίδια από ΟΛΑ τα είδη κτιρίων.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder, MultiTargetPathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class GarbageTruck(BaseVehicle):
    """
    Πράκτορας οχήματος συλλογής απορριμμάτων.
    
    Συμπεριφορά:
    - Ανήκει στον στόλο N, με χωρητικότητα N1 μονάδες.
    - Στόχοι: ΟΛΑ τα οικοδομικά τετράγωνα (κατηγορίες 1-5).
    - Μπαίνει/Βγαίνει από τα όρια του χάρτη (είσοδοι R1).
    - Λειτουργεί 24 ώρες το 24ωρο, συνεχόμενα.
    - Παρκάρει δίπλα στην είσοδο του κτιρίου για να μαζέψει τα σκουπίδια.
    - Όταν γεμίσει, επιστρέφει σε μια έξοδο για να "αδειάσει" και ξαναμπαίνει.
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random, capacity: int):
        super().__init__(world, VehicleType.GARBAGE_TRUCK, pathfinder, rng)
        self.capacity: int = capacity          # N1 - Μέγιστη χωρητικότητα
        self.current_load: float = 0.0         # Ξεκινάει άδειο (0.0)
        self.multi_pathfinder = MultiTargetPathfinder(world)
        self.target_blocks: List[BuildingBlock] = []  # Λίστα με τα κτίρια που θέλουν καθάρισμα
        self.current_target_idx: int = 0
        self.is_servicing: bool = False
        self.service_timer: int = 0

    def decide_action(self, current_tick: int, current_hour: int):
        """Αποφασίζει τι θα κάνει σε κάθε χρονικό βήμα (tick)."""
        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return  # Αν έχει βλάβη, κάθεται

        if self.state == VehicleState.MOVING:
            return  # Αν ταξιδεύει, συνεχίζει το ταξίδι του

        if self.is_servicing:
            self._service_tick() # Αν μαζεύει σκουπίδια, συνεχίζει να μαζεύει
            return

        if self.current_load >= self.capacity:
            # Είναι γεμάτο! Πρέπει να πάει στη χωματερή (εκτός χάρτη) να αδειάσει
            self._navigate_to_exit_for_unload()
            return

        if self.state == VehicleState.IDLE:
            # Ψάχνει το επόμενο κτίριο για να μαζέψει σκουπίδια
            self._find_next_target()

    def spawn_at_entry(self) -> bool:
        """Εμφανίζεται σε μια τυχαία είσοδο R1 με άδειο κάδο."""
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
        """Σχεδιάζει δρομολόγιο για να επισκεφθεί τα πιο "βρώμικα" κτίρια."""
        dirty_blocks = []
        for block in self.world.blocks.values():
            # Πάει μόνο σε κτίρια που είναι γεμάτα σκουπίδια πάνω από 30%
            if block.pollution_level > block.pollution_capacity * 0.3:
                dirty_blocks.append(block)

        # Ταξινομεί τα κτίρια βάζοντας πρώτα τα πιο βρώμικα (για να τα σώσει γρήγορα)
        dirty_blocks.sort(key=lambda b: -b.pollution_level)
        self.target_blocks = dirty_blocks
        self.current_target_idx = 0

        # Ξεκινάει προς τον πρώτο στόχο
        if self.target_blocks:
            self._navigate_to_target(self.target_blocks[0])

    def _find_next_target(self):
        """Βρίσκει τον επόμενο στόχο (κτίριο)."""
        if self.current_target_idx < len(self.target_blocks):
            target = self.target_blocks[self.current_target_idx]
            self._navigate_to_target(target)
        else:
            # Αν τελείωσε η λίστα, φτιάχνει νέο δρομολόγιο
            self._plan_collection_route()
            if not self.target_blocks:
                # Αν η πόλη είναι πεντακάθαρη, περιμένει (IDLE)
                self.state = VehicleState.IDLE

    def _navigate_to_target(self, block: BuildingBlock):
        """Υπολογίζει διαδρομή προς την είσοδο του κτιρίου για συλλογή."""
        dest = block.entry_point
        self.start_journey(dest, "COLLECTION")

    def _navigate_to_exit_for_unload(self):
        """Υπολογίζει διαδρομή προς την έξοδο της πόλης για άδειασμα."""
        if self.world.border_exits:
            exit_point = self.rng.choice(self.world.border_exits)
            self.start_journey(exit_point, "UNLOAD")

    def on_arrival(self):
        """Καλείται μόλις φτάσει στον προορισμό του."""
        if self.journey_purpose == "COLLECTION":
            self._start_service() # Αρχίζει να μαζεύει
        elif self.journey_purpose == "UNLOAD":
            # Βγαίνει από τον χάρτη, αδειάζει τα πάντα, και ξαναμπαίνει στο επόμενο tick
            self.despawn()
            self.current_load = 0.0
            self.state = VehicleState.IDLE
            self.spawn_at_entry()

    def _start_service(self):
        """Αλλάζει την κατάσταση σε SERVICING και ξεκινάει τη συλλογή."""
        self.is_servicing = True
        self.state = VehicleState.SERVICING
        self.service_timer = max(1, 5)  # Σταθερός χρόνος (π.χ. 5 ticks) για το άδειασμα κάδων

    def _service_tick(self):
        """Εκτελεί ένα tick από τη διαδικασία συλλογής σκουπιδιών."""
        self.service_timer -= 1

        if self.current_target_idx < len(self.target_blocks):
            block = self.target_blocks[self.current_target_idx]
            
            # Υπολογίζει πόσο ελεύθερο χώρο έχει ακόμα το απορριμματοφόρο
            remaining_capacity = self.capacity - self.current_load
            
            # Παίρνει σκουπίδια από το κτίριο (όσα χωράνε)
            collected = block.collect_pollution(min(5.0, remaining_capacity))
            self.current_load += collected

        # Αν τελείωσε ο χρόνος ή αν γέμισε τελείως το φορτηγό
        if self.service_timer <= 0 or self.current_load >= self.capacity:
            self.is_servicing = False
            self.current_target_idx += 1
            self.state = VehicleState.IDLE
