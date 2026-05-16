import sys
import os
sys.path.append(os.getcwd())
from simulation import Simulation
from config import SimulationConfig
import time

config = SimulationConfig()
sim = Simulation(config)
sim.initialize()

print("Running benchmark for 2000 ticks on branch:", os.popen("git branch --show-current").read().strip())
start_time = time.time()
for i in range(2000):
    sim.tick()
    if i % 500 == 0:
        print(f"Tick {i}...")

stats = sim.stats.to_dict()
print("--- RESULTS ---")
print(f"Time taken: {time.time() - start_time:.2f}s")
print(f"Ticks: {sim.current_tick}")
print(f"Active Vehicles: {stats['active_vehicles']}")
print(f"Trips Done: {stats['trips_completed']}")
print(f"Breakdowns: {stats['total_breakdowns']}")
print(f"Accidents: {stats['total_accidents']}")
print("---------------")
