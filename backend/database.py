import json
import os
import sqlite3
from typing import Any, Dict, List, Optional
from algorithms.core_models import Priority, Stop
from algorithms.sample_data import get_sample_scenario
from backend.models import SCHEMA_SQL, VehicleConfigModel, StopModel, RouteRecordModel, RoadClosureModel

DB_PATH = os.path.join(os.path.dirname(__file__), "optimizer.db")


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Execute normalized schema
    cursor.executescript(SCHEMA_SQL)
    conn.commit()

    # Seed initial vehicle configuration if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM vehicle_configs")
    if cursor.fetchone()["cnt"] == 0:
        cursor.execute(
            """
            INSERT INTO vehicle_configs (id, name, capacity, speed_kmh, depot_stop_id, max_shift_duration_min, is_active)
            VALUES (1, 'Primary Electric Delivery Van', 80.0, 35.0, 0, 480.0, 1)
            """
        )
        conn.commit()

    # Seed initial stops if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM stops")
    if cursor.fetchone()["cnt"] == 0:
        seed_sample_stops()

    conn.close()


def seed_sample_stops():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stops")

    scenario = get_sample_scenario()
    for s in scenario["stops"]:
        cursor.execute(
            """
            INSERT INTO stops (id, name, lat, lng, demand, tw_start, tw_end, service_time, priority, is_depot)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                s.id,
                s.name,
                s.lat,
                s.lng,
                s.demand,
                s.time_window[0],
                s.time_window[1],
                s.service_time,
                s.priority.name,
                1 if s.is_depot else 0,
            ),
        )
    conn.commit()
    conn.close()


def get_all_stops() -> List[Stop]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM stops ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    if not rows:
        seed_sample_stops()
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM stops ORDER BY id ASC")
        rows = cursor.fetchall()
        conn.close()

    stops = []
    for r in rows:
        stops.append(
            Stop(
                id=r["id"],
                name=r["name"],
                lat=r["lat"],
                lng=r["lng"],
                demand=r["demand"],
                time_window=(r["tw_start"], r["tw_end"]),
                service_time=r["service_time"],
                priority=Priority.from_string(r["priority"]),
                is_depot=bool(r["is_depot"]),
            )
        )
    return stops


def add_or_update_stop(
    name: str,
    lat: float,
    lng: float,
    demand: float,
    tw_start: float,
    tw_end: float,
    service_time: float,
    priority: str,
    is_depot: bool = False,
    stop_id: Optional[int] = None,
) -> int:
    conn = get_connection()
    cursor = conn.cursor()

    if stop_id is None:
        cursor.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM stops")
        stop_id = cursor.fetchone()["next_id"]

    cursor.execute(
        """
        INSERT OR REPLACE INTO stops (id, name, lat, lng, demand, tw_start, tw_end, service_time, priority, is_depot)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            stop_id,
            name,
            lat,
            lng,
            demand,
            tw_start,
            tw_end,
            service_time,
            priority.upper(),
            1 if is_depot else 0,
        ),
    )
    conn.commit()
    conn.close()
    return stop_id


def delete_stop(stop_id: int) -> bool:
    if stop_id == 0:
        return False  # Cannot delete depot
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM stops WHERE id = ?", (stop_id,))
    deleted = cursor.rowcount > 0
    cursor.execute("DELETE FROM road_closures WHERE from_id = ? OR to_id = ?", (stop_id, stop_id))
    conn.commit()
    conn.close()
    return deleted


def record_route_run(
    algorithm: str,
    route_ids: List[int],
    distance_km: float,
    total_time_min: float,
    execution_time_ms: float,
    cost: float,
    is_valid: bool,
    violations: List[str],
) -> int:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        INSERT INTO routes (algorithm, route_ids, distance_km, total_time_min, execution_time_ms, cost, is_valid, violations)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            algorithm,
            json.dumps(route_ids),
            distance_km,
            total_time_min,
            execution_time_ms,
            cost,
            1 if is_valid else 0,
            json.dumps(violations),
        ),
    )
    route_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return route_id


def get_all_closures() -> List[Dict[str, int]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT from_id, to_id FROM road_closures WHERE is_closed = 1")
    rows = cursor.fetchall()
    conn.close()
    return [{"from_id": r["from_id"], "to_id": r["to_id"]} for r in rows]


def toggle_closure(from_id: int, to_id: int, is_closed: bool):
    conn = get_connection()
    cursor = conn.cursor()
    u, v = min(from_id, to_id), max(from_id, to_id)
    if is_closed:
        cursor.execute(
            """
            INSERT OR REPLACE INTO road_closures (from_id, to_id, is_closed)
            VALUES (?, ?, 1)
            """,
            (u, v),
        )
    else:
        cursor.execute("DELETE FROM road_closures WHERE from_id = ? AND to_id = ?", (u, v))
    conn.commit()
    conn.close()


def get_analytics_summary() -> dict:
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) as total_runs FROM routes")
    total_runs = cursor.fetchone()["total_runs"]

    cursor.execute("SELECT AVG(distance_km) as avg_dist, AVG(execution_time_ms) as avg_time FROM routes")
    row_avg = cursor.fetchone()
    avg_dist = round(row_avg["avg_dist"] or 0.0, 2)
    avg_exec_ms = round(row_avg["avg_time"] or 0.0, 1)

    cursor.execute("SELECT COUNT(*) as valid_runs FROM routes WHERE is_valid = 1")
    valid_runs = cursor.fetchone()["valid_runs"]
    success_rate = round((valid_runs / total_runs * 100), 1) if total_runs > 0 else 100.0

    cursor.execute("SELECT * FROM routes ORDER BY id DESC LIMIT 10")
    recent_routes = [
        {
            "id": r["id"],
            "timestamp": r["timestamp"],
            "algorithm": r["algorithm"],
            "route": json.loads(r["route_ids"]),
            "distance_km": r["distance_km"],
            "total_time_min": r["total_time_min"],
            "execution_time_ms": r["execution_time_ms"],
            "cost": r["cost"],
            "is_valid": bool(r["is_valid"]),
        }
        for r in cursor.fetchall()
    ]

    conn.close()

    return {
        "total_runs": total_runs,
        "avg_distance_km": avg_dist,
        "avg_execution_ms": avg_exec_ms,
        "success_rate_percent": success_rate,
        "recent_history": recent_routes,
    }


def get_active_vehicle_config() -> VehicleConfigModel:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM vehicle_configs WHERE is_active = 1 ORDER BY id ASC LIMIT 1")
    row = cursor.fetchone()
    conn.close()
    if row:
        return VehicleConfigModel.from_row(row)
    return VehicleConfigModel()


def update_vehicle_config(
    capacity: float,
    speed_kmh: float,
    name: str = "Primary Electric Delivery Van",
    depot_stop_id: int = 0,
    max_shift_duration_min: float = 480.0,
) -> VehicleConfigModel:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute(
        """
        UPDATE vehicle_configs
        SET name = ?, capacity = ?, speed_kmh = ?, depot_stop_id = ?, max_shift_duration_min = ?
        WHERE id = 1
        """,
        (name, float(capacity), float(speed_kmh), int(depot_stop_id), float(max_shift_duration_min)),
    )
    if cursor.rowcount == 0:
        cursor.execute(
            """
            INSERT INTO vehicle_configs (id, name, capacity, speed_kmh, depot_stop_id, max_shift_duration_min, is_active)
            VALUES (1, ?, ?, ?, ?, ?, 1)
            """,
            (name, float(capacity), float(speed_kmh), int(depot_stop_id), float(max_shift_duration_min)),
        )
    conn.commit()
    conn.close()
    return get_active_vehicle_config()


def get_total_stops_demand() -> float:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COALESCE(SUM(demand), 0.0) as total_demand FROM stops WHERE is_depot = 0")
    total = cursor.fetchone()["total_demand"]
    conn.close()
    return float(total)