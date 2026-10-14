import time
from typing import Any, Dict, List, Optional, Tuple

from algorithms.aco import AntColonyOptimizer
from algorithms.core_models import DistanceMatrix, Stop, Vehicle
from algorithms.cost_function import CostFunction
from algorithms.ga import GeneticAlgorithmOptimizer
from backend import database


class DisruptionEngine:
    """
    Module 4: Road Closure & Dynamic Re-routing Engine.
    Handles unexpected edge closures, updates the distance matrix with heavy penalties,
    and conducts warm-start rapid re-optimization without cold restarting.
    """

    def __init__(
        self,
        stops: Optional[List[Stop]] = None,
        vehicle: Optional[Vehicle] = None,
        distance_matrix: Optional[DistanceMatrix] = None,
    ):
        self.stops = stops or database.get_all_stops()
        v_config = database.get_active_vehicle_config()
        self.vehicle = vehicle or Vehicle(
            id=v_config.id,
            capacity=v_config.capacity,
            speed_kmh=v_config.speed_kmh,
        )
        self.dm = distance_matrix or DistanceMatrix(self.stops)
        self._sync_active_closures()

    def _sync_active_closures(self):
        """Syncs all database closures into the in-memory distance matrix."""
        closures = database.get_all_closures()
        for c in closures:
            self.dm.close_road(c["from_id"], c["to_id"])

    def handle_closure(self, from_id: int, to_id: int, is_closed: bool = True) -> Dict[str, Any]:
        """Updates database closure status and distance matrix penalties."""
        database.toggle_closure(from_id, to_id, is_closed)
        if is_closed:
            self.dm.close_road(from_id, to_id)
        else:
            self.dm.open_road(from_id, to_id)

        return {
            "from_id": min(from_id, to_id),
            "to_id": max(from_id, to_id),
            "is_closed": is_closed,
            "active_closures": database.get_all_closures(),
        }

    def is_route_impacted(self, route_ids: List[int], from_id: int, to_id: int) -> bool:
        """Checks whether the given route directly traverses the disrupted road edge."""
        target_edge = {min(from_id, to_id), max(from_id, to_id)}
        for i in range(len(route_ids) - 1):
            edge = {min(route_ids[i], route_ids[i + 1]), max(route_ids[i], route_ids[i + 1])}
            if edge == target_edge:
                return True
        return False

    def rapid_reroute(
        self,
        current_route: List[int],
        disrupted_edge: Optional[Tuple[int, int]] = None,
        algorithm: str = "aco",
    ) -> Dict[str, Any]:
        """
        Performs warm-start rapid re-routing.
        Instead of a cold restart (uniform pheromones, full 80 iterations),
        it primes the pheromone matrix using the valid segments of the prior route,
        zeros out the severed road, and runs an accelerated convergence pass (15-20 iterations).
        """
        start_time = time.perf_counter()
        cost_fn = CostFunction(self.dm, self.vehicle)

        prior_eval = cost_fn.evaluate(current_route)
        u, v = disrupted_edge if disrupted_edge else (0, 0)
        traverses_blocked = self.is_route_impacted(current_route, u, v) if disrupted_edge else False

        if disrupted_edge and not traverses_blocked and prior_eval["is_valid"]:
            exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
            return {
                "reroute_needed": False,
                "message": f"Existing route does not traverse closed segment ({u} <-> {v}). Current route remains optimal.",
                "route_ids": current_route,
                "evaluation": prior_eval,
                "execution_time_ms": exec_ms,
                "distance_delta_km": 0.0,
                "time_delta_min": 0.0,
            }

        # Warm-start rapid re-routing
        try:
            from algorithms.engine_adapter import optimize as run_engine_optimization

            opt_result = run_engine_optimization(
                stops=self.stops,
                vehicle=self.vehicle,
                distance_matrix=self.dm,
                algorithm=algorithm,
                num_ants=20,
                iterations=25,
                warm_start=current_route,
            )
            depot_id = next(s.id for s in self.stops if s.is_depot)
            new_route_ids = [depot_id, *opt_result["route_ids"], depot_id]
            new_eval = cost_fn.evaluate(new_route_ids)
            convergence = opt_result["convergence_history"]
        except Exception:
            # Robust fallback to legacy ACO solver
            optimizer = AntColonyOptimizer(
                stops=self.stops,
                vehicle=self.vehicle,
                distance_matrix=self.dm,
                num_ants=20,
                iterations=25,
                random_seed=int(time.time()),
            )
            for i in range(len(current_route) - 1):
                p1, p2 = current_route[i], current_route[i + 1]
                if not self.dm.is_edge_closed(p1, p2):
                    optimizer.pheromones[(p1, p2)] = 3.5
                    optimizer.pheromones[(p2, p1)] = 3.5
                else:
                    optimizer.pheromones[(p1, p2)] = 0.0001
                    optimizer.pheromones[(p2, p1)] = 0.0001
            legacy_res = optimizer.optimize()
            new_route_ids = legacy_res["route_ids"]
            new_eval = legacy_res["evaluation"]
            convergence = legacy_res["convergence_history"]

        exec_ms = round((time.perf_counter() - start_time) * 1000, 2)
        dist_delta = round(new_eval["distance_km"] - prior_eval["distance_km"], 2)
        time_delta = round(new_eval["total_time_min"] - prior_eval["total_time_min"], 2)

        ordered_stops = []
        for sid in new_route_ids:
            s = self.dm.stop_map.get(sid)
            if s:
                ordered_stops.append(s.to_dict())

        # Persist re-routed result to SQLite
        database.record_route_run(
            algorithm="ACO-Dynamic-Reroute",
            route_ids=new_route_ids,
            distance_km=new_eval["distance_km"],
            total_time_min=new_eval["total_time_min"],
            execution_time_ms=exec_ms,
            cost=new_eval["cost"],
            is_valid=new_eval["is_valid"],
            violations=new_eval["violations"],
        )

        return {
            "reroute_needed": True,
            "algorithm": "ACO-Dynamic-Reroute",
            "execution_time_ms": exec_ms,
            "route_ids": new_route_ids,
            "ordered_stops": ordered_stops,
            "evaluation": new_eval,
            "prior_route": current_route,
            "distance_delta_km": dist_delta,
            "time_delta_min": time_delta,
            "convergence_history": convergence,
            "disrupted_edge": list(disrupted_edge) if disrupted_edge else None,
        }