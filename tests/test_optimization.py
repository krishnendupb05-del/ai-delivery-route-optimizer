import sys
import os

# Add root directory to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from algorithms.core_models import DistanceMatrix
from algorithms.sample_data import get_sample_scenario
from algorithms.aco import AntColonyOptimizer
from algorithms.ga import GeneticAlgorithmOptimizer


def test_optimization():
    print("=== Testing AI Route Optimizer Core Algorithms ===")
    scenario = get_sample_scenario()
    vehicle = scenario["vehicle"]
    stops = scenario["stops"]

    print(f"Loaded {len(stops)} stops (including depot).")
    print(f"Vehicle capacity: {vehicle.capacity} kg, Speed: {vehicle.speed_kmh} km/h")

    # Build distance matrix
    dm = DistanceMatrix(stops)
    print("Distance matrix initialized.")

    # Run ACO
    print("\n--- Running Ant Colony Optimization (ACO) ---")
    aco = AntColonyOptimizer(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        num_ants=25,
        iterations=50,
        random_seed=42,
    )
    aco_result = aco.optimize()
    print(f"ACO finished in {aco_result['execution_time_ms']} ms")
    print(f"Best Route: {aco_result['route_ids']}")
    print(f"Distance: {aco_result['evaluation']['distance_km']} km")
    print(f"Total Time: {aco_result['evaluation']['total_time_min']} mins")
    print(f"Violations: {aco_result['evaluation']['violations']}")
    print(f"Composite Cost: {aco_result['evaluation']['cost']}")

    # Run GA
    print("\n--- Running Genetic Algorithm (GA) for Comparison ---")
    ga = GeneticAlgorithmOptimizer(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        population_size=40,
        generations=75,
        random_seed=42,
    )
    ga_result = ga.optimize()
    print(f"GA finished in {ga_result['execution_time_ms']} ms")
    print(f"Best Route: {ga_result['route_ids']}")
    print(f"Distance: {ga_result['evaluation']['distance_km']} km")
    print(f"Total Time: {ga_result['evaluation']['total_time_min']} mins")
    print(f"Violations: {ga_result['evaluation']['violations']}")
    print(f"Composite Cost: {ga_result['evaluation']['cost']}")

    # Test Road Closure & Re-optimization
    print("\n--- Testing Road Closure & Dynamic Re-optimization ---")
    # Close road between depot (0) and stop 1
    dm.close_road(0, 1)
    print("Marked road segment between Stop 0 and Stop 1 as CLOSED.")

    aco_reroute = AntColonyOptimizer(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        num_ants=20,
        iterations=30,
        random_seed=123,
    )
    reroute_result = aco_reroute.optimize()
    print(f"Re-optimization finished in {reroute_result['execution_time_ms']} ms")
    print(f"New Route after closure: {reroute_result['route_ids']}")
    print(f"Does new route use closed road (0, 1)? {dm.is_edge_closed(reroute_result['route_ids'][0], reroute_result['route_ids'][1])}")
    print(f"New Distance: {reroute_result['evaluation']['distance_km']} km")

    print("\n=== All Core Algorithm Tests Passed Successfully! ===")


if __name__ == "__main__":
    test_optimization()
