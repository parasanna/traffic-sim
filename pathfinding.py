"""
Μονάδα Εύρεσης Διαδρομής (Pathfinding module): Αλγόριθμος A* (A-star) για την εύρεση διαδρομών
στο οδικό δίκτυο του πλέγματος.
Υποστηρίζει περιορισμούς κίνησης (απαγόρευση διαγώνιας κίνησης, σεβασμός στην κατεύθυνση λωρίδας, 
και στον τύπο του δρόμου).
"""
import heapq
from typing import List, Tuple, Optional, Set, Dict, Callable
from world import GridWorld, CellType, Direction, Cell


def manhattan_distance(a: Tuple[int, int], b: Tuple[int, int]) -> int:
    """Ευρετική (Heuristic) απόσταση Manhattan (κατάλληλη για κίνηση σε πλέγμα/grid)."""
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


class PathNode:
    """Κόμβος για την αναζήτηση με τον αλγόριθμο A*."""
    __slots__ = ['pos', 'g', 'h', 'f', 'parent']

    def __init__(self, pos: Tuple[int, int], g: float, h: float,
                 parent: Optional['PathNode'] = None):
        self.pos = pos # Θέση (row, col)
        self.g = g     # Κόστος από την αφετηρία μέχρι αυτόν τον κόμβο
        self.h = h     # Εκτιμώμενο κόστος από αυτόν τον κόμβο μέχρι τον στόχο (heuristic)
        self.f = g + h # Συνολικό κόστος f(n) = g(n) + h(n)
        self.parent = parent # Ο γονικός κόμβος (για την ανακατασκευή της διαδρομής στο τέλος)

    def __lt__(self, other: 'PathNode'):
        # Σύγκριση για την ουρά προτεραιότητας (Priority Queue)
        return self.f < other.f

    def __eq__(self, other):
        if isinstance(other, PathNode):
            return self.pos == other.pos
        return False

    def __hash__(self):
        return hash(self.pos)


class Pathfinder:
    """
    Υλοποίηση του A* (A-star) pathfinder για τον grid world.
    Επιτρέπει κίνηση ΜΟΝΟ σε κελιά ΔΡΟΜΟΥ (ROAD) και ΕΙΣΟΔΟΥ_ΕΞΟΔΟΥ (ENTRY_EXIT).
    Σέβεται την κατεύθυνση των λωρίδων και τους μονόδρομους.
    """

    def __init__(self, world: GridWorld):
        self.world = world

    def find_path(self, start: Tuple[int, int], goal: Tuple[int, int],
                  respect_lanes: bool = True,
                  avoid_occupied: bool = True,
                  allowed_types: Optional[Set[CellType]] = None,
                  avoid_positions: Optional[Set[Tuple[int, int]]] = None
                  ) -> Optional[List[Tuple[int, int]]]:
        """
        Εύρεση διαδρομής από την αφετηρία (start) στον στόχο (goal) χρησιμοποιώντας τον A*.
        
        Ορίσματα:
            start: (row, col) Θέση εκκίνησης
            goal: (row, col) Θέση στόχου
            respect_lanes: Αν True, κινείται μόνο προς την κατεύθυνση της λωρίδας
            avoid_occupied: Αν True, αποφεύγει τα κελιά που έχουν ήδη οχήματα
            allowed_types: Σύνολο από επιτρεπόμενους τύπους κελιών (CellTypes)
            
        Επιστρέφει:
            Μια λίστα από θέσεις (row, col) που αποτελούν τη διαδρομή, ή None αν δεν βρεθεί.
        """
        if not allowed_types:
            # Από προεπιλογή, κινείται μόνο σε δρόμους και σημεία εισόδου κτιρίων
            allowed_types = {CellType.ROAD, CellType.ENTRY_EXIT, CellType.BLOCK_ENTRY}

        start_cell = self.world.get_cell(*start)
        goal_cell = self.world.get_cell(*goal)

        if not start_cell or not goal_cell:
            return None # Εκτός ορίων χάρτη

        # Σύνολο ανοιχτών κόμβων (αναζήτηση A*)
        open_set = []
        start_node = PathNode(start, 0, manhattan_distance(start, goal))
        heapq.heappush(open_set, start_node)

        # Κλειστό σύνολο (κόμβοι που έχουν ήδη εξεταστεί)
        closed_set: Set[Tuple[int, int]] = set()
        g_scores: Dict[Tuple[int, int], float] = {start: 0}

        while open_set:
            current = heapq.heappop(open_set)

            # Αν φτάσαμε στο στόχο, επιστρέφουμε τη διαδρομή
            if current.pos == goal:
                return self._reconstruct_path(current)

            if current.pos in closed_set:
                continue
            closed_set.add(current.pos)

            # Εξερεύνηση γειτόνων (4 κατευθύνσεις: Πάνω, Κάτω, Αριστερά, Δεξιά - ΟΧΙ διαγώνια)
            for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                nr, nc = current.pos[0] + dr, current.pos[1] + dc
                neighbor_pos = (nr, nc)

                if neighbor_pos in closed_set:
                    continue

                neighbor_cell = self.world.get_cell(nr, nc)
                if not neighbor_cell:
                    continue # Εκτός ορίων

                # Έλεγχος αν ο τύπος του κελιού επιτρέπεται
                if neighbor_cell.cell_type not in allowed_types:
                    continue

                # Έλεγχος πληρότητας (αποφυγή τρακαρίσματος αν ζητηθεί)
                if avoid_occupied and neighbor_cell.is_occupied:
                    continue

                # Απόλυτη αποφυγή συγκεκριμένων κελιών (π.χ. βλάβες V2V)
                if avoid_positions and neighbor_pos in avoid_positions:
                    continue

                # Έλεγχος κατεύθυνσης της λωρίδας (για σεβασμό των μονόδρομων/λωρίδων)
                if respect_lanes and neighbor_cell.lane_direction:
                    move_dir = self._get_direction(dr, dc)
                    if move_dir and move_dir != neighbor_cell.lane_direction:
                        # Επιτρέπεται η κίνηση μόνο προς τη σωστή κατεύθυνση της λωρίδας
                        continue

                # Υπολογισμός κόστους κίνησης (1 κελί = 1 μονάδα κόστους)
                move_cost = 1.0
                tentative_g = current.g + move_cost

                if neighbor_pos in g_scores and tentative_g >= g_scores[neighbor_pos]:
                    continue # Υπάρχει ήδη καλύτερη (φθηνότερη) διαδρομή για αυτό το κελί

                # Ενημέρωση σκορ και προσθήκη του γείτονα στην ουρά προς εξερεύνηση
                g_scores[neighbor_pos] = tentative_g
                h = manhattan_distance(neighbor_pos, goal)
                neighbor_node = PathNode(neighbor_pos, tentative_g, h, current)
                heapq.heappush(open_set, neighbor_node)

        return None  # Δεν βρέθηκε καμία διαδρομή προς τον στόχο

    def find_path_to_nearest(self, start: Tuple[int, int],
                              targets: List[Tuple[int, int]],
                              **kwargs) -> Optional[Tuple[Tuple[int, int], List[Tuple[int, int]]]]:
        """
        Βρίσκει τη διαδρομή προς τον κοντινότερο στόχο από μια λίστα με στόχους.
        Επιστρέφει (Θέση_στόχου, Διαδρομή) ή None.
        """
        best_path = None
        best_target = None
        best_cost = float('inf')

        for target in targets:
            path = self.find_path(start, target, **kwargs)
            if path and len(path) < best_cost:
                best_path = path
                best_target = target
                best_cost = len(path)

        if best_path:
            return (best_target, best_path)
        return None

    def find_path_relaxed(self, start: Tuple[int, int], goal: Tuple[int, int], avoid_positions: Optional[Set[Tuple[int, int]]] = None
                          ) -> Optional[List[Tuple[int, int]]]:
        """
        Βρίσκει διαδρομή με πιο "χαλαρούς" κανόνες (π.χ. δεν ελέγχει is_occupied),
        υποθέτοντας ότι τα σταματημένα οχήματα κάποια στιγμή θα μετακινηθούν.
        """
        return self.find_path(start, goal, respect_lanes=False, avoid_occupied=False, avoid_positions=avoid_positions)

    def _reconstruct_path(self, node: PathNode) -> List[Tuple[int, int]]:
        """Ανακατασκευάζει τη διαδρομή από τον κόμβο-στόχο πίσω στην αφετηρία."""
        path = []
        current = node
        while current:
            path.append(current.pos)
            current = current.parent
        path.reverse() # Αντιστροφή για να είναι από την αφετηρία προς το στόχο
        return path

    def _get_direction(self, dr: int, dc: int) -> Optional[Direction]:
        """Μετατρέπει τη διαφορά (delta) γραμμής/στήλης σε Κατεύθυνση (Direction)."""
        if dr == -1 and dc == 0:
            return Direction.NORTH
        elif dr == 1 and dc == 0:
            return Direction.SOUTH
        elif dr == 0 and dc == 1:
            return Direction.EAST
        elif dr == 0 and dc == -1:
            return Direction.WEST
        return None


class MultiTargetPathfinder(Pathfinder):
    """
    Εκτεταμένος pathfinder για οχήματα υπηρεσιών (π.χ. απορριμματοφόρα, τροφοδοσία)
    που πρέπει να επισκεφθούν πολλαπλά τετράγωνα.
    Υλοποιεί μια απλή ευρετική του 'κοντινότερου γείτονα' (nearest-neighbor) για σχεδιασμό δρομολογίου.
    """

    def plan_route(self, start: Tuple[int, int],
                    targets: List[Tuple[int, int]],
                    end: Tuple[int, int]) -> Optional[List[List[Tuple[int, int]]]]:
        """
        Σχεδιάζει ένα δρομολόγιο που περνάει από όλους τους στόχους και καταλήγει στο 'end'.
        
        Επιστρέφει μια λίστα με τμήματα διαδρομών (path segments) ή None αν είναι αδύνατο.
        """
        if not targets:
            path = self.find_path(start, end)
            return [path] if path else None

        remaining = list(targets)
        current_pos = start
        segments = []

        while remaining:
            # Εύρεση του κοντινότερου στόχου που δεν έχουμε επισκεφθεί
            result = self.find_path_to_nearest(current_pos, remaining)
            if not result:
                # Δοκιμάζουμε τη χαλαρή αναζήτηση (αγνοώντας μονόδρομους) αν κολλήσουμε
                best = None
                best_dist = float('inf')
                for t in remaining:
                    d = manhattan_distance(current_pos, t)
                    if d < best_dist:
                        best_dist = d
                        best = t
                if best:
                    path = self.find_path_relaxed(current_pos, best)
                    if path:
                        segments.append(path)
                        current_pos = best
                        remaining.remove(best)
                        continue
                return None  # Δεν μπορούμε να φτάσουμε σε κανέναν από τους εναπομείναντες στόχους

            target, path = result
            segments.append(path)
            current_pos = target
            remaining.remove(target)

        # Τελικό τμήμα: επιστροφή στο σημείο λήξης (end)
        final_path = self.find_path(current_pos, end)
        if not final_path:
            final_path = self.find_path_relaxed(current_pos, end)
        if final_path:
            segments.append(final_path)

        return segments
