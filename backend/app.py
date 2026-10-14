import os
import sys
from typing import Any, Dict, List, Optional

# Ensure root folder is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from flask import Flask, jsonify, render_template, request
from flask_cors import CORS

from algorithms.aco import AntColonyOptimizer
from algorithms.core_models import DistanceMatrix, Priority, Stop, Vehicle
from algorithms.cost_function import CostFunction
from algorithms.engine_adapter import optimize as run_engine_optimization
from algorithms.ga import GeneticAlgorithmOptimizer
from backend import database
from backend.disruption import DisruptionEngine
from backend.models import StopModel, VehicleConfigModel

app = Flask(
    __name__,
    template_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "templates")),
    static_folder=os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "static")),
)
CORS(app)

# Initialize SQLite database schema and seed data
database.init_db()


def get_current_environment(capacity: Optional[float] = None, speed_kmh: Optional[float] = None):
    v_config = database.get_active_vehicle_config()
    eff_capacity = capacity if capacity is not None else v_config.capacity
    eff_speed = speed_kmh if speed_kmh is not None else v_config.speed_kmh

    stops = database.get_all_stops()
    vehicle = Vehicle(id=v_config.id, capacity=eff_capacity, speed_kmh=eff_speed)
    dm = DistanceMatrix(stops)

    # Apply stored road closures
    closures = database.get_all_closures()
    for c in closures:
        dm.close_road(c["from_id"], c["to_id"])

    return stops, vehicle, dm


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/stops", methods=["GET"])
def get_stops():
    stops = database.get_all_stops()
    return jsonify([s.to_dict() for s in stops])


@app.route("/api/stops", methods=["POST"])
def add_stop():
    data = request.json or {}
    try:
        name = data.get("name", "New Delivery Stop")
        lat = float(data.get("lat"))
        lng = float(data.get("lng"))
        demand = float(data.get("demand", 20.0))
        tw_start = float(data.get("tw_start", 0.0))
        tw_end = float(data.get("tw_end", 480.0))
        service_time = float(data.get("service_time", 10.0))
        priority = data.get("priority", "NORMAL")

        # Validate input bounds
        stop_model = StopModel(
            id=0,
            name=name,
            lat=lat,
            lng=lng,
            demand=demand,
            tw_start=tw_start,
            tw_end=tw_end,
            service_time=service_time,
            priority=priority,
            is_depot=False,
        )
        is_valid, err_msg = stop_model.validate()
        if not is_valid:
            return jsonify({"success": False, "error": err_msg}), 422

        stop_id = database.add_or_update_stop(
            name=name,
            lat=lat,
            lng=lng,
            demand=demand,
            tw_start=tw_start,
            tw_end=tw_end,
            service_time=service_time,
            priority=priority,
            is_depot=False,
        )
        return jsonify({"success": True, "id": stop_id}), 201
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 400


@app.route("/api/stops/<int:stop_id>", methods=["DELETE"])
def delete_stop(stop_id):
    success = database.delete_stop(stop_id)
    if success:
        return jsonify({"success": True})
    return jsonify({"success": False, "error": "Cannot delete depot or stop not found"}), 400


@app.route("/api/reset-scenario", methods=["POST"])
def reset_scenario():
    database.seed_sample_stops()
    conn = database.get_connection()
    conn.execute("DELETE FROM road_closures")
    conn.commit()
    conn.close()
    return jsonify({"success": True, "message": "Demo scenario reset successfully"})


@app.route("/api/closures", methods=["GET"])
def get_closures():
    return jsonify(database.get_all_closures())


@app.route("/api/closures/toggle", methods=["POST"])
def toggle_closure():
    data = request.json or {}
    from_id = int(data.get("from_id"))
    to_id = int(data.get("to_id"))
    is_closed = bool(data.get("is_closed", True))
    database.toggle_closure(from_id, to_id, is_closed)
    return jsonify({"success": True, "closures": database.get_all_closures()})


@app.route("/api/optimize", methods=["POST"])
def optimize():
    data = request.json or {}
    algo_choice = data.get("algorithm", "aco").lower()
    capacity = float(data.get("capacity", 400.0))
    speed = float(data.get("speed", 35.0))

    stops, vehicle, dm = get_current_environment(capacity=capacity, speed_kmh=speed)

    # Input Validation: Check total delivery load against vehicle capacity before dispatch
    total_demand = sum(s.demand for s in stops if not s.is_depot)
    v_config = database.get_active_vehicle_config()
    v_config.capacity = capacity
    is_cap_valid, cap_err = v_config.validate_capacity(total_demand)
    if not is_cap_valid and data.get("enforce_capacity", True):
        return jsonify({
            "success": False,
            "error": "Capacity Overload",
            "message": cap_err,
            "total_demand": round(total_demand, 2),
            "vehicle_capacity": round(vehicle.capacity, 2),
        }), 422

    # 1. Evaluate baseline unoptimized route (Sequential ID order: 0 -> 1 -> 2 ... -> 0)
    naive_route = [0] + [s.id for s in stops if not s.is_depot] + [0]
    cost_fn = CostFunction(dm, vehicle)
    baseline_eval = cost_fn.evaluate(naive_route)

    # 2. Run selected algorithm using the new engine adapter
    result = run_engine_optimization(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        algorithm=algo_choice,
        num_ants=int(data.get("num_ants", 30)),
        iterations=int(data.get("iterations", 80)),
        population_size=int(data.get("population_size", 40)),
        generations=int(data.get("generations", 80)),
    )

    # Restore the depot at the start and end of the route
    depot_id = next(s.id for s in stops if s.is_depot)
    result["route_ids"] = [
        depot_id,
        *result["route_ids"],
        depot_id,
    ]

    # Use the existing evaluator to preserve the frontend's expected fields
    eval_res = cost_fn.evaluate(result["route_ids"])

    # Preserve the algorithm names used by the existing frontend
    result["algorithm"] = (
        "Genetic Algorithm (GA)"
        if algo_choice == "ga"
        else "Ant Colony Optimization (ACO)"
    )

    dist_saved_km = max(0.0, baseline_eval["distance_km"] - eval_res["distance_km"])
    pct_saved = (
        round((dist_saved_km / baseline_eval["distance_km"]) * 100, 1)
        if baseline_eval["distance_km"] > 0
        else 0.0
    )

    ordered_stops = []
    for sid in result["route_ids"]:
        s = dm.stop_map.get(sid)
        if s:
            ordered_stops.append(s.to_dict())

    # Record in database
    database.record_route_run(
        algorithm=result["algorithm"],
        route_ids=result["route_ids"],
        distance_km=eval_res["distance_km"],
        total_time_min=eval_res["total_time_min"],
        execution_time_ms=result["execution_time_ms"],
        cost=eval_res["cost"],
        is_valid=eval_res["is_valid"],
        violations=eval_res["violations"],
    )

    return jsonify({
        "algorithm": result["algorithm"],
        "execution_time_ms": result["execution_time_ms"],
        "route_ids": result["route_ids"],
        "ordered_stops": ordered_stops,
        "evaluation": eval_res,
        "baseline": {
            "route_ids": naive_route,
            "distance_km": baseline_eval["distance_km"],
            "total_time_min": baseline_eval["total_time_min"],
        },
        "improvements": {
            "distance_saved_km": round(dist_saved_km, 2),
            "percentage_saved": pct_saved,
        },
        "convergence_history": result["convergence_history"],
    })


@app.route("/api/reroute", methods=["POST"])
def reroute():
    data = request.json or {}
    current_route = data.get("current_route", [])
    from_id = data.get("from_id")
    to_id = data.get("to_id")
    algorithm = data.get("algorithm", "aco").lower()

    if not current_route:
        return jsonify({"success": False, "error": "'current_route' list is required"}), 400

    disrupted_edge = None
    if from_id is not None and to_id is not None:
        disrupted_edge = (int(from_id), int(to_id))
        database.toggle_closure(disrupted_edge[0], disrupted_edge[1], is_closed=True)

    engine = DisruptionEngine()
    result = engine.rapid_reroute(
        current_route=current_route,
        disrupted_edge=disrupted_edge,
        algorithm=algorithm,
    )
    return jsonify(result)


@app.route("/api/vehicle", methods=["GET"])
def get_vehicle_config():
    v = database.get_active_vehicle_config()
    return jsonify(v.to_dict())


@app.route("/api/vehicle", methods=["POST"])
def update_vehicle():
    data = request.json or {}
    capacity = float(data.get("capacity", 400.0))
    speed = float(data.get("speed_kmh", data.get("speed", 35.0)))
    name = data.get("name", "Primary Electric Delivery Van")
    v = database.update_vehicle_config(capacity=capacity, speed_kmh=speed, name=name)
    return jsonify({"success": True, "vehicle": v.to_dict()})


@app.route("/api/compare", methods=["POST"])
def compare():
    data = request.json or {}
    capacity = float(data.get("capacity", 400.0))
    speed = float(data.get("speed", 35.0))

    stops, vehicle, dm = get_current_environment(capacity=capacity, speed_kmh=speed)

    naive_route = [0] + [s.id for s in stops if not s.is_depot] + [0]
    cost_fn = CostFunction(dm, vehicle)
    baseline_eval = cost_fn.evaluate(naive_route)
    depot_id = next(s.id for s in stops if s.is_depot)

    # Run ACO using Person 1's new algorithm engine
    aco_res = run_engine_optimization(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        algorithm="aco",
        num_ants=int(data.get("num_ants", 30)),
        iterations=int(data.get("iterations", 80)),
    )
    aco_route = [depot_id, *aco_res["route_ids"], depot_id]
    aco_eval = cost_fn.evaluate(aco_route)

    # Run GA using Person 1's new algorithm engine
    ga_res = run_engine_optimization(
        stops=stops,
        vehicle=vehicle,
        distance_matrix=dm,
        algorithm="ga",
        population_size=int(data.get("population_size", 40)),
        generations=int(data.get("generations", 80)),
    )
    ga_route = [depot_id, *ga_res["route_ids"], depot_id]
    ga_eval = cost_fn.evaluate(ga_route)

    return jsonify({
        "baseline": {
            "distance_km": baseline_eval["distance_km"],
            "total_time_min": baseline_eval["total_time_min"],
        },
        "aco": {
            "algorithm": "Ant Colony Optimization (ACO)",
            "execution_time_ms": aco_res["execution_time_ms"],
            "route_ids": aco_route,
            "evaluation": aco_eval,
            "convergence": aco_res["convergence_history"],
        },
        "ga": {
            "algorithm": "Genetic Algorithm (GA)",
            "execution_time_ms": ga_res["execution_time_ms"],
            "route_ids": ga_route,
            "evaluation": ga_eval,
            "convergence": ga_res["convergence_history"],
        },
    })


@app.route("/api/analytics", methods=["GET"])
def get_analytics():
    return jsonify(database.get_analytics_summary())


if __name__ == "__main__":
    print("Starting AI Delivery Route Optimizer on http://127.0.0.1:5000 ...")
    app.run(host="127.0.0.1", port=5000, debug=True)