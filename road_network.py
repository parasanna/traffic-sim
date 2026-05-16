"""
Road Network Generator: Creates a realistic road network on the grid world.
Handles R1 (Avenues), R2 (Streets), and R3 (One-way streets).
"""
import random
from typing import List, Tuple, Optional, Set, Dict
from world import (
    GridWorld, CellType, Direction, RoadType, Road, RoadSegment, Cell
)
from config import SimulationConfig


class RoadNetworkGenerator:
    """
    Generates the road network on the grid.
    
    Layout strategy:
    - R1 Avenues: Major arteries, 4 cells wide (2 lanes per direction),
      always connect to border (entry/exit points)
    - R2 Streets: 2 cells wide (1 lane per direction), internal roads
    - R3 One-way: 1 cell wide, internal, single direction
    - Sidewalks (1 cell) between roads and blocks
    - Traffic lights at intersections
    """

    def __init__(self, world: GridWorld, config: SimulationConfig):
        self.world = world
        self.config = config
        self.rng = random.Random(config.random_seed + 1)
        self._road_cells: Set[Tuple[int, int]] = set()
        self._sidewalk_cells: Set[Tuple[int, int]] = set()

    def generate(self):
        """Generate the complete road network."""
        # Step 1: Place perimeter walls
        self.world.initialize_perimeter_walls()

        # Step 2: Plan road layout
        h_roads, v_roads = self._plan_road_layout()

        # Step 3: Generate R1 avenues (connect to borders)
        r1_h, r1_v = self._select_avenues(h_roads, v_roads)

        # Step 4: Generate R2 streets
        r2_h, r2_v = self._select_streets(h_roads, v_roads, r1_h, r1_v)

        # Step 5: Generate R3 one-way streets from remaining
        r3_h, r3_v = self._select_oneways(h_roads, v_roads, r1_h, r1_v, r2_h, r2_v)

        # Step 6: Place roads on grid (separate h and v to track orientation)
        self._place_roads(r1_h, r1_v, RoadType.R1, lanes=2)
        self._place_roads(r2_h, r2_v, RoadType.R2, lanes=1)
        self._place_roads(r3_h, r3_v, RoadType.R3, lanes=1)

        # Step 7: Place sidewalks
        self._place_sidewalks()

        # Step 8: Place traffic lights at intersections
        self._place_traffic_lights()

        # Step 9: Set R1 border entries/exits
        self._setup_border_entries()

    def _plan_road_layout(self) -> Tuple[List[int], List[int]]:
        """
        Plan a grid of horizontal and vertical road centerlines.
        Returns (horizontal_rows, vertical_cols).
        """
        rows = self.world.rows
        cols = self.world.cols

        # Calculate spacing based on desired block sizes (roughly 8-12 cells)
        target_spacing = 10
        
        # Horizontal roads (rows where roads will be placed)
        h_roads = []
        r = target_spacing
        while r < rows - target_spacing:
            h_roads.append(r)
            r += target_spacing + self.rng.randint(-2, 2)

        # Vertical roads (columns where roads will be placed)
        v_roads = []
        c = target_spacing
        while c < cols - target_spacing:
            v_roads.append(c)
            c += target_spacing + self.rng.randint(-2, 2)

        return h_roads, v_roads

    def _select_avenues(self, h_roads: List[int], v_roads: List[int]
                         ) -> Tuple[List[int], List[int]]:
        """Select road positions for R1 avenues. These must reach borders."""
        target_r1_count = max(2, int(0.15 * (len(h_roads) + len(v_roads))))

        # Pick evenly-spaced roads for avenues
        r1_h = []
        r1_v = []

        if h_roads:
            # Select ~equal spread among horizontal
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
        """Select R2 streets from remaining road positions."""
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
        """Select R3 one-way streets from remaining positions."""
        used_h = set(r1_h + r2_h)
        used_v = set(r1_v + r2_v)
        r3_h = [r for r in h_roads if r not in used_h]
        r3_v = [v for v in v_roads if v not in used_v]
        return r3_h, r3_v

    def _place_roads(self, h_centerlines: List[int], v_centerlines: List[int],
                      road_type: RoadType, lanes: int):
        """
        Place road cells on the grid.
        For R1: 4 cells wide (2 lanes each direction)
        For R2: 2 cells wide (1 lane each direction)  
        For R3: 1 cell wide (1 lane, 1 direction)
        """
        if road_type == RoadType.R1:
            width = 4
        elif road_type == RoadType.R2:
            width = 2
        else:
            width = 1

        # Place horizontal roads
        for centerline in h_centerlines:
            self._place_single_road(centerline, True, road_type, width, lanes)

        # Place vertical roads
        for centerline in v_centerlines:
            self._place_single_road(centerline, False, road_type, width, lanes)

    def _place_single_road(self, centerline: int, is_horizontal: bool,
                            road_type: RoadType, width: int, lanes: int):
        """Place a single road on the grid."""
        road_id = self.world.next_road_id()
        road = Road(road_id=road_id, road_type=road_type)
        cells = []
        is_r1 = road_type == RoadType.R1

        # For R3, pick a consistent direction for the whole road
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
                    # R1 roads can overwrite WALL at borders for entry/exit
                    if cell.cell_type == CellType.WALL:
                        if is_r1 and self.world.is_border(row, col):
                            pass  # Allow overwrite
                        else:
                            continue
                    cell.cell_type = CellType.ROAD
                    cell.road_id = road_id
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
        """Place sidewalk cells adjacent to roads."""
        for (row, col) in list(self._road_cells):
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = row + dr, col + dc
                if self.world.is_valid(nr, nc):
                    cell = self.world.grid[nr][nc]
                    if cell.cell_type == CellType.EMPTY:
                        cell.cell_type = CellType.SIDEWALK
                        self._sidewalk_cells.add((nr, nc))

    def _place_traffic_lights(self):
        """Place traffic lights at road intersections (on sidewalk cells)."""
        # Find intersection points (where roads cross)
        road_positions = {}
        for (r, c) in self._road_cells:
            cell = self.world.grid[r][c]
            if cell.road_id is not None:
                if (r, c) not in road_positions:
                    road_positions[(r, c)] = set()
                road_positions[(r, c)].add(cell.road_id)

        # Intersections are where multiple road IDs meet
        for (r, c), road_ids in road_positions.items():
            if len(road_ids) > 1:
                # Place traffic lights on adjacent sidewalks
                for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                    nr, nc = r + dr, c + dc
                    if self.world.is_valid(nr, nc):
                        cell = self.world.grid[nr][nc]
                        if cell.cell_type == CellType.SIDEWALK:
                            cell.cell_type = CellType.TRAFFIC_LIGHT

    def _setup_border_entries(self):
        """Set up entry/exit points for R1 roads at borders."""
        for road in self.world.roads.values():
            if road.road_type != RoadType.R1:
                continue
            for seg in road.segments:
                for (r, c) in seg.cells:
                    if self.world.is_border(r, c):
                        cell = self.world.grid[r][c]
                        cell.cell_type = CellType.ENTRY_EXIT
                        # Determine if entry or exit based on direction
                        if cell.lane_direction:
                            # If direction points inward, it's an entry
                            if self._is_inward_direction(r, c, cell.lane_direction):
                                cell.is_border_entry = True
                                road.entry_points.append((r, c))
                                self.world.border_entries.append((r, c))
                            else:
                                cell.is_border_exit = True
                                road.exit_points.append((r, c))
                                self.world.border_exits.append((r, c))

    def _is_inward_direction(self, row: int, col: int, direction: Direction) -> bool:
        """Check if a direction at a border cell points inward."""
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
        """Get the road at a specific cell position."""
        cell = self.world.get_cell(row, col)
        if cell and cell.road_id is not None:
            return self.world.roads.get(cell.road_id)
        return None

    def get_road_width(self, road_type: RoadType) -> int:
        """Get the total width of a road type in cells."""
        if road_type == RoadType.R1:
            return 4
        elif road_type == RoadType.R2:
            return 2
        return 1
