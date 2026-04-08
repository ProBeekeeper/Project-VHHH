import math

class GeoConverter:
    def __init__(self, center_lat: float, center_lon: float):
        self.center_lat = center_lat
        self.center_lon = center_lon
        self.lat_to_nm = 60.0
        self.lon_to_nm = 60.0 * math.cos(math.radians(center_lat))

    def to_xy(self, lat: float, lon: float) -> tuple[float, float]:
        dy = (lat - self.center_lat) * self.lat_to_nm
        dx = (lon - self.center_lon) * self.lon_to_nm
        return dx, dy

class SpatialHashGrid:
    def __init__(self, cell_size: float):
        self.cell_size = cell_size
        self.grid: dict[tuple[int, int], list] = {}

    def _get_cell_coords(self, x: float, y: float) -> tuple[int, int]:
        return (int(x // self.cell_size), int(y // self.cell_size))

    def insert(self, obj, x: float, y: float):
        cell = self._get_cell_coords(x, y)
        if cell not in self.grid:
            self.grid[cell] = []
        self.grid[cell].append(obj)

    def get_nearby(self, x: float, y: float, radius: float) -> list:
        nearby_objects = []
        min_cell = self._get_cell_coords(x - radius, y - radius)
        max_cell = self._get_cell_coords(x + radius, y + radius)

        for cx in range(min_cell[0], max_cell[0] + 1):
            for cy in range(min_cell[1], max_cell[1] + 1):
                cell = (cx, cy)
                if cell in self.grid:
                    nearby_objects.extend(self.grid[cell])
                    
        return nearby_objects