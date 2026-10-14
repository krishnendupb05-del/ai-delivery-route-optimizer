"""Shared cost function for ACO and GA — the single definition of a "good" route.

A candidate solution is a permutation of stop indices. It is simulated as one
vehicle leaving the depot fully loaded at the dispatch time, visiting stops in
order, and returning to the depot to reload whenever the next stop's delivery
would not fit in the remaining load. The route ends back at the depot.

One running clock (minutes since midnight) covers everything: travel, waiting
for a window to open, service time at each stop, and reload time at the depot.

Cost = distance cost
     + closed-road penalty   (each drive along a closed road segment)
     + capacity penalty      (only for a stop heavier than the whole vehicle)
     + lateness penalty      (minutes past a time window, scaled by priority)
     + priority delay cost   (arrival time, scaled by priority — serve urgent stops early)

Arriving before a window opens is not penalised: the vehicle waits.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from algorithms.engine.problem import DEPOT, RoutingProblem
from algorithms.engine.models.stop import Priority

# --- Named penalties (no magic numbers in the algorithms) -------------------

# Cost per kilometre driven, including depot returns.
DISTANCE_COST_PER_KM = 1.0

# Cost per unit of weight that exceeds the vehicle's capacity. Only reachable
# when a single stop is heavier than the vehicle — reloading can't fix that.
# Large so any such route is dominated by every feasible route.
CAPACITY_PENALTY_PER_UNIT = 1000.0

# Cost each time the route drives along a closed road segment. Must dominate
# every other term combined (lateness alone can reach tens of thousands on a
# 50-stop day), so any route that avoids all closures beats any route that doesn't.
CLOSED_ROAD_PENALTY = 1_000_000.0

# Cost per minute a delivery starts after its time window closes, before
# priority scaling.
LATE_PENALTY_PER_MINUTE = 10.0

# Cost per minute of arrival time, before priority scaling. Small, so it only
# breaks ties between routes of similar length in favour of serving
# high-priority stops first.
PRIORITY_DELAY_COST_PER_MINUTE = 0.01

# Multiplier applied to lateness and delay cost for each priority level.
PRIORITY_WEIGHTS: dict[Priority, float] = {
    Priority.CRITICAL: 4.0,
    Priority.HIGH: 2.0,
    Priority.NORMAL: 1.0,
    Priority.LOW: 0.5,
}


@dataclass(frozen=True)
class CostWeights:
    """Coefficients for each cost term. Override to isolate terms in tests."""

    distance_per_km: float = DISTANCE_COST_PER_KM
    capacity_per_unit: float = CAPACITY_PENALTY_PER_UNIT
    late_per_minute: float = LATE_PENALTY_PER_MINUTE
    priority_delay_per_minute: float = PRIORITY_DELAY_COST_PER_MINUTE
    closed_road: float = CLOSED_ROAD_PENALTY


DEFAULT_WEIGHTS = CostWeights()


@dataclass
class RouteEvaluation:
    """Full breakdown of a simulated route."""

    total_cost: float
    distance_cost: float
    capacity_penalty: float
    lateness_penalty: float
    priority_delay_cost: float
    closed_road_penalty: float
    total_distance: float
    total_time: float
    depot_returns: int
    late_stops: int
    excess_weight: float
    closed_edges_used: int
    # Matrix node sequence actually driven, including depot start/reloads/end.
    node_sequence: list[int] = field(default_factory=list)
    # Service start time (minutes since midnight) per stop index.
    service_start: dict[int, float] = field(default_factory=dict)

    @property
    def is_feasible(self) -> bool:
        return self.late_stops == 0 and self.excess_weight == 0 and self.closed_edges_used == 0


def _validate_order(order: Sequence[int], num_stops: int) -> None:
    if sorted(order) != list(range(num_stops)):
        raise ValueError(f"order must be a permutation of 0..{num_stops - 1}, got {list(order)}")


def evaluate_route(
    order: Sequence[int],
    problem: RoutingProblem,
    weights: CostWeights = DEFAULT_WEIGHTS,
) -> RouteEvaluation:
    """Simulate visiting stops in `order` and return the full cost breakdown."""
    _validate_order(order, problem.num_stops)
    capacity = problem.vehicle.capacity

    node = DEPOT
    clock = problem.start_time
    load = capacity
    distance = 0.0
    depot_returns = 0
    closed_edges_used = 0
    excess_weight = 0.0
    late_stops = 0
    lateness_penalty = 0.0
    priority_delay = 0.0
    sequence = [DEPOT]
    service_start: dict[int, float] = {}

    def drive(to_node: int) -> None:
        nonlocal node, clock, distance, closed_edges_used
        if problem.is_closed(node, to_node):
            closed_edges_used += 1
        distance += problem.distance(node, to_node)
        clock += problem.travel_minutes(node, to_node)
        node = to_node
        sequence.append(to_node)

    for idx in order:
        stop = problem.stops[idx]
        deliverable = min(stop.weight, capacity)

        if deliverable > load and node != DEPOT:
            drive(DEPOT)
            clock += problem.reload_time_min
            load = capacity
            depot_returns += 1

        drive(problem.node_of(idx))

        start = max(clock, stop.time_window.start)
        clock = start + getattr(
            stop, "service_time", problem.service_time_min
            )
        service_start[idx] = start

        priority_weight = PRIORITY_WEIGHTS[stop.priority]
        minutes_late = max(0.0, start - stop.time_window.end)
        if minutes_late > 0:
            late_stops += 1
            lateness_penalty += weights.late_per_minute * priority_weight * minutes_late
        priority_delay += weights.priority_delay_per_minute * priority_weight * start

        load -= deliverable
        excess_weight += stop.weight - deliverable

    if node != DEPOT:
        drive(DEPOT)

    distance_cost = weights.distance_per_km * distance
    capacity_penalty = weights.capacity_per_unit * excess_weight
    closed_road_penalty = weights.closed_road * closed_edges_used

    return RouteEvaluation(
        total_cost=distance_cost + closed_road_penalty + capacity_penalty + lateness_penalty + priority_delay,
        distance_cost=distance_cost,
        capacity_penalty=capacity_penalty,
        lateness_penalty=lateness_penalty,
        priority_delay_cost=priority_delay,
        closed_road_penalty=closed_road_penalty,
        total_distance=distance,
        total_time=clock - problem.start_time,
        depot_returns=depot_returns,
        late_stops=late_stops,
        excess_weight=excess_weight,
        closed_edges_used=closed_edges_used,
        node_sequence=sequence,
        service_start=service_start,
    )


def route_cost(
    order: Sequence[int],
    problem: RoutingProblem,
    weights: CostWeights = DEFAULT_WEIGHTS,
) -> float:
    """Scalar objective minimised by both ACO and GA."""
    return evaluate_route(order, problem, weights).total_cost
