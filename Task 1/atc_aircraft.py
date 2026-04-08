import math
import random
from enum import Enum
from typing import List, Tuple, Optional

class FlightPhase(Enum):
    SPAWN_BUFFER = 1
    ACTIVE = 2
    LANDING = 3
    HANDOFF = 4
    DONE = 5

class Aircraft:
    def __init__(self, callsign: str, start_x: float, start_y: float, heading: float, speed: float, alt: float, flight_plan: List[dict] = None, is_arrival: bool = True, acft_category: str = "Medium", acft_type: str = "A320", procedure_name: str = ""):
        self.callsign = callsign
        self.is_arrival = is_arrival
        self.flight_plan = flight_plan or []
        self.lnav_active = True if self.flight_plan else False
        
        self.procedure_name = procedure_name 
        self.acft_type = acft_type 
        self.acft_category = acft_category
        self.squawk = str(random.randint(1000, 7777)) 
        
        self.ils_locked = False              
        self.cleared_ils: Optional[str] = None 
        self.is_accepted = False 
        
        self.manual_heading = False 
        self.manual_speed = False    
        self.manual_altitude = False 
        
        self.phase = FlightPhase.SPAWN_BUFFER
        self.is_departing_roll = not is_arrival
        
        self.x = start_x
        self.y = start_y
        self.altitude = alt if is_arrival else 0.0
        self.speed = speed if is_arrival else 0.0
        self.heading = heading
        
        self.target_altitude = alt
        self.target_speed = speed
        self.target_heading = heading
        
        self.history: List[Tuple[float, float]] = []
        self.history_timer = 0.0
        
        self.climb_rate_fpm = random.uniform(1800, 2500) if self.acft_category == "Medium" else random.uniform(1200, 1800)
        self.accel_rate = 2.0 
        self.turn_rate = 3.0 
        
        self.hold_state = 0 
        self.hold_center = None
        self.hold_inbound_hdg = 0.0
        self.hold_turn_dir = 1 
        self.hold_timer = 0.0
        
        self.out_of_bounds_timer = 0.0

    def direct_to(self, wp_name: str, db):
        self.manual_heading = False
        self.hold_state = 0
        
        for i, wp in enumerate(self.flight_plan):
            name = wp.get("name") if isinstance(wp, dict) else wp
            if name == wp_name:
                self.flight_plan = self.flight_plan[i:]
                return
                
        if self.is_arrival:
            target_rwys = []
            for r_id, _, _, _, _ in db.runways:
                target_rwys.extend(r_id.split('/'))
                
            path = db.find_shortest_path(wp_name, target_rwys)
            if path:
                new_plan = []
                for p in path:
                    wp_dict = {"name": p}
                    if p in db.wp_restrictions:
                        wp_dict.update(db.wp_restrictions[p])
                    new_plan.append(wp_dict)
                self.flight_plan = new_plan
                return
                
        self.flight_plan = [{"name": wp_name}]

    def set_target_heading(self, hdg: int):
        self.target_heading = float(hdg % 360)
        self.manual_heading = True
        self.hold_state = 0
        
    def set_target_speed(self, spd: int):
        self.target_speed = max(140.0, min(320.0, float(spd)))
        self.manual_speed = True
        
    def set_target_altitude(self, alt: int):
        self.target_altitude = max(0.0, min(45000.0, float(alt)))
        self.manual_altitude = True
        
    def enable_hold(self, direction: str = "right"):
        self.hold_state = 1
        self.manual_heading = True
        self.hold_center = (self.x, self.y)
        self.hold_inbound_hdg = self.heading
        self.hold_turn_dir = 1 if direction == "right" else -1
        self.target_speed = min(self.target_speed, 220)

    def go_around(self):
        self.phase = FlightPhase.ACTIVE
        self.is_arrival = False
        self.manual_heading = True
        self.manual_altitude = True
        self.manual_speed = True
        self.ils_locked = False
        self.target_altitude = 5000
        self.target_speed = 220
        self.target_heading = self.heading
        self.flight_plan = []
        
    def update_physics(self, dt: float):
        if self.phase == FlightPhase.DONE: 
            return
        
        if self.is_departing_roll:
            if self.speed < 160: self.speed += 5.0 * dt
            else:
                self.is_departing_roll = False
                self.altitude = 100
            dist_moved = (self.speed / 3600.0) * dt
            math_angle = math.radians(90 - self.heading)
            self.x += dist_moved * math.cos(math_angle)
            self.y += dist_moved * math.sin(math_angle)
            return

        if self.hold_state > 0:
            self._update_holding(dt)
        else:
            hdg_diff = (self.target_heading - self.heading + 180) % 360 - 180
            if abs(hdg_diff) > 0.5:
                turn_dir = 1 if hdg_diff > 0 else -1
                turn_amount = self.turn_rate * dt
                if abs(hdg_diff) < turn_amount: self.heading = self.target_heading
                else: self.heading = (self.heading + turn_dir * turn_amount) % 360

        is_hard_braking = False
        if abs(self.speed - self.target_speed) > 0.5:
            if self.speed < self.target_speed: self.speed = min(self.speed + self.accel_rate * dt, self.target_speed)
            else: 
                self.speed = max(self.speed - self.accel_rate * dt, self.target_speed)
                if self.speed - self.target_speed > 20: is_hard_braking = True
                
        alt_diff = self.target_altitude - self.altitude
        if abs(alt_diff) > 0.1:
            density = max(0.2, 1.0 - (self.altitude / 45000.0)**1.5)
            actual_climb = self.climb_rate_fpm * density
            
            if alt_diff < 0: 
                climb_step = -(actual_climb * (0.4 if is_hard_braking else 1.2)) / 60.0 * dt 
            else: climb_step = actual_climb / 60.0 * dt

            if abs(alt_diff) <= abs(climb_step): self.altitude = self.target_altitude 
            else: self.altitude += climb_step

        dist_moved = (self.speed / 3600.0) * dt 
        math_angle = math.radians(90 - self.heading)
        self.x += dist_moved * math.cos(math_angle)
        self.y += dist_moved * math.sin(math_angle)

        self.history_timer += dt
        if self.history_timer >= 6.0:  
            self.history.insert(0, (self.x, self.y))
            if len(self.history) > 1000: 
                self.history.pop()
            self.history_timer = 0.0

    def _update_holding(self, dt: float):
        turn_rate = 3.0
        if self.hold_state == 1:
            hdg_diff = (self.hold_inbound_hdg + 180 - self.heading + 180) % 360 - 180
            if abs(hdg_diff) < turn_rate * dt:
                self.heading = (self.hold_inbound_hdg + 180) % 360
                self.hold_state = 2
                self.hold_timer = 0.0
            else: self.heading = (self.heading + self.hold_turn_dir * turn_rate * dt) % 360
        elif self.hold_state == 2:
            self.hold_timer += dt
            if self.hold_timer >= 60.0: self.hold_state = 3
        elif self.hold_state == 3:
            hdg_diff = (self.hold_inbound_hdg - self.heading + 180) % 360 - 180
            if abs(hdg_diff) < turn_rate * dt:
                self.heading = self.hold_inbound_hdg
                self.hold_state = 4
                self.hold_timer = 0.0
            else: self.heading = (self.heading + self.hold_turn_dir * turn_rate * dt) % 360
        elif self.hold_state == 4:
            self.hold_timer += dt
            if self.hold_timer >= 60.0: self.hold_state = 1