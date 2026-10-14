"""Run ACO and GA side by side on one problem, plus a greedy baseline.

Both solvers are called through the same `run(problem, params, seed)` shape,
so neither is special-cased.
"""
from __future__ import annotations

from dataclasses import dataclass

from algorithms.engine import aco, ga
from algorithms.engine.aco import ACOParams, nearest_neighbour_order
from algorithms.engine.constraints import RouteEvaluation, evaluate_route
from algorithms.engine.ga import GAParams
from algorithms.engine.problem import RoutingProblem
from algorithms.engine.result import SolverResult
from algorithms.engine.models.optimization_result import Algorithm


@dataclass
class Comparison:
    results: dict[Algorithm, SolverResult]
    baseline_order: list[int]
    baseline: RouteEvaluation

    @property
    def winner(self) -> Algorithm:
        """Lowest cost wins; ties go to ACO (the primary algorithm)."""
        return min(self.results, key=lambda a: (self.results[a].cost, a is not Algorithm.ACO))

    def distance_saved(self, algorithm: Algorithm) -> float:
        """Kilometres saved versus the greedy nearest-neighbour route (negative = worse)."""
        return self.baseline.total_distance - self.results[algorithm].evaluation.total_distance


def compare(
    problem: RoutingProblem,
    aco_params: ACOParams = aco.DEFAULT_PARAMS,
    ga_params: GAParams = ga.DEFAULT_PARAMS,
    seed: int | None = None,
    warm_starts: dict[Algorithm, list[int]] | None = None,
) -> Comparison:
    """Run both solvers. `warm_starts` gives each algorithm its own previous best
    order for live re-optimization."""
    warm = warm_starts or {}
    baseline_order = nearest_neighbour_order(problem)
    return Comparison(
        results={
            Algorithm.ACO: aco.run(problem, aco_params, seed, warm_start=warm.get(Algorithm.ACO)),
            Algorithm.GA: ga.run(problem, ga_params, seed, warm_start=warm.get(Algorithm.GA)),
        },
        baseline_order=baseline_order,
        baseline=evaluate_route(baseline_order, problem),
    )
