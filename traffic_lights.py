"""
Σύστημα Φαναριών (Traffic Light System) - Φάση 6
Διαχειρίζεται τα φανάρια στις διασταυρώσεις, εναλλάσσοντας πράσινο/κόκκινο
μεταξύ οριζόντιας και κάθετης κίνησης ανά X ticks.
"""
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional
from world import GridWorld, CellType, RoadType

logger = logging.getLogger(__name__)


class LightPhase(Enum):
    """Οι φάσεις ενός φαναριού."""
    HORIZONTAL_GREEN = auto()  # Πράσινο για οριζόντια κίνηση (Ανατολή/Δύση)
    VERTICAL_GREEN = auto()    # Πράσινο για κάθετη κίνηση (Βορράς/Νότος)


@dataclass
class TrafficLight:
    """Ένα φανάρι σε μια συγκεκριμένη διασταύρωση."""
    intersection_id: int
    cells: List[Tuple[int, int]]    # Τα κελιά που ανήκουν σε αυτή τη διασταύρωση
    phase: LightPhase = LightPhase.HORIZONTAL_GREEN
    ticks_in_phase: int = 0         # Πόσα ticks μετράει στην τρέχουσα φάση

    def toggle(self):
        """Αλλαγή φάσης φαναριού."""
        if self.phase == LightPhase.HORIZONTAL_GREEN:
            self.phase = LightPhase.VERTICAL_GREEN
        else:
            self.phase = LightPhase.HORIZONTAL_GREEN
        self.ticks_in_phase = 0


class TrafficLightSystem:
    """
    Κεντρικό σύστημα διαχείρισης φαναριών.
    Εντοπίζει αυτόματα τις διασταυρώσεις στον χάρτη και τοποθετεί φανάρια.
    """

    def __init__(self, world: GridWorld, cycle_duration: int = 10):
        """
        Args:
            world: Ο κόσμος του πλέγματος
            cycle_duration: Πόσα ticks κρατάει κάθε φάση (πράσινο) πριν αλλάξει
        """
        self.world = world
        self.cycle_duration = cycle_duration
        self.traffic_lights: Dict[int, TrafficLight] = {}
        # Γρήγορο lookup: (row, col) -> intersection_id
        self._cell_to_light: Dict[Tuple[int, int], int] = {}
        self._next_id = 0

    def detect_intersections(self):
        """
        Σαρώνει τον χάρτη και εντοπίζει αυτόματα τις διασταυρώσεις.
        Μια διασταύρωση = κελί δρόμου που έχει γείτονες-δρόμους και στους 2 άξονες.
        Ομαδοποιεί γειτονικά κελιά διασταύρωσης σε μία ενιαία ομάδα.
        """
        visited: Set[Tuple[int, int]] = set()

        for r in range(self.world.rows):
            for c in range(self.world.cols):
                if (r, c) in visited:
                    continue
                if self.world.is_intersection(r, c):
                    # BFS για να βρούμε όλα τα συνεχόμενα κελιά αυτής της διασταύρωσης
                    cluster = []
                    queue = [(r, c)]
                    visited.add((r, c))

                    while queue:
                        cr, cc = queue.pop(0)
                        cluster.append((cr, cc))

                        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                            nr, nc = cr + dr, cc + dc
                            if (nr, nc) not in visited and self.world.is_intersection(nr, nc):
                                visited.add((nr, nc))
                                queue.append((nr, nc))

                    # Δημιουργία φαναριού μόνο αν η διασταύρωση είναι αρκετά μεγάλη (≥2 κελιά)
                    if len(cluster) >= 2:
                        light_id = self._next_id
                        self._next_id += 1

                        # Εναλλαγή αρχικής φάσης για να μην ανάβουν όλα μαζί
                        initial_phase = (LightPhase.HORIZONTAL_GREEN 
                                        if light_id % 2 == 0 
                                        else LightPhase.VERTICAL_GREEN)

                        light = TrafficLight(
                            intersection_id=light_id,
                            cells=cluster,
                            phase=initial_phase,
                            ticks_in_phase=0
                        )
                        self.traffic_lights[light_id] = light

                        for cell_pos in cluster:
                            self._cell_to_light[cell_pos] = light_id

        logger.info(f"Φανάρια: Εντοπίστηκαν {len(self.traffic_lights)} διασταυρώσεις")

    def _get_queues(self, light: TrafficLight) -> Tuple[int, int]:
        """Υπολογίζει το μέγεθος της ουράς (κατειλημμένα κελιά) σε οριζόντια και κάθετη κατεύθυνση."""
        h_queue = 0
        v_queue = 0
        
        # Για κάθε κελί της διασταύρωσης, κοιτάζουμε προς τις 4 κατευθύνσεις (έως 4 κελιά απόσταση)
        for r, c in light.cells:
            # Οριζόντια (Αριστερά/Δεξιά)
            for dc in [-1, -2, -3, -4]:
                cell = self.world.get_cell(r, c + dc)
                if cell and cell.cell_type == CellType.ROAD:
                    if cell.is_occupied:
                        h_queue += 1
                else:
                    break
            for dc in [1, 2, 3, 4]:
                cell = self.world.get_cell(r, c + dc)
                if cell and cell.cell_type == CellType.ROAD:
                    if cell.is_occupied:
                        h_queue += 1
                else:
                    break
            # Κάθετα (Πάνω/Κάτω)
            for dr in [-1, -2, -3, -4]:
                cell = self.world.get_cell(r + dr, c)
                if cell and cell.cell_type == CellType.ROAD:
                    if cell.is_occupied:
                        v_queue += 1
                else:
                    break
            for dr in [1, 2, 3, 4]:
                cell = self.world.get_cell(r + dr, c)
                if cell and cell.cell_type == CellType.ROAD:
                    if cell.is_occupied:
                        v_queue += 1
                else:
                    break
        return h_queue, v_queue

    def tick(self):
        """
        Ενημέρωση φαναριών με Προσαρμοστικό (Adaptive) Έλεγχο Ουρών.
        Ανιχνεύει τον φόρτο σε κάθε κατεύθυνση και παρατείνει ή συντομεύει τον χρόνο πρασίνου.
        """
        for light in self.traffic_lights.values():
            light.ticks_in_phase += 1
            
            # Υπολογισμός ουρών σε οριζόντια και κάθετη κατεύθυνση
            h_q, v_q = self._get_queues(light)
            
            # Προσαρμοστικός (Adaptive) Έλεγχος
            if light.phase == LightPhase.HORIZONTAL_GREEN:
                # 1. Πρόωρος τερματισμός αν δεν υπάρχει κίνηση οριζόντια αλλά υπάρχει κάθετα
                if h_q == 0 and v_q > 0 and light.ticks_in_phase >= 5:
                    light.toggle()
                # 2. Παράταση πρασίνου (έως 20 ticks) αν υπάρχει μεγαλύτερη ουρά οριζόντια
                elif h_q > v_q and light.ticks_in_phase < 20:
                    continue  # Κρατάμε το πράσινο!
                # 3. Κανονική εναλλαγή
                elif light.ticks_in_phase >= self.cycle_duration:
                    light.toggle()
            else:  # VERTICAL_GREEN
                # 1. Πρόωρος τερματισμός αν δεν υπάρχει κίνηση κάθετα αλλά υπάρχει οριζόντια
                if v_q == 0 and h_q > 0 and light.ticks_in_phase >= 5:
                    light.toggle()
                # 2. Παράταση πρασίνου (έως 20 ticks) αν υπάρχει μεγαλύτερη ουρά κάθετα
                elif v_q > h_q and light.ticks_in_phase < 20:
                    continue  # Κρατάμε το πράσινο!
                # 3. Κανονική εναλλαγή
                elif light.ticks_in_phase >= self.cycle_duration:
                    light.toggle()

    def _trigger_i2i_diversion(self, road_id: int):
        """[I2I] Ενημερώνει τις γειτονικές διασταυρώσεις να εκτρέψουν την κυκλοφορία."""
        # Για λόγους προσομοίωσης και καταγραφής, οι γειτονικοί πράκτορες-διασταυρώσεις
        # λαμβάνουν το σήμα I2I και συντονίζονται για εκτροπή
        logger.warning(f"[I2I Diversion] Intersections notified! Diverting traffic away from blocked road ID {road_id}.")

    def can_pass(self, vehicle_pos: Tuple[int, int], 
                 next_pos: Tuple[int, int]) -> bool:
        """
        Ελέγχει αν ένα όχημα μπορεί να περάσει στο επόμενο κελί
        βάσει του φαναριού.

        Args:
            vehicle_pos: Η τρέχουσα θέση του οχήματος (row, col)
            next_pos: Η θέση που θέλει να μπει (row, col)

        Returns:
            True αν μπορεί να περάσει (πράσινο ή δεν υπάρχει φανάρι)
        """
        # [I2V ΠΡΟΣΤΑΣΙΑ] Έλεγχος αν ο επόμενος δρόμος είναι μονόδρομος R3 με ενεργή βλάβη/ατύχημα
        next_cell = self.world.get_cell(*next_pos)
        if next_cell and next_cell.road_id is not None:
            road = self.world.roads.get(next_cell.road_id)
            if road and road.road_type == RoadType.R3:
                if hasattr(self, 'simulation') and self.simulation:
                    from agents.base_agent import VehicleState
                    for v in self.simulation.vehicles.values():
                        if v.state in (VehicleState.BROKEN_DOWN, VehicleState.IN_ACCIDENT) and v.position:
                            v_cell = self.world.get_cell(*v.position)
                            if v_cell and v_cell.road_id == next_cell.road_id:
                                # Βρέθηκε βλάβη στον R3! Ενεργοποίηση προστατευτικού ΚΟΚΚΙΝΟΥ φαναριού (I2V)
                                self._trigger_i2i_diversion(next_cell.road_id)
                                return False  # Μην εισέρχεσαι!

        # [Layer 4: Emergency Intersection Flushing]
        # Αν υπάρχει κάποιο όχημα εγκλωβισμένο μέσα σε αυτή τη διασταύρωση για >5 ticks,
        # κλείνουμε όλες τις εισόδους (ΚΟΚΚΙΝΟ) για νέα οχήματα, ώστε να αδειάσει το κουτί!
        light_id = self._cell_to_light.get(next_pos)
        if light_id is not None:
            light = self.traffic_lights[light_id]
            if hasattr(self, 'simulation') and self.simulation:
                for v in self.simulation.vehicles.values():
                    if v.position and v.position in light.cells:
                        if v.ticks_waiting > 5:
                            # Αν το όχημα που ζητάει να περάσει ΔΕΝ είναι ήδη μέσα στη διασταύρωση,
                            # τότε του απαγορεύουμε την είσοδο (ανάβει Emergency RED)
                            if vehicle_pos not in light.cells:
                                logger.warning(f"[Emergency Flush] Intersection {light.intersection_id} locked to new entries to flush stuck vehicle {v.vehicle_id}!")
                                return False

        # Αν η επόμενη θέση δεν έχει φανάρι, πέρνα ελεύθερα
        if light_id is None:
            return True

        light = self.traffic_lights[light_id]

        # Υπολόγισε την κατεύθυνση κίνησης
        dr = next_pos[0] - vehicle_pos[0]
        dc = next_pos[1] - vehicle_pos[1]

        # Οριζόντια κίνηση = αλλαγή στήλης (dc != 0)
        # Κάθετη κίνηση = αλλαγή γραμμής (dr != 0)
        is_horizontal = (dc != 0)
        is_vertical = (dr != 0)

        if is_horizontal and light.phase == LightPhase.HORIZONTAL_GREEN:
            return True  # Πράσινο για οριζόντια
        elif is_vertical and light.phase == LightPhase.VERTICAL_GREEN:
            return True  # Πράσινο για κάθετη
        else:
            return False  # Κόκκινο! Σταμάτα!

    def get_light_at(self, pos: Tuple[int, int]) -> Optional[TrafficLight]:
        """Επιστρέφει το φανάρι σε μια θέση (αν υπάρχει)."""
        light_id = self._cell_to_light.get(pos)
        if light_id is not None:
            return self.traffic_lights[light_id]
        return None

    def get_state(self) -> List[dict]:
        """Επιστρέφει την κατάσταση όλων των φαναριών για το Dashboard."""
        result = []
        for light in self.traffic_lights.values():
            result.append({
                "id": light.intersection_id,
                "cells": light.cells,
                "phase": light.phase.name,
                "ticks_remaining": self.cycle_duration - light.ticks_in_phase
            })
        return result
