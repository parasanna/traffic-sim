"""
Μονάδα Κόσμου (World module): Αναπαράσταση του 'Grid World' (Πλέγματος) και διαχείριση κελιών.
Υλοποιεί το ορθογώνιο πλέγμα με διάφορους τύπους κελιών (δρόμοι, κτίρια, πεζοδρόμια κλπ).
"""
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Set
from config import SimulationConfig


class CellType(Enum):
    """Τύποι κελιών στον κόσμο του πλέγματος."""
    EMPTY = auto()          # Ελεύθερος χώρος
    ROAD = auto()           # Τμήμα δρόμου
    SIDEWALK = auto()       # Πεζοδρόμιο (μεταξύ κτιρίων και δρόμων)
    BLOCK = auto()          # Μέρος ενός οικοδομικού τετραγώνου (κτίριο)
    WALL = auto()           # Τοίχος (περιμετρικά του χάρτη)
    ENTRY_EXIT = auto()     # Σημείο εισόδου/εξόδου στους κεντρικούς δρόμους (R1) στα όρια του χάρτη
    TRAFFIC_LIGHT = auto()  # Φανάρι σε διασταυρώσεις
    BLOCK_ENTRY = auto()    # Πόρτα (σημείο εισόδου/εξόδου) για ένα οικοδομικό τετράγωνο


class Direction(Enum):
    """Βασικές κατευθύνσεις (Ορίζοντα) για την κίνηση και τον προσανατολισμό των δρόμων."""
    NORTH = (0, -1)   # Βορράς / Πάνω (μείωση γραμμής)
    SOUTH = (0, 1)    # Νότος / Κάτω (αύξηση γραμμής)
    EAST = (1, 0)     # Ανατολή / Δεξιά (αύξηση στήλης)
    WEST = (-1, 0)    # Δύση / Αριστερά (μείωση στήλης)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> 'Direction':
        """Επιστρέφει την αντίθετη κατεύθυνση."""
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return opposites[self]


class RoadType(Enum):
    """Κατηγορίες Οδικού Δικτύου."""
    R1 = "avenue"       # Λεωφόρος: 2 λωρίδες ανά κατεύθυνση
    R2 = "street"       # Οδός: 1 λωρίδα ανά κατεύθυνση
    R3 = "one_way"      # Μονόδρομος: 1 λωρίδα, μία κατεύθυνση


class BlockCategory(Enum):
    """Κατηγορίες Οικοδομικών Τετραγώνων."""
    RESIDENTIAL = 1     # Κατοικίες
    OFFICE = 2          # Γραφεία
    MARKET = 3          # Αγορές / Καταστήματα
    LEISURE = 4         # Διασκέδαση
    OTHER = 5           # Λοιπά


@dataclass
class RoadSegment:
    """Ένα τμήμα ενός δρόμου που καταλαμβάνει συγκεκριμένα κελιά του πλέγματος."""
    road_id: int
    road_type: RoadType
    cells: List[Tuple[int, int]]   # Λίστα από θέσεις (row, col) που καταλαμβάνει το τμήμα
    direction: Direction           # Κύρια κατεύθυνση κυκλοφορίας
    lanes: int                     # Αριθμός λωρίδων ανά κατεύθυνση
    is_border_entry: bool = False  # Αν είναι σημείο εισόδου από τα όρια του χάρτη
    is_border_exit: bool = False   # Αν είναι σημείο εξόδου προς τα όρια του χάρτη


@dataclass
class Road:
    """Ένας ολόκληρος δρόμος που αποτελείται από πολλά τμήματα (segments)."""
    road_id: int
    road_type: RoadType
    segments: List[RoadSegment] = field(default_factory=list)
    entry_points: List[Tuple[int, int]] = field(default_factory=list)  # Μόνο για R1
    exit_points: List[Tuple[int, int]] = field(default_factory=list)   # Μόνο για R1

    @property
    def total_area(self) -> int:
        """Το συνολικό εμβαδόν (σε αριθμό κελιών) που καταλαμβάνει ο δρόμος."""
        all_cells = set()
        for seg in self.segments:
            all_cells.update(seg.cells)
        return len(all_cells)


@dataclass
class BuildingBlock:
    """Ένα Οικοδομικό Τετράγωνο (Building block / City block)."""
    block_id: int
    category: BlockCategory
    cells: List[Tuple[int, int]]        # Τα κελιά που αποτελούν το τετράγωνο
    entry_point: Tuple[int, int] = (0, 0)  # Η "πόρτα" του τετραγώνου (πάνω στο πεζοδρόμιο)
    facing_road_cell: Tuple[int, int] = (0, 0)  # Το κελί του δρόμου στο οποίο "βλέπει" η πόρτα

    # Παρακολούθηση Πόρων (Resources)
    food_level: float = 0.0             # Τρέχον επίπεδο διαθέσιμου φαγητού
    food_capacity: float = 0.0          # Μέγιστη χωρητικότητα αποθήκης φαγητού
    pollution_level: float = 0.0        # Τρέχον επίπεδο συσσωρευμένης ρύπανσης/σκουπιδιών
    pollution_capacity: float = 0.0     # Μέγιστη χωρητικότητα σκουπιδιών

    @property
    def area(self) -> int:
        """Εμβαδόν του τετραγώνου σε κελιά."""
        return len(self.cells)

    def update_resources(self, fcr: float, pgr: float):
        """Ενημέρωση (ανά tick) της κατανάλωσης φαγητού και παραγωγής σκουπιδιών."""
        # Κατανάλωση φαγητού
        self.food_level = max(0.0, self.food_level - fcr)
        # Παραγωγή ρύπανσης/σκουπιδιών
        self.pollution_level = min(self.pollution_capacity, self.pollution_level + pgr)

    def deliver_food(self, amount: float) -> float:
        """Παράδοση φαγητού σε αυτό το τετράγωνο. Επιστρέφει την ποσότητα που παραδόθηκε πραγματικά."""
        space = self.food_capacity - self.food_level
        delivered = min(amount, space)
        self.food_level += delivered
        return delivered

    def collect_pollution(self, capacity: float) -> float:
        """Συλλογή σκουπιδιών από αυτό το τετράγωνο. Επιστρέφει την ποσότητα που συλλέχθηκε."""
        collected = min(self.pollution_level, capacity)
        self.pollution_level -= collected
        return collected


@dataclass
class Cell:
    """Ένα μεμονωμένο κελί μέσα στον κόσμο του πλέγματος."""
    row: int
    col: int
    cell_type: CellType = CellType.EMPTY
    road_segment: Optional[RoadSegment] = None
    block: Optional[BuildingBlock] = None
    vehicle_id: Optional[int] = None    # Το ID του οχήματος που βρίσκεται πάνω στο κελί (αν υπάρχει)
    is_occupied: bool = False           # Αν το κελί είναι πιασμένο από όχημα
    lane_direction: Optional[Direction] = None  # Η κατεύθυνση κυκλοφορίας της λωρίδας
    road_id: Optional[int] = None
    # Σημεία εισόδου/εξόδου στα σύνορα του χάρτη για δρόμους R1
    is_border_entry: bool = False
    is_border_exit: bool = False

    @property
    def is_passable(self) -> bool:
        """Μπορεί ένα όχημα να περάσει μέσα από αυτό το κελί;"""
        # Περνάει μόνο αν είναι δρόμος ή πόρτα ΚΑΙ δεν είναι ήδη πιασμένο
        return (self.cell_type in (CellType.ROAD, CellType.ENTRY_EXIT, CellType.BLOCK_ENTRY)
                and not self.is_occupied)

    @property
    def position(self) -> Tuple[int, int]:
        return (self.row, self.col)


class GridWorld:
    """
    Η κεντρική κλάση του Grid World. 
    Περιέχει όλα τα κελιά, τους δρόμους, και τα οικοδομικά τετράγωνα.
    Υλοποιεί ένα ορθογώνιο πλέγμα διαστάσεων GR (γραμμές) x GC (στήλες).
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rows = config.world.grid_rows
        self.cols = config.world.grid_cols
        self.rng = random.Random(config.random_seed)

        # Αρχικοποίηση του πίνακα (πλέγματος) με κενά κελιά
        self.grid: List[List[Cell]] = [
            [Cell(row=r, col=c) for c in range(self.cols)]
            for r in range(self.rows)
        ]

        # Μητρώα (Registries) για γρήγορη εύρεση
        self.roads: Dict[int, Road] = {}
        self.blocks: Dict[int, BuildingBlock] = {}
        self.border_entries: List[Tuple[int, int]] = []
        self.border_exits: List[Tuple[int, int]] = []

        # Μετρητές για δημιουργία μοναδικών ID
        self._next_road_id = 0
        self._next_block_id = 0

    def get_cell(self, row: int, col: int) -> Optional[Cell]:
        """Φέρνει το κελί στη συγκεκριμένη θέση. Επιστρέφει None αν είναι εκτός ορίων."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None

    def is_valid(self, row: int, col: int) -> bool:
        """Ελέγχει αν οι συντεταγμένες είναι μέσα στα όρια του χάρτη."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_border(self, row: int, col: int) -> bool:
        """Ελέγχει αν ένα κελί βρίσκεται στα ακριανά σύνορα (περίμετρος) του χάρτη."""
        return row == 0 or row == self.rows - 1 or col == 0 or col == self.cols - 1

    def get_neighbors(self, row: int, col: int, include_diagonal: bool = False) -> List[Cell]:
        """Επιστρέφει τα γειτονικά κελιά (Σταυρός: Πάνω, Κάτω, Αριστερά, Δεξιά)."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            cell = self.get_cell(nr, nc)
            if cell:
                neighbors.append(cell)
        # Προαιρετικά συμπεριλαμβάνει και τα διαγώνια κελιά
        if include_diagonal:
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = row + dr, col + dc
                cell = self.get_cell(nr, nc)
                if cell:
                    neighbors.append(cell)
        return neighbors

    def get_moore_neighborhood(self, row: int, col: int) -> List[Cell]:
        """Επιστρέφει τη γειτονιά Moore (Και τα 8 γειτονικά κελιά, μαζί με τα διαγώνια)."""
        return self.get_neighbors(row, col, include_diagonal=True)

    def is_intersection(self, r: int, c: int) -> bool:
        """Ελέγχει αν ένα κελί είναι διασταύρωση (έχει δρόμους και στους δύο άξονες)."""
        cell = self.get_cell(r, c)
        if not cell or cell.cell_type != CellType.ROAD:
            return False
            
        has_v_road = False
        has_h_road = False
        
        # Έλεγχος Κάθετου άξονα (Πάνω/Κάτω)
        up = self.get_cell(r - 1, c)
        if up and up.cell_type == CellType.ROAD: has_v_road = True
        down = self.get_cell(r + 1, c)
        if down and down.cell_type == CellType.ROAD: has_v_road = True
        
        # Έλεγχος Οριζόντιου άξονα (Αριστερά/Δεξιά)
        left = self.get_cell(r, c - 1)
        if left and left.cell_type == CellType.ROAD: has_h_road = True
        right = self.get_cell(r, c + 1)
        if right and right.cell_type == CellType.ROAD: has_h_road = True
        
        return has_v_road and has_h_road

    def set_cell_type(self, row: int, col: int, cell_type: CellType):
        """Αλλάζει τον τύπο ενός κελιού."""
        if self.is_valid(row, col):
            self.grid[row][col].cell_type = cell_type

    def place_vehicle(self, row: int, col: int, vehicle_id: int) -> bool:
        """Τοποθετεί ένα όχημα σε ένα κελί. Επιστρέφει True αν πέτυχε."""
        cell = self.get_cell(row, col)
        if cell and cell.is_passable:
            cell.vehicle_id = vehicle_id
            cell.is_occupied = True
            return True
        return False

    def remove_vehicle(self, row: int, col: int):
        """Αφαιρεί ένα όχημα από ένα κελί."""
        cell = self.get_cell(row, col)
        if cell:
            cell.vehicle_id = None
            cell.is_occupied = False

    def next_road_id(self) -> int:
        """Παράγει το επόμενο μοναδικό ID δρόμου."""
        rid = self._next_road_id
        self._next_road_id += 1
        return rid

    def next_block_id(self) -> int:
        """Παράγει το επόμενο μοναδικό ID οικοδομικού τετραγώνου."""
        bid = self._next_block_id
        self._next_block_id += 1
        return bid

    def register_road(self, road: Road):
        """Καταχωρεί (αποθηκεύει) έναν δρόμο μέσα στον κόσμο."""
        self.roads[road.road_id] = road
        for ep in road.entry_points:
            self.border_entries.append(ep)
        for ep in road.exit_points:
            self.border_exits.append(ep)

    def register_block(self, block: BuildingBlock):
        """Καταχωρεί ένα οικοδομικό τετράγωνο μέσα στον κόσμο."""
        self.blocks[block.block_id] = block

    def get_blocks_by_category(self, category: BlockCategory) -> List[BuildingBlock]:
        """Φέρνει όλα τα τετράγωνα μιας συγκεκριμένης κατηγορίας (π.χ. μόνο τα Σπίτια)."""
        return [b for b in self.blocks.values() if b.category == category]

    def get_random_block(self, category: Optional[BlockCategory] = None) -> Optional[BuildingBlock]:
        """Επιλέγει ένα τυχαίο τετράγωνο (προαιρετικά από συγκεκριμένη κατηγορία)."""
        if category:
            candidates = self.get_blocks_by_category(category)
        else:
            candidates = list(self.blocks.values())
        if candidates:
            return self.rng.choice(candidates)
        return None

    def initialize_perimeter_walls(self):
        """Στήνει τοίχους (τείχη) στην περίμετρο του χάρτη για να μην βγαίνουν τα οχήματα εκτός."""
        for c in range(self.cols):
            self.grid[0][c].cell_type = CellType.WALL
            self.grid[self.rows - 1][c].cell_type = CellType.WALL
        for r in range(self.rows):
            self.grid[r][0].cell_type = CellType.WALL
            self.grid[r][self.cols - 1].cell_type = CellType.WALL

    def update_block_resources(self):
        """Ενημερώνει τους πόρους (φαγητό/σκουπίδια) όλων των τετραγώνων. Καλείται σε κάθε tick."""
        fcr = self.config.blocks.food_consumption_rate
        pgr = self.config.blocks.pollution_generation_rate
        for block in self.blocks.values():
            block.update_resources(fcr, pgr)

    def __repr__(self) -> str:
        return (f"GridWorld({self.rows}x{self.cols}, "
                f"roads={len(self.roads)}, blocks={len(self.blocks)})")
