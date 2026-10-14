"""Ant Colony Optimization (Ant System with elitist reinforcement).

Each ant builds a permutation of stops starting at the depot, tracking the clock
and load as it goes. The probability of moving from node i to unvisited stop j
is proportional to

    tau[i][j]^alpha * (1 / distance[i][j])^beta * priority_weight[j]^gamma
                    * (1 / slack_j)^delta

where slack_j is the minutes left in j's time window if service started there
next (at least 1; already-late stops get the maximum). So ants are pulled toward
strong pheromone trails, nearby stops, high-priority stops, and stops whose
window is about to close. Every route is scored with the shared `route_cost`, so capacity reloads
and time windows feed back into the pheromone via cost. After each iteration
pheromone evaporates, each ant deposits q / cost on the edges it used, and the
best-so-far route gets an extra elitist deposit.

Closed road segments get zero attractiveness, so ants never choose them while
any open option remains (the shared cost function still penalises them if a
reload trip is forced onto one).

Live re-optimization: pass `warm_start` (the previous best order). It becomes
the initial best-so-far route (so the result is never worse than it), and its
still-open edges start with boosted pheromone, so the colony resumes from the
old solution instead of a cold start.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from algorithms.engine.constraints import (
    DEFAULT_WEIGHTS,
    PRIORITY_WEIGHTS,
    CostWeights,
    evaluate_route,
    route_cost,
)
from algorithms.engine.problem import DEPOT, RoutingProblem
from algorithms.engine.result import Snapshot, SolverResult, snapshot_iterations

# Distances below this are treated as this, so co-located stops don't divide by zero.
MIN_DISTANCE_KM = 1e-6

# Slack (minutes left in a window when service would start) below this counts
# as this, so stops that are due now or already late get the strongest pull.
MIN_SLACK_MINUTES = 1.0

# Warm start: initial pheromone on the previous best route's open edges is this
# multiple of the normal starting level.
WARM_START_PHEROMONE_BOOST = 5.0

# Pheromone never drops below this fraction of its initial value, so no edge
# becomes permanently unreachable.
PHEROMONE_FLOOR_RATIO = 1e-3


@dataclass(frozen=True)
class ACOParams:
    num_ants: int = 20
    iterations: int = 100
    alpha: float = 1.0  # pheromone influence
    beta: float = 2.0  # inverse-distance influence
    gamma: float = 1.0  # priority influence
    evaporation: float = 0.1  # fraction of pheromone lost per iteration (rho)
    deposit: float = 1.0  # q: pheromone deposited = q / route cost
    elitist_weight: float = 2.0  # extra deposits for the best-so-far route
    delta: float = 1.0  # time-window urgency influence (0 = ignore time windows)

    def __post_init__(self) -> None:
        if self.num_ants < 1 or self.iterations < 1:
            raise ValueError("num_ants and iterations must be at least 1")
        if not 0.0 < self.evaporation <= 1.0:
            raise ValueError("evaporation must be in (0, 1]")
        if min(self.alpha, self.beta, self.gamma, self.deposit, self.elitist_weight, self.delta) < 0:
            raise ValueError("alpha, beta, gamma, delta, deposit and elitist_weight must be non-negative")


DEFAULT_PARAMS = ACOParams()


def nearest_neighbour_order(problem: RoutingProblem) -> list[int]:
    """Greedy baseline: always drive to the closest unvisited stop, skipping
    closed roads whenever an open one is available (so the baseline is a route
    a driver could actually take, and savings against it are fair)."""
    unvisited = list(range(problem.num_stops))
    order: list[int] = []
    node = DEPOT
    while unvisited:
        open_options = [i for i in unvisited if not problem.is_closed(node, problem.node_of(i))]
        candidates = open_options or unvisited
        nxt = min(candidates, key=lambda i: problem.distance(node, problem.node_of(i)))
        unvisited.remove(nxt)
        order.append(nxt)
        node = problem.node_of(nxt)
    return order


def _route_edges(order: list[int], problem: RoutingProblem) -> list[tuple[int, int]]:
    nodes = [DEPOT] + [problem.node_of(i) for i in order] + [DEPOT]
    return list(zip(nodes, nodes[1:]))


def _build_ant_route(
    problem: RoutingProblem,
    pheromone: list[list[float]],
    attractiveness: list[list[float]],
    travel: list[list[float]],
    params: ACOParams,
    rng: random.Random,
) -> list[int]:
    """Build one ant's route.

    The ant tracks the clock and load exactly as the shared cost function will
    simulate them (travel, waiting, service, reload trips), so for every
    candidate it knows when service would start and how much of the time window
    would be left. Less slack means a stronger pull.
    """
    capacity = problem.vehicle.capacity
    n = problem.num_stops
    nodes = [problem.node_of(i) for i in range(n)]
    deliverable = [min(s.weight, capacity) for s in problem.stops]
    opens = [s.time_window.start for s in problem.stops]
    closes = [s.time_window.end for s in problem.stops]
    use_urgency = params.delta > 0

    unvisited = list(range(n))
    order: list[int] = []
    node = DEPOT
    clock = problem.start_time
    load = capacity
    to_depot_and_reload = 0.0

    while unvisited:
        if node != DEPOT:
            to_depot_and_reload = clock + travel[node][DEPOT] + problem.reload_time_min
        tau = pheromone[node]
        attract = attractiveness[node]
        scores = []
        starts = []
        for i in unvisited:
            j = nodes[i]
            if deliverable[i] > load and node != DEPOT:
                arrival = to_depot_and_reload + travel[DEPOT][j]
            else:
                arrival = clock + travel[node][j]
            start = arrival if arrival > opens[i] else opens[i]
            starts.append(start)
            score = tau[j] ** params.alpha * attract[j]
            if use_urgency:
                slack = closes[i] - start
                score *= (1.0 / (slack if slack > MIN_SLACK_MINUTES else MIN_SLACK_MINUTES)) ** params.delta
            scores.append(score)

        total = sum(scores)
        if total <= 0:
            pick = rng.randrange(len(unvisited))
        else:
            pick = rng.choices(range(len(unvisited)), weights=scores)[0]

        nxt = unvisited.pop(pick)
        start = starts[pick]
        if deliverable[nxt] > load and node != DEPOT:
            load = capacity
        load -= deliverable[nxt]
        clock = start + getattr(
            problem.stops[nxt], "service_time", problem.service_time_min
            )
        order.append(nxt)
        node = nodes[nxt]
    return order


def run(
    problem: RoutingProblem,
    params: ACOParams = DEFAULT_PARAMS,
    seed: int | None = None,
    weights: CostWeights = DEFAULT_WEIGHTS,
    warm_start: list[int] | None = None,
) -> SolverResult:
    """Run ACO and return the best route found plus best-cost-per-iteration history.

    warm_start: previous best order to resume from (live re-optimization).
    """
    started = time.perf_counter()
    n = problem.num_stops
    if n == 0:
        evaluation = evaluate_route([], problem, weights)
        return SolverResult([], evaluation.total_cost, evaluation)

    rng = random.Random(seed)
    size = n + 1

    # Static part of the transition rule: inverse distance and priority pull.
    priority_pull = [1.0] + [PRIORITY_WEIGHTS[s.priority] ** params.gamma for s in problem.stops]
    attractiveness = [
        [
            0.0
            if i == j or j == DEPOT or problem.is_closed(i, j)
            else (1.0 / max(problem.distance(i, j), MIN_DISTANCE_KM)) ** params.beta * priority_pull[j]
            for j in range(size)
        ]
        for i in range(size)
    ]

    travel = [[problem.travel_minutes(i, j) for j in range(size)] for i in range(size)]

    # Ant System initialisation: tau0 = num_ants / cost of a greedy route.
    baseline_cost = route_cost(nearest_neighbour_order(problem), problem, weights)
    tau0 = params.num_ants / max(baseline_cost, MIN_DISTANCE_KM)
    tau_floor = tau0 * PHEROMONE_FLOOR_RATIO
    pheromone = [[tau0] * size for _ in range(size)]
    if warm_start is not None:
        if sorted(warm_start) != list(range(n)):
            raise ValueError("warm_start must be a permutation of the problem's stop indices")
        for a, b in _route_edges(warm_start, problem):
            if not problem.is_closed(a, b):
                pheromone[a][b] = tau0 * WARM_START_PHEROMONE_BOOST

    best_order: list[int] = []
    best_cost = float("inf")
    if warm_start is not None:
        best_order, best_cost = list(warm_start), route_cost(warm_start, problem, weights)
    history: list[float] = []
    snapshot_at = snapshot_iterations(params.iterations)
    snapshots: list[Snapshot] = []

    for iteration in range(1, params.iterations + 1):
        ants = []
        for _ in range(params.num_ants):
            order = _build_ant_route(problem, pheromone, attractiveness, travel, params, rng)
            cost = route_cost(order, problem, weights)
            ants.append((order, cost))
            if cost < best_cost:
                best_order, best_cost = order, cost

        keep = 1.0 - params.evaporation
        for row in pheromone:
            for j in range(size):
                row[j] *= keep

        for order, cost in ants:
            amount = params.deposit / max(cost, MIN_DISTANCE_KM)
            for a, b in _route_edges(order, problem):
                pheromone[a][b] += amount

        elite = params.elitist_weight * params.deposit / max(best_cost, MIN_DISTANCE_KM)
        for a, b in _route_edges(best_order, problem):
            pheromone[a][b] += elite

        for row in pheromone:
            for j in range(size):
                if row[j] < tau_floor:
                    row[j] = tau_floor

        history.append(best_cost)
        if iteration in snapshot_at:
            snapshots.append(Snapshot(iteration, list(best_order), best_cost))

    evaluation = evaluate_route(best_order, problem, weights)
    return SolverResult(
        order=best_order,
        cost=best_cost,
        evaluation=evaluation,
        history=history,
        iterations=params.iterations,
        elapsed_seconds=time.perf_counter() - started,
        snapshots=snapshots,
    )
