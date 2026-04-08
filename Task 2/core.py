import math
import random
from dsu import DSU

class GameEngine:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.reset()

    def reset(self):
        self.num_cities = random.randint(6, 8)
        self.cities = []
        margin = 100
        top_margin = 150
        
        for _ in range(self.num_cities):
            valid = False
            while not valid:
                x = random.randint(margin, self.width - margin)
                y = random.randint(top_margin, self.height - margin)
                valid = True
                for cx, cy in self.cities:
                    if math.hypot(x - cx, y - cy) < 100:
                        valid = False
                        break
            self.cities.append((x, y))
            
        self.player_dsu = DSU(self.num_cities)
        self.player_edges = []
        self.player_cost = 0.0
        self.kruskal_edges = []
        self.min_cost = 0.0
        self.is_game_over = False
        self._calculate_kruskal()

    def calculate_distance(self, p1, p2):
        return math.hypot(p1[0] - p2[0], p1[1] - p2[1])

    def _calculate_kruskal(self):
        edges = []
        for i in range(self.num_cities):
            for j in range(i + 1, self.num_cities):
                dist = self.calculate_distance(self.cities[i], self.cities[j])
                edges.append((dist, i, j))
                
        edges.sort(key=lambda x: x[0])
        system_dsu = DSU(self.num_cities)
        
        for dist, u, v in edges:
            if system_dsu.union(u, v):
                self.kruskal_edges.append((u, v))
                self.min_cost += dist
                if len(self.kruskal_edges) == self.num_cities - 1:
                    break

    def connect_cities(self, u, v):
        dist = self.calculate_distance(self.cities[u], self.cities[v])
        success = self.player_dsu.union(u, v)
        if success:
            self.player_edges.append((u, v))
            self.player_cost += dist
            if len(self.player_edges) == self.num_cities - 1:
                self.is_game_over = True
        return success

    def get_clicked_city(self, pos, radius):
        for i, city in enumerate(self.cities):
            if math.hypot(pos[0] - city[0], pos[1] - city[1]) <= radius:
                return i
        return None