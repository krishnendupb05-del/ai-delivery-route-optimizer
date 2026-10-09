import random
import time
from typing import Dict, List, Tuple
from algorithms.core_models import DistanceMatrix, Priority, Stop, Vehicle
from algorithms.cost_function import CostFunction


class AntColonyOptimizer:
    """
    Ant Colony Optimization (ACO) algorithm implemented from scratch
    for Capacitated Vehicle Routing Problem with Time Windows & Delivery Priority (CVRPTW-P).
    """

    def __init__(
        self,
        stops: List[Stop],
        vehicle: Vehicle,
        distance_matrix: DistanceMatrix,
        num_ants: int = 30,
        iterations: int = 100,
        alpha: float = 1.2,
        beta: float = 2.8,
        evaporation_rate: float = 0.15,
        q: float = 100.0,
        random_seed: int = 42,
    ):
        self.stops = stops
        self.vehicle = vehicle
        self.dm = distance_matrix
        self.cost_fn = CostFunction(self.dm, self.vehicle)

        self.num_ants = num_ants
        self.iterations = iterations
        self.alpha = alpha  # pheromone sensitivity
        self.beta = beta  # heuristic desirability sensitivity
        self.rho = evaporation_rate  # evaporation coefficient
        self.q = q
        self.rng = random.Random(random_seed)

        # Initialize pheromone trails
        self.pheromones: Dict[Tuple[int, int], float] = {}
        self.initial_pheromone = 1.0
        self._init_pheromones()

    def _init_pheromones(self):
        for s1 in self.stops:
            for s2 in self.stops:
                if s1.id != s2.id:
                    self.pheromones[(s1.id, s2.id)] = self.initial_pheromone

    def _heuristic(self, from_id: int, to_id: int) -> float:
        dist = self.dm.get_distance(from_id, to_id)
        if dist >= 999999.0:
            return 0.000001
        dest_stop = self.dm.stop_map.get(to_id)
        # Priority weight bonus: higher priority makes the stop more desirable to visit earlier
        prio_weight = 1.0 + (0.35 * int(dest_stop.priority)) if dest_stop else 1.0
        return (prio_weight / (dist + 0.1))

    def _construct_ant_route(self) -> List[int]:
        unvisited = [s.id for s in self.stops if not s.is_depot]
        route = [0]  # Start at depot
        current = 0

        while unvisited:
            probabilities = []
            candidates = []

            for candidate in unvisited:
                # If road is blocked, minimize probability
                if self.dm.is_edge_closed(current, candidate):
                    continue

                tau = self.pheromones.get((current, candidate), self.initial_pheromone) ** self.alpha
                eta = self._heuristic(current, candidate) ** self.beta
                p = tau * eta
                if p > 0:
                    probabilities.append(p)
                    candidates.append(candidate)

            # If all remaining edges are blocked, fallback to any unvisited stop
            if not candidates:
                chosen = self.rng.choice(unvisited)
            else:
                total_prob = sum(probabilities)
                if total_prob == 0:
                    chosen = self.rng.choice(candidates)
                else:
                    norm_probs = [p / total_prob for p in probabilities]
                    # Roulette wheel selection
                    r = self.rng.random()
                    cumulative = 0.0
                    chosen = candidates[-1]
                    for cand, prob in zip(candidates, norm_probs):
                        cumulative += prob
                        if r <= cumulative:
                            chosen = cand
                            break

            route.append(chosen)
            unvisited.remove(chosen)
            current = chosen

        route.append(0)  # Return to depot
        return route

    def optimize(self) -> dict:
        start_time = time.perf_counter()
        best_route = None
        best_eval = None
        best_cost = float("inf")
        convergence_history = []

        for it in range(1, self.iterations + 1):
            iteration_routes = []
            iteration_evals = []

            # 1. Ants construct solutions
            for _ in range(self.num_ants):
                route = self._construct_ant_route()
                ev = self.cost_fn.evaluate(route)
                iteration_routes.append(route)
                iteration_evals.append(ev)

                if ev["cost"] < best_cost:
                    best_cost = ev["cost"]
                    best_route = route
                    best_eval = ev

            # 2. Pheromone evaporation
            for edge in self.pheromones:
                self.pheromones[edge] = max(0.001, (1.0 - self.rho) * self.pheromones[edge])

            # 3. Pheromone reinforcement (Deposit)
            for route, ev in zip(iteration_routes, iteration_evals):
                if ev["cost"] > 0:
                    deposit = self.q / ev["cost"]
                    for i in range(len(route) - 1):
                        u, v = route[i], route[i + 1]
                        if (u, v) in self.pheromones:
                            self.pheromones[(u, v)] += deposit

            # Elitist reinforcement for global best route
            if best_route and best_cost > 0:
                elite_deposit = (2.0 * self.q) / best_cost
                for i in range(len(best_route) - 1):
                    u, v = best_route[i], best_route[i + 1]
                    if (u, v) in self.pheromones:
                        self.pheromones[(u, v)] += elite_deposit

            avg_cost = sum(e["cost"] for e in iteration_evals) / len(iteration_evals)
            convergence_history.append({
                "iteration": it,
                "best_cost": round(best_cost, 2),
                "best_distance": round(best_eval["distance_km"], 2) if best_eval else 0.0,
                "avg_cost": round(avg_cost, 2),
            })

        elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)

        return {
            "algorithm": "Ant Colony Optimization (ACO)",
            "execution_time_ms": elapsed_ms,
            "route_ids": best_route,
            "evaluation": best_eval,
            "convergence_history": convergence_history,
            "hyperparameters": {
                "num_ants": self.num_ants,
                "iterations": self.iterations,
                "alpha": self.alpha,
                "beta": self.beta,
                "evaporation_rate": self.rho,
            },
        }
