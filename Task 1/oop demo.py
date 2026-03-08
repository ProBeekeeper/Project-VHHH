import math
from typing import List, Dict, Tuple

class Aircraft:
    def __init__(self, callsign: str, x: float, y: float, heading: float, speed: float, altitude: int):
        self.callsign = callsign
        self.x = x
        self.y = y
        self.heading = heading  # 0-360
        self.speed = speed      # knots
        self.altitude = altitude # ft

    def update_position(self, delta_time: float):
        radians = math.radians(90 - self.heading)
        distance = self.speed * delta_time
        
        self.x += distance * math.cos(radians)
        self.y += distance * math.sin(radians)
# Flight heading: 0 degrees is due north, increasing clockwise.
