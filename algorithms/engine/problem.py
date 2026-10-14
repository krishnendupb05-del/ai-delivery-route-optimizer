"""Routing problem definition shared by ACO and GA.

Node indexing: node 0 is the depot, node i + 1 is `stops[i]`. Algorithms work on
permutations of stop indices (0..n-1); `node_of(i)` converts to matrix indices.
"""
from __future__ import annotations

import math
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field, replace

from algorithms.engine.models.stop import Stop
from algorithms.engine.models.vehicle import Vehicle

from algorithms.engine.config import (  # noqa: F401  (re-exported defaults)
    DEFAULT_RELOAD_TIME_MIN,
    DEFAULT_SERVICE_TIME_MIN,
    DEFAULT_SPEED_KMH,
)

EARTH_RADIUS_KM = 6371.0
DEPOT = 0


def haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two coordinates in kilometres."""
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * EARTH_RADIUS_KM * math.asin(math.sqrt(a))


@dataclass
class RoutingProblem:
    """Everything an algorithm needs to evaluate a stop ordering.

    distance_matrix: (n + 1) x (n + 1) kilometres, node 0 = depot.
    speed_kmh: constant travel speed used to convert distance to minutes.
    service_time_min: time spent unloading at each stop.
    reload_time_min: time spent at the depot on each mid-route reload trip.
    start_time: dispatch time, minutes since midnight.
    closed_edges: road segments that cannot be driven, as node pairs. Closures
        are undirected: closing (a, b) also closes (b, a).
    """

    stops: list[Stop]
    vehicle: Vehicle
    distance_matrix: list[list[float]]
    speed_kmh: float = DEFAULT_SPEED_KMH
    service_time_min: float = DEFAULT_SERVICE_TIME_MIN
    reload_time_min: float = DEFAULT_RELOAD_TIME_MIN
    start_time: float = 0.0
    depot: tuple[float, float] | None = field(default=None)
    closed_edges: frozenset[frozenset[int]] = field(default_factory=frozenset)

    def __post_init__(self) -> None:
        size = len(self.stops) + 1
        if len(self.distance_matrix) != size or any(len(r) != size for r in self.distance_matrix):
            raise ValueError(f"distance_matrix must be {size}x{size} (depot + {len(self.stops)} stops)")
        if self.speed_kmh <= 0:
            raise ValueError("speed_kmh must be positive")
        if self.service_time_min < 0 or self.reload_time_min < 0:
            raise ValueError("service_time_min and reload_time_min must be non-negative")
        self.closed_edges = frozenset(frozenset(e) for e in self.closed_edges)
        for edge in self.closed_edges:
            if len(edge) != 2 or not all(0 <= node < size for node in edge):
                raise ValueError(f"closed edge must join two different nodes in 0..{size - 1}")

    @property
    def num_stops(self) -> int:
        return len(self.stops)

    @staticmethod
    def node_of(stop_index: int) -> int:
        return stop_index + 1

    def is_closed(self, from_node: int, to_node: int) -> bool:
        return frozenset((from_node, to_node)) in self.closed_edges

    def with_closed_edges(self, edges: Iterable[tuple[int, int]]) -> RoutingProblem:
        """Copy of this problem with extra closed edges added to the existing ones."""
        extra = {frozenset(e) for e in edges}
        return replace(self, closed_edges=self.closed_edges | extra)

    def distance(self, from_node: int, to_node: int) -> float:
        return self.distance_matrix[from_node][to_node]

    def travel_minutes(self, from_node: int, to_node: int) -> float:
        return self.distance(from_node, to_node) / self.speed_kmh * 60.0

    @classmethod
    def from_coordinates(
        cls,
        depot: tuple[float, float],
        stops: Sequence[Stop],
        vehicle: Vehicle,
        **kwargs: float,
    ) -> RoutingProblem:
        """Build a problem using straight-line (haversine) distances."""
        points = [depot] + [(s.lat, s.lng) for s in stops]
        matrix = [[haversine_km(*a, *b) for b in points] for a in points]
        return cls(stops=list(stops), vehicle=vehicle, distance_matrix=matrix, depot=depot, **kwargs)
