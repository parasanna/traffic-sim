"""
World module: Grid World representation and cell management.
Implements the orthogonal grid with various cell types.
"""
import random
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Optional, Tuple, List, Dict, Set
from config import SimulationConfig


class CellType(Enum):
    """Types of cells in the grid world."""
    EMPTY = auto()          # Free space
    ROAD = auto()           # Road segment
    SIDEWALK = auto()       # Sidewalk (between blocks and roads)
    BLOCK = auto()          # Part of a building block
    WALL = auto()           # Perimeter wall
    ENTRY_EXIT = auto()     # Entry/exit point on R1 at border
    TRAFFIC_LIGHT = auto()  # Traffic light at intersections
    BLOCK_ENTRY = auto()    # Entry/exit point for a building block


class Direction(Enum):
    """Cardinal directions for movement and road orientation."""
    NORTH = (0, -1)   # Up (decreasing row)
    SOUTH = (0, 1)    # Down (increasing row)
    EAST = (1, 0)     # Right (increasing col)
    WEST = (-1, 0)    # Left (decreasing col)

    @property
    def dx(self) -> int:
        return self.value[0]

    @property
    def dy(self) -> int:
        return self.value[1]

    @property
    def opposite(self) -> 'Direction':
        opposites = {
            Direction.NORTH: Direction.SOUTH,
            Direction.SOUTH: Direction.NORTH,
            Direction.EAST: Direction.WEST,
            Direction.WEST: Direction.EAST,
        }
        return opposites[self]


class RoadType(Enum):
    """Road classification types."""
    R1 = "avenue"       # 2 lanes per direction
    R2 = "street"       # 1 lane per direction
    R3 = "one_way"      # 1 lane, one direction


class BlockCategory(Enum):
    """Building block categories."""
    RESIDENTIAL = 1
    OFFICE = 2
    MARKET = 3
    LEISURE = 4
    OTHER = 5


@dataclass
class RoadSegment:
    """A segment of a road occupying grid cells."""
    road_id: int
    road_type: RoadType
    cells: List[Tuple[int, int]]  # List of (row, col) grid positions
    direction: Direction           # Primary traffic direction
    lanes: int                     # Number of lanes per direction
    is_border_entry: bool = False  # If it's an entry/exit point at border
    is_border_exit: bool = False


@dataclass
class Road:
    """A complete road composed of segments."""
    road_id: int
    road_type: RoadType
    segments: List[RoadSegment] = field(default_factory=list)
    entry_points: List[Tuple[int, int]] = field(default_factory=list)  # For R1
    exit_points: List[Tuple[int, int]] = field(default_factory=list)   # For R1

    @property
    def total_area(self) -> int:
        """Total number of cells this road occupies."""
        all_cells = set()
        for seg in self.segments:
            all_cells.update(seg.cells)
        return len(all_cells)


@dataclass
class BuildingBlock:
    """A building block (city block / oikodomiko tetragono)."""
    block_id: int
    category: BlockCategory
    cells: List[Tuple[int, int]]        # Grid cells of this block
    entry_point: Tuple[int, int] = (0, 0)  # Entry/exit point (on sidewalk)
    facing_road_cell: Tuple[int, int] = (0, 0)  # Road cell it faces

    # Resource tracking
    food_level: float = 0.0
    food_capacity: float = 0.0
    pollution_level: float = 0.0
    pollution_capacity: float = 0.0

    @property
    def area(self) -> int:
        return len(self.cells)

    def update_resources(self, fcr: float, pgr: float):
        """Update food consumption and pollution generation per tick."""
        # Consume food
        self.food_level = max(0.0, self.food_level - fcr)
        # Generate pollution
        self.pollution_level = min(self.pollution_capacity, self.pollution_level + pgr)

    def deliver_food(self, amount: float) -> float:
        """Deliver food to this block. Returns actual amount delivered."""
        space = self.food_capacity - self.food_level
        delivered = min(amount, space)
        self.food_level += delivered
        return delivered

    def collect_pollution(self, capacity: float) -> float:
        """Collect pollution from this block. Returns amount collected."""
        collected = min(self.pollution_level, capacity)
        self.pollution_level -= collected
        return collected


@dataclass
class Cell:
    """A single cell in the grid world."""
    row: int
    col: int
    cell_type: CellType = CellType.EMPTY
    road_segment: Optional[RoadSegment] = None
    block: Optional[BuildingBlock] = None
    vehicle_id: Optional[int] = None    # ID of vehicle occupying this cell
    is_occupied: bool = False
    lane_direction: Optional[Direction] = None  # Direction of traffic flow
    road_id: Optional[int] = None
    # For R1 border entry/exit
    is_border_entry: bool = False
    is_border_exit: bool = False

    @property
    def is_passable(self) -> bool:
        """Can a vehicle move through this cell?"""
        return (self.cell_type in (CellType.ROAD, CellType.ENTRY_EXIT, CellType.BLOCK_ENTRY)
                and not self.is_occupied)

    @property
    def position(self) -> Tuple[int, int]:
        return (self.row, self.col)


class GridWorld:
    """
    The main grid world containing all cells, roads, and building blocks.
    Implements a GR x GC orthogonal grid.
    """

    def __init__(self, config: SimulationConfig):
        self.config = config
        self.rows = config.world.grid_rows
        self.cols = config.world.grid_cols
        self.rng = random.Random(config.random_seed)

        # Initialize grid
        self.grid: List[List[Cell]] = [
            [Cell(row=r, col=c) for c in range(self.cols)]
            for r in range(self.rows)
        ]

        # Registries
        self.roads: Dict[int, Road] = {}
        self.blocks: Dict[int, BuildingBlock] = {}
        self.border_entries: List[Tuple[int, int]] = []
        self.border_exits: List[Tuple[int, int]] = []

        # Counters for ID generation
        self._next_road_id = 0
        self._next_block_id = 0

    def get_cell(self, row: int, col: int) -> Optional[Cell]:
        """Get cell at position, return None if out of bounds."""
        if 0 <= row < self.rows and 0 <= col < self.cols:
            return self.grid[row][col]
        return None

    def is_valid(self, row: int, col: int) -> bool:
        """Check if coordinates are within grid bounds."""
        return 0 <= row < self.rows and 0 <= col < self.cols

    def is_border(self, row: int, col: int) -> bool:
        """Check if a cell is on the border of the grid."""
        return row == 0 or row == self.rows - 1 or col == 0 or col == self.cols - 1

    def get_neighbors(self, row: int, col: int, include_diagonal: bool = False) -> List[Cell]:
        """Get neighboring cells (4-connected or 8-connected)."""
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = row + dr, col + dc
            cell = self.get_cell(nr, nc)
            if cell:
                neighbors.append(cell)
        if include_diagonal:
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = row + dr, col + dc
                cell = self.get_cell(nr, nc)
                if cell:
                    neighbors.append(cell)
        return neighbors

    def get_moore_neighborhood(self, row: int, col: int) -> List[Cell]:
        """Get Moore neighborhood (8-connected including diagonals)."""
        return self.get_neighbors(row, col, include_diagonal=True)

    def set_cell_type(self, row: int, col: int, cell_type: CellType):
        """Set the type of a cell."""
        if self.is_valid(row, col):
            self.grid[row][col].cell_type = cell_type

    def place_vehicle(self, row: int, col: int, vehicle_id: int) -> bool:
        """Place a vehicle on a cell. Returns True if successful."""
        cell = self.get_cell(row, col)
        if cell and cell.is_passable:
            cell.vehicle_id = vehicle_id
            cell.is_occupied = True
            return True
        return False

    def remove_vehicle(self, row: int, col: int):
        """Remove a vehicle from a cell."""
        cell = self.get_cell(row, col)
        if cell:
            cell.vehicle_id = None
            cell.is_occupied = False

    def next_road_id(self) -> int:
        """Generate next unique road ID."""
        rid = self._next_road_id
        self._next_road_id += 1
        return rid

    def next_block_id(self) -> int:
        """Generate next unique block ID."""
        bid = self._next_block_id
        self._next_block_id += 1
        return bid

    def register_road(self, road: Road):
        """Register a road in the world."""
        self.roads[road.road_id] = road
        for ep in road.entry_points:
            self.border_entries.append(ep)
        for ep in road.exit_points:
            self.border_exits.append(ep)

    def register_block(self, block: BuildingBlock):
        """Register a building block in the world."""
        self.blocks[block.block_id] = block

    def get_blocks_by_category(self, category: BlockCategory) -> List[BuildingBlock]:
        """Get all blocks of a specific category."""
        return [b for b in self.blocks.values() if b.category == category]

    def get_random_block(self, category: Optional[BlockCategory] = None) -> Optional[BuildingBlock]:
        """Get a random building block, optionally filtered by category."""
        if category:
            candidates = self.get_blocks_by_category(category)
        else:
            candidates = list(self.blocks.values())
        if candidates:
            return self.rng.choice(candidates)
        return None

    def initialize_perimeter_walls(self):
        """Set up wall cells around the perimeter."""
        for c in range(self.cols):
            self.grid[0][c].cell_type = CellType.WALL
            self.grid[self.rows - 1][c].cell_type = CellType.WALL
        for r in range(self.rows):
            self.grid[r][0].cell_type = CellType.WALL
            self.grid[r][self.cols - 1].cell_type = CellType.WALL

    def update_block_resources(self):
        """Update all block resources (called each tick)."""
        fcr = self.config.blocks.food_consumption_rate
        pgr = self.config.blocks.pollution_generation_rate
        for block in self.blocks.values():
            block.update_resources(fcr, pgr)

    def __repr__(self) -> str:
        return (f"GridWorld({self.rows}x{self.cols}, "
                f"roads={len(self.roads)}, blocks={len(self.blocks)})")
