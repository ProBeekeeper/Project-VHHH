import os
import json
import math
import heapq
from typing import Optional, Tuple
from atc_utils import GeoConverter
from atc_constants import DATA_DIR

class ATCDatabase:
    def __init__(self):
        self.geo = GeoConverter(22.308, 113.918)
        self.coastlines = []
        self.airspace_boundaries = [] 
        self.runways = [] 
        self.beacons = {}
        self.procedures = {"stars": {}, "sids": {}}
        self.airlines = []
        self.comms_templates = {}
        
        self.custom_spawns = [] 
        self.custom_despawns = [] 
        self.app_lines = [] 
        self.dep_lines = []
        self.wp_restrictions = {}
        
        self.nav_graph = {}
        
        self.fir_min_x, self.fir_max_x = float('inf'), float('-inf')
        self.fir_min_y, self.fir_max_y = float('inf'), float('-inf')

    def load_json(self, filename: str) -> Optional[dict]:
        base_path = os.path.join(DATA_DIR, filename)
        names_to_try = [base_path, f"{base_path}.json", base_path.replace('.json', '')]
        for name in set(names_to_try):
            if os.path.exists(name):
                try:
                    with open(name, 'r', encoding='utf-8') as f: return json.load(f)
                except Exception: return None
        return None

    def initialize(self):
        print("Loading Database...")
        
        airline_data = self.load_json('VHHH_airlines.json') or self.load_json('airlines.json')
        if airline_data and 'airlines' in airline_data: self.airlines = airline_data['airlines']
        else: self.airlines = [{"icao": "CPA", "callsign": "CATHAY", "weight": 100, "fleet": ["A359"]}]

        comms_data = self.load_json('VHHH_atc_comms.json')
        if comms_data: self.comms_templates = comms_data

        target_display_wps = {"ABBEY", "GAMBA", "MAGOG", "SABNO", "ADLAD", "HOCKY", "MALKA", "SIERA", "AGOMU", "IDOSI", "MANGO", "SIKOU", "AKEKU", "MAPLE", "SILVA", "ALLEY", "KAPLI", "MEBKI", "SKATE", "BAKER", "LARIT", "MEPUT", "SONNY", "BEKOL", "LAXET", "MURRY", "SOUSA", "BESDA", "LEKEN", "MUSEL", "SUKER", "BETTY", "LELIM", "MYWAY", "SURFA", "CANTO", "LIMES", "NOMAN", "TEDUR", "CARSO", "LIMSU", "NUDPI", "TOFEE", "COMBI", "LUDLA", "OSUMO", "UNTUL", "CONGA", "PECAN", "XEMEK", "CYBER", "POVAM", "DAKTO", "RIVMI", "DALOL", "ROCCA", "DOTMI", "DUMEP", "TD", "SMT"}

        nav_data = self.load_json('VHHH_NAV.json')
        if nav_data:
            c = nav_data.get('metadata', {}).get('center', {})
            if c: self.geo = GeoConverter(c['lat'], c['lon'])
            calibrated_runways = [
              { "id": "07L/25R", "lat": 22.326039, "lon": 113.898861, "hdg": 70.93, "len": 2.27 },
              { "id": "07C/25C", "lat": 22.31614, "lon": 113.913684, "hdg": 71.16, "len": 2.32 },
              { "id": "07R/25L", "lat": 22.301917, "lon": 113.915918, "hdg": 71.44, "len": 2.19 }
            ]
            for rw in calibrated_runways:
                r_id, lat, lon, hdg_deg, length = rw['id'], rw['lat'], rw['lon'], rw['hdg'], rw['len']
                cx, cy = self.geo.to_xy(lat, lon)
                hdg_rad = math.radians(90 - hdg_deg)
                half_len = length / 2.0
                self.runways.append((r_id, cx, cy, hdg_rad, length))
                
                parts = r_id.split('/')
                tx1, ty1 = cx - math.cos(hdg_rad) * half_len, cy - math.sin(hdg_rad) * half_len
                self.beacons[parts[0]] = {"xy": (tx1, ty1), "type": "runway", "is_major": True}
                tx2, ty2 = cx + math.cos(hdg_rad) * half_len, cy + math.sin(hdg_rad) * half_len
                self.beacons[parts[1]] = {"xy": (tx2, ty2), "type": "runway", "is_major": True}

            for b_name, b_data in nav_data.get('waypoints', {}).items():
                self.beacons[b_name] = {"xy": self.geo.to_xy(b_data['lat'], b_data['lon']), "type": b_data.get('type', 'standard'), "is_major": (b_name in target_display_wps)}

        proc_data = self.load_json('VHHH_Procedures.json')
        if proc_data:
            for star in proc_data.get('procedures', {}).get('stars', []): 
                self.procedures["stars"][star["name"]] = star
                for wp in star["route"]:
                    if isinstance(wp, dict):
                        name = wp.get("name")
                        if name not in self.wp_restrictions: self.wp_restrictions[name] = {}
                        if "alt" in wp: self.wp_restrictions[name]["alt"] = wp["alt"]
                        if "speed" in wp: self.wp_restrictions[name]["speed"] = wp["speed"]

            for sid in proc_data.get('procedures', {}).get('sids', []): 
                self.procedures["sids"][sid["name"]] = sid
                for wp in sid["route"]:
                    if isinstance(wp, dict):
                        name = wp.get("name")
                        if name not in self.wp_restrictions: self.wp_restrictions[name] = {}
                        if "alt" in wp: self.wp_restrictions[name]["alt"] = wp["alt"]
                        if "speed" in wp: self.wp_restrictions[name]["speed"] = wp["speed"]

        fir_data = self.load_json('VHHH_FIR.json')
        if fir_data:
            for path in fir_data:
                xy_path = [self.geo.to_xy(p['lat'], p['lon']) for p in path]
                self.airspace_boundaries.append(xy_path)
                for x, y in xy_path:
                    self.fir_min_x, self.fir_max_x = min(self.fir_min_x, x), max(self.fir_max_x, x)
                    self.fir_min_y, self.fir_max_y = min(self.fir_min_y, y), max(self.fir_max_y, y)

        geo_data = self.load_json('VHHH_GEO.json')
        if geo_data:
            for path in geo_data.get('geography', {}).get('coastlines', []):
                self.coastlines.append([self.geo.to_xy(p['lat'], p['lon']) for p in path])

        spawn_data = self.load_json('VHHH_Spawn.json')
        if spawn_data and 'custom_spawns' in spawn_data:
            for sp in spawn_data['custom_spawns']:
                xy = self.geo.to_xy(sp['lat'], sp['lon'])
                self.custom_spawns.append({"xy": xy, "route": sp.get("route", []), "alt": sp.get("alt", 28000)})

        despawn_data = self.load_json('VHHH_despawn.json')
        if despawn_data:
            if 'fictional_waypoints' in despawn_data:
                for f_name, f_coords in despawn_data['fictional_waypoints'].items():
                    xy = self.geo.to_xy(f_coords['lat'], f_coords['lon'])
                    self.beacons[f_name] = {"xy": xy, "type": "rnav", "is_major": False}
            if 'custom_despawns' in despawn_data:
                self.custom_despawns = despawn_data['custom_despawns']

        app_line_data = self.load_json('VHHH_APP_Line.json')
        if app_line_data and 'background_routes' in app_line_data:
            for line in app_line_data['background_routes']:
                self.app_lines.append([self.geo.to_xy(pt['lat'], pt['lon']) for pt in line])

        dep_line_data = self.load_json('VHHH_DEP_Line.json')
        if dep_line_data and 'background_routes' in dep_line_data:
            for line in dep_line_data['background_routes']:
                self.dep_lines.append([self.geo.to_xy(pt['lat'], pt['lon']) for pt in line])

        self.build_nav_graph()

    def build_nav_graph(self):
        self.nav_graph = {}
        for star in self.procedures["stars"].values():
            route = star["route"]
            for i in range(len(route) - 1):
                n1 = route[i].get("name") if isinstance(route[i], dict) else route[i]
                n2 = route[i+1].get("name") if isinstance(route[i+1], dict) else route[i+1]
                c1 = self.get_waypoint_coords(n1)
                c2 = self.get_waypoint_coords(n2)
                if c1 and c2:
                    dist = math.hypot(c1[0]-c2[0], c1[1]-c2[1])
                    if n1 not in self.nav_graph: self.nav_graph[n1] = {}
                    self.nav_graph[n1][n2] = dist
                    
        for node_name, data in self.beacons.items():
            if data.get("type") == "runway": continue
            for r_name, r_data in self.beacons.items():
                if r_data.get("type") == "runway":
                    dist = math.hypot(data["xy"][0]-r_data["xy"][0], data["xy"][1]-r_data["xy"][1])
                    if dist < 30.0:
                        if node_name not in self.nav_graph: self.nav_graph[node_name] = {}
                        self.nav_graph[node_name][r_name] = dist

    def find_shortest_path(self, start_node: str, target_nodes: list) -> Optional[list]:
        queue = [(0, start_node, [])]
        visited = set()
        while queue:
            cost, node, path = heapq.heappop(queue)
            if node in visited: continue
            visited.add(node)
            path = path + [node]
            
            if node in target_nodes: return path
                
            for neighbor, weight in self.nav_graph.get(node, {}).items():
                if neighbor not in visited:
                    heapq.heappush(queue, (cost + weight, neighbor, path))
        return None

    def get_waypoint_coords(self, wp_name: str) -> Optional[Tuple[float, float]]:
        if wp_name in self.beacons: return self.beacons[wp_name]['xy']
        return None