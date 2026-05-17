"""
Σύστημα Φαναριών (Traffic Light System) - Φάση 6
Διαχειρίζεται τα φανάρια στις διασταυρώσεις, εναλλάσσοντας πράσινο/κόκκινο
μεταξύ οριζόντιας και κάθετης κίνησης ανά X ticks.
"""
import logging
from enum import Enum, auto
from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Set, Optional
from world import GridWorld, CellType

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

    def tick(self):
        """Ενημέρωση φαναριών σε κάθε tick. Αλλάζει φάση μετά από cycle_duration ticks."""
        for light in self.traffic_lights.values():
            light.ticks_in_phase += 1
            if light.ticks_in_phase >= self.cycle_duration:
                light.toggle()

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
        # Αν η επόμενη θέση δεν έχει φανάρι, πέρνα ελεύθερα
        light_id = self._cell_to_light.get(next_pos)
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
