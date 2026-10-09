from typing import Dict, List, Tuple
from algorithms.core_models import DistanceMatrix, Priority, Stop, Vehicle


class CostFunction:
    """
    Evaluates multi-constraint cost for a candidate delivery route.
    Constraints handled:
    1. Vehicle capacity limits (CVRP)
    2. Customer delivery time windows (VRPTW)
    3. Delivery priority levels (Critical / High / Normal / Low)
    4. Closed road penalties (Disruptions)
    """

    def __init__(
        self,
        distance_matrix: DistanceMatrix,
        vehicle: Vehicle,
        w_distance: float = 1.0,
        w_time_window_late: float = 10.0,
        w_capacity_excess: float = 50.0,
        w_priority_delay: float = 2.0,
        w_closed_edge: float = 10000.0,
    ):
        self.dm = distance_matrix
        self.vehicle = vehicle
        self.w_distance = w_distance
        self.w_tw = w_time_window_late
        self.w_cap = w_capacity_excess
        self.w_priority = w_priority_delay
        self.w_closed = w_closed_edge

    def evaluate(self, route_ids: List[int]) -> dict:
        """
        route_ids: list of stop IDs in visit order, e.g. [0, 3, 1, 4, 2, 0]
        starting and ending at the depot (0).
        """
        if not route_ids or len(route_ids) < 2:
            return {
                "cost": float("inf"),
                "distance_km": 0.0,
                "total_time_min": 0.0,
                "is_valid": False,
                "capacity_used": 0.0,
                "capacity_limit": self.vehicle.capacity,
                "violations": ["Route must have at least depot start and end"],
                "timeline": [],
            }

        total_distance = 0.0
        current_time = 0.0  # in minutes from shift start
        total_load = 0.0
        tw_violations_min = 0.0
        priority_penalty = 0.0
        closed_edge_hits = 0
        violations = []
        timeline = []

        # Check total load
        for sid in route_ids:
            if sid != 0 and sid in self.dm.stop_map:
                total_load += self.dm.stop_map[sid].demand

        excess_load = max(0.0, total_load - self.vehicle.capacity)
        if excess_load > 0:
            violations.append(f"Load {total_load:.1f}kg exceeds vehicle capacity {self.vehicle.capacity:.1f}kg by {excess_load:.1f}kg")

        # Traverse route
        for i in range(len(route_ids) - 1):
            u = route_ids[i]
            v = route_ids[i + 1]

            # Check if road is closed
            if self.dm.is_edge_closed(u, v):
                closed_edge_hits += 1
                violations.append(f"Road segment between Stop {u} and Stop {v} is closed")

            leg_dist = self.dm.get_distance(u, v)
            leg_time = self.dm.get_travel_time_minutes(u, v, self.vehicle.speed_kmh)

            total_distance += leg_dist
            arrival_time = current_time + leg_time

            stop_v = self.dm.stop_map.get(v)
            wait_time = 0.0
            lateness = 0.0

            if stop_v and not stop_v.is_depot:
                window_start, window_end = stop_v.time_window
                # Arrived before window opens -> vehicle must wait
                if arrival_time < window_start:
                    wait_time = window_start - arrival_time
                    service_start = window_start
                else:
                    service_start = arrival_time

                # Arrived after window closes -> lateness penalty
                if service_start > window_end:
                    lateness = service_start - window_end
                    tw_violations_min += lateness
                    violations.append(
                        f"Stop {v} ({stop_v.name}) delivered {lateness:.1f} mins late (deadline {window_end:.0f}m)"
                    )

                # Priority weighting penalty: higher priority delivered later incur higher penalty
                # Critical priority stops (4) delayed accumulate 4x penalty per minute
                priority_weight = int(stop_v.priority)
                priority_penalty += priority_weight * (service_start / 30.0)
                if lateness > 0:
                    priority_penalty += priority_weight * lateness * 2.0

                departure_time = service_start + stop_v.service_time
                current_time = departure_time
            else:
                service_start = arrival_time
                departure_time = arrival_time
                current_time = departure_time

            timeline.append({
                "from_id": u,
                "to_id": v,
                "distance_km": round(leg_dist, 2),
                "arrival_time": round(arrival_time, 1),
                "departure_time": round(departure_time, 1),
                "wait_time": round(wait_time, 1),
                "lateness": round(lateness, 1),
            })

        # Calculate final composite cost
        composite_cost = (
            (self.w_distance * total_distance)
            + (self.w_tw * tw_violations_min)
            + (self.w_cap * excess_load)
            + (self.w_priority * priority_penalty)
            + (self.w_closed * closed_edge_hits)
        )

        is_valid = (excess_load == 0.0) and (tw_violations_min == 0.0) and (closed_edge_hits == 0)

        return {
            "cost": round(composite_cost, 2),
            "distance_km": round(total_distance, 2),
            "total_time_min": round(current_time, 1),
            "is_valid": is_valid,
            "capacity_used": round(total_load, 1),
            "capacity_limit": self.vehicle.capacity,
            "violations": violations,
            "lateness_minutes": round(tw_violations_min, 1),
            "timeline": timeline,
        }
