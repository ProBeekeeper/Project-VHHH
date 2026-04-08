import math
import random
import time
from typing import Optional
from atc_aircraft import Aircraft, FlightPhase
from atc_database import ATCDatabase
from atc_tts import TTSManager
from atc_fmc_logic import ATCFMCLogic
from atc_conflict_logic import ATCConflictLogic

class ATCGameManager:
    def __init__(self, db: ATCDatabase):
        self.db = db
        self.aircraft_list: list[Aircraft] = []
        
        self.conflicts: set[tuple[str, str]] = set() 
        self.stca_alerts: set[tuple[str, str]] = set() 
        self.wake_alerts: set[tuple[str, str]] = set() 
        
        self.messages: list[tuple[str, str, float]] = [] 
        self.active_config = "07" 
        
        self.total_time = 0.0
        self.spawn_timer = 0.0
        self.spawn_interval = random.uniform(80.0, 150.0) 
        self.spawn_cooldowns: dict[tuple[float, float], float] = {} 
        
        self.first_spawn_triggered = False
        self.time_scale = 1.0
        self.is_paused = False
        
        self.tts_enabled = True 
        self.play_handin_sound = False
        
        airlines_map = {a["icao"]: a["callsign"] for a in self.db.airlines}
        self.tts = TTSManager(airlines_map) 

        self.fmc = ATCFMCLogic(self)
        self.conflict = ATCConflictLogic(self)

    def set_config(self, config: str):
        if self.active_config == config: return
        self.active_config = config
        self.aircraft_list.clear()
        self.conflicts.clear()
        self.stca_alerts.clear()
        self.wake_alerts.clear()
        self.messages.clear()
        self.spawn_timer = 0.0
        self.total_time = 0.0
        self.first_spawn_triggered = False 
        self.add_comm("ATC", f"Information updated. Runways in use {config}.")

    def get_active_runways(self):
        if self.active_config == "07":
            return {"arr": ["07L", "07C"], "dep": ["07R", "07C"]}
        else:
            return {"arr": ["25R", "25C"], "dep": ["25L", "25C"]}

    def add_comm(self, sender: str, msg: str):
        self.messages.append((sender, msg, time.time()))
        if len(self.messages) > 50: self.messages.pop(0)
        if sender != "ATC" and self.tts_enabled: self.tts.speak(msg)

    def trigger_checkin(self, acft: Aircraft):
        if acft.is_arrival:
            templates = self.db.comms_templates.get("arrival_checkin", ["Hong Kong Approach, {callsign} passing FL{alt} descending."])
            msg = random.choice(templates).format(callsign=acft.callsign, alt=int(acft.altitude/100))
        else:
            templates = self.db.comms_templates.get("departure_checkin", ["Hong Kong Departure, {callsign} leaving {alt} for FL{tgt_alt}."])
            msg = random.choice(templates).format(callsign=acft.callsign, alt=int(acft.altitude), tgt_alt=int(acft.target_altitude/100))
        self.add_comm(acft.callsign, msg)

    def rebuild_route(self, acft: Aircraft) -> bool:
        return self.fmc.rebuild_route(acft)

    def is_in_tma(self, x: float, y: float) -> bool:
        if not (self.db.fir_min_x <= x <= self.db.fir_max_x and self.db.fir_min_y <= y <= self.db.fir_max_y): return False
        inside = False
        for poly in self.db.airspace_boundaries:
            n = len(poly)
            p1x, p1y = poly[0]
            for i in range(1, n + 1):
                p2x, p2y = poly[i % n]
                if y > min(p1y, p2y) and y <= max(p1y, p2y) and x <= max(p1x, p2x):
                    if p1y != p2y:
                        xints = (y - p1y) * (p2x - p1x) / (p2y - p1y) + p1x
                        if p1x == p2x or x <= xints: inside = not inside
                p1x, p1y = p2x, p2y
            if inside: return True
        return inside

    def _is_spawn_point_clear(self, x: float, y: float, safe_dist_nm: float = 5.0) -> bool:
        for acft in self.aircraft_list:
            if math.hypot(acft.x - x, acft.y - y) < safe_dist_nm: return False
        return True

    def _get_runway_threshold(self, runway_name: str) -> tuple[Optional[float], Optional[float], Optional[float]]:
        for r_id, cx, cy, hdg_rad, rlen in self.db.runways:
            if runway_name in r_id:
                half_len = rlen / 2.0
                if "07" in runway_name: return cx - math.cos(hdg_rad) * half_len, cy - math.sin(hdg_rad) * half_len, 90 - math.degrees(hdg_rad)
                else: return cx + math.cos(hdg_rad) * half_len, cy + math.sin(hdg_rad) * half_len, (90 - math.degrees(hdg_rad) + 180) % 360
        return None, None, None

    def _generate_flight_profile(self) -> tuple[str, str, str]:
        existing_calls = {a.callsign for a in self.aircraft_list}
        weights = [a.get('weight', 1) for a in self.db.airlines]
        while True:
            airline = random.choices(self.db.airlines, weights=weights, k=1)[0]
            callsign = f"{airline['icao']}{random.randint(100, 999)}"
            if callsign not in existing_calls:
                model = random.choice(airline.get('fleet', ['A320']))
                is_heavy = any(h in model for h in ['A33', 'A35', 'A38', 'B74', 'B77', 'B78'])
                return callsign, "Heavy" if is_heavy else "Medium", model

    def _spawn_arrival(self):
        valid_stars = [s for name, s in self.db.procedures["stars"].items() if self.active_config in s.get("rwy_target", "")]
        if not valid_stars or not self.db.custom_spawns: return

        valid_combinations = []
        for star in valid_stars:
            star_route = star["route"]
            star_wp_names = [wp.get("name") if isinstance(wp, dict) else wp for wp in star_route]
            for spawn in self.db.custom_spawns:
                spawn_route = spawn.get("route", [])
                if not spawn_route: continue
                for i, wp_name in enumerate(star_wp_names):
                    if wp_name in spawn_route:
                        valid_combinations.append({"star": star, "spawn": spawn, "star_idx": i, "spawn_idx": spawn_route.index(wp_name)})
                        break 
                        
        if not valid_combinations: return
            
        random.shuffle(valid_combinations)
        spawn_x, spawn_y = 0.0, 0.0
        selected_combo = None
        
        for combo in valid_combinations:
            spawn_data = combo["spawn"]
            sx, sy = spawn_data["xy"]
            spawn_key = (round(sx, 1), round(sy, 1))
            if spawn_key in self.spawn_cooldowns and (self.total_time - self.spawn_cooldowns[spawn_key]) < 180.0: continue 
            
            if self._is_spawn_point_clear(sx, sy, safe_dist_nm=10.0):
                selected_combo = combo
                spawn_x, spawn_y = sx, sy
                self.spawn_cooldowns[spawn_key] = self.total_time
                break

        if not selected_combo: return 
        
        spawn_data = selected_combo["spawn"]
        star_data = selected_combo["star"]
        spawn_alt = spawn_data.get("alt", 28000) 
        
        final_flight_plan = []
        for wp_name in spawn_data["route"][:selected_combo["spawn_idx"]]:
            wp_dict = {"name": wp_name}
            if wp_name in self.db.wp_restrictions: wp_dict.update(self.db.wp_restrictions[wp_name])
            final_flight_plan.append(wp_dict)
            
        for wp in star_data["route"][selected_combo["star_idx"]:]:
            final_flight_plan.append(wp)
            
        target_rwys = self.get_active_runways()["arr"]
        star_rwy_target = star_data.get("rwy_target", "")
        
        if star_rwy_target in target_rwys: target_rwy = star_rwy_target
        else:
            matching = [r for r in target_rwys if star_rwy_target in r]
            target_rwy = random.choice(matching) if matching else random.choice(target_rwys)
        
        final_flight_plan = [wp for wp in final_flight_plan if not any((wp.get("name") if isinstance(wp, dict) else wp) in r_id for r_id, _, _, _, _ in self.db.runways)]
        final_flight_plan.append({"name": target_rwy, "alt": 0, "speed": 140})
            
        first_wp_name = final_flight_plan[0].get("name") if isinstance(final_flight_plan[0], dict) else final_flight_plan[0]
        coords = self.db.get_waypoint_coords(first_wp_name)
        spawn_angle_rad = math.atan2(coords[1] - spawn_y, coords[0] - spawn_x) if coords else 0.0
        
        callsign, category, acft_type = self._generate_flight_profile()
        acft = Aircraft(callsign, spawn_x, spawn_y, (90 - math.degrees(spawn_angle_rad)) % 360, 280, spawn_alt, 
                        flight_plan=final_flight_plan, is_arrival=True, acft_category=category, acft_type=acft_type, procedure_name=star_data["name"])
        acft.target_altitude = spawn_alt
        self.aircraft_list.append(acft)

    def _spawn_departure(self):
        valid_sids = [s for name, s in self.db.procedures["sids"].items() if self.active_config in s.get("rwy_origin", "")]
        if not valid_sids: return
        sid = random.choice(valid_sids)
        route_list = list(sid["route"])
        if not route_list: return
        
        dep_rwys = self.get_active_runways()["dep"]
        sid_rwy_origin = sid.get("rwy_origin", "")
        
        if sid_rwy_origin in dep_rwys: rwy_origin = sid_rwy_origin
        else:
            matching = [r for r in dep_rwys if sid_rwy_origin in r]
            rwy_origin = random.choice(matching) if matching else random.choice(dep_rwys)
            
        start_wp_data = route_list.pop(0) 
        tx, ty, hdg_deg = self._get_runway_threshold(rwy_origin)
        
        if tx is None or not self._is_spawn_point_clear(tx, ty, safe_dist_nm=5.0): return

        last_sid_wp_data = route_list[-1]
        last_sid_wp_name = last_sid_wp_data.get("name") if isinstance(last_sid_wp_data, dict) else last_sid_wp_data
        
        matching_despawns = [dp for dp in self.db.custom_despawns if dp.get("route") and dp["route"][0] == last_sid_wp_name]
        if matching_despawns:
            chosen_despawn = random.choice(matching_despawns)
            for wp_name in chosen_despawn["route"][1:]:
                wp_dict = {"name": wp_name}
                if wp_name in self.db.wp_restrictions: wp_dict.update(self.db.wp_restrictions[wp_name])
                route_list.append(wp_dict)
        
        callsign, category, acft_type = self._generate_flight_profile()
        acft = Aircraft(callsign, tx, ty, hdg_deg, 0, 0, flight_plan=route_list, is_arrival=False, acft_category=category, acft_type=acft_type, procedure_name=sid["name"])
        acft.target_altitude, acft.target_speed = 20000, 250 
        self.aircraft_list.append(acft)

    def can_handoff(self, acft: Aircraft) -> bool:
        if acft.phase != FlightPhase.ACTIVE: return False
        if not acft.is_arrival: return acft.altitude >= 10000 
        else:
            if acft.ils_locked:
                wp_data = acft.flight_plan[0] if acft.flight_plan else None
                if wp_data:
                    wp_name = wp_data.get("name") if isinstance(wp_data, dict) else wp_data
                    coords = self.db.get_waypoint_coords(wp_name)
                    if coords is not None:
                        dist = math.hypot(acft.x - coords[0], acft.y - coords[1])
                        if dist < 15.0: return True
            return False

    def execute_handoff(self, acft: Aircraft):
        acft.phase = FlightPhase.HANDOFF 
        if acft.is_arrival:
            freq = "118.40" 
            if acft.cleared_ils in ["07C", "25C"]: freq = "118.20"
            elif acft.cleared_ils in ["07L", "25R"]: freq = "118.70"
            
            templates = self.db.comms_templates.get("handoff_tower", ["{callsign}, contact Hong Kong Tower {freq}."])
            msg = random.choice(templates).format(callsign=acft.callsign, freq=freq)
            self.add_comm("ATC", msg)
            replies = self.db.comms_templates.get("readback_tower", ["Tower on {freq}, {callsign}."])
            rep = random.choice(replies).format(callsign=acft.callsign, freq=freq)
            self.add_comm(acft.callsign, rep)
        else:
            hdg = acft.heading
            if 45 <= hdg < 135: freq = "126.50"   
            elif 135 <= hdg < 225: freq = "126.30" 
            else: freq = "127.55"                  
            
            templates = self.db.comms_templates.get("handoff_radar", ["{callsign}, contact Hong Kong Radar {freq}."])
            msg = random.choice(templates).format(callsign=acft.callsign, freq=freq)
            self.add_comm("ATC", msg)
            replies = self.db.comms_templates.get("readback_radar", ["Radar on {freq}, {callsign}."])
            rep = random.choice(replies).format(callsign=acft.callsign, freq=freq)
            self.add_comm(acft.callsign, rep)

    def update_logic(self, dt: float):
        scaled_dt = dt * self.time_scale

        self.total_time += scaled_dt
        
        if not self.first_spawn_triggered and self.total_time >= 10.0:
            if random.random() < 0.6: self._spawn_arrival()
            else: self._spawn_departure()
            self.first_spawn_triggered = True
            self.spawn_timer = 0.0 
            self.spawn_interval = random.uniform(80.0, 150.0)
            
        self.spawn_timer += scaled_dt
        if self.spawn_timer >= self.spawn_interval:
            self.spawn_timer = 0.0
            self.spawn_interval = random.uniform(80.0, 150.0) 
            if random.random() < 0.6: self._spawn_arrival()
            else: self._spawn_departure()

        if self.is_paused: return

        alive_aircrafts = []
        for acft in self.aircraft_list:
            if acft.phase in [FlightPhase.ACTIVE, FlightPhase.HANDOFF]:
                self.fmc.process_aircraft(acft)
                
            acft.update_physics(scaled_dt)
            in_tma = self.is_in_tma(acft.x, acft.y)

            if acft.phase == FlightPhase.SPAWN_BUFFER:
                if acft.is_arrival and in_tma:
                    acft.phase = FlightPhase.ACTIVE
                    acft.is_accepted = False 
                    self.trigger_checkin(acft) 
                    self.play_handin_sound = True 
                elif not acft.is_arrival and acft.altitude >= 2000:
                    acft.phase = FlightPhase.ACTIVE
                    acft.is_accepted = False 
                    self.trigger_checkin(acft) 
                    self.play_handin_sound = True 
            
            if acft.phase == FlightPhase.ACTIVE and not in_tma:
                acft.phase = FlightPhase.HANDOFF

            if acft.phase == FlightPhase.HANDOFF and not in_tma: 
                acft.out_of_bounds_timer += scaled_dt
                if acft.out_of_bounds_timer >= 10.0: acft.phase = FlightPhase.DONE
            else:
                acft.out_of_bounds_timer = 0.0

            if acft.phase == FlightPhase.LANDING and acft.speed <= 40:
                acft.phase = FlightPhase.DONE

            if acft.phase != FlightPhase.DONE: alive_aircrafts.append(acft)
                
        self.aircraft_list = alive_aircrafts
        self.conflict.check_separations()