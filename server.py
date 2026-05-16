"""
Διακομιστής Οπτικοποίησης (Visualization Server): Ένα web-based dashboard (ταμπλό) για την προσομοίωση.
Σερβίρει την οπτική αναπαράσταση του "grid world" και τα στατιστικά σε πραγματικό χρόνο.
Χρησιμοποιεί έναν απλό HTTP server.
"""
import json
import threading
import http.server
import socketserver
import os
from typing import Optional
from simulation import Simulation, SimulationStats
from config import SimulationConfig


class SimulationServer:
    """
    HTTP server που "σερβίρει" το ταμπλό οπτικοποίησης
    και παρέχει δεδομένα της προσομοίωσης ως JSON API.
    """

    def __init__(self, simulation: Simulation, port: int = 8080):
        self.simulation = simulation # Σύνδεση με το αντικείμενο της προσομοίωσης
        self.port = port # Η θύρα που θα ακούει ο server
        self.server: Optional[socketserver.TCPServer] = None
        self._static_dir = os.path.dirname(os.path.abspath(__file__)) # Ο φάκελος των αρχείων

    def start(self):
        """Εκκίνηση του διακομιστή οπτικοποίησης."""
        sim = self.simulation
        static_dir = self._static_dir

        class Handler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                # Ρυθμίζει το HTTP Request Handler να σερβίρει από τον τρέχοντα φάκελο
                super().__init__(*args, directory=static_dir, **kwargs)

            def do_GET(self):
                # Ανάλογα με το URL, επιστρέφει είτε την HTML σελίδα είτε δεδομένα (JSON)
                if self.path == '/':
                    self.path = '/dashboard.html'
                    return super().do_GET()
                elif self.path == '/api/state':
                    # Επιστρέφει τη γενική κατάσταση
                    self._send_json(self._get_state())
                elif self.path == '/api/stats':
                    # Επιστρέφει τα στατιστικά
                    self._send_json(sim.stats.to_dict())
                elif self.path == '/api/vehicles':
                    # Επιστρέφει τις θέσεις των οχημάτων
                    self._send_json(sim.get_vehicle_positions())
                elif self.path == '/api/grid':
                    # Επιστρέφει την κατάσταση του πλέγματος (grid)
                    self._send_json(sim.get_grid_state())
                elif self.path == '/api/config':
                    # Επιστρέφει βασικές ρυθμίσεις του χάρτη
                    self._send_json({
                        'rows': sim.config.world.grid_rows,
                        'cols': sim.config.world.grid_cols,
                    })
                elif self.path == '/api/blocks':
                    # Επιστρέφει πληροφορίες για τα οικοδομικά τετράγωνα (π.χ. επίπεδα μόλυνσης, φαγητού)
                    self._send_json(self._get_blocks())
                elif self.path == '/api/weather':
                    # Επιστρέφει πληροφορίες για τον καιρό (καταιγίδες)
                    self._send_json(self._get_weather())
                else:
                    return super().do_GET()

            def _send_json(self, data):
                # Βοηθητική μέθοδος για την αποστολή δεδομένων σε μορφή JSON
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*') # Επιτρέπει cross-origin requests
                self.end_headers()
                self.wfile.write(json.dumps(data).encode())

            def _get_state(self):
                # Συλλέγει τη συνολική τρέχουσα κατάσταση
                return {
                    'tick': sim.current_tick,
                    'hour': sim.current_hour,
                    'zone': sim.current_zone_id,
                    'day': sim.day,
                    'running': sim.is_running,
                    'paused': sim.is_paused,
                    'stats': sim.stats.to_dict(),
                    'vehicles': sim.get_vehicle_positions(),
                    'storms': self._get_weather(),
                }

            def _get_blocks(self):
                # Επιστρέφει δεδομένα για κάθε οικοδομικό τετράγωνο (blocks)
                blocks = []
                if sim.world:
                    for block in sim.world.blocks.values():
                        blocks.append({
                            'id': block.block_id,
                            'category': block.category.name,
                            'area': block.area,
                            'food': round(block.food_level, 1),
                            'food_cap': round(block.food_capacity, 1),
                            'pollution': round(block.pollution_level, 1),
                            'pollution_cap': round(block.pollution_capacity, 1),
                            'entry': block.entry_point,
                        })
                return blocks

            def _get_weather(self):
                # Επιστρέφει δεδομένα για τις καταιγίδες
                storms = []
                if sim.weather:
                    for storm in sim.weather.storms:
                        storms.append({
                            'id': storm.storm_id,
                            'center': storm.center,
                            'radius': storm.radius,
                            'duration': storm.duration,
                            'active': storm.active,
                        })
                return storms

            def log_message(self, format, *args):
                pass  # Καταστέλλει (κρύβει) τα logs των HTTP αιτημάτων για να μην γεμίζει η κονσόλα

        # Δημιουργία και εκκίνηση του server σε ξεχωριστό thread (νήμα) για να μην μπλοκάρει την προσομοίωση
        self.server = socketserver.TCPServer(("", self.port), Handler)
        print(f"Το Dashboard είναι διαθέσιμο στο http://localhost:{self.port}")

        thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        thread.start()

    def stop(self):
        """Τερματισμός του server."""
        if self.server:
            self.server.shutdown()
