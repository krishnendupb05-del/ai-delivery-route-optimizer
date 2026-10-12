import json
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class StopModel:
    id: int
    name: str
    lat: float
    lng: float
    demand: float = 0.0
    tw_start: float = 0.0
    tw_end: float = 480.0
    service_time: float = 10.0
    priority: str = "NORMAL"
    is_depot: bool = False

    def validate(self) -> Tuple[bool, Optional[str]]:
        if not (-90.0 <= self.lat <= 90.0):
            return False, f"Latitude {self.lat} must be between -90 and 90 degrees."
        if not (-180.0 <= self.lng <= 180.0):
            return False, f"Longitude {self.lng} must be between -180 and 180 degrees."
        if self.demand < 0:
            return False, f"Demand ({self.demand} kg) cannot be negative."
        if self.tw_start < 0 or self.tw_end < 0:
            return False, "Time window boundaries cannot be negative."
        if self.tw_start > self.tw_end:
            return False, f"Time window start ({self.tw_start}) cannot exceed end ({self.tw_end})."
        if self.service_time < 0:
            return False, "Service time cannot be negative."
        return True, None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "demand": self.demand,
            "tw_start": self.tw_start,
            "tw_end": self.tw_end,
            "time_window": [self.tw_start, self.tw_end],
            "service_time": self.service_time,
            "priority": self.priority.upper(),
            "is_depot": bool(self.is_depot),
        }

    @classmethod
    def from_row(cls, row) -> "StopModel":
        return cls(
            id=row["id"],
            name=row["name"],
            lat=float(row["lat"]),
            lng=float(row["lng"]),
            demand=float(row["demand"]),
            tw_start=float(row["tw_start"]),
            tw_end=float(row["tw_end"]),
            service_time=float(row["service_time"]),
            priority=row["priority"].upper(),
            is_depot=bool(row["is_depot"]),
        )


@dataclass
class VehicleConfigModel:
    id: int = 1
    name: str = "Primary Electric Delivery Van"
    capacity: float = 400.0
    speed_kmh: float = 35.0
    depot_stop_id: int = 0
    max_shift_duration_min: float = 480.0
    is_active: bool = True

    def validate_capacity(self, total_demand: float) -> Tuple[bool, Optional[str]]:
        if total_demand > self.capacity:
            excess = round(total_demand - self.capacity, 2)
            return (
                False,
                f"Capacity overload: Total stops demand ({total_demand:.1f} kg) exceeds "
                f"vehicle capacity ({self.capacity:.1f} kg) by {excess:.1f} kg.",
            )
        return True, None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_row(cls, row) -> "VehicleConfigModel":
        return cls(
            id=row["id"],
            name=row["name"],
            capacity=float(row["capacity"]),
            speed_kmh=float(row["speed_kmh"]),
            depot_stop_id=int(row["depot_stop_id"]),
            max_shift_duration_min=float(row["max_shift_duration_min"]),
            is_active=bool(row["is_active"]),
        )


@dataclass
class RouteRecordModel:
    id: Optional[int]
    timestamp: str
    algorithm: str
    route_ids: List[int]
    distance_km: float
    total_time_min: float
    execution_time_ms: float
    cost: float
    is_valid: bool = True
    violations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "algorithm": self.algorithm,
            "route_ids": self.route_ids,
            "distance_km": self.distance_km,
            "total_time_min": self.total_time_min,
            "execution_time_ms": self.execution_time_ms,
            "cost": self.cost,
            "is_valid": self.is_valid,
            "violations": self.violations,
        }

    @classmethod
    def from_row(cls, row) -> "RouteRecordModel":
        raw_routes = row["route_ids"]
        route_list = json.loads(raw_routes) if isinstance(raw_routes, str) else raw_routes
        raw_violations = row["violations"]
        violation_list = json.loads(raw_violations) if isinstance(raw_violations, str) else raw_violations

        return cls(
            id=row["id"],
            timestamp=row["timestamp"] if "timestamp" in row.keys() else str(datetime.utcnow()),
            algorithm=row["algorithm"],
            route_ids=route_list,
            distance_km=float(row["distance_km"]),
            total_time_min=float(row["total_time_min"]),
            execution_time_ms=float(row["execution_time_ms"]),
            cost=float(row["cost"]),
            is_valid=bool(row["is_valid"]),
            violations=violation_list or [],
        )


@dataclass
class RoadClosureModel:
    from_id: int
    to_id: int
    is_closed: bool = True

    def normalized_edge(self) -> Tuple[int, int]:
        return min(self.from_id, self.to_id), max(self.from_id, self.to_id)

    def to_dict(self) -> Dict[str, Any]:
        u, v = self.normalized_edge()
        return {"from_id": u, "to_id": v, "is_closed": self.is_closed}


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS stops (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    lat REAL NOT NULL,
    lng REAL NOT NULL,
    demand REAL NOT NULL DEFAULT 0.0,
    tw_start REAL NOT NULL DEFAULT 0.0,
    tw_end REAL NOT NULL DEFAULT 480.0,
    service_time REAL NOT NULL DEFAULT 10.0,
    priority TEXT NOT NULL DEFAULT 'NORMAL',
    is_depot INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS vehicle_configs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    capacity REAL NOT NULL DEFAULT 400.0,
    speed_kmh REAL NOT NULL DEFAULT 35.0,
    depot_stop_id INTEGER NOT NULL DEFAULT 0,
    max_shift_duration_min REAL NOT NULL DEFAULT 480.0,
    is_active INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS routes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    algorithm TEXT NOT NULL,
    route_ids TEXT NOT NULL,
    distance_km REAL NOT NULL,
    total_time_min REAL NOT NULL,
    execution_time_ms REAL NOT NULL,
    cost REAL NOT NULL,
    is_valid INTEGER NOT NULL DEFAULT 1,
    violations TEXT NOT NULL DEFAULT '[]'
);

CREATE TABLE IF NOT EXISTS road_closures (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    from_id INTEGER NOT NULL,
    to_id INTEGER NOT NULL,
    is_closed INTEGER NOT NULL DEFAULT 1,
    UNIQUE(from_id, to_id)
);
"""