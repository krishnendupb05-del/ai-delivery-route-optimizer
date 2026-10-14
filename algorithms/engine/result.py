"""Result type returned by every solver (ACO and GA) so callers never special-case."""
from __future__ import annotations

from dataclasses import dataclass, field

from algorithms.engine.constraints import RouteEvaluation
from algorithms.engine.problem import RoutingProblem
from algorithms.engine.models.optimization_result import Algorithm, OptimizationResult
from algorithms.engine.models.route import Route


# How many best-so-far routes a solver records for the "algorithm replay" view.
SNAPSHOT_COUNT = 20


@dataclass(frozen=True)
class Snapshot:
    """Best-so-far route after a given iteration (1-based)."""

    iteration: int
    order: list[int]
    cost: float


def snapshot_iterations(total: int, count: int = SNAPSHOT_COUNT) -> set[int]:
    """~`count` iterations (1-based) spread evenly over 1..total, always
    including the first and last."""
    if total <= 0:
        return set()
    if total <= count:
        return set(range(1, total + 1))
    return {1 + round(k * (total - 1) / (count - 1)) for k in range(count)}


@dataclass
class SolverResult:
    """Best solution found by a solver run.

    order: best permutation of stop indices.
    cost: route_cost of `order`.
    evaluation: full cost breakdown of `order` (includes depot reload trips).
    history: best-so-far cost after each iteration/generation.
    snapshots: best-so-far route at ~SNAPSHOT_COUNT evenly spaced iterations.
    """

    order: list[int]
    cost: float
    evaluation: RouteEvaluation
    history: list[float] = field(default_factory=list)
    iterations: int = 0
    elapsed_seconds: float = 0.0
    snapshots: list[Snapshot] = field(default_factory=list)

    def to_optimization_result(
        self, algorithm: Algorithm, problem: RoutingProblem
    ) -> OptimizationResult:
        route = Route(
            stops=[problem.stops[i] for i in self.order],
            total_distance=self.evaluation.total_distance,
            total_time=self.evaluation.total_time,
        )
        return OptimizationResult(
            algorithm=algorithm,
            route=route,
            cost=self.cost,
            iterations=self.iterations,
            history=list(self.history),
        )
