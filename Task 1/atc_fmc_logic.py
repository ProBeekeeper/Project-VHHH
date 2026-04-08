import math
import random
from atc_constants import *
from atc_aircraft import Aircraft, FlightPhase

class ATCFMCLogic:

    def __init__(self, game_manager):
        self.gm = game_manager
        self.db = game_manager.db

    def process_aircraft(self, acft: Aircraft):
        if acft.phase == FlightPhase.LANDING or acft.is_departing_roll: 
            return
        
        self._check_ils_capture(acft) 
        if acft.ils_locked:
            self._process_ils_tracking(acft)
            return 
            
        if acft.manual_heading and acft.phase == FlightPhase.ACTIVE: 
            return 
            
        if acft.lnav_active and len(acft.flight_plan) > 0:
            self._process_waypoint_navigation(acft)

    def _check_ils_capture(self, acft: Aircraft):
        if not acft.is_arrival or acft.ils_locked or acft.phase == FlightPhase.LANDING: return
        if acft.altitude > 4500: return 
        if not acft.cleared_ils: return 
        
        rwy_coords = self.db.get_waypoint_coords(acft.cleared_ils)
        if not rwy_coords: return
        tx, ty = rwy_coords
        
        rwy_hdg_deg = 0.0
        for r_id, cx, cy, hdg_rad, rlen in self.db.runways:
            parts = r_id.split('/')
            if acft.cleared_ils == parts[0]: rwy_hdg_deg = (90 - math.degrees(hdg_rad)) % 360
            elif acft.cleared_ils == parts[1]: rwy_hdg_deg = (90 - math.degrees(hdg_rad) + 180) % 360

        dist = math.hypot(acft.x - tx, acft.y - ty)
        if dist < 25.0: 
            intercept_angle = abs((acft.heading - rwy_hdg_deg + 180) % 360 - 180)
            rwy_math_rad = math.radians(90 - rwy_hdg_deg)
            ux, uy = math.cos(rwy_math_rad), math.sin(rwy_math_rad)
            dx, dy = acft.x - tx, acft.y - ty
            cross_track = dx * (-uy) + dy * ux
            
            if intercept_angle < 60 and abs(cross_track) < 2.0: 
                acft.ils_locked = True
                acft.manual_heading = False
                acft.flight_plan = [{"name": acft.cleared_ils, "alt": 0, "speed": 140}]
                acft.procedure_name = f"ILS {acft.cleared_ils}"
                self.gm.add_comm("ATC", f"{acft.callsign}, localizer established, cleared ILS approach runway {acft.cleared_ils}.")
                self.gm.add_comm(acft.callsign, f"Cleared ILS runway {acft.cleared_ils}, {acft.callsign}.")

    def _process_ils_tracking(self, acft: Aircraft):
        rwy_coords = self.db.get_waypoint_coords(acft.cleared_ils)
        if not rwy_coords: return
        tx, ty = rwy_coords
        
        rwy_hdg_deg = 0.0
        for r_id, cx, cy, hdg_rad, rlen in self.db.runways:
            parts = r_id.split('/')
            if acft.cleared_ils == parts[0]: rwy_hdg_deg = (90 - math.degrees(hdg_rad)) % 360
            elif acft.cleared_ils == parts[1]: rwy_hdg_deg = (90 - math.degrees(hdg_rad) + 180) % 360
        
        rwy_math_rad = math.radians(90 - rwy_hdg_deg)
        ux, uy = math.cos(rwy_math_rad), math.sin(rwy_math_rad)
        dx, dy = acft.x - tx, acft.y - ty
        
        along_track = -(dx * ux + dy * uy)
        cross_track = dx * (-uy) + dy * ux
        
        correction = max(-30.0, min(30.0, cross_track * 25.0))
        acft.target_heading = (rwy_hdg_deg + correction) % 360
        
        if along_track > 0:
            gs_alt = along_track * 318.0
            if not acft.manual_altitude: acft.target_altitude = min(acft.target_altitude, max(0, gs_alt))
        if not acft.manual_speed: acft.target_speed = min(acft.target_speed, 140)
        
        if along_track < 0.5: 
            acft.flight_plan = []
            acft.phase = FlightPhase.LANDING
            acft.target_speed, acft.target_altitude = 30, 0

    def _process_waypoint_navigation(self, acft: Aircraft):
        required_target_alt = acft.target_altitude
        required_target_spd = acft.target_speed
        cum_dist = 0.0
        prev_x, prev_y = acft.x, acft.y
        
        for i in range(len(acft.flight_plan)):
            wp_data = acft.flight_plan[i]
            wp_name = wp_data.get("name") if isinstance(wp_data, dict) else wp_data
            coords = self.db.get_waypoint_coords(wp_name)
            if not coords:
                tx, ty, hdg = self.gm._get_runway_threshold(wp_name)
                coords = (tx, ty) if tx is not None else None
                
            if coords:
                dist_to_wp = math.hypot(coords[0] - prev_x, coords[1] - prev_y)
                cum_dist += dist_to_wp
                if acft.is_arrival:
                    wp_alt = wp_data.get("alt") if isinstance(wp_data, dict) else None
                    if wp_alt is not None and not acft.manual_altitude:
                        alt_diff = acft.altitude - wp_alt
                        if alt_diff > 0:
                            descent_nm_needed = (acft.speed / 3600.0) * (alt_diff / acft.climb_rate_fpm * 60.0) + 1.0
                            if cum_dist <= descent_nm_needed: required_target_alt = min(required_target_alt, wp_alt)
                                
                    wp_spd = wp_data.get("speed") if isinstance(wp_data, dict) else None
                    if wp_spd is not None and not acft.manual_speed:
                        spd_diff = acft.speed - wp_spd
                        if spd_diff > 0:
                            decel_time = spd_diff / acft.accel_rate
                            avg_spd = (acft.speed + wp_spd) / 2.0
                            decel_nm_needed = (avg_spd / 3600.0) * decel_time + 0.5
                            if cum_dist <= decel_nm_needed: required_target_spd = min(required_target_spd, wp_spd)
                prev_x, prev_y = coords[0], coords[1]
                
        if acft.is_arrival and not acft.manual_speed:
            if acft.ils_locked: required_target_spd = min(required_target_spd, 140)
            elif acft.altitude <= 4000: required_target_spd = min(required_target_spd, 170)
            elif acft.altitude <= 10000: required_target_spd = min(required_target_spd, 220)

        if not acft.manual_altitude: acft.target_altitude = required_target_alt
        if not acft.manual_speed: acft.target_speed = required_target_spd

        immediate_wp_data = acft.flight_plan[0]
        imm_wp_name = immediate_wp_data.get("name") if isinstance(immediate_wp_data, dict) else immediate_wp_data
        imm_coords = self.db.get_waypoint_coords(imm_wp_name)
        if not imm_coords:
            tx, ty, hdg = self.gm._get_runway_threshold(imm_wp_name)
            imm_coords = (tx, ty) if tx is not None else None
            
        if imm_coords:
            dist_to_imm = math.hypot(imm_coords[0] - acft.x, imm_coords[1] - acft.y)
            is_arrival_final = (acft.is_arrival and len(acft.flight_plan) == 1)
            
            if is_arrival_final and dist_to_imm < 2.0:
                if acft.altitude > 3000 or acft.speed > 180:
                    self.gm.add_comm(acft.callsign, f"Going around, {acft.callsign}.")
                    acft.go_around()
                    return

            threshold = 0.5 if is_arrival_final else 1.0
            if len(acft.flight_plan) > 1:
                next_wp_data = acft.flight_plan[1]
                next_wp_name = next_wp_data.get("name") if isinstance(next_wp_data, dict) else next_wp_data
                next_coords = self.db.get_waypoint_coords(next_wp_name)
                if next_coords:
                    trk_in = math.degrees(math.atan2(imm_coords[1] - acft.y, imm_coords[0] - acft.x))
                    trk_out = math.degrees(math.atan2(next_coords[1] - imm_coords[1], next_coords[0] - imm_coords[0]))
                    turn_angle = abs((trk_out - trk_in + 180) % 360 - 180)
                    turn_radius = max(1.0, acft.speed / 180.0) 
                    turn_angle_clamped = min(150.0, turn_angle) 
                    lead_dist = turn_radius * math.tan(math.radians(turn_angle_clamped / 2.0))
                    threshold = max(threshold, lead_dist)

            if dist_to_imm < threshold: 
                acft.flight_plan.pop(0) 
                if acft.is_arrival and len(acft.flight_plan) == 0:
                    acft.phase = FlightPhase.LANDING
                    acft.target_speed, acft.target_altitude = 30, 0
                    acft.manual_heading = False 
            else:
                acft.target_heading = (90 - math.degrees(math.atan2(imm_coords[1] - acft.y, imm_coords[0] - acft.x))) % 360

    def rebuild_route(self, acft: Aircraft) -> bool:
        proc_type = "stars" if acft.is_arrival else "sids"
        valid_procs = [p for p in self.db.procedures[proc_type].values() if p["name"] == acft.procedure_name]
        
        full_route = []
        if valid_procs: full_route = valid_procs[0].get("route", [])

        if not full_route: return self._fallback_routing(acft)

        min_dist = float('inf')
        best_idx = -1
        
        for i, wp in enumerate(full_route):
            wp_name = wp.get("name") if isinstance(wp, dict) else wp
            coords = self.db.get_waypoint_coords(wp_name)
            if coords:
                dist = math.hypot(coords[0] - acft.x, coords[1] - acft.y)
                
                angle_to_wp = (90 - math.degrees(math.atan2(coords[1] - acft.y, coords[0] - acft.x))) % 360
                angle_diff = abs((acft.heading - angle_to_wp + 180) % 360 - 180)
                if angle_diff > 90: dist += 20.0 
                
                if dist < min_dist:
                    min_dist = dist
                    best_idx = i
        
        if best_idx == -1: return self._fallback_routing(acft)

        new_plan = []
        for wp in full_route[best_idx:]:
            wp_name = wp.get("name") if isinstance(wp, dict) else wp
            wp_dict = {"name": wp_name}
            if isinstance(wp, dict):
                if "alt" in wp: wp_dict["alt"] = wp["alt"]
                if "speed" in wp: wp_dict["speed"] = wp["speed"]
            elif wp_name in self.db.wp_restrictions:
                wp_dict.update(self.db.wp_restrictions[wp_name])
            new_plan.append(wp_dict)

        if acft.is_arrival:
            new_plan = [wp for wp in new_plan if not any((wp.get("name") if isinstance(wp, dict) else wp) in r_id for r_id, _, _, _, _ in self.db.runways)]
            if acft.cleared_ils: new_plan.append({"name": acft.cleared_ils, "alt": 0, "speed": 140})
            else:
                star_rwy_target = valid_procs[0].get("rwy_target", "")
                target_rwys = self.gm.get_active_runways()["arr"]
                if star_rwy_target in target_rwys: new_plan.append({"name": star_rwy_target, "alt": 0, "speed": 140})
                else:
                    matching = [r for r in target_rwys if star_rwy_target in r]
                    target_rwy = random.choice(matching) if matching else random.choice(target_rwys)
                    new_plan.append({"name": target_rwy, "alt": 0, "speed": 140})
        else:
            last_wp_name = new_plan[-1].get("name") if isinstance(new_plan[-1], dict) else new_plan[-1]
            matching_despawns = [dp for dp in self.db.custom_despawns if dp.get("route") and dp["route"][0] == last_wp_name]
            if matching_despawns:
                chosen_despawn = random.choice(matching_despawns)
                for wp_name in chosen_despawn["route"][1:]:
                    wp_dict = {"name": wp_name}
                    if wp_name in self.db.wp_restrictions: wp_dict.update(self.db.wp_restrictions[wp_name])
                    new_plan.append(wp_dict)

        acft.flight_plan = new_plan
        acft.manual_heading = False
        first_target = new_plan[0].get("name") if isinstance(new_plan[0], dict) else new_plan[0]
        self.gm.add_comm("ATC", f"{acft.callsign}, resume own navigation, cleared direct {first_target}.")
        return True

    def _fallback_routing(self, acft: Aircraft) -> bool:
        if acft.is_arrival:
            target_rwy = acft.cleared_ils if acft.cleared_ils else random.choice(self.gm.get_active_runways()["arr"])
            coords = self.db.get_waypoint_coords(target_rwy)
            if coords:
                acft.flight_plan = [{"name": target_rwy, "alt": 0, "speed": 140}]
                acft.manual_heading = False
                self.gm.add_comm("ATC", f"{acft.callsign}, proceed direct to runway {target_rwy}.")
                return True
        return False