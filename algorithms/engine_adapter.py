"""Adapter connecting the new routing engine to the existing project models."""

from algorithms.core_models import Stop as LegacyStop
from algorithms.core_models import Vehicle as LegacyVehicle
from algorithms.core_models import DistanceMatrix as LegacyDistanceMatrix

from algorithms.engine import aco, ga
from algorithms.engine.constraints import evaluate_route
from algorithms.engine.models.stop import (
    Priority as EnginePriority,
    Stop as EngineStop,
    TimeWindow,
)
from algorithms.engine.models.vehicle import Vehicle as EngineVehicle
from algorithms.engine.problem import RoutingProblem


PRIORITY_MAP = {
    "LOW": EnginePriority.LOW,
    "NORMAL": EnginePriority.NORMAL,
    "HIGH": EnginePriority.HIGH,
    "CRITICAL": EnginePriority.CRITICAL,
}


def build_problem(
    stops: list[LegacyStop],
    vehicle: LegacyVehicle,
    distance_matrix: LegacyDistanceMatrix,
) -> tuple[RoutingProblem, list[int]]:
    """Convert existing models to the new engine's models.

    Returns the routing problem and the legacy IDs in engine stop order.
    """
    depot_stops = [s for s in stops if s.is_depot]
    if len(depot_stops) != 1:
        raise ValueError(
            f"Expected exactly one depot, found {len(depot_stops)}."
        )

    depot = depot_stops[0]
    delivery_stops = [s for s in stops if not s.is_depot]

    engine_stops = []
    legacy_ids = []

    for stop in delivery_stops:
        start, end = stop.time_window

        engine_stop = EngineStop(
            id=stop.id,
            name=stop.name,
            lat=stop.lat,
            lng=stop.lng,
            weight=stop.demand,
            time_window=TimeWindow(start=float(start), end=float(end)),
            priority=PRIORITY_MAP[stop.priority.name.upper()],
            service_time=float(stop.service_time),
        )

        engine_stops.append(engine_stop)
        legacy_ids.append(stop.id)

    # The engine uses matrix node 0 for the depot and nodes 1..n for deliveries.
    points = [depot] + delivery_stops
    matrix = [
        [distance_matrix.matrix[(a.id, b.id)] for b in points]
        for a in points
    ]

    # Translate closed legacy stop IDs into the engine's matrix-node indices.
    node_by_legacy_id = {depot.id: 0}
    node_by_legacy_id.update(
        {stop.id: i + 1 for i, stop in enumerate(delivery_stops)}
    )

    closed_edges = set()
    for u, v in distance_matrix.closed_edges:
        if u in node_by_legacy_id and v in node_by_legacy_id:
            closed_edges.add(
                (node_by_legacy_id[u], node_by_legacy_id[v])
            )

    problem = RoutingProblem(
        stops=engine_stops,
        vehicle=EngineVehicle(id=vehicle.id, capacity=vehicle.capacity),
        distance_matrix=matrix,
        speed_kmh=vehicle.speed_kmh,
        service_time_min=(
            sum(s.service_time for s in delivery_stops) / len(delivery_stops)
            if delivery_stops else 10.0
        ),
        depot=(depot.lat, depot.lng),
        closed_edges=frozenset(frozenset(edge) for edge in closed_edges),
    )

    return problem, legacy_ids


def optimize(
    stops: list[LegacyStop],
    vehicle: LegacyVehicle,
    distance_matrix: LegacyDistanceMatrix,
    algorithm: str = "aco",
    num_ants: int = 30,
    iterations: int = 80,
    population_size: int = 40,
    generations: int = 80,
    seed: int | None = None,
    warm_start: list[int] | None = None,
) -> dict:
    """Run the new engine and return results mapped to legacy stop IDs."""
    problem, legacy_ids = build_problem(stops, vehicle, distance_matrix)

    warm_order = None
    if warm_start is not None:
        id_to_idx = {sid: i for i, sid in enumerate(legacy_ids)}
        filtered = [id_to_idx[sid] for sid in warm_start if sid in id_to_idx]
        if len(filtered) == len(legacy_ids) and len(set(filtered)) == len(legacy_ids):
            warm_order = filtered

    if algorithm.lower() == "ga":
        result = ga.run(
            problem,
            params=ga.GAParams(
                population_size=max(2, population_size),
                generations=max(1, generations),
            ),
            seed=seed,
            warm_start=warm_order,
        )
        algorithm_name = "GA"
    else:
        result = aco.run(
            problem,
            params=aco.ACOParams(
                num_ants=max(1, num_ants),
                iterations=max(1, iterations),
            ),
            seed=seed,
            warm_start=warm_order,
        )
        algorithm_name = "ACO"

    evaluation = result.evaluation
    depot_id = next(s.id for s in stops if s.is_depot)
    delivery_stops = [s for s in stops if not s.is_depot]
    node_to_legacy = {0: depot_id}
    node_to_legacy.update({i + 1: s.id for i, s in enumerate(delivery_stops)})

    # Map full driving sequence with depot reloads (multi-trip vehicle routing)
    if evaluation.node_sequence:
        full_route = [node_to_legacy[n] for n in evaluation.node_sequence]
    else:
        full_route = [depot_id, *[legacy_ids[i] for i in result.order], depot_id]

    # Partition full route into distinct vehicle trips
    trips = []
    if full_route:
        curr_trip = [full_route[0]]
        for sid in full_route[1:]:
            curr_trip.append(sid)
            if sid == depot_id:
                trips.append(curr_trip)
                curr_trip = [depot_id]
        if len(curr_trip) > 1:
            trips.append(curr_trip)

    num_trips = max(1, len(trips))

    violations = []
    if evaluation.late_stops:
        violations.append(f"{evaluation.late_stops} stop(s) outside time windows")
    if evaluation.excess_weight > 0:
        violations.append(f"Excess delivery weight: {evaluation.excess_weight:.2f}")
    if evaluation.closed_edges_used:
        violations.append(f"{evaluation.closed_edges_used} closed road segment(s) used")

    # Format convergence history into structured points expected by the UI charts
    history_formatted = []
    for idx, item in enumerate(result.history):
        if isinstance(item, dict):
            history_formatted.append(item)
        else:
            history_formatted.append({
                "iteration": idx + 1,
                "best_cost": round(float(item), 2),
                "best_distance": round(evaluation.total_distance, 2),
            })

    return {
        "algorithm": algorithm_name,
        "execution_time_ms": result.elapsed_seconds * 1000.0,
        "route_ids": full_route,
        "num_trips": num_trips,
        "depot_returns": evaluation.depot_returns,
        "trips": trips,
        "evaluation": {
            "distance_km": evaluation.total_distance,
            "total_time_min": evaluation.total_time,
            "cost": evaluation.total_cost,
            "is_valid": evaluation.is_feasible,
            "violations": violations,
            "late_stops": evaluation.late_stops,
            "depot_returns": evaluation.depot_returns,
            "num_trips": num_trips,
            "excess_weight": evaluation.excess_weight,
            "closed_edges_used": evaluation.closed_edges_used,
        },
        "convergence_history": history_formatted,
    }