import arcade
import time
from atc_constants import *
from atc_aircraft import FlightPhase

class ATCUIPanel:
    def __init__(self, engine):
        self.engine = engine
        self.gm = engine.game_manager
        
        self.cli_active = False
        self.cli_text = ""
        self.show_settings = False
        self.efs_scroll = 0 
        self.show_full_comms = False 
        
        self.mouse_down_action = None
        self.mouse_down_time = 0.0
        self.last_scroll_time = 0.0
        
        self.active_ui_buttons = []
        self.text_cache = {}

    def draw_text_fast(self, cache_key, text, x, y, color, font_size, bold=False, anchor_x="left"):
        ix, iy = int(x), int(y)
        if cache_key not in self.text_cache:
            self.text_cache[cache_key] = arcade.Text(str(text), ix, iy, color, font_size, font_name="Consolas", bold=bold, anchor_x=anchor_x)
        else:
            t = self.text_cache[cache_key]
            t.text, t.x, t.y, t.color = str(text), ix, iy, color
        self.text_cache[cache_key].draw()

    def _draw_rect_safe(self, cx, cy, width, height, color, filled=True, line_width=1):
        hw, hh = width / 2.0, height / 2.0
        pts = [(cx-hw, cy-hh), (cx+hw, cy-hh), (cx+hw, cy+hh), (cx-hw, cy+hh)]
        if filled: arcade.draw_polygon_filled(pts, color)
        else: arcade.draw_polygon_outline(pts, color, line_width)

    def draw_loading_screen(self, load_step, total_load_steps, loading_text):
        cx, cy = self.engine.width / 2, self.engine.height / 2
        self.draw_text_fast("loading_title", "PROJECT VHHH", cx, cy + 60, arcade.color.CYAN, 26, bold=True, anchor_x="center")
        
        bar_w = 400
        bar_h = 20
        progress = min(1.0, load_step / total_load_steps)
        
        self._draw_rect_safe(cx, cy, bar_w, bar_h, arcade.color.DARK_GRAY, filled=False, line_width=2)
        if progress > 0:
            self._draw_rect_safe(cx - (bar_w * (1 - progress))/2, cy, bar_w * progress, bar_h, arcade.color.CYAN, filled=True)
            
        self.draw_text_fast("loading_sub", loading_text, cx, cy - 40, arcade.color.LIGHT_GRAY, 12, anchor_x="center")
        self.draw_text_fast("loading_pct", f"{int(progress * 100)}%", cx, cy - 65, arcade.color.WHITE, 14, bold=True, anchor_x="center")

    def draw(self):
        self.active_ui_buttons.clear()
        self.draw_right_panel()
        self.draw_cli_panel()
        self.draw_settings_panel()
        
        if self.gm.messages and not self.show_settings:
            self._draw_comms_log()
            
        active_count = len([a for a in self.gm.aircraft_list if a.phase == FlightPhase.ACTIVE])
        speed_text = 'PAUSED' if self.gm.is_paused else f'{int(self.gm.time_scale)}x'
        self.draw_text_fast("status_lbl", f"ACFT IN TMA: {active_count} | SPEED: {speed_text}", 20, self.engine.height - 30, RADAR_GREEN, 14, bold=True)
        
        if self.gm.conflicts: 
            self.draw_text_fast("sys_alert", "⚠️ TCAS ⚠️", self.engine.width//2 - 50, self.engine.height - 40, TCAS_RED, 20, bold=True)

    def draw_right_panel(self):
        panel_w = 320 
        panel_x = self.engine.width - panel_w / 2
        divider_y = self.engine.height / 2
        
        self._draw_rect_safe(panel_x, self.engine.height * 0.75, panel_w, self.engine.height / 2, (15, 20, 25, 240), filled=True)
        self._draw_rect_safe(panel_x, self.engine.height * 0.25, panel_w, self.engine.height / 2, (10, 12, 15, 240), filled=True)
        self._draw_rect_safe(panel_x, self.engine.height / 2, panel_w, self.engine.height, (50, 50, 60, 255), filled=False, line_width=2.0)
        arcade.draw_line(self.engine.width - panel_w, divider_y, self.engine.width, divider_y, arcade.color.CYAN, 2)

        start_y = self.engine.height - 140 + self.efs_scroll 
        active_acfts = [a for a in self.gm.aircraft_list if a.phase != FlightPhase.DONE]
        
        for i, acft in enumerate(active_acfts):
            strip_y = start_y - (i * 75) 
            if strip_y > self.engine.height - 100 or strip_y < divider_y + 40: continue
            
            color = ARR_LABEL_COLOR if acft.is_arrival else DEP_LABEL_COLOR
            if self.engine.selected_aircraft == acft: color = HOLLOW_YELLOW
            
            card_cx, card_cy = panel_x, strip_y + 25
            card_w, card_h = panel_w - 30, 65 
            
            self._draw_rect_safe(card_cx, card_cy, card_w, card_h, (25, 30, 35, 255), filled=True)
            self._draw_rect_safe(card_cx, card_cy, card_w, card_h, color if self.engine.selected_aircraft == acft else (60, 65, 70, 255), filled=False, line_width=1.5 if self.engine.selected_aircraft == acft else 1.0)
            self._draw_rect_safe(card_cx - card_w/2 + 3, card_cy, 6, card_h, color, filled=True)
            
            tx_left = self.engine.width - panel_w + 35
            self.draw_text_fast(f"efs_cs_{acft.callsign}", acft.callsign, tx_left, card_cy + 16, color, 14, bold=True)
            self.draw_text_fast(f"efs_type_{acft.callsign}", f"{acft.acft_type}/{acft.acft_category[0]}", tx_left + 80, card_cy + 16, arcade.color.LIGHT_GRAY, 11, bold=True)
            self.draw_text_fast(f"efs_sq_{acft.callsign}", f"SQ:{acft.squawk}", tx_left + 190, card_cy + 16, arcade.color.GRAY, 11)

            next_wp = "HDG"
            if acft.flight_plan:
                fp_0 = acft.flight_plan[0]
                next_wp = fp_0.get("name") if isinstance(fp_0, dict) else str(fp_0)
            self.draw_text_fast(f"efs_proc_{acft.callsign}", f"RTE: {acft.procedure_name[:10]} -> {next_wp}", tx_left, card_cy - 2, arcade.color.WHITE, 11)

            alt_str = f"A: F{int(acft.altitude/100):03d} -> F{int(acft.target_altitude/100):03d}"
            spd_str = f"S: {int(acft.speed):03d} -> {int(acft.target_speed):03d}KT"
            self.draw_text_fast(f"efs_alt_{acft.callsign}", alt_str, tx_left, card_cy - 20, arcade.color.CYAN, 11)
            self.draw_text_fast(f"efs_spd_{acft.callsign}", spd_str, tx_left + 140, card_cy - 20, arcade.color.ORANGE, 11)

        header_h = 60
        header_y = self.engine.height - header_h / 2
        self._draw_rect_safe(panel_x, header_y, panel_w - 4, header_h, (15, 20, 25, 255), filled=True) 
        self.draw_text_fast("efs_title", "FLIGHT PANEL", self.engine.width - panel_w + 15, self.engine.height - 35, arcade.color.CYAN, 16, bold=True)
        
        btn_sys_x, btn_sys_y = self.engine.width - 30, self.engine.height - 25
        self.draw_text_fast("btn_sys_icon", "⚙️", btn_sys_x, btn_sys_y - 10, arcade.color.WHITE, 18, bold=True, anchor_x="center")
        if not self.show_settings:
            self.active_ui_buttons.append((btn_sys_x, btn_sys_y, 30, 30, "open_settings"))

        if not self.engine.selected_aircraft or self.engine.selected_aircraft.phase != FlightPhase.ACTIVE:
            self.draw_text_fast("tac_empty", "NO AIRCRAFT SELECTED", panel_x, divider_y / 2, arcade.color.DIM_GRAY, 18, bold=True, anchor_x="center")
            return

        acft = self.engine.selected_aircraft
        icao, flt_num = acft.callsign[:3], acft.callsign[3:]
        spoken_airline = next((a["callsign"] for a in self.gm.db.airlines if a["icao"] == icao), icao)
        self.draw_text_fast("tac_title", f"CMD: {acft.callsign} ({spoken_airline.upper()} {flt_num})", panel_x, divider_y - 30, arcade.color.CYAN, 15, bold=True, anchor_x="center")

        def draw_vertical_control_group(gx, gy, label, val_str, action_prefix, is_manual):
            self.draw_text_fast(f"lbl_{label}", label, gx, gy + 14, arcade.color.LIGHT_GRAY, 13, anchor_x="center")
            bx1, by1, bw, bh = gx - 65, gy - 5, 28, 28 
            self._draw_rect_safe(bx1, by1, bw, bh, arcade.color.DIM_GRAY, filled=True)
            self.draw_text_fast(f"btn_l_{label}", "<", bx1, by1-8, arcade.color.WHITE, 16, bold=True, anchor_x="center")
            self.active_ui_buttons.append((bx1, by1, bw, bh, f"{action_prefix}_minus"))
            
            val_color = HOLLOW_YELLOW if is_manual else arcade.color.WHITE
            self.draw_text_fast(f"val_{label}", val_str, gx, gy - 12, val_color, 16, bold=True, anchor_x="center")
            
            bx2, by2 = gx + 65, gy - 5
            self._draw_rect_safe(bx2, by2, bw, bh, arcade.color.DIM_GRAY, filled=True)
            self.draw_text_fast(f"btn_r_{label}", ">", bx2, by2-8, arcade.color.WHITE, 16, bold=True, anchor_x="center")
            self.active_ui_buttons.append((bx2, by2, bw, bh, f"{action_prefix}_plus"))

        draw_vertical_control_group(panel_x, divider_y - 80, "HEADING", f"{int(acft.target_heading):03d}", "hdg", acft.manual_heading)
        draw_vertical_control_group(panel_x, divider_y - 145, "SPEED", f"{int(acft.target_speed)}", "spd", acft.manual_speed)
        draw_vertical_control_group(panel_x, divider_y - 210, "ALTITUDE", f"{int(round(acft.target_altitude/100)):03d}", "alt", acft.manual_altitude)

        is_manual = acft.manual_heading
        is_holding = acft.hold_state > 0
        base_text = "APP" if acft.is_arrival else "DEP"

        lnav_color, lnav_text = (arcade.color.GREEN, "HOLDING") if is_holding else ((arcade.color.GREEN, base_text) if not is_manual else (arcade.color.GRAY, base_text))
            
        bx_l, by_l, bw_l, bh_l = panel_x - 65, divider_y - 275, 95, 35
        self._draw_rect_safe(bx_l, by_l, bw_l, bh_l, (50, 50, 50, 255), filled=True)
        self._draw_rect_safe(bx_l, by_l, bw_l, bh_l, lnav_color, filled=False, line_width=2.0)
        self.draw_text_fast("btn_lnav", lnav_text, bx_l, by_l - 6, lnav_color, 14, bold=True, anchor_x="center")
        self.active_ui_buttons.append((bx_l, by_l, bw_l, bh_l, "toggle_lnav"))

        can_handoff = self.gm.can_handoff(acft)
        handoff_border, handoff_text = (arcade.color.ORANGE, arcade.color.ORANGE) if can_handoff else (arcade.color.DIM_GRAY, arcade.color.GRAY)

        bx_h, by_h, bw_h, bh_h = panel_x + 65, divider_y - 275, 95, 35
        self._draw_rect_safe(bx_h, by_h, bw_h, bh_h, (50, 50, 50, 255), filled=True)
        self._draw_rect_safe(bx_h, by_h, bw_h, bh_h, handoff_border, filled=False, line_width=2.0)
        self.draw_text_fast("btn_handoff", "HANDOFF", bx_h, by_h - 6, handoff_text, 14, bold=True, anchor_x="center")
        if can_handoff: self.active_ui_buttons.append((bx_h, by_h, bw_h, bh_h, "execute_handoff"))

        if acft.is_arrival and not acft.ils_locked:
            available_rwys = self.gm.get_active_runways()["arr"]
            ils_w, ils_gap = 75, 90
            start_x = panel_x - (len(available_rwys) - 1) * ils_gap / 2
            for i, r_name in enumerate(available_rwys):
                bx, by, bw, bh = start_x + (i * ils_gap), divider_y - 330, ils_w, 30
                btn_color = (0, 150, 0, 255) if acft.cleared_ils == r_name else (50, 50, 50, 255)
                outline_color = arcade.color.GREEN if acft.cleared_ils == r_name else arcade.color.GRAY
                self._draw_rect_safe(bx, by, bw, bh, btn_color, filled=True)
                self._draw_rect_safe(bx, by, bw, bh, outline_color, filled=False, line_width=1.5)
                self.draw_text_fast(f"btn_ils_{r_name}", f"ILS {r_name}", bx, by - 6, arcade.color.WHITE, 13, bold=True, anchor_x="center")
                self.active_ui_buttons.append((bx, by, bw, bh, f"ils_{r_name}"))

    def draw_cli_panel(self):
        if not self.cli_active: return
        self._draw_rect_safe(150, 20, 280, 30, (30, 30, 30, 200), filled=True) 
        self.draw_text_fast("cli_text", f"> {self.cli_text}_", 20, 14, arcade.color.WHITE, 14, bold=True)

    def _draw_comms_log(self):
        offset_y = 40 if self.cli_active else 0 
        recent = self.gm.messages[-15:] if self.show_full_comms else self.gm.messages[-3:]
        for i, (sender, txt, t) in enumerate(reversed(recent)):
            color = arcade.color.CYAN if sender == "ATC" else arcade.color.LIGHT_GREEN
            self.draw_text_fast(f"comm_{i}", f"[{sender}] {txt}", 20, 20 + i * 20 + offset_y, color, 13, bold=True)

    def draw_settings_panel(self):
        if not self.show_settings: return
        self._draw_rect_safe(self.engine.width//2, self.engine.height//2, self.engine.width, self.engine.height, (0, 0, 0, 200), filled=True)

        cx, cy = self.engine.width // 2, self.engine.height // 2
        mw, mh = 380, 280
        self._draw_rect_safe(cx, cy, mw, mh, (20, 25, 30, 255), filled=True)
        self._draw_rect_safe(cx, cy, mw, mh, arcade.color.CYAN, filled=False, line_width=2)
        self.draw_text_fast("mod_title", "SYSTEM SETTINGS", cx, cy + mh//2 - 30, arcade.color.CYAN, 16, bold=True, anchor_x="center")

        tts_color = arcade.color.GREEN if self.gm.tts_enabled else arcade.color.RED
        tts_txt = "TTS VOICE: ON" if self.gm.tts_enabled else "TTS VOICE: OFF"
        self._draw_rect_safe(cx, cy + 50, 240, 45, (50, 50, 50, 255), filled=True)
        self._draw_rect_safe(cx, cy + 50, 240, 45, tts_color, filled=False, line_width=2)
        self.draw_text_fast("mod_tts", tts_txt, cx, cy + 44, tts_color, 14, bold=True, anchor_x="center")
        self.active_ui_buttons.append((cx, cy + 50, 240, 45, "toggle_tts"))

        btn_07_color = arcade.color.GREEN if self.gm.active_config == "07" else arcade.color.GRAY
        self._draw_rect_safe(cx - 65, cy - 10, 110, 35, (40, 40, 40, 255), filled=True)
        self._draw_rect_safe(cx - 65, cy - 10, 110, 35, btn_07_color, filled=False, line_width=2)
        self.draw_text_fast("mod_cfg_07", "CONFIG: 07", cx - 65, cy - 16, btn_07_color, 12, bold=True, anchor_x="center")
        self.active_ui_buttons.append((cx - 65, cy - 10, 110, 35, "cfg_07"))
        
        btn_25_color = arcade.color.GREEN if self.gm.active_config == "25" else arcade.color.GRAY
        self._draw_rect_safe(cx + 65, cy - 10, 110, 35, (40, 40, 40, 255), filled=True)
        self._draw_rect_safe(cx + 65, cy - 10, 110, 35, btn_25_color, filled=False, line_width=2)
        self.draw_text_fast("mod_cfg_25", "CONFIG: 25", cx + 65, cy - 16, btn_25_color, 12, bold=True, anchor_x="center")
        self.active_ui_buttons.append((cx + 65, cy - 10, 110, 35, "cfg_25"))

        self._draw_rect_safe(cx, cy - 65, 240, 35, (50, 50, 50, 255), filled=True)
        self._draw_rect_safe(cx, cy - 65, 240, 35, arcade.color.RED, filled=False, line_width=2)
        self.draw_text_fast("mod_exit", "EXIT TO DESKTOP", cx, cy - 71, arcade.color.RED, 12, bold=True, anchor_x="center")
        self.active_ui_buttons.append((cx, cy - 65, 240, 35, "exit_game"))

        self._draw_rect_safe(cx, cy - mh//2 + 25, 100, 25, (60, 60, 60, 255), filled=True)
        self._draw_rect_safe(cx, cy - mh//2 + 25, 100, 25, arcade.color.WHITE, filled=False, line_width=1.5)
        self.draw_text_fast("mod_close", "CLOSE", cx, cy - mh//2 + 20, arcade.color.WHITE, 12, bold=True, anchor_x="center")
        self.active_ui_buttons.append((cx, cy - mh//2 + 25, 100, 25, "close_settings"))

    def process_cli(self, command: str):
        parts = command.upper().split()
        if len(parts) < 2: return
        target_callsign = parts[0]
        acft = next((a for a in self.gm.aircraft_list if a.callsign == target_callsign), None)
        if not acft or acft.phase in [FlightPhase.SPAWN_BUFFER, FlightPhase.HANDOFF, FlightPhase.LANDING]: return
        try:
            for i in range(1, len(parts), 2):
                if i+1 >= len(parts): break
                cmd, val = parts[i], int(parts[i+1])
                if cmd == 'H': 
                    acft.target_heading = val
                    acft.manual_heading = True
                elif cmd == 'S': 
                    acft.target_speed = val
                    acft.manual_speed = True
                elif cmd == 'A': 
                    acft.target_altitude = val * 100
                    acft.manual_altitude = True
        except Exception: pass

    def on_mouse_press(self, x, y, button):
        if button != arcade.MOUSE_BUTTON_LEFT: return False

        for bx, by, bw, bh, action in self.active_ui_buttons:
            if abs(x - bx) <= bw/2 and abs(y - by) <= bh/2:
                if action == "open_settings": self.show_settings = True; return True
                elif action == "close_settings": self.show_settings = False; return True
                
                elif action == "toggle_tts": 
                    self.gm.tts_enabled = not self.gm.tts_enabled
                    if not self.gm.tts_enabled:
                        self.gm.tts.stop_immediate()
                    else:
                        self.gm.tts.enable()
                    return True
                    
                elif action == "cfg_07": self.gm.set_config("07"); return True
                elif action == "cfg_25": self.gm.set_config("25"); return True
                elif action == "exit_game": arcade.exit(); return True
                
                if self.show_settings: return True
                
                if self.engine.selected_aircraft:
                    acft = self.engine.selected_aircraft
                    if action == "hdg_minus": 
                        acft.target_heading = (acft.target_heading - 5) % 360
                        acft.manual_heading = True
                    elif action == "hdg_plus": 
                        acft.target_heading = (acft.target_heading + 5) % 360
                        acft.manual_heading = True
                    elif action == "spd_minus": 
                        acft.target_speed = max(140, acft.target_speed - 10)
                        acft.manual_speed = True
                    elif action == "spd_plus": 
                        acft.target_speed = min(320, acft.target_speed + 10)
                        acft.manual_speed = True
                    elif action == "alt_minus": 
                        acft.target_altitude = max(0, acft.target_altitude - 1000)
                        acft.manual_altitude = True
                    elif action == "alt_plus": 
                        acft.target_altitude = min(45000, acft.target_altitude + 1000)
                        acft.manual_altitude = True
                        
                    self.mouse_down_action = action
                    self.mouse_down_time = time.time()
                return True

        if self.show_settings: return True

        if x > self.engine.width - 320 and y > self.engine.height / 2 and y < self.engine.height - 40:
            start_y = self.engine.height - 140 + self.efs_scroll 
            active_acfts = [a for a in self.gm.aircraft_list if a.phase != FlightPhase.DONE]
            for i, acft in enumerate(active_acfts):
                strip_y = start_y - (i * 75)
                if strip_y - 5 <= y <= strip_y + 65 and strip_y >= self.engine.height / 2 + 30:
                    if acft.phase in [FlightPhase.SPAWN_BUFFER, FlightPhase.HANDOFF, FlightPhase.LANDING]:
                        return True
                    self.engine.selected_aircraft = acft
                    self.engine.world_camera.position = (acft.x * BASE_SCALE, acft.y * BASE_SCALE) 
                    if not acft.is_accepted:
                        acft.is_accepted = True
                        self.gm.add_comm("ATC", f"{acft.callsign}, radar contact.")
                    return True
        return False

    def on_mouse_release(self, x, y, button):
        if self.show_settings: return True
        if button == arcade.MOUSE_BUTTON_LEFT and self.mouse_down_action:
            press_duration = time.time() - self.mouse_down_time
            action = self.mouse_down_action
            acft = self.engine.selected_aircraft
            
            if press_duration >= 0.5 and action in ["hdg_plus", "hdg_minus"]:
                direction = "right" if action == "hdg_plus" else "left"
                acft.enable_hold(direction)
                self.gm.add_comm("ATC", f"{acft.callsign}, hold present position, {direction} turns.")
            elif acft:
                if action == "execute_handoff":
                    self.gm.execute_handoff(acft)
                    self.engine.selected_aircraft = None
                elif action.startswith("ils_"):
                    rwy_name = action.split("_")[1]
                    acft.cleared_ils = rwy_name
                    self.gm.add_comm("ATC", f"{acft.callsign}, cleared ILS runway {rwy_name}.")
                    self.gm.rebuild_route(acft)
                elif action == "toggle_lnav": 
                    if acft.manual_heading:
                        success = self.gm.rebuild_route(acft)
                        if not success: acft.manual_heading = True
                    else: acft.manual_heading = True
            
            self.mouse_down_action = None
            return True
        return False

    def on_mouse_scroll(self, x, y, scroll_y):
        if self.show_settings: return True
        if x > self.engine.width - 320 and y > self.engine.height / 2:
            self.efs_scroll += scroll_y * 20
            self.efs_scroll = max(0, min(self.efs_scroll, len(self.gm.aircraft_list) * 75))
            return True

        self.last_scroll_time = time.time()
        
        acft = self.engine.selected_aircraft
        if acft and acft.phase == FlightPhase.ACTIVE:
            if scroll_y > 0: 
                acft.target_altitude = min(45000, acft.target_altitude + 1000)
            elif scroll_y < 0: 
                acft.target_altitude = max(0, acft.target_altitude - 1000)
            
            acft.manual_altitude = True
            
            if acft.callsign not in self.engine.pending_readbacks: 
                self.engine.pending_readbacks[acft.callsign] = {"time": time.time(), "actions": {}}
                
            p_data = self.engine.pending_readbacks[acft.callsign]
            p_data["is_scroll"] = True
            p_data["time"] = time.time() 
            dir_str = "Climbing" if acft.target_altitude > acft.altitude else "Descending"
            p_data["actions"]["alt"] = f"{dir_str} FL{int(round(acft.target_altitude/100)):03d}"
            return True
            
        return False

    def on_key_press(self, key, modifiers):
        if self.show_settings: return False
        if key == arcade.key.ENTER: 
            if self.cli_active and self.cli_text: 
                self.process_cli(self.cli_text)
            self.cli_active = not self.cli_active
            self.cli_text = ""
            return True
        if self.cli_active:
            if key == arcade.key.BACKSPACE: self.cli_text = self.cli_text[:-1]
            return True
        return False