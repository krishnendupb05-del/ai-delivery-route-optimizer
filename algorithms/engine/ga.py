"""Genetic Algorithm for the same routing problem as aco.py.

A chromosome is a permutation of stop indices, scored with the shared
`route_cost` (fitness = lower cost). Each generation:

  1. Elitism: the best `elitism` chromosomes are copied unchanged.
  2. Tournament selection picks parents.
  3. Order crossover (OX1) combines two parents into a valid permutation.
  4. Inversion mutation reverses a random segment (a 2-opt style move).

Mirrors aco.py: `run(problem, params, seed, weights, warm_start) -> SolverResult`.

Live re-optimization: pass `warm_start` (the previous best order). It replaces
one chromosome in the otherwise random initial population, so the GA resumes from the old
solution instead of a cold start — the same head start ACO gets.
"""
from __future__ import annotations

import random
import time
from dataclasses import dataclass

from algorithms.engine.constraints import DEFAULT_WEIGHTS, CostWeights, evaluate_route, route_cost
from algorithms.engine.problem import RoutingProblem
from algorithms.engine.result import Snapshot, SolverResult, snapshot_iterations

Chromosome = list[int]


@dataclass(frozen=True)
class GAParams:
    population_size: int = 20
    generations: int = 100
    crossover_rate: float = 0.9  # chance a child is bred by crossover rather than copied
    mutation_rate: float = 0.3  # chance a child gets an inversion mutation
    tournament_size: int = 3
    elitism: int = 2  # best chromosomes carried over unchanged each generation

    def __post_init__(self) -> None:
        if self.population_size < 2 or self.generations < 1:
            raise ValueError("population_size must be >= 2 and generations >= 1")
        if not 0.0 <= self.crossover_rate <= 1.0 or not 0.0 <= self.mutation_rate <= 1.0:
            raise ValueError("crossover_rate and mutation_rate must be in [0, 1]")
        if not 1 <= self.tournament_size <= self.population_size:
            raise ValueError("tournament_size must be between 1 and population_size")
        if not 0 <= self.elitism < self.population_size:
            raise ValueError("elitism must be between 0 and population_size - 1")


DEFAULT_PARAMS = GAParams()


def order_crossover(p1: Chromosome, p2: Chromosome, rng: random.Random) -> Chromosome:
    """OX1: keep a slice of p1 in place, fill the rest in p2's order (wrapping after the slice)."""
    n = len(p1)
    if n < 2:
        return list(p1)
    i, j = sorted(rng.sample(range(n + 1), 2))
    child: list[int | None] = [None] * n
    child[i:j] = p1[i:j]
    kept = set(p1[i:j])
    fill = [g for g in p2[j:] + p2[:j] if g not in kept]
    positions = list(range(j, n)) + list(range(0, i))
    for pos, gene in zip(positions, fill):
        child[pos] = gene
    return child  # type: ignore[return-value]


def inversion_mutation(chromosome: Chromosome, rng: random.Random) -> Chromosome:
    """Reverse a random segment of length >= 2."""
    n = len(chromosome)
    if n < 2:
        return list(chromosome)
    i, j = sorted(rng.sample(range(n), 2))
    return chromosome[:i] + chromosome[i : j + 1][::-1] + chromosome[j + 1 :]


def _tournament(
    population: list[Chromosome], costs: list[float], size: int, rng: random.Random
) -> Chromosome:
    contenders = rng.sample(range(len(population)), size)
    return population[min(contenders, key=lambda k: costs[k])]


def run(
    problem: RoutingProblem,
    params: GAParams = DEFAULT_PARAMS,
    seed: int | None = None,
    weights: CostWeights = DEFAULT_WEIGHTS,
    warm_start: list[int] | None = None,
) -> SolverResult:
    """Run the GA and return the best route found plus best-cost-per-generation history.

    warm_start: previous best order to resume from (live re-optimization).
    """
    started = time.perf_counter()
    n = problem.num_stops
    if n == 0:
        evaluation = evaluate_route([], problem, weights)
        return SolverResult([], evaluation.total_cost, evaluation)

    rng = random.Random(seed)

    def cost_of(c: Chromosome) -> float:
        return route_cost(c, problem, weights)

    population: list[Chromosome] = []
    for _ in range(params.population_size):
        c = list(range(n))
        rng.shuffle(c)
        population.append(c)
    if warm_start is not None:
        if sorted(warm_start) != list(range(n)):
            raise ValueError("warm_start must be a permutation of the problem's stop indices")
        population[0] = list(warm_start)
    costs = [cost_of(c) for c in population]

    best_idx = min(range(len(population)), key=lambda k: costs[k])
    best_order, best_cost = list(population[best_idx]), costs[best_idx]
    history: list[float] = []
    snapshot_at = snapshot_iterations(params.generations)
    snapshots: list[Snapshot] = []

    for generation in range(1, params.generations + 1):
        ranked = sorted(range(len(population)), key=lambda k: costs[k])
        next_pop = [list(population[k]) for k in ranked[: params.elitism]]
        next_costs = [costs[k] for k in ranked[: params.elitism]]

        while len(next_pop) < params.population_size:
            p1 = _tournament(population, costs, params.tournament_size, rng)
            if rng.random() < params.crossover_rate:
                p2 = _tournament(population, costs, params.tournament_size, rng)
                child = order_crossover(p1, p2, rng)
            else:
                child = list(p1)
            if rng.random() < params.mutation_rate:
                child = inversion_mutation(child, rng)
            next_pop.append(child)
            next_costs.append(cost_of(child))

        population, costs = next_pop, next_costs
        gen_best = min(range(len(population)), key=lambda k: costs[k])
        if costs[gen_best] < best_cost:
            best_order, best_cost = list(population[gen_best]), costs[gen_best]
        history.append(best_cost)
        if generation in snapshot_at:
            snapshots.append(Snapshot(generation, list(best_order), best_cost))

    evaluation = evaluate_route(best_order, problem, weights)
    return SolverResult(
        order=best_order,
        cost=best_cost,
        evaluation=evaluation,
        history=history,
        iterations=params.generations,
        elapsed_seconds=time.perf_counter() - started,
        snapshots=snapshots,
    )
