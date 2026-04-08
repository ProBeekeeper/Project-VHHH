import math
from atc_aircraft import Aircraft, FlightPhase

class ATCConflictLogic:
    def __init__(self, game_manager):
        self.gm = game_manager

    def check_separations(self):
        self.gm.conflicts.clear()
        self.gm.stca_alerts.clear()
        self.gm.wake_alerts.clear()
        
        active = [a for a in self.gm.aircraft_list if a.phase == FlightPhase.ACTIVE and a.altitude >= 100]
        n = len(active)
        
        for i in range(n):
            for j in range(i + 1, n):
                a, b = active[i], active[j]
                
                dx, dy = a.x - b.x, a.y - b.y
                dist_nm = math.hypot(dx, dy)
                alt_diff_ft = abs(a.altitude - b.altitude)
                
                #基本雷達隔離檢查
                if dist_nm < 3.0 and alt_diff_ft < 1000:
                    self.gm.conflicts.add(tuple(sorted([a.callsign, b.callsign])))
                
                #尾流亂流警告
                if b.altitude <= a.altitude + 300 and b.altitude >= a.altitude - 2000:
                    dot_a = math.cos(math.radians(90 - a.heading)) * (-dx) + math.sin(math.radians(90 - a.heading)) * (-dy)
                    if dot_a > 0: 
                        req_dist = 5.0 if a.acft_category == "Heavy" and b.acft_category != "Heavy" else 4.0 if a.acft_category == "Heavy" else 3.0
                        if dist_nm < req_dist: self.gm.wake_alerts.add((a.callsign, b.callsign))
                elif a.altitude <= b.altitude + 300 and a.altitude >= b.altitude - 2000:
                    dot_b = math.cos(math.radians(90 - b.heading)) * dx + math.sin(math.radians(90 - b.heading)) * dy
                    if dot_b > 0: 
                        req_dist = 5.0 if b.acft_category == "Heavy" and a.acft_category != "Heavy" else 4.0 if b.acft_category == "Heavy" else 3.0
                        if dist_nm < req_dist: self.gm.wake_alerts.add((b.callsign, a.callsign))
                
                #STCA
                vx_a = (a.speed / 3600.0) * math.cos(math.radians(90 - a.heading))
                vy_a = (a.speed / 3600.0) * math.sin(math.radians(90 - a.heading))
                vx_b = (b.speed / 3600.0) * math.cos(math.radians(90 - b.heading))
                vy_b = (b.speed / 3600.0) * math.sin(math.radians(90 - b.heading))
                
                dvx, dvy = vx_a - vx_b, vy_a - vy_b
                
                A = dvx**2 + dvy**2
                B = 2 * (dx * dvx + dy * dvy)
                C = dx**2 + dy**2 - 3.0**2 
                
                if A > 0:
                    delta = B**2 - 4 * A * C
                    if delta > 0:
                        t1 = (-B - math.sqrt(delta)) / (2 * A)
                        t2 = (-B + math.sqrt(delta)) / (2 * A)
                        
                        if t2 >= 0 and t1 <= 120:
                            t_conflict = max(0.0, t1) 
                            pred_alt_a = self._get_predicted_alt(a, t_conflict)
                            pred_alt_b = self._get_predicted_alt(b, t_conflict)
                            
                            if abs(pred_alt_a - pred_alt_b) < 1000:
                                self.gm.stca_alerts.add(tuple(sorted([a.callsign, b.callsign])))

    def _get_predicted_alt(self, acft: Aircraft, t_sec: float) -> float:
        diff = acft.target_altitude - acft.altitude
        if abs(diff) < 10: return acft.altitude
        density = max(0.2, 1.0 - (acft.altitude / 45000.0)**1.5)
        rate_sec = (acft.climb_rate_fpm * density) / 60.0
        if diff > 0: return min(acft.target_altitude, acft.altitude + rate_sec * t_sec)
        else: return max(acft.target_altitude, acft.altitude - (rate_sec * 1.2) * t_sec)