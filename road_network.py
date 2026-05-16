"""
Road Network Generator (Γεννήτρια Οδικού Δικτύου): Δημιουργεί ένα ρεαλιστικό δίκτυο δρόμων στο πλέγμα.
Διαχειρίζεται τους δρόμους R1 (Λεωφόρους), R2 (Οδούς), και R3 (Μονόδρομους).
"""
import random
from typing import List, Tuple, Optional, Set, Dict
from world import (
    GridWorld, CellType, Direction, RoadType, Road, RoadSegment, Cell
)
from config import SimulationConfig


class RoadNetworkGenerator:
    """
    Δημιουργεί το οδικό δίκτυο πάνω στο πλέγμα (Grid).
    
    Στρατηγική σχεδιασμού:
    - R1 Λεωφόροι (Avenues): Κύριες αρτηρίες, πλάτους 4 κελιών (2 λωρίδες ανά κατεύθυνση).
      Ενώνουν πάντα τα όρια του χάρτη (είσοδοι/έξοδοι πόλης).
    - R2 Οδοί (Streets): Πλάτους 2 κελιών (1 λωρίδα ανά κατεύθυνση), εσωτερικοί δρόμοι.
    - R3 Μονόδρομοι (One-way): Πλάτους 1 κελιού, εσωτερικοί δρόμοι με μία μόνο κατεύθυνση.
    - Πεζοδρόμια (1 κελί) που μπαίνουν ενδιάμεσα από τους δρόμους και τα κτίρια.
    - Φανάρια (Traffic lights) στις διασταυρώσεις.
    """

    def __init__(self, world: GridWorld, config: SimulationConfig):
        self.world = world
        self.config = config
        self.rng = random.Random(config.random_seed + 1)
        self._road_cells: Set[Tuple[int, int]] = set()
        self._sidewalk_cells: Set[Tuple[int, int]] = set()

    def generate(self):
        """Κατασκευάζει ολόκληρο το οδικό δίκτυο βήμα προς βήμα."""
        # Βήμα 1: Τοποθέτηση "Τοίχων" στην περίμετρο του χάρτη (για να μη βγαίνουν εκτός τα αυτοκίνητα)
        self.world.initialize_perimeter_walls()

        # Βήμα 2: Σχεδιασμός του βασικού κανάβου (οριζόντιοι και κάθετοι άξονες δρόμων)
        h_roads, v_roads = self._plan_road_layout()

        # Βήμα 3: Επιλογή των δρόμων που θα γίνουν Λεωφόροι R1
        r1_h, r1_v = self._select_avenues(h_roads, v_roads)

        # Βήμα 4: Επιλογή των δρόμων που θα γίνουν Οδοί R2
        r2_h, r2_v = self._select_streets(h_roads, v_roads, r1_h, r1_v)

        # Βήμα 5: Επιλογή των υπόλοιπων δρόμων για Μονόδρομους R3
        r3_h, r3_v = self._select_oneways(h_roads, v_roads, r1_h, r1_v, r2_h, r2_v)

        # Βήμα 6: Τοποθέτηση (ζωγράφισμα) των δρόμων πάνω στο πλέγμα
        self._place_roads(r1_h, r1_v, RoadType.R1, lanes=2)
        self._place_roads(r2_h, r2_v, RoadType.R2, lanes=1)
        self._place_roads(r3_h, r3_v, RoadType.R3, lanes=1)

        # Βήμα 7: Τοποθέτηση πεζοδρομίων δίπλα από τους δρόμους
        self._place_sidewalks()

        # Βήμα 8: Τοποθέτηση φαναριών στις διασταυρώσεις
        self._place_traffic_lights()

        # Βήμα 9: Ορισμός εισόδων/εξόδων της πόλης στα όρια των δρόμων R1
        self._setup_border_entries()

    def _plan_road_layout(self) -> Tuple[List[int], List[int]]:
        """
        Σχεδιάζει το πλέγμα των κεντρικών αξόνων των δρόμων (κέντρα δρόμων).
        Επιστρέφει (Οριζόντιες γραμμές, Κάθετες στήλες).
        """
        rows = self.world.rows
        cols = self.world.cols

        # Υπολογισμός απόστασης (spacing) ώστε τα οικοδομικά τετράγωνα να έχουν ικανοποιητικό μέγεθος
        target_spacing = 10
        
        # Οριζόντιοι άξονες (γραμμές)
        h_roads = []
        r = target_spacing
        while r < rows - target_spacing:
            h_roads.append(r)
            r += target_spacing + self.rng.randint(-2, 2)

        # Κάθετοι άξονες (στήλες)
        v_roads = []
        c = target_spacing
        while c < cols - target_spacing:
            v_roads.append(c)
            c += target_spacing + self.rng.randint(-2, 2)

        return h_roads, v_roads

    def _select_avenues(self, h_roads: List[int], v_roads: List[int]
                         ) -> Tuple[List[int], List[int]]:
        """Επιλέγει ποιοι άξονες θα γίνουν μεγάλες Λεωφόροι R1 (~15% του συνόλου)."""
        target_r1_count = max(2, int(0.15 * (len(h_roads) + len(v_roads))))

        r1_h = []
        r1_v = []

        if h_roads:
            # Προσπαθεί να τις κατανείμει ομοιόμορφα στο χώρο
            h_count = max(1, target_r1_count // 2)
            step = max(1, len(h_roads) // h_count)
            r1_h = [h_roads[i] for i in range(0, len(h_roads), step)][:h_count]

        if v_roads:
            v_count = max(1, target_r1_count - len(r1_h))
            step = max(1, len(v_roads) // v_count)
            r1_v = [v_roads[i] for i in range(0, len(v_roads), step)][:v_count]

        return r1_h, r1_v

    def _select_streets(self, h_roads: List[int], v_roads: List[int],
                         r1_h: List[int], r1_v: List[int]
                         ) -> Tuple[List[int], List[int]]:
        """Επιλέγει ποιοι από τους υπόλοιπους άξονες θα γίνουν δρόμοι R2 (~70%)."""
        remaining_h = [r for r in h_roads if r not in r1_h]
        remaining_v = [v for v in v_roads if v not in r1_v]

        total_remaining = len(remaining_h) + len(remaining_v)
        target_r2 = int(0.70 / (0.70 + 0.15) * total_remaining)

        r2_h = remaining_h[:max(1, target_r2 // 2)]
        r2_v = remaining_v[:max(1, target_r2 - len(r2_h))]

        return r2_h, r2_v

    def _select_oneways(self, h_roads: List[int], v_roads: List[int],
                         r1_h: List[int], r1_v: List[int],
                         r2_h: List[int], r2_v: List[int]
                         ) -> Tuple[List[int], List[int]]:
        """Επιλέγει ότι περίσσεψε για Μονόδρομους R3 (~15%)."""
        used_h = set(r1_h + r2_h)
        used_v = set(r1_v + r2_v)
        r3_h = [r for r in h_roads if r not in used_h]
        r3_v = [v for v in v_roads if v not in used_v]
        return r3_h, r3_v

    def _place_roads(self, h_centerlines: List[int], v_centerlines: List[int],
                      road_type: RoadType, lanes: int):
        """
        Τοποθετεί ("ζωγραφίζει") τα κελιά του δρόμου πάνω στο πλέγμα (Grid).
        R1: 4 κελιά πλάτος (2 λωρίδες * 2 κατευθύνσεις)
        R2: 2 κελιά πλάτος (1 λωρίδα * 2 κατευθύνσεις)
        R3: 1 κελί πλάτος (1 λωρίδα * 1 κατεύθυνση)
        """
        if road_type == RoadType.R1:
            width = 4
        elif road_type == RoadType.R2:
            width = 2
        else:
            width = 1

        # Τοποθέτηση Οριζόντιων Δρόμων
        for centerline in h_centerlines:
            self._place_single_road(centerline, True, road_type, width, lanes)

        # Τοποθέτηση Κάθετων Δρόμων
        for centerline in v_centerlines:
            self._place_single_road(centerline, False, road_type, width, lanes)

    def _place_single_road(self, centerline: int, is_horizontal: bool,
                            road_type: RoadType, width: int, lanes: int):
        """Τοποθετεί έναν μεμονωμένο δρόμο (είτε οριζόντιο είτε κάθετο)."""
        road_id = self.world.next_road_id()
        road = Road(road_id=road_id, road_type=road_type)
        cells = []
        is_r1 = road_type == RoadType.R1

        # Για τους μονόδρομους R3, επιλέγουμε τυχαία μία σταθερή κατεύθυνση
        if road_type == RoadType.R3:
            r3_dir = self.rng.choice(
                [Direction.EAST, Direction.WEST] if is_horizontal
                else [Direction.NORTH, Direction.SOUTH]
            )

        if is_horizontal:
            row_start = centerline - width // 2
            for r_offset in range(width):
                row = row_start + r_offset
                if not self.world.is_valid(row, 0):
                    continue
                for col in range(self.world.cols):
                    if not self.world.is_valid(row, col):
                        continue
                    cell = self.world.grid[row][col]
                    
                    # Οι Λεωφόροι R1 επιτρέπεται να "σπάσουν" τον εξωτερικό τοίχο για να φτιάξουν εισόδους
                    if cell.cell_type == CellType.WALL:
                        if is_r1 and self.world.is_border(row, col):
                            pass  
                        else:
                            continue
                            
                    cell.cell_type = CellType.ROAD
                    cell.road_id = road_id
                    
                    # Ορισμός της κατεύθυνσης της λωρίδας
                    if road_type == RoadType.R3:
                        cell.lane_direction = r3_dir
                    elif r_offset < width // 2:
                        cell.lane_direction = Direction.EAST
                    else:
                        cell.lane_direction = Direction.WEST
                        
                    cells.append((row, col))
                    self._road_cells.add((row, col))
        else:
            col_start = centerline - width // 2
            for c_offset in range(width):
                col = col_start + c_offset
                if not self.world.is_valid(0, col):
                    continue
                for row in range(self.world.rows):
                    if not self.world.is_valid(row, col):
                        continue
                    cell = self.world.grid[row][col]
                    if cell.cell_type == CellType.WALL:
                        if is_r1 and self.world.is_border(row, col):
                            pass
                        else:
                            continue
                            
                    cell.cell_type = CellType.ROAD
                    cell.road_id = road_id
                    
                    # Ορισμός της κατεύθυνσης της λωρίδας
                    if road_type == RoadType.R3:
                        cell.lane_direction = r3_dir
                    elif c_offset < width // 2:
                        cell.lane_direction = Direction.SOUTH
                    else:
                        cell.lane_direction = Direction.NORTH
                        
                    cells.append((row, col))
                    self._road_cells.add((row, col))

        seg = RoadSegment(
            road_id=road_id, road_type=road_type, cells=cells,
            direction=Direction.EAST if is_horizontal else Direction.SOUTH,
            lanes=lanes
        )
        road.segments.append(seg)
        self.world.register_road(road)

    def _place_sidewalks(self):
        """Τοποθετεί πεζοδρόμια περιμετρικά όλων των δρόμων."""
        for (row, col) in list(self._road_cells):
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if self.world.is_valid(nr, nc):
                    cell = self.world.grid[nr][nc]
                    if cell.cell_type == CellType.EMPTY:
                        cell.cell_type = CellType.SIDEWALK
                        self._sidewalk_cells.add((nr, nc))

    def _place_traffic_lights(self):
        """Τοποθετεί φανάρια πάνω στα πεζοδρόμια που βρίσκονται σε διασταυρώσεις."""
        road_positions = {}
        for (r, c) in self._road_cells:
            cell = self.world.grid[r][c]
            if cell.road_id is not None:
                if (r, c) not in road_positions:
                    road_positions[(r, c)] = set()
                road_positions[(r, c)].add(cell.road_id)

        # Διασταύρωση θεωρείται ένα κελί όπου συναντιούνται παραπάνω από 1 ID δρόμου
        for (r, c), road_ids in road_positions.items():
            if len(road_ids) > 1:
                # Βάζει φανάρια στα διαγώνια πεζοδρόμια γύρω από τη διασταύρωση
                for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    nr, nc = r + dr, c + dc
                    if self.world.is_valid(nr, nc):
                        cell = self.world.grid[nr][nc]
                        if cell.cell_type == CellType.SIDEWALK:
                            cell.cell_type = CellType.TRAFFIC_LIGHT

    def _setup_border_entries(self):
        """Καθορίζει ποια ακριανά κελιά των R1 δρόμων είναι είσοδοι και ποια έξοδοι πόλης."""
        for road in self.world.roads.values():
            if road.road_type != RoadType.R1:
                continue
            for seg in road.segments:
                for (r, c) in seg.cells:
                    if self.world.is_border(r, c):
                        cell = self.world.grid[r][c]
                        cell.cell_type = CellType.ENTRY_EXIT
                        # Ανάλογα με την κατεύθυνση, το βλέπουμε σαν είσοδο (προς τα μέσα) ή έξοδο (προς τα έξω)
                        if cell.lane_direction:
                            if self._is_inward_direction(r, c, cell.lane_direction):
                                cell.is_border_entry = True
                                road.entry_points.append((r, c))
                                self.world.border_entries.append((r, c))
                            else:
                                cell.is_border_exit = True
                                road.exit_points.append((r, c))
                                self.world.border_exits.append((r, c))

    def _is_inward_direction(self, row: int, col: int, direction: Direction) -> bool:
        """Ελέγχει αν μια κατεύθυνση στα σύνορα της πόλης κοιτάει "προς τα μέσα"."""
        if row == 0 and direction == Direction.SOUTH:
            return True
        if row == self.world.rows - 1 and direction == Direction.NORTH:
            return True
        if col == 0 and direction == Direction.EAST:
            return True
        if col == self.world.cols - 1 and direction == Direction.WEST:
            return True
        return False

    def get_road_at(self, row: int, col: int) -> Optional[Road]:
        """Βρίσκει τον δρόμο (αντικείμενο Road) σε μια συγκεκριμένη συντεταγμένη."""
        cell = self.world.get_cell(row, col)
        if cell and cell.road_id is not None:
            return self.world.roads.get(cell.road_id)
        return None

    def get_road_width(self, road_type: RoadType) -> int:
        """Επιστρέφει το πλάτος (σε κελιά) για κάθε τύπο δρόμου."""
        if road_type == RoadType.R1:
            return 4
        elif road_type == RoadType.R2:
            return 2
        return 1
