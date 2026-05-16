"""
Food Truck (Φορτηγό Τροφοδοσίας): Όχημα logistics (Κατηγορία "FOOD").
Μπαίνει από δρόμους R1, παραδίδει φαγητό σε κτίρια (Αγορές, Διασκέδαση) και βγαίνει για ανεφοδιασμό.
"""
import random
from typing import Optional, Tuple, List
from world import GridWorld, BlockCategory, BuildingBlock
from pathfinding import Pathfinder, MultiTargetPathfinder
from agents.base_agent import BaseVehicle, VehicleState, VehicleType


class FoodTruck(BaseVehicle):
    """
    Πράκτορας οχήματος τροφοδοσίας φαγητού.
    
    Συμπεριφορά:
    - Ανήκει στον στόλο M, μεταφέρει M1 μονάδες φαγητού.
    - Στόχοι: Οικοδομικά τετράγωνα Αγοράς (Market) και Διασκέδασης (Leisure).
    - Μπαίνει και βγαίνει από τα σημεία (πόρτες) των δρόμων R1 στα όρια του χάρτη.
    - Λειτουργεί 24 ώρες το 24ωρο, συνεχόμενα.
    - Παρκάρει δίπλα στο σημείο εισόδου (πεζοδρόμιο) του κτιρίου για να ξεφορτώσει.
    - Όταν αδειάσει (ξοδέψει όλο το φαγητό), πάει στην έξοδο, βγαίνει από τον χάρτη για "Ανεφοδιασμό" και ξαναμπαίνει.
    """

    def __init__(self, world: GridWorld, pathfinder: Pathfinder,
                 rng: random.Random, capacity: int):
        super().__init__(world, VehicleType.FOOD_TRUCK, pathfinder, rng)
        self.capacity: int = capacity          # M1 - Μέγιστη χωρητικότητα φαγητού
        self.current_load: float = capacity    # Ξεκινάει πάντα γεμάτο
        self.multi_pathfinder = MultiTargetPathfinder(world)
        self.target_blocks: List[BuildingBlock] = []  # Λίστα με τα κτίρια που πρέπει να παραδώσει
        self.current_target_idx: int = 0
        self.is_servicing: bool = False
        self.service_timer: int = 0

    def decide_action(self, current_tick: int, current_hour: int):
        """Αποφασίζει ποια ενέργεια θα κάνει σε αυτό το tick."""
        if self.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT):
            return  # Δεν μπορεί να κάνει τίποτα αν έχει βλάβη/ατύχημα

        if self.state == VehicleState.MOVING:
            return  # Αν ταξιδεύει, συνεχίζει το ταξίδι του

        if self.is_servicing:
            self._service_tick() # Αν ξεφορτώνει, συνεχίζει τη δουλειά
            return

        if self.current_load <= 0:
            # Έμεινε από φαγητό - Πρέπει να πάει στην έξοδο για ανεφοδιασμό
            self._navigate_to_exit_for_reload()
            return

        if self.state == VehicleState.IDLE:
            # Ψάχνει το επόμενο κτίριο για να παραδώσει φαγητό
            self._find_next_target()

    def spawn_at_entry(self) -> bool:
        """Εμφανίζεται σε ένα τυχαίο σημείο εισόδου (R1) με πλήρες φορτίο."""
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
        """Σχεδιάζει το δρομολόγιο για να επισκεφθεί τα κτίρια που ξεμένουν από φαγητό."""
        # Ψάχνει μόνο σε Αγορές (Market) και Διασκέδαση (Leisure)
        target_categories = [BlockCategory.MARKET, BlockCategory.LEISURE]
        needy_blocks = []

        for cat in target_categories:
            for block in self.world.get_blocks_by_category(cat):
                # Αν το φαγητό τους έχει πέσει κάτω από το 50%
                if block.food_level < block.food_capacity * 0.5:
                    needy_blocks.append(block)

        # Ταξινομεί τα κτίρια βάζοντας πρώτα αυτά που "πεινάνε" περισσότερο
        needy_blocks.sort(key=lambda b: b.food_level / max(1, b.food_capacity))
        self.target_blocks = needy_blocks
        self.current_target_idx = 0

        # Ξεκινάει προς το πρώτο κτίριο της λίστας
        if self.target_blocks:
            self._navigate_to_target(self.target_blocks[0])

    def _find_next_target(self):
        """Βρίσκει τον επόμενο στόχο για παράδοση φαγητού."""
        if self.current_target_idx < len(self.target_blocks):
            target = self.target_blocks[self.current_target_idx]
            self._navigate_to_target(target)
        else:
            # Τελείωσε η λίστα, φτιάχνει νέο δρομολόγιο
            self._plan_delivery_route()
            if not self.target_blocks:
                # Αν κανένα κτίριο δεν θέλει φαγητό προς το παρόν, απλά περιμένει
                self.state = VehicleState.IDLE

    def _navigate_to_target(self, block: BuildingBlock):
        """Υπολογίζει διαδρομή προς την πόρτα (είσοδο) του κτιρίου."""
        dest = block.entry_point
        self.start_journey(dest, "FOOD_DELIVERY")

    def _navigate_to_exit_for_reload(self):
        """Υπολογίζει διαδρομή προς μια έξοδο του χάρτη για ανεφοδιασμό."""
        if self.world.border_exits:
            exit_point = self.rng.choice(self.world.border_exits)
            self.start_journey(exit_point, "RELOAD")

    def on_arrival(self):
        """Καλείται όταν το φορτηγό φτάσει στον προορισμό του."""
        if self.journey_purpose == "FOOD_DELIVERY":
            # Ξεκινάει να ξεφορτώνει
            self._start_service()
        elif self.journey_purpose == "RELOAD":
            # Βγαίνει εκτός χάρτη για ανεφοδιασμό και ξαναμπαίνει αμέσως γεμάτο
            self.despawn()
            self.current_load = self.capacity
            self.state = VehicleState.IDLE
            self.spawn_at_entry() # Ξαναμπαίνει στο επόμενο tick

    def _start_service(self):
        """Αλλάζει την κατάσταση σε SERVICING και ξεκινάει να ξεφορτώνει."""
        self.is_servicing = True
        self.state = VehicleState.SERVICING
        # Ο χρόνος ξεφορτώματος εξαρτάται από το πόσο φορτίο έχει
        self.service_timer = max(1, int(self.current_load * 0.1))

    def _service_tick(self):
        """Εκτελεί ένα tick από τη διαδικασία ξεφορτώματος/εξυπηρέτησης."""
        self.service_timer -= 1

        if self.current_target_idx < len(self.target_blocks):
            block = self.target_blocks[self.current_target_idx]
            # Παραδίδει φαγητό
            deliver_amount = min(5.0, self.current_load)
            actually_delivered = block.deliver_food(deliver_amount)
            self.current_load -= actually_delivered

        if self.service_timer <= 0 or self.current_load <= 0:
            self.is_servicing = False
            self.current_target_idx += 1
            self.state = VehicleState.IDLE
