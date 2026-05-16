"""
Κύριο σημείο εισόδου (Main entry point) για την Προσομοίωση Αστικής Κυκλοφορίας.
Εδώ αρχικοποιείται η προσομοίωση και ξεκινάει ο web server (dashboard).
"""
import sys
import argparse
from config import SimulationConfig
from simulation import Simulation
from server import SimulationServer


def main():
    # Ρύθμιση ορισμάτων γραμμής εντολών (command-line arguments) για την προσαρμογή της προσομοίωσης
    parser = argparse.ArgumentParser(description="Multi-Agent Traffic Simulation")
    parser.add_argument('--ticks', type=int, default=5000, help='Αριθμός κύκλων (ticks) για την προσομοίωση')
    parser.add_argument('--port', type=int, default=8080, help='Θύρα διακομιστή (port) για το Dashboard')
    parser.add_argument('--rows', type=int, default=60, help='Γραμμές πλέγματος (Grid rows - GR)')
    parser.add_argument('--cols', type=int, default=80, help='Στήλες πλέγματος (Grid columns - GC)')
    parser.add_argument('--population', type=int, default=200, help='Μόνιμος πληθυσμός (P1)')
    parser.add_argument('--transient', type=int, default=50, help='Διερχόμενος πληθυσμός (P2)')
    parser.add_argument('--food-trucks', type=int, default=5, help='Αριθμός οχημάτων τροφοδοσίας (M)')
    parser.add_argument('--garbage-trucks', type=int, default=5, help='Αριθμός απορριμματοφόρων (N)')
    parser.add_argument('--seed', type=int, default=42, help='Αρχική τιμή τυχαιότητας (Random seed)')
    parser.add_argument('--config', type=str, default=None, help='Αρχείο ρυθμίσεων JSON')
    parser.add_argument('--no-server', action='store_true', help='Εκτέλεση χωρίς το web dashboard')
    parser.add_argument('--tick-delay', type=float, default=0.05, help='Καθυστέρηση μεταξύ των κύκλων σε δευτερόλεπτα (s)')
    args = parser.parse_args()

    # Υποστήριξη για δυναμική θύρα από υπηρεσίες Cloud (όπως το Render.com)
    import os
    if 'PORT' in os.environ:
        args.port = int(os.environ['PORT'])

    # Φόρτωση ή δημιουργία των ρυθμίσεων (config)
    if args.config:
        # Αν δόθηκε αρχείο, το φορτώνουμε
        config = SimulationConfig.load(args.config)
    else:
        # Διαφορετικά δημιουργούμε ένα νέο χρησιμοποιώντας τα ορίσματα (arguments)
        config = SimulationConfig()
        config.world.grid_rows = args.rows
        config.world.grid_cols = args.cols
        config.population.permanent_population = args.population
        config.population.transient_population = args.transient
        config.fleet.food_fleet_size = args.food_trucks
        config.fleet.collection_fleet_size = args.garbage_trucks
        config.random_seed = args.seed

    # Δημιουργία και αρχικοποίηση της προσομοίωσης με βάση τις ρυθμίσεις
    sim = Simulation(config)
    sim.initialize()

    # Εκκίνηση του web server (εκτός αν ορίστηκε το --no-server)
    server = None
    if not args.no_server:
        server = SimulationServer(sim, port=args.port)
        server.start()
        print(f"\n{'='*50}")
        print(f"  Ταμπλό (Dashboard): http://localhost:{args.port}")
        print(f"  Διαστάσεις Χάρτη: {args.rows}x{args.cols}")
        print(f"  Πληθυσμός: P1={args.population}, P2={args.transient}")
        print(f"  Στόλοι: Φαγητό={args.food_trucks}, Σκουπίδια={args.garbage_trucks}")
        print(f"{'='*50}\n")

    # Εκτέλεση του κεντρικού βρόχου (loop) της προσομοίωσης
    try:
        sim.run(ticks=args.ticks, real_time=True, tick_delay=args.tick_delay)
    except KeyboardInterrupt:
        # Αν ο χρήστης πατήσει Ctrl+C, σταματάμε ομαλά την προσομοίωση
        print("\nΗ προσομοίωση διακόπηκε (Simulation stopped).")
    finally:
        # Κλείσιμο του server και αποθήκευση της τελικής κατάστασης/ρυθμίσεων
        if server:
            server.stop()
        # Αποθήκευση του τελευταίου config για μελλοντική χρήση
        config.save('last_config.json')
        print(f"Τελικά στατιστικά: {sim.stats.to_dict()}")


if __name__ == '__main__':
    main()
