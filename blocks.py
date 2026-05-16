"""
Building Blocks Generator: Creates and places building blocks on the grid.
Handles block categories, entry points, and resource initialization.
"""
import random
from typing import List, Tuple, Optional, Set, Dict
from world import (
    GridWorld, CellType, BuildingBlock, BlockCategory, Direction
)
from config import SimulationConfig


class BlockGenerator:
    """
    Generates building blocks to fill the spaces between roads.
    Each block has a category, entry point, and resource capacities.
    """

    def __init__(self, world: GridWorld, config: SimulationConfig):
        self.world = world
        self.config = config
        self.rng = random.Random(config.random_seed + 2)

    def generate(self):
        """Generate all building blocks in the grid."""
        # Step 1: Find all connected regions of EMPTY cells (spaces between roads)
        empty_regions = self._find_empty_regions()

        # Step 2: Filter out tiny regions (not big enough for blocks)
        min_block_size = 4  # Minimum cells for a block
        valid_regions = [r for r in empty_regions if len(r) >= min_block_size]

        # Step 3: Assign categories based on distribution
        categories = self._assign_categories(len(valid_regions))

        # Step 4: Create blocks
        for i, (region, category) in enumerate(zip(valid_regions, categories)):
            self._create_block(region, category)

    def _find_empty_regions(self) -> List[Set[Tuple[int, int]]]:
        """Find connected regions of EMPTY cells using flood fill."""
        visited = set()
        regions = []

        for r in range(1, self.world.rows - 1):  # Skip border walls
            for c in range(1, self.world.cols - 1):
                if (r, c) in visited:
                    continue
                cell = self.world.grid[r][c]
                if cell.cell_type != CellType.EMPTY:
                    visited.add((r, c))
                    continue

                # Flood fill to find connected region
                region = set()
                stack = [(r, c)]
                while stack:
                    cr, cc = stack.pop()
                    if (cr, cc) in visited:
                        continue
                    if not self.world.is_valid(cr, cc):
                        continue
                    cell = self.world.grid[cr][cc]
                    if cell.cell_type != CellType.EMPTY:
                        visited.add((cr, cc))
                        continue

                    visited.add((cr, cc))
                    region.add((cr, cc))

                    # Check 4-connected neighbors
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if (nr, nc) not in visited and self.world.is_valid(nr, nc):
                            stack.append((nr, nc))

                if region:
                    regions.append(region)

        return regions

    def _assign_categories(self, count: int) -> List[BlockCategory]:
        """Assign block categories based on configured distribution."""
        dist = self.config.blocks.block_distribution
        categories = []

        # Calculate counts for each category
        cat_counts = {
            BlockCategory.RESIDENTIAL: int(count * dist["residential"]),
            BlockCategory.OFFICE: int(count * dist["office"]),
            BlockCategory.MARKET: int(count * dist["market"]),
            BlockCategory.LEISURE: int(count * dist["leisure"]),
            BlockCategory.OTHER: int(count * dist["other"]),
        }

        # Fill remainder with random categories
        total = sum(cat_counts.values())
        remaining = count - total
        all_cats = list(BlockCategory)

        for cat, cnt in cat_counts.items():
            categories.extend([cat] * cnt)

        for _ in range(remaining):
            categories.append(self.rng.choice(all_cats))

        self.rng.shuffle(categories)
        return categories[:count]

    def _create_block(self, region: Set[Tuple[int, int]], category: BlockCategory):
        """Create a building block from a region of cells."""
        block_id = self.world.next_block_id()
        cells_list = list(region)

        # Find entry point: a cell on the perimeter that faces a road/sidewalk
        entry_point, facing_road = self._find_entry_point(region)

        # Calculate resource capacities
        area = len(cells_list)
        food_cap = area * self.config.blocks.food_capacity_factor
        poll_cap = area * self.config.blocks.pollution_capacity_factor

        block = BuildingBlock(
            block_id=block_id,
            category=category,
            cells=cells_list,
            entry_point=entry_point,
            facing_road_cell=facing_road,
            food_level=food_cap * 0.5,  # Start half-full
            food_capacity=food_cap,
            pollution_level=0.0,
            pollution_capacity=poll_cap,
        )

        # Mark cells on grid
        for (r, c) in cells_list:
            cell = self.world.grid[r][c]
            cell.cell_type = CellType.BLOCK
            cell.block = block

        # Mark entry point
        er, ec = entry_point
        if self.world.is_valid(er, ec):
            entry_cell = self.world.grid[er][ec]
            if entry_cell.cell_type in (CellType.SIDEWALK, CellType.EMPTY):
                entry_cell.cell_type = CellType.BLOCK_ENTRY
                entry_cell.block = block

        self.world.register_block(block)

    def _find_entry_point(self, region: Set[Tuple[int, int]]
                           ) -> Tuple[Tuple[int, int], Tuple[int, int]]:
        """
        Find the best entry point for a block.
        The entry point should be on the block's perimeter facing a road.
        Returns (entry_point_on_sidewalk, facing_road_cell).
        """
        perimeter_cells = self._get_perimeter(region)
        best_entry = None
        best_road = None

        for (r, c) in perimeter_cells:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if not self.world.is_valid(nr, nc):
                    continue
                # Check for sidewalk (entry point on sidewalk)
                adj_cell = self.world.grid[nr][nc]
                if adj_cell.cell_type == CellType.SIDEWALK:
                    # Check if there's a road next to the sidewalk
                    for dr2, dc2 in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        rr, rc = nr + dr2, nc + dc2
                        if not self.world.is_valid(rr, rc):
                            continue
                        road_cell = self.world.grid[rr][rc]
                        if road_cell.cell_type == CellType.ROAD:
                            return (nr, nc), (rr, rc)

        # Fallback: use first perimeter cell
        if perimeter_cells:
            first = list(perimeter_cells)[0]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = first[0] + dr, first[1] + dc
                if self.world.is_valid(nr, nc):
                    return (nr, nc), (nr, nc)

        # Ultimate fallback
        first = list(region)[0]
        return first, first

    def _get_perimeter(self, region: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """Get perimeter cells of a region (cells with at least one non-region neighbor)."""
        perimeter = set()
        for (r, c) in region:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) not in region:
                    perimeter.add((r, c))
                    break
        return perimeter
