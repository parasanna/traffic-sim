"""
Παράμετροι ρυθμίσεων (Configuration) για την Προσομοίωση Αστικής Κυκλοφορίας.
Όλες οι ρυθμιζόμενες παράμετροι ορίζονται εδώ ως προεπιλογές (defaults) και μπορούν να
παρακαμφθούν μέσω ενός αρχείου ρυθμίσεων JSON.
"""
import json
import os
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Tuple


@dataclass
class WorldConfig:
    """Διαστάσεις του 'Grid World' και γενικές παράμετροι (World parameters)."""
    grid_rows: int = 100         # GR - Αριθμός γραμμών του πλέγματος
    grid_cols: int = 140         # GC - Αριθμός στηλών του πλέγματος
    ticks_per_hour: int = 20     # Πόσοι κύκλοι (ticks) προσομοίωσης αντιστοιχούν σε μία ώρα
    hours_per_day: int = 24      # Ώρες ανά ημέρα


@dataclass
class RoadConfig:
    """Παράμετροι για το οδικό δίκτυο (Road network parameters)."""
    min_road_area: int = 8       # RAT - Ελάχιστο εμβαδόν δρόμου (σε κελιά)
    # Κατανομή των τύπων δρόμου (πρέπει να αθροίζουν σε 1.0)
    road_type_distribution: Dict[str, float] = field(default_factory=lambda: {
        "R1": 0.15,   # Λεωφόροι (Avenues) - 2 λωρίδες ανά κατεύθυνση
        "R2": 0.70,   # Οδοί (Streets) - 1 λωρίδα ανά κατεύθυνση
        "R3": 0.15,   # Μονόδρομοι (One-way streets)
    })
    # Οι δρόμοι R1 έχουν σημεία εισόδου/εξόδου στα σύνορα (borders)
    r1_lane_width: int = 1       # Πλάτος κάθε λωρίδας σε κελιά
    r2_lane_width: int = 1
    r3_lane_width: int = 1


@dataclass
class BlockConfig:
    """Παράμετροι για τα οικοδομικά τετράγωνα (Building block parameters)."""
    # Κατανομή των κατηγοριών τετραγώνων (πρέπει να αθροίζουν σε 1.0)
    block_distribution: Dict[str, float] = field(default_factory=lambda: {
        "residential": 0.25, # Κατοικίες
        "office": 0.25,      # Γραφεία
        "market": 0.20,      # Αγορές
        "leisure": 0.20,     # Διασκέδαση
        "other": 0.10,       # Λοιπά
    })
    food_consumption_rate: float = 0.5    # FCR - Ρυθμός κατανάλωσης φαγητού (μονάδες/tick)
    food_capacity_factor: float = 10.0    # F - Μέγιστη αποθήκευση φαγητού = Εμβαδόν * F
    pollution_generation_rate: float = 0.3  # PGR - Ρυθμός παραγωγής ρύπανσης (μονάδες/tick)
    pollution_capacity_factor: float = 8.0  # P - Μέγιστη αποθήκευση ρύπανσης = Εμβαδόν * P


@dataclass
class PopulationConfig:
    """Παράμετροι πληθυσμού (Population parameters)."""
    permanent_population: int = 800   # P1 - Μόνιμοι κάτοικοι
    transient_population: int = 300   # P2 - Διερχόμενος πληθυσμός (απλά περνούν από την πόλη)


@dataclass
class FleetConfig:
    """Παράμετροι στόλου για logistics (Fleet parameters)."""
    food_fleet_size: int = 15       # M - Αριθμός οχημάτων τροφοδοσίας φαγητού
    food_capacity: int = 50         # M1 - Χωρητικότητα μονάδων φαγητού ανά όχημα
    food_target_categories: List[int] = field(default_factory=lambda: [3, 4])  # Στοχεύουν: Market (3), Leisure (4)

    collection_fleet_size: int = 15  # N - Αριθμός απορριμματοφόρων
    collection_capacity: int = 40    # N1 - Χωρητικότητα μονάδων απορριμμάτων ανά απορριμματοφόρο
    collection_target_categories: List[int] = field(default_factory=lambda: [1, 2, 3, 4, 5])  # Στοχεύουν: Όλα (1-5)


@dataclass
class VehicleConfig:
    """Παράμετροι κίνησης οχημάτων (Vehicle movement parameters)."""
    min_speed: int = 1              # Ελάχιστη ταχύτητα (κελιά/tick)
    max_speed: int = 5              # Μέγιστη ταχύτητα (κελιά/tick)
    # Σημείωση: Δεν επιτρέπεται η διαγώνια κίνηση


@dataclass
class WeatherConfig:
    """Παράμετροι καιρού (Weather parameters)."""
    max_storms: int = 3            # S - Μέγιστος αριθμός ταυτόχρονων καταιγίδων
    storm_radius: int = 8          # SR - Ακτίνα επίδρασης της καταιγίδας (σε κελιά)
    storm_speed_reduction: int = 2  # VR - Μείωση της ταχύτητας οχημάτων κατά τη διάρκεια καταιγίδας
    storm_probability: float = 0.05  # Πιθανότητα εμφάνισης καταιγίδας ανά tick


@dataclass
class EventConfig:
    """Παράμετροι τυχαίων γεγονότων (Random event parameters)."""
    breakdown_probability: float = 0.00005 # PMF - Δραστική μείωση (ήταν 0.002) για ρεαλισμό και αποφυγή ατέλειωτων μποτιλιαρισμάτων
    breakdown_duration: int = 30           # MD - Χρόνος (σε ticks) για επισκευή/παραμονή στο δρόμο
    accident_probability: float = 0.0001   # PA - Δραστική μείωση (ήταν 0.001)
    accident_duration: int = 50            # AD - Χρόνος (σε ticks) ακινητοποίησης λόγω ατυχήματος
    service_breakdown_factor: float = 1.0  # SD - Συντελεστής για βλάβη οχημάτων υπηρεσίας (ανάλογος του εμβαδού του block)


@dataclass
class TrafficZone:
    """Ορισμός μίας 'Ζώνης Χρόνου' για κυκλοφοριακά μοτίβα (αναλόγως της ώρας)."""
    zone_id: int
    start_hour: int
    end_hour: int
    transient_probability: float # Πιθανότητα εμφάνισης διερχόμενου οχήματος
    internal_probability: float  # Πιθανότητα εμφάνισης εσωτερικού/μόνιμου οχήματος
    transitions: Dict[str, float] = field(default_factory=dict)
    # Παράδειγμα transitions: {"Res->Off(W)": 0.05, "Res->Mar(W)": 0.05, ...}
    # (π.χ. από Residential (Σπίτι) προς Office (Γραφείο) λόγω Εργασίας (Work) με πιθανότητα 5%)


@dataclass
class TrafficConfig:
    """Ρυθμίσεις δυναμικής κυκλοφορίας - 8 χρονικές ζώνες της ημέρας."""
    zones: List[TrafficZone] = field(default_factory=lambda: [
        TrafficZone( # 1η Ζώνη: 06:00 - 09:00
            zone_id=1, start_hour=6, end_hour=9,
            transient_probability=0.15,
            internal_probability=0.15,
            transitions={
                "Res->Off(W)": 0.05, "Res->Mar(W)": 0.05,
                "Res->Lei(W)": 0.02, "Res->Oth(W)": 0.03,
            }
        ),
        TrafficZone( # 2η Ζώνη: 09:00 - 12:00
            zone_id=2, start_hour=9, end_hour=12,
            transient_probability=0.20,
            internal_probability=0.20,
            transitions={
                "Res->Mar(F)": 0.10, "Res->Oth(O)": 0.04,
                "Off->Oth(O)": 0.06,
            }
        ),
        TrafficZone( # 3η Ζώνη: 12:00 - 15:00
            zone_id=3, start_hour=12, end_hour=15,
            transient_probability=0.15,
            internal_probability=0.15,
            transitions={
                "Res->Mar(F)": 0.07, "Res->Oth(O)": 0.03,
                "Off->Oth(O)": 0.05,
            }
        ),
        TrafficZone( # 4η Ζώνη: 15:00 - 18:00
            zone_id=4, start_hour=15, end_hour=18,
            transient_probability=0.15,
            internal_probability=0.15,
            transitions={
                "Res->Mar(F)": 0.03, "Off->Oth(O)": 0.05,
                "Mar->Oth(O)": 0.05, "Lei->Oth(O)": 0.02,
            }
        ),
        TrafficZone( # 5η Ζώνη: 18:00 - 21:00
            zone_id=5, start_hour=18, end_hour=21,
            transient_probability=0.12,
            internal_probability=0.12,
            transitions={
                "Res->Oth(O)": 0.02, "Res->Lei(L)": 0.02,
                "Off->Lei(L)": 0.02, "Mar->Lei(L)": 0.03,
                "Oth->Lei(L)": 0.03,
            }
        ),
        TrafficZone( # 6η Ζώνη: 21:00 - 24:00
            zone_id=6, start_hour=21, end_hour=24,
            transient_probability=0.10,
            internal_probability=0.10,
            transitions={
                "Off->Res(S)": 0.05, "Mar->Res(S)": 0.02,
                "Lei->Res(S)": 0.02, "Oth->Res(S)": 0.01,
            }
        ),
        TrafficZone( # 7η Ζώνη: 00:00 - 03:00
            zone_id=7, start_hour=0, end_hour=3,
            transient_probability=0.08,
            internal_probability=0.08,
            transitions={
                "Off->Res(S)": 0.03, "Lei->Res(S)": 0.03,
                "Oth->Res(S)": 0.02,
            }
        ),
        TrafficZone( # 8η Ζώνη: 03:00 - 06:00
            zone_id=8, start_hour=3, end_hour=6,
            transient_probability=0.05,
            internal_probability=0.05,
            transitions={
                "Lei->Res(S)": 0.03, "Oth->Res(S)": 0.02,
            }
        ),
    ])


@dataclass
class SimulationConfig:
    """Η κεντρική ρύθμιση (Master configuration) που συνδυάζει όλα τα παραπάνω."""
    world: WorldConfig = field(default_factory=WorldConfig)
    roads: RoadConfig = field(default_factory=RoadConfig)
    blocks: BlockConfig = field(default_factory=BlockConfig)
    population: PopulationConfig = field(default_factory=PopulationConfig)
    fleet: FleetConfig = field(default_factory=FleetConfig)
    vehicle: VehicleConfig = field(default_factory=VehicleConfig)
    weather: WeatherConfig = field(default_factory=WeatherConfig)
    events: EventConfig = field(default_factory=EventConfig)
    traffic: TrafficConfig = field(default_factory=TrafficConfig)
    random_seed: int = 42  # Αρχική τιμή τυχαιότητας για να μπορούμε να αναπαράγουμε τα ίδια αποτελέσματα

    def save(self, filepath: str):
        """Αποθήκευση όλων των ρυθμίσεων σε αρχείο JSON."""
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(asdict(self), f, indent=2, ensure_ascii=False)

    @classmethod
    def load(cls, filepath: str) -> 'SimulationConfig':
        """Φόρτωση ρυθμίσεων από αρχείο JSON."""
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        # Ανακατασκευή των εμφωλευμένων (nested) dataclasses
        config = cls()
        config.world = WorldConfig(**data.get('world', {}))
        config.roads = RoadConfig(**data.get('roads', {}))
        config.blocks = BlockConfig(**data.get('blocks', {}))
        config.population = PopulationConfig(**data.get('population', {}))
        config.fleet = FleetConfig(**data.get('fleet', {}))
        config.vehicle = VehicleConfig(**data.get('vehicle', {}))
        config.weather = WeatherConfig(**data.get('weather', {}))
        config.events = EventConfig(**data.get('events', {}))
        if 'random_seed' in data:
            config.random_seed = data['random_seed']
        # Ειδικός χειρισμός για την ανακατασκευή των ζωνών κυκλοφορίας
        if 'traffic' in data and 'zones' in data['traffic']:
            config.traffic = TrafficConfig(
                zones=[TrafficZone(**z) for z in data['traffic']['zones']]
            )
        return config
