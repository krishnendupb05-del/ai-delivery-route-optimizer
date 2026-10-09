import random
import time
from typing import List, Tuple
from algorithms.core_models import DistanceMatrix, Stop, Vehicle
from algorithms.cost_function import CostFunction


class GeneticAlgorithmOptimizer:
    """
    Genetic Algorithm (GA) implemented from scratch for CVRPTW-P
    benchmarked against Ant Colony Optimization.
    """

    def __init__(
        self,
        stops: List[Stop],
        vehicle: Vehicle,
        distance_matrix: DistanceMatrix,
        population_size: int = 50,
        generations: int = 120,
        crossover_rate: float = 0.85,
        mutation_rate: float = 0.15,
        tournament_size: int = 3,
        random_seed: int = 42,
    ):
        self.stops = stops
        self.vehicle = vehicle
        self.dm = distance_matrix
        self.cost_fn = CostFunction(self.dm, self.vehicle)

        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.tournament_size = tournament_size
        self.rng = random.Random(random_seed)

        self.delivery_stop_ids = [s.id for s in self.stops if not s.is_depot]

    def _create_individual(self) -> List[int]:
        genes = list(self.delivery_stop_ids)
        self.rng.shuffle(genes)
        return genes

    def _route_from_individual(self, individual: List[int]) -> List[int]:
        return [0] + individual + [0]

    def _tournament_select(self, population: List[List[int]], costs: List[float]) -> List[int]:
        selected_indices = self.rng.sample(range(len(population)), self.tournament_size)
        best_idx = min(selected_indices, key=lambda idx: costs[idx])
        return list(population[best_idx])

    def _order_crossover(self, parent1: List[int], parent2: List[int]) -> Tuple[List[int], List[int]]:
        """Order Crossover (OX1) preserving relative ordering without duplicates."""
        size = len(parent1)
        if size < 2:
            return list(parent1), list(parent2)

        pt1, pt2 = sorted(self.rng.sample(range(size), 2))

        def create_child(p1, p2):
            child = [-1] * size
            child[pt1 : pt2 + 1] = p1[pt1 : pt2 + 1]
            p1_segment_set = set(child[pt1 : pt2 + 1])

            p2_filtered = [item for item in p2 if item not in p1_segment_set]
            p2_idx = 0
            for i in range(size):
                if child[i] == -1:
                    child[i] = p2_filtered[p2_idx]
                    p2_idx += 1
            return child

        return create_child(parent1, parent2), create_child(parent2, parent1)

    def _mutate(self, individual: List[int]) -> List[int]:
        mutated = list(individual)
        if len(mutated) < 2:
            return mutated

        if self.rng.random() < self.mutation_rate:
            # Swap mutation
            i, j = self.rng.sample(range(len(mutated)), 2)
            mutated[i], mutated[j] = mutated[j], mutated[i]

        if self.rng.random() < (self.mutation_rate * 0.5):
            # Inversion mutation
            i, j = sorted(self.rng.sample(range(len(mutated)), 2))
            mutated[i : j + 1] = reversed(mutated[i : j + 1])

        return mutated

    def optimize(self) -> dict:
        start_time = time.perf_counter()

        # Initialize population
        population = [self._create_individual() for _ in range(self.population_size)]
        evaluations = [self.cost_fn.evaluate(self._route_from_individual(ind)) for ind in population]
        costs = [ev["cost"] for ev in evaluations]

        best_idx = min(range(len(costs)), key=lambda i: costs[i])
        best_individual = list(population[best_idx])
        best_eval = evaluations[best_idx]
        best_cost = costs[best_idx]

        convergence_history = []

        for gen in range(1, self.generations + 1):
            new_population = []

            # Elitism: retain top 2 best solutions
            sorted_indices = sorted(range(len(costs)), key=lambda i: costs[i])
            new_population.append(list(population[sorted_indices[0]]))
            if len(population) > 1:
                new_population.append(list(population[sorted_indices[1]]))

            # Generate rest of new population
            while len(new_population) < self.population_size:
                p1 = self._tournament_select(population, costs)
                p2 = self._tournament_select(population, costs)

                if self.rng.random() < self.crossover_rate:
                    c1, c2 = self._order_crossover(p1, p2)
                else:
                    c1, c2 = list(p1), list(p2)

                new_population.append(self._mutate(c1))
                if len(new_population) < self.population_size:
                    new_population.append(self._mutate(c2))

            population = new_population
            evaluations = [self.cost_fn.evaluate(self._route_from_individual(ind)) for ind in population]
            costs = [ev["cost"] for ev in evaluations]

            cur_best_idx = min(range(len(costs)), key=lambda i: costs[i])
            if costs[cur_best_idx] < best_cost:
                best_cost = costs[cur_best_idx]
                best_individual = list(population[cur_best_idx])
                best_eval = evaluations[cur_best_idx]

            avg_cost = sum(costs) / len(costs)
            convergence_history.append({
                "iteration": gen,
                "best_cost": round(best_cost, 2),
                "best_distance": round(best_eval["distance_km"], 2) if best_eval else 0.0,
                "avg_cost": round(avg_cost, 2),
            })

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
        best_route = self._route_from_individual(best_individual)

        return {
            "algorithm": "Genetic Algorithm (GA)",
            "execution_time_ms": elapsed_ms,
            "route_ids": best_route,
            "evaluation": best_eval,
            "convergence_history": convergence_history,
            "hyperparameters": {
                "population_size": self.population_size,
                "generations": self.generations,
                "crossover_rate": self.crossover_rate,
                "mutation_rate": self.mutation_rate,
                "tournament_size": self.tournament_size,
            },
        }
