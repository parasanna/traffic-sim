"""
Agents package initialization.
"""
from agents.base_agent import BaseVehicle, VehicleState, VehicleType, MovementEpisode
from agents.resident import ResidentVehicle
from agents.transient import TransientVehicle
from agents.food_truck import FoodTruck
from agents.garbage_truck import GarbageTruck

__all__ = [
    'BaseVehicle', 'VehicleState', 'VehicleType', 'MovementEpisode',
    'ResidentVehicle', 'TransientVehicle', 'FoodTruck', 'GarbageTruck',
]
