import sys
import os
sys.path.append(os.getcwd())
from simulation import Simulation
from config import SimulationConfig
import time

config = SimulationConfig()
sim = Simulation(config)
sim.initialize()

print("Running benchmark for 5000 ticks on branch:", os.popen("git branch --show-current").read().strip())
start_time = time.time()
for i in range(5000):
    sim.tick()
    if i % 1000 == 0:
        print(f"Tick {i}...")

stats = sim.stats.to_dict()
print("\n===== ΑΠΟΤΕΛΕΣΜΑΤΑ (RESULTS) =====")
print(f"Time taken: {time.time() - start_time:.2f}s")
print(f"Ticks: {sim.current_tick}")
print(f"Active Vehicles: {stats['active_vehicles']}")
print(f"Trips Done: {stats['total_trips']}")
print(f"Breakdowns: {stats['breakdowns']}")
print(f"Accidents: {stats['accidents']}")

print("\n--- ΜΕΤΡΙΚΕΣ ΠΡΟΒΛΗΜΑΤΟΣ ---")
print(f"Μ1. Μέσος χρόνος διαδρομής (Διερχόμενοι):        {stats['avg_transit_time']:.2f} ticks")
print(f"Μ2. Μέσος χρόνος διαδρομής (Κάτοικοι):           {stats['avg_resident_time']:.2f} ticks")
print(f"Μ3. Μέσος χρόνος/μονάδα μήκους (Διερχόμενοι):    {stats['avg_transit_time_per_dist']:.2f} ticks/cell")
print(f"Μ4. Μέσος χρόνος/μονάδα μήκους (Κάτοικοι):       {stats['avg_resident_time_per_dist']:.2f} ticks/cell")
print(f"Μ5. Διαφορά ροής (Εισερχόμενοι - Εξερχόμενοι):   {stats['transit_flow_diff']}")
print(f"    -> Εισήλθαν: {stats['transit_entered']}, Εξήλθαν: {stats['transit_exited']}")
print("===================================")
