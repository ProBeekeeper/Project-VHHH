import arcade
import math
import time
import os
from atc_constants import *
from atc_aircraft import FlightPhase
from atc_game_manager import ATCGameManager


from atc_ui_panel import ATCUIPanel
from atc_renderer import ATCRenderer

class ATCRadarEngine(arcade.Window):
    def __init__(self, game_manager):
        super().__init__(1200, 900, "Project VHHH", resizable=True, antialiasing=True)
        self.game_manager = game_manager
        self.db = game_manager.db 
        self.background_color = (10, 15, 20) 
        
        self.world_camera = arcade.camera.Camera2D()
        self.gui_camera = arcade.camera.Camera2D()
        
        self.is_loading = True
        self.load_step = 0
        self.total_load_steps = 11  
        
        self.selected_aircraft = None
        self.is_dragging_heading = False
        self.drag_start_time = 0.0 

        self.renderer = ATCRenderer(self)
        self.ui_panel = ATCUIPanel(self)
        
        self.pending_readbacks = {}
        
        self.tcas_playing = False
        self.tcas_player = None
        
        try: 
            self.tcas_sound = arcade.Sound(os.path.join(ASSETS_DIR, "tcas alert.mp3"))
        except Exception as e: 
            print(f"[Warning] 無法載入 TCAS 音效: {e}")
            self.tcas_sound = None
            
        try:
            self.handin_sound = arcade.Sound(os.path.join(ASSETS_DIR, "Hand in.mp3"))
        except Exception as e:
            print(f"[Warning] 無法載入 Hand in 音效: {e}")
            self.handin_sound = None

    def setup(self):
        pass

    def _async_load_step(self):
        if self.load_step == 0:
            self.renderer.build_ui_cache()
        else:
            self.renderer.build_one_lod_step(self.load_step - 1, steps=10)
            
        self.load_step += 1
        if self.load_step >= self.total_load_steps:
            self.is_loading = False

    def on_text(self, text):
        if self.is_loading or self.ui_panel.show_settings: return 
        if self.ui_panel.cli_active and text.isprintable(): self.ui_panel.cli_text += text.upper()

    def on_key_press(self, key, modifiers):
        if self.is_loading: return
        if self.ui_panel.on_key_press(key, modifiers): return
            
        if key == arcade.key.SPACE: self.game_manager.is_paused = not self.game_manager.is_paused
        elif key == arcade.key.KEY_1: self.game_manager.time_scale = 1.0
        elif key == arcade.key.KEY_2: self.game_manager.time_scale = 2.0
        elif key == arcade.key.KEY_3: self.game_manager.time_scale = 3.0
        elif key == arcade.key.KEY_4: self.game_manager.time_scale = 4.0
        elif key == arcade.key.KEY_5: self.game_manager.time_scale = 5.0
        elif key in [arcade.key.KEY_0, arcade.key.NUM_0]: self.game_manager.time_scale = 20.0 

    def on_mouse_press(self, x, y, button, modifiers):
        if self.is_loading: return
        if self.ui_panel.on_mouse_press(x, y, button): return

        hit_any = False
        for acft in self.game_manager.aircraft_list:
            if acft.phase in [FlightPhase.SPAWN_BUFFER, FlightPhase.HANDOFF, FlightPhase.LANDING]: continue 
            sp = self.world_camera.project((acft.x * BASE_SCALE, acft.y * BASE_SCALE))
            if sp and math.hypot(sp.x - x, sp.y - y) < 25:
                if not acft.is_accepted:
                    acft.is_accepted = True
                    self.game_manager.add_comm("ATC", f"{acft.callsign}, radar contact.")
                self.selected_aircraft = acft
                hit_any = True
                self.is_dragging_heading = True
                self.drag_start_time = time.time()
                break
                
        if not hit_any and x < self.width - 320: 
            self.selected_aircraft = None
            self.is_dragging_heading = False

    def on_mouse_release(self, x, y, button, modifiers):
        if self.is_loading: return
        if self.ui_panel.on_mouse_release(x, y, button): return

        if self.selected_aircraft and self.is_dragging_heading:
            if time.time() - self.drag_start_time >= 0.2:
                acft = self.selected_aircraft
                nearest_wp = None
                min_dist = 35 
                for wp_name, wp_data in self.db.beacons.items():
                    if wp_data.get("type") == "runway": continue
                    wp_coords = wp_data['xy']
                    sp_wp = self.world_camera.project((wp_coords[0] * BASE_SCALE, wp_coords[1] * BASE_SCALE))
                    if sp_wp:
                        dist = math.hypot(x - sp_wp.x, y - sp_wp.y)
                        if dist < min_dist:
                            min_dist = dist; nearest_wp = wp_name
                
                if nearest_wp:
                    acft.direct_to(nearest_wp, self.db)
                    self.game_manager.add_comm("ATC", f"{acft.callsign}, cleared direct to {nearest_wp}.")
                    self.pending_readbacks[acft.callsign] = {"time": time.time(), "actions": {"hdg": f"Direct {nearest_wp}"}}
                else:
                    self.pending_readbacks[acft.callsign] = {"time": time.time(), "actions": {"hdg": f"Turning heading {int(acft.target_heading):03d}"}}
        self.is_dragging_heading = False

    def on_mouse_drag(self, x, y, dx, dy, buttons, modifiers):
        if self.is_loading or self.ui_panel.show_settings: return 

        if (buttons & arcade.MOUSE_BUTTON_LEFT) and self.selected_aircraft and self.is_dragging_heading:
            if time.time() - self.drag_start_time < 0.2: return
            acft = self.selected_aircraft
            sp_plane = self.world_camera.project((acft.x * BASE_SCALE, acft.y * BASE_SCALE))
            if sp_plane:
                dx_screen = x - sp_plane.x
                dy_screen = y - sp_plane.y
                target_hdg = (90 - math.degrees(math.atan2(dy_screen, dx_screen))) % 360
                acft.set_target_heading(round(target_hdg))
            return 

        if (buttons & arcade.MOUSE_BUTTON_LEFT) and not self.is_dragging_heading:
            new_x = self.world_camera.position.x - dx / self.world_camera.zoom
            new_y = self.world_camera.position.y - dy / self.world_camera.zoom
            self.world_camera.position = (new_x, new_y)

    def on_mouse_scroll(self, x, y, scroll_x, scroll_y):
        if self.is_loading: return
        if self.ui_panel.on_mouse_scroll(x, y, scroll_y): return
            
        self.world_camera.zoom = max(0.4, min(self.world_camera.zoom * (1 + scroll_y * 0.1), 12.0))

    def on_update(self, delta_time: float):
        if self.is_loading:
            self._async_load_step()
            return
            
        self.game_manager.update_logic(delta_time)
        self.renderer.update_proxies()
        
        current_time = time.time()
        to_remove = []
        for callsign, data in self.pending_readbacks.items():
            is_scroll = data.get("is_scroll", False)
            delay_threshold = 0.8 if is_scroll else 0.2
            time_since_action = current_time - self.ui_panel.last_scroll_time if is_scroll else current_time - data["time"]

            if time_since_action >= delay_threshold:
                msg_parts = list(data["actions"].values())
                msg = ", ".join(msg_parts) + f", {callsign}."
                self.game_manager.add_comm(callsign, msg)
                to_remove.append(callsign)
                
        for callsign in to_remove: del self.pending_readbacks[callsign]

        if self.game_manager.play_handin_sound:
            if self.handin_sound:
                try: self.handin_sound.play()
                except Exception: pass
            self.game_manager.play_handin_sound = False

        is_conflict = len(self.game_manager.conflicts) > 0
        if is_conflict:
            if not self.tcas_playing and self.tcas_sound:
                try:
                    self.tcas_player = self.tcas_sound.play(loop=True)
                    self.tcas_playing = True
                except Exception as e: print(f"TCAS Sound Play Error: {e}")
        else:
            if self.tcas_playing:
                if self.tcas_player:
                    try: 
                        self.tcas_player.pause()
                    except Exception: pass
                self.tcas_playing = False

    def on_draw(self):
        self.clear()
        
        if self.is_loading:
            loading_text = "BUILDING UI CACHE..." if self.load_step == 0 else f"COMPILING GPU GEOMETRY {self.load_step}/10..."
            self.ui_panel.draw_loading_screen(self.load_step, self.total_load_steps, loading_text)
            return
            
        blink = int(time.time() * 4) % 2 == 0
        
        with self.world_camera.activate():
            self.renderer.draw_world(blink)

        with self.gui_camera.activate():
            self.renderer.draw_gui_overlay(blink)
            self.ui_panel.draw()

    def on_resize(self, width: int, height: int):
        super().on_resize(width, height)
        old_pos = self.world_camera.position
        old_zoom = self.world_camera.zoom
        self.world_camera = arcade.camera.Camera2D()
        self.world_camera.position, self.world_camera.zoom = old_pos, old_zoom
        self.gui_camera = arcade.camera.Camera2D()