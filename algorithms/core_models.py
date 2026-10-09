import math
from enum import IntEnum
from typing import Dict, List, Set, Tuple


class Priority(IntEnum):
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4

    @classmethod
    def from_string(cls, name: str) -> "Priority":
        lookup = {
            "critical": cls.CRITICAL,
            "high": cls.HIGH,
            "normal": cls.NORMAL,
            "low": cls.LOW,
        }
        return lookup.get(name.strip().lower(), cls.NORMAL)


class Stop:
    def __init__(
        self,
        id: int,
        name: str,
        lat: float,
        lng: float,
        demand: float = 0.0,
        time_window: Tuple[float, float] = (0.0, 480.0),
        service_time: float = 10.0,
        priority: Priority = Priority.NORMAL,
        is_depot: bool = False,
    ):
        self.id = id
        self.name = name
        self.lat = lat
        self.lng = lng
        self.demand = float(demand)
        self.time_window = (float(time_window[0]), float(time_window[1]))
        self.service_time = float(service_time)
        self.priority = priority if isinstance(priority, Priority) else Priority(priority)
        self.is_depot = is_depot

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "demand": self.demand,
            "time_window": list(self.time_window),
            "service_time": self.service_time,
            "priority": self.priority.name,
            "priority_value": int(self.priority),
            "is_depot": self.is_depot,
        }


class Vehicle:
    def __init__(self, id: int = 1, capacity: float = 500.0, speed_kmh: float = 30.0):
        self.id = id
        self.capacity = float(capacity)
        self.speed_kmh = float(speed_kmh)

    def check_load(self, stops: List[Stop]) -> bool:
        total_load = sum(s.demand for s in stops if not s.is_depot)
        return total_load <= self.capacity

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "capacity": self.capacity,
            "speed_kmh": self.speed_kmh,
        }


def haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculates great-circle distance between two points in kilometers."""
    R = 6371.0  # Earth radius in kilometers
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (
        math.sin(dlat / 2.0) ** 2
        + math.cos(math.radians(lat1))
        * math.cos(math.radians(lat2))
        * math.sin(dlng / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return round(R * c, 3)


class DistanceMatrix:
    def __init__(self, stops: List[Stop]):
        self.stops = stops
        self.stop_map: Dict[int, Stop] = {s.id: s for s in stops}
        self.closed_edges: Set[Tuple[int, int]] = set()
        self.matrix: Dict[Tuple[int, int], float] = {}
        self._build_matrix()

    def _build_matrix(self):
        for s1 in self.stops:
            for s2 in self.stops:
                if s1.id == s2.id:
                    self.matrix[(s1.id, s2.id)] = 0.0
                else:
                    dist = haversine_distance_km(s1.lat, s1.lng, s2.lat, s2.lng)
                    self.matrix[(s1.id, s2.id)] = dist

    def is_edge_closed(self, u: int, v: int) -> bool:
        return (u, v) in self.closed_edges or (v, u) in self.closed_edges

    def close_road(self, u: int, v: int):
        self.closed_edges.add((u, v))
        self.closed_edges.add((v, u))

    def open_road(self, u: int, v: int):
        self.closed_edges.discard((u, v))
        self.closed_edges.discard((v, u))

    def get_closed_edges_list(self) -> List[List[int]]:
        seen = set()
        result = []
        for u, v in self.closed_edges:
            edge = tuple(sorted((u, v)))
            if edge not in seen:
                seen.add(edge)
                result.append([edge[0], edge[1]])
        return result

    def get_distance(self, u: int, v: int) -> float:
        if self.is_edge_closed(u, v):
            return 999999.0  # Heavy penalty for blocked road
        return self.matrix.get((u, v), 999999.0)

    def get_travel_time_minutes(self, u: int, v: int, speed_kmh: float = 30.0) -> float:
        dist = self.get_distance(u, v)
        if dist >= 999999.0:
            return 999999.0
        return (dist / speed_kmh) * 60.0
