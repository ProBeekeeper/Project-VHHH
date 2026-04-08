import arcade
import math
from atc_constants import *
from atc_aircraft import Aircraft, FlightPhase

class AircraftUIProxy:
    def __init__(self, acft: Aircraft):
        self.acft = acft
        self.text_label = arcade.Text("", 0, 0, arcade.color.WHITE, 10, font_name=("Consolas", "Courier New"), bold=True, multiline=True, width=150)

class ATCRenderer:

    def __init__(self, engine):
        self.engine = engine
        self.gm = engine.game_manager
        self.db = self.gm.db
        
        self.map_lods = []
        self.cached_major_beacons = []
        self.cached_runways = []
        self.ui_proxies: dict[str, AircraftUIProxy] = {}
        self.text_cache = {}

    def draw_text_fast(self, cache_key, text, x, y, color, font_size, bold=False, anchor_x="left"):
        ix, iy = int(x), int(y)
        if cache_key not in self.text_cache:
            self.text_cache[cache_key] = arcade.Text(str(text), ix, iy, color, font_size, font_name="Consolas", bold=bold, anchor_x=anchor_x)
        else:
            t = self.text_cache[cache_key]
            t.text, t.x, t.y, t.color = str(text), ix, iy, color
        self.text_cache[cache_key].draw()

    def build_ui_cache(self):
        for name, data in self.db.beacons.items():
            if data['type'] in ['runway', 'rnav'] or not data.get('is_major', False): continue
            txt = arcade.Text(name, 0, 0, BEACON_TEAL, font_size=10, font_name=("Consolas", "Courier New"), bold=True)
            self.cached_major_beacons.append((name, data['xy'], txt))

        for name, x, y, heading_rad, length_nm in self.db.runways:
            xy = (x * BASE_SCALE, y * BASE_SCALE)
            parts = name.split('/') 
            txt_1 = arcade.Text(parts[0], 0, 0, arcade.color.CORNFLOWER_BLUE, 10, font_name=("Consolas"), bold=True)
            txt_2 = arcade.Text(parts[1], 0, 0, arcade.color.CORNFLOWER_BLUE, 10, font_name=("Consolas"), bold=True)
            self.cached_runways.append({"name": name, "xy": xy, "hdg": heading_rad, "len": length_nm, "txt_1": txt_1, "txt_2": txt_2, "pts_1":parts[0], "pts_2":parts[1]})

    def build_one_lod_step(self, i, steps=10):
        min_z, max_z = 0.05, 15.0  
        t = i / (steps - 1) if steps > 1 else 1.0
        z = math.exp(math.log(min_z) * (1 - t) + math.log(max_z) * t)
        
        shape_list = arcade.shape_list.ShapeElementList()
        
        coast_w = max(1.0, 0.8 / z)
        fir_w = max(1.0, 1.2 / z)
        route_w = max(1.0, 1.2 / z)
        
        for path in self.db.coastlines:
            pts = [(x * BASE_SCALE, y * BASE_SCALE) for x, y in path]
            if len(pts) >= 2: shape_list.append(arcade.shape_list.create_line_strip(pts, COASTLINE_GRAY, coast_w))
            
        for path in self.db.airspace_boundaries:
            pts = [(x * BASE_SCALE, y * BASE_SCALE) for x, y in path]
            if len(pts) >= 2: shape_list.append(arcade.shape_list.create_line_strip(pts, BOUNDARY_BLUE, fir_w))

        for line in self.db.app_lines: 
            pts = [(x * BASE_SCALE, y * BASE_SCALE) for x, y in line]
            if len(pts) >= 2: shape_list.append(arcade.shape_list.create_line_strip(pts, (0, 180, 0, 180), route_w))
                
        for line in self.db.dep_lines: 
            pts = [(x * BASE_SCALE, y * BASE_SCALE) for x, y in line]
            if len(pts) >= 2: shape_list.append(arcade.shape_list.create_line_strip(pts, (150, 50, 200, 180), route_w))
                
        self.map_lods.append((z, shape_list))

    def draw_ils_glideslope(self, thres_x_scaled, thres_y_scaled, ils_angle_rad):
        current_nm, dash_len, dash_gap = 0.0, 0.4, 0.4 
        line_thickness = max(1.0, 1.2 / self.engine.world_camera.zoom)
        while current_nm < 10.0:
            p1x = thres_x_scaled + math.cos(ils_angle_rad) * current_nm * BASE_SCALE
            p1y = thres_y_scaled + math.sin(ils_angle_rad) * current_nm * BASE_SCALE
            p2x = thres_x_scaled + math.cos(ils_angle_rad) * (current_nm + dash_len) * BASE_SCALE
            p2y = thres_y_scaled + math.sin(ils_angle_rad) * (current_nm + dash_len) * BASE_SCALE
            arcade.draw_line(p1x, p1y, p2x, p2y, arcade.color.CORNFLOWER_BLUE, line_thickness)
            current_nm += (dash_len + dash_gap)

        for dist in [2.5, 5.0, 7.5, 10.0]:
            cx = thres_x_scaled + math.cos(ils_angle_rad) * dist * BASE_SCALE
            cy = thres_y_scaled + math.sin(ils_angle_rad) * dist * BASE_SCALE
            perp = ils_angle_rad + math.pi/2
            cross_len = 0.35 * BASE_SCALE
            p1x = cx + math.cos(perp) * cross_len
            p1y = cy + math.sin(perp) * cross_len
            p2x = cx - math.cos(perp) * cross_len
            p2y = cy - math.sin(perp) * cross_len
            arcade.draw_line(p1x, p1y, p2x, p2y, arcade.color.CORNFLOWER_BLUE, line_thickness)

    def update_proxies(self):
        current_callsigns = {acft.callsign for acft in self.gm.aircraft_list}
        dead_proxies = [cs for cs in self.ui_proxies if cs not in current_callsigns]
        for cs in dead_proxies:
            del self.ui_proxies[cs]
            
        for acft in self.gm.aircraft_list:
            if acft.callsign not in self.ui_proxies:
                self.ui_proxies[acft.callsign] = AircraftUIProxy(acft)

    def draw_world(self, blink):
        if not self.map_lods: return
        
        current_zoom = self.engine.world_camera.zoom
        best_shape_list = self.map_lods[0][1]
        min_diff = float('inf')
        
        for z, shape_list in self.map_lods:
            diff = abs(math.log(z) - math.log(current_zoom))
            if diff < min_diff:
                min_diff = diff
                best_shape_list = shape_list
                
        best_shape_list.draw()

        arr_rwys = self.gm.get_active_runways()["arr"]
        for rw in self.cached_runways:
            cx, cy = rw["xy"]
            hdg = rw["hdg"]
            half_len = (rw["len"] * BASE_SCALE) / 2.0
            p1x, p1y = cx + math.cos(hdg) * half_len, cy + math.sin(hdg) * half_len
            p2x, p2y = cx - math.cos(hdg) * half_len, cy - math.sin(hdg) * half_len
            
            arcade.draw_line(p1x, p1y, p2x, p2y, arcade.color.CORNFLOWER_BLUE, max(1.0, 3.0 / current_zoom))

            if rw["pts_1"] in arr_rwys: self.draw_ils_glideslope(p2x, p2y, hdg + math.pi)
            if rw["pts_2"] in arr_rwys: self.draw_ils_glideslope(p1x, p1y, hdg)
        
        sel_acft = self.engine.selected_aircraft
        
        for acft in self.gm.aircraft_list:
            if acft.phase in [FlightPhase.SPAWN_BUFFER, FlightPhase.HANDOFF, FlightPhase.DONE]: continue
            is_selected = (acft == sel_acft)
            
            pred_dist = acft.speed / 60.0 
            pred_rad = math.radians(90 - acft.heading)
            px = (acft.x + pred_dist * math.cos(pred_rad)) * BASE_SCALE
            py = (acft.y + pred_dist * math.sin(pred_rad)) * BASE_SCALE
            arcade.draw_line(acft.x * BASE_SCALE, acft.y * BASE_SCALE, px, py, RADAR_GREEN, max(1.0, 1.5 / current_zoom))

            if is_selected and self.engine.is_dragging_heading:
                tgt_rad = math.radians(90 - acft.target_heading)
                tx = (acft.x + pred_dist * math.cos(tgt_rad)) * BASE_SCALE
                ty = (acft.y + pred_dist * math.sin(tgt_rad)) * BASE_SCALE
                arcade.draw_line(acft.x * BASE_SCALE, acft.y * BASE_SCALE, tx, ty, HOLLOW_YELLOW, max(1.0, 1.5 / current_zoom))

        if sel_acft and sel_acft.flight_plan and not sel_acft.manual_heading:
            route_pts = [(sel_acft.x * BASE_SCALE, sel_acft.y * BASE_SCALE)]
            for wp_data in sel_acft.flight_plan:
                wp_name = wp_data.get("name") if isinstance(wp_data, dict) else wp_data
                wp = self.db.get_waypoint_coords(wp_name)
                if wp:
                    route_pts.append((wp[0] * BASE_SCALE, wp[1] * BASE_SCALE))
                    arcade.draw_circle_outline(wp[0] * BASE_SCALE, wp[1] * BASE_SCALE, 4.0 / current_zoom, HOLLOW_YELLOW, max(1.0, 1.2 / current_zoom))
            if len(route_pts) > 1:
                arcade.draw_line_strip(route_pts, HOLLOW_YELLOW, max(1.0, 1.2 / current_zoom))

        if blink:
            for a_cs, b_cs in self.gm.stca_alerts:
                a = next((ac for ac in self.gm.aircraft_list if ac.callsign == a_cs), None)
                b = next((bc for bc in self.gm.aircraft_list if bc.callsign == b_cs), None)
                if a and b:
                    x1, y1 = a.x * BASE_SCALE, a.y * BASE_SCALE
                    x2, y2 = b.x * BASE_SCALE, b.y * BASE_SCALE
                    radius_world = 3.0 * BASE_SCALE
                    arcade.draw_circle_outline(x1, y1, radius_world, STCA_YELLOW, max(1.5, 3.0 / current_zoom))
                    arcade.draw_circle_outline(x2, y2, radius_world, STCA_YELLOW, max(1.5, 3.0 / current_zoom))
                    arcade.draw_line(x1, y1, x2, y2, STCA_YELLOW, max(1.0, 2.0 / current_zoom))

        if blink:
            for a_cs, b_cs in self.gm.conflicts:
                a = next((ac for ac in self.gm.aircraft_list if ac.callsign == a_cs), None)
                b = next((bc for bc in self.gm.aircraft_list if bc.callsign == b_cs), None)
                if a and b:
                    x1, y1 = a.x * BASE_SCALE, a.y * BASE_SCALE
                    x2, y2 = b.x * BASE_SCALE, b.y * BASE_SCALE
                    radius_world = 3.0 * BASE_SCALE
                    arcade.draw_circle_outline(x1, y1, radius_world, TCAS_RED, max(1.5, 3.0 / current_zoom))
                    arcade.draw_circle_outline(x2, y2, radius_world, TCAS_RED, max(1.5, 3.0 / current_zoom))
                    arcade.draw_line(x1, y1, x2, y2, TCAS_RED, max(1.0, 3.0 / current_zoom))

    def draw_gui_overlay(self, blink):
        active_cfg = self.gm.active_config
        active_rwys_combined = set(self.gm.get_active_runways()["arr"] + self.gm.get_active_runways()["dep"])
        
        for rw in self.cached_runways:
            cx, cy = rw["xy"]
            hdg = rw["hdg"]
            half_len = (rw["len"] * BASE_SCALE) / 2.0
            
            p1x, p1y = cx + math.cos(hdg) * half_len, cy + math.sin(hdg) * half_len
            p2x, p2y = cx - math.cos(hdg) * half_len, cy - math.sin(hdg) * half_len
            
            offset = 1.5 * BASE_SCALE 
            lbl_07_x, lbl_07_y = p1x + math.cos(hdg) * offset, p1y + math.sin(hdg) * offset
            lbl_25_x, lbl_25_y = p2x - math.cos(hdg) * offset, p2y - math.sin(hdg) * offset
            
            sp_25 = self.engine.world_camera.project((lbl_25_x, lbl_25_y))
            sp_07 = self.engine.world_camera.project((lbl_07_x, lbl_07_y))
            
            if active_cfg == "25" and rw['pts_2'] in active_rwys_combined:
                if sp_25 and 0 < sp_25.x < self.engine.width and 0 < sp_25.y < self.engine.height:
                    self.draw_text_fast(f"rwy_lbl_{rw['pts_2']}", rw['pts_2'], sp_25.x, sp_25.y, arcade.color.LIGHT_GRAY, 12, bold=True, anchor_x="center")
            if active_cfg == "07" and rw['pts_1'] in active_rwys_combined:
                if sp_07 and 0 < sp_07.x < self.engine.width and 0 < sp_07.y < self.engine.height:
                    self.draw_text_fast(f"rwy_lbl_{rw['pts_1']}", rw['pts_1'], sp_07.x, sp_07.y, arcade.color.LIGHT_GRAY, 12, bold=True, anchor_x="center")

        for name, (x, y), text_obj in self.cached_major_beacons:
            sp = self.engine.world_camera.project((x * BASE_SCALE, y * BASE_SCALE))
            if sp:
                sx, sy = int(sp.x), int(sp.y)
                if 0 < sx < self.engine.width and 0 < sy < self.engine.height:
                    arcade.draw_polygon_outline([(sx, sy + 4), (sx - 4, sy - 4), (sx + 4, sy - 4)], (180, 180, 180), 1.0)
                    text_obj.x, text_obj.y = sx + 8, sy - 12
                    text_obj.draw()

        sel_acft = self.engine.selected_aircraft
        if sel_acft and not sel_acft.manual_heading and sel_acft.flight_plan:
            for wp_data in sel_acft.flight_plan:
                if isinstance(wp_data, dict):
                    wp_name, alt, spd = wp_data.get("name"), wp_data.get("alt"), wp_data.get("speed")
                else: wp_name, alt, spd = wp_data, None, None
                    
                wp_coords = self.db.get_waypoint_coords(wp_name)
                if wp_coords and (alt is not None or spd is not None):
                    sp_wp = self.engine.world_camera.project((wp_coords[0] * BASE_SCALE, wp_coords[1] * BASE_SCALE))
                    if sp_wp and 0 < sp_wp.x < self.engine.width and 0 < sp_wp.y < self.engine.height:
                        alt_str = f"F{int(alt/100):03d}" if alt is not None else "---"
                        spd_str = f"{spd}KT" if spd is not None else "---"
                        self.draw_text_fast(f"wp_lbl_{wp_name}", f"{spd_str}\n{alt_str}", sp_wp.x + 8, sp_wp.y - 4, HOLLOW_YELLOW, 10, bold=True)

        for cs, proxy in self.ui_proxies.items():
            acft = proxy.acft
            sp = self.engine.world_camera.project((acft.x * BASE_SCALE, acft.y * BASE_SCALE))
            if not sp: continue
            sx, sy = int(sp.x), int(sp.y)
            
            is_conflict = any(acft.callsign in pair for pair in self.gm.conflicts)
            is_wake_alert = any(acft.callsign in pair for pair in self.gm.wake_alerts)
            is_selected = (self.engine.selected_aircraft == acft)

            if acft.phase in [FlightPhase.SPAWN_BUFFER, FlightPhase.HANDOFF]: lbl_color, body_color = (120, 120, 120, 255), (120, 120, 120, 255)
            else:
                lbl_color = HOLLOW_YELLOW if is_selected else (ARR_LABEL_COLOR if acft.is_arrival else DEP_LABEL_COLOR)
                if not acft.is_accepted: body_color = (0, 150, 255, 255) if blink else (120, 120, 120, 255)
                elif is_conflict and blink: body_color = TCAS_RED 
                else: body_color = HOLLOW_YELLOW if is_selected else RADAR_GREEN                    
            
            if acft.phase != FlightPhase.DONE:
                self.engine.ui_panel._draw_rect_safe(sx, sy, 8, 8, body_color, filled=False, line_width=1.5)

                proxy.text_label.x, proxy.text_label.y = sx + 12, sy + 12
                proxy.text_label.color = lbl_color 
                manual_tag = " M" if (acft.manual_heading or acft.manual_speed or acft.manual_altitude) else ""
                category_tag = " H" if acft.acft_category == "Heavy" else ""
                
                line1 = f"{acft.callsign}{category_tag}{manual_tag}"
                alt_curr, alt_tgt = int(round(acft.altitude / 100)), int(round(acft.target_altitude / 100))
                if alt_curr == alt_tgt: line2 = f"{alt_curr:03d} = {alt_tgt:03d}"
                elif alt_curr < alt_tgt: line2 = f"{alt_curr:03d} ↑ {alt_tgt:03d}"
                else: line2 = f"{alt_curr:03d} ↓ {alt_tgt:03d}"
                line3 = f"{int(acft.speed):03d} {acft.procedure_name}"
                
                if is_wake_alert and blink: line3 += " WAKE"
                proxy.text_label.text = f"{line1}\n{line2}\n{line3}"
                proxy.text_label.draw()

                pts_to_draw = acft.history if is_selected else acft.history[:5]
                for i, (hx, hy) in enumerate(pts_to_draw):
                    hsp = self.engine.world_camera.project((hx * BASE_SCALE, hy * BASE_SCALE))
                    if hsp:
                        alpha = max(20, 255 - int(i * (235 / len(pts_to_draw)) if len(pts_to_draw) > 1 else 0)) if is_selected else max(50, 255 - i * 40)
                        self.engine.ui_panel._draw_rect_safe(hsp.x, hsp.y, 2, 2, (0, 220, 0, alpha), filled=True)

                if is_selected and self.engine.is_dragging_heading:
                    pred_dist = acft.speed / 60.0 
                    target_pred_rad = math.radians(90 - acft.target_heading)
                    target_pred_sp = self.engine.world_camera.project(((acft.x + pred_dist * math.cos(target_pred_rad)) * BASE_SCALE, 
                                                                       (acft.y + pred_dist * math.sin(target_pred_rad)) * BASE_SCALE))
                    if target_pred_sp:
                        self.draw_text_fast(f"tgt_hdg_{acft.callsign}", f"{round(acft.target_heading):03d}", int(target_pred_sp.x)+5, int(target_pred_sp.y)+5, HOLLOW_YELLOW, 12, bold=True)