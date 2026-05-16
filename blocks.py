"""
Γεννήτρια Οικοδομικών Τετραγώνων (Building Blocks Generator): Δημιουργεί και τοποθετεί
τα τετράγωνα-κτίρια πάνω στο πλέγμα του χάρτη.
Χειρίζεται τις κατηγορίες τους, τις πόρτες εισόδου και την αρχικοποίηση των πόρων.
"""
import random
from typing import List, Tuple, Optional, Set, Dict
from world import (
    GridWorld, CellType, BuildingBlock, BlockCategory, Direction
)
from config import SimulationConfig


class BlockGenerator:
    """
    Δημιουργεί οικοδομικά τετράγωνα για να γεμίσει τους κενούς χώρους ανάμεσα στους δρόμους.
    Κάθε τετράγωνο ανήκει σε μια κατηγορία, έχει πόρτα, και χωρητικότητα για πόρους.
    """

    def __init__(self, world: GridWorld, config: SimulationConfig):
        self.world = world
        self.config = config
        self.rng = random.Random(config.random_seed + 2)

    def generate(self):
        """Δημιουργεί όλα τα οικοδομικά τετράγωνα στο πλέγμα."""
        # Βήμα 1: Εντοπισμός όλων των περιοχών με συνεχόμενα άδεια (EMPTY) κελιά (τα κενά μεταξύ των δρόμων)
        empty_regions = self._find_empty_regions()

        # Βήμα 2: Φιλτράρισμα μικρών περιοχών (αγνοούμε τις πολύ μικρές τρύπες)
        min_block_size = 4  # Ελάχιστος αριθμός κελιών για να φτιαχτεί κτίριο
        valid_regions = [r for r in empty_regions if len(r) >= min_block_size]

        # Βήμα 3: Εκχώρηση κατηγοριών (Σπίτια, Γραφεία κλπ) βάσει των ποσοστών που ορίσαμε
        categories = self._assign_categories(len(valid_regions))

        # Βήμα 4: Δημιουργία των τετραγώνων
        for i, (region, category) in enumerate(zip(valid_regions, categories)):
            self._create_block(region, category)

    def _find_empty_regions(self) -> List[Set[Tuple[int, int]]]:
        """Εντοπίζει περιοχές από συνεχόμενα άδεια κελιά, χρησιμοποιώντας τον αλγόριθμο 'Flood Fill'."""
        visited = set()
        regions = []

        for r in range(1, self.world.rows - 1):  # Προσπερνάμε τους εξωτερικούς τοίχους
            for c in range(1, self.world.cols - 1):
                if (r, c) in visited:
                    continue
                cell = self.world.grid[r][c]
                if cell.cell_type != CellType.EMPTY:
                    visited.add((r, c))
                    continue

                # Αλγόριθμος Flood Fill για να βρούμε όλα τα διπλανά άδεια κελιά (σαν να ρίχνουμε "κουβά με χρώμα")
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

                    # Έλεγχος των 4 γειτόνων
                    for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        nr, nc = cr + dr, cc + dc
                        if (nr, nc) not in visited and self.world.is_valid(nr, nc):
                            stack.append((nr, nc))

                if region:
                    regions.append(region)

        return regions

    def _assign_categories(self, count: int) -> List[BlockCategory]:
        """Εκχωρεί κατηγορίες στα τετράγωνα με βάση την κατανομή που έχουμε στις ρυθμίσεις."""
        dist = self.config.blocks.block_distribution
        categories = []

        # Υπολογισμός του πλήθους για κάθε κατηγορία (π.χ. 25% Κατοικίες = 0.25 * πλήθος)
        cat_counts = {
            BlockCategory.RESIDENTIAL: int(count * dist["residential"]),
            BlockCategory.OFFICE: int(count * dist["office"]),
            BlockCategory.MARKET: int(count * dist["market"]),
            BlockCategory.LEISURE: int(count * dist["leisure"]),
            BlockCategory.OTHER: int(count * dist["other"]),
        }

        # Συμπλήρωση των υπολοίπων (λόγω στρογγυλοποίησης) με τυχαίες κατηγορίες
        total = sum(cat_counts.values())
        remaining = count - total
        all_cats = list(BlockCategory)

        for cat, cnt in cat_counts.items():
            categories.extend([cat] * cnt)

        for _ in range(remaining):
            categories.append(self.rng.choice(all_cats))

        self.rng.shuffle(categories) # Ανακάτεμα για να μοιραστούν τυχαία στο χάρτη
        return categories[:count]

    def _create_block(self, region: Set[Tuple[int, int]], category: BlockCategory):
        """Δημιουργεί το αντικείμενο ενός οικοδομικού τετραγώνου από μία περιοχή κελιών."""
        block_id = self.world.next_block_id()
        cells_list = list(region)

        # Βρίσκει το σημείο εισόδου (την πόρτα): ένα κελί στην περίμετρο που "βλέπει" στο δρόμο
        entry_point, facing_road = self._find_entry_point(region)

        # Υπολογισμός μέγιστης χωρητικότητας πόρων (βάσει του εμβαδού)
        area = len(cells_list)
        food_cap = area * self.config.blocks.food_capacity_factor
        poll_cap = area * self.config.blocks.pollution_capacity_factor

        block = BuildingBlock(
            block_id=block_id,
            category=category,
            cells=cells_list,
            entry_point=entry_point,
            facing_road_cell=facing_road,
            food_level=food_cap * 0.5,  # Ξεκινάει μισογεμάτο με φαγητό
            food_capacity=food_cap,
            pollution_level=0.0,        # Ξεκινάει χωρίς σκουπίδια
            pollution_capacity=poll_cap,
        )

        # Μαρκάρισμα των κελιών πάνω στο πλέγμα (Grid)
        for (r, c) in cells_list:
            cell = self.world.grid[r][c]
            cell.cell_type = CellType.BLOCK
            cell.block = block

        # Μαρκάρισμα του σημείου εισόδου (της πόρτας)
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
        Βρίσκει την καλύτερη πόρτα εισόδου για ένα τετράγωνο.
        Ιδανικά, η πόρτα πρέπει να είναι στην περίμετρο και να συνορεύει με δρόμο.
        Επιστρέφει: (πόρτα_στο_πεζοδρόμιο, κελί_δρόμου_που_βλέπει).
        """
        perimeter_cells = self._get_perimeter(region)
        best_entry = None
        best_road = None

        for (r, c) in perimeter_cells:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if not self.world.is_valid(nr, nc):
                    continue
                # Ελέγχει αν το διπλανό κελί είναι πεζοδρόμιο (κατάλληλο για πόρτα)
                adj_cell = self.world.grid[nr][nc]
                if adj_cell.cell_type == CellType.SIDEWALK:
                    # Ελέγχει αν δίπλα από το πεζοδρόμιο υπάρχει δρόμος!
                    for dr2, dc2 in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                        rr, rc = nr + dr2, nc + dc2
                        if not self.world.is_valid(rr, rc):
                            continue
                        road_cell = self.world.grid[rr][rc]
                        if road_cell.cell_type == CellType.ROAD:
                            return (nr, nc), (rr, rc) # Βρέθηκε η τέλεια πόρτα!

        # Αν δεν βρεθεί η τέλεια πόρτα, δοκιμάζουμε το πρώτο κελί στην περίμετρο (Fallback)
        if perimeter_cells:
            first = list(perimeter_cells)[0]
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = first[0] + dr, first[1] + dc
                if self.world.is_valid(nr, nc):
                    return (nr, nc), (nr, nc)

        # Ύστατη λύση (Ultimate fallback): οποιοδήποτε κελί
        first = list(region)[0]
        return first, first

    def _get_perimeter(self, region: Set[Tuple[int, int]]) -> Set[Tuple[int, int]]:
        """Επιστρέφει τα κελιά που βρίσκονται στην εξωτερική περίμετρο μιας περιοχής (κτιρίου)."""
        perimeter = set()
        for (r, c) in region:
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = r + dr, c + dc
                if (nr, nc) not in region:
                    perimeter.add((r, c))
                    break
        return perimeter
