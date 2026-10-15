import json
import os
import sys
import unittest

# Ensure root directory is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend import database
from backend.app import app
from backend.disruption import DisruptionEngine
from backend.models import StopModel, VehicleConfigModel


class TestPerson2Backend(unittest.TestCase):
    def setUp(self):
        # Configure app for testing
        self.client = app.test_client()
        database.init_db()
        database.seed_sample_stops()

    def test_stop_model_validation(self):
        """Test input validation boundaries for stops."""
        # Valid stop
        valid_stop = StopModel(
            id=10,
            name="Valid Stop",
            lat=12.9716,
            lng=77.5946,
            demand=25.0,
            tw_start=60.0,
            tw_end=180.0,
        )
        is_valid, err = valid_stop.validate()
        self.assertTrue(is_valid)
        self.assertIsNone(err)

        # Invalid latitude (> 90)
        invalid_lat = StopModel(id=11, name="Bad Lat", lat=105.0, lng=77.0)
        is_valid, err = invalid_lat.validate()
        self.assertFalse(is_valid)
        self.assertIn("Latitude", err)

        # Negative demand
        invalid_demand = StopModel(id=12, name="Negative Demand", lat=12.0, lng=77.0, demand=-10.0)
        is_valid, err = invalid_demand.validate()
        self.assertFalse(is_valid)
        self.assertIn("negative", err)

        # Inverted time windows
        invalid_tw = StopModel(id=13, name="Bad TW", lat=12.0, lng=77.0, tw_start=200.0, tw_end=100.0)
        is_valid, err = invalid_tw.validate()
        self.assertFalse(is_valid)
        self.assertIn("cannot exceed", err)

    def test_vehicle_capacity_validation(self):
        """Test capacity overload validation check before dispatch."""
        v = VehicleConfigModel(id=1, capacity=300.0)
        # Safe demand
        is_valid, err = v.validate_capacity(250.0)
        self.assertTrue(is_valid)

        # Overloaded demand
        is_valid, err = v.validate_capacity(350.0)
        self.assertFalse(is_valid)
        self.assertIn("Capacity overload", err)

    def test_database_vehicle_configs(self):
        """Test reading and updating vehicle configurations in SQLite."""
        v = database.get_active_vehicle_config()
        self.assertIsNotNone(v)
        self.assertEqual(v.id, 1)

        # Update config
        updated = database.update_vehicle_config(capacity=550.0, speed_kmh=42.0, name="Heavy Van")
        self.assertEqual(updated.capacity, 550.0)
        self.assertEqual(updated.speed_kmh, 42.0)
        self.assertEqual(updated.name, "Heavy Van")

        # Reset back to default
        database.update_vehicle_config(capacity=400.0, speed_kmh=35.0, name="Primary Electric Delivery Van")

    def test_disruption_engine_rapid_reroute(self):
        """Test Module 4: Road Closure & Dynamic Re-routing Engine."""
        engine = DisruptionEngine()
        current_route = [0, 1, 5, 4, 7, 2, 8, 3, 6, 0]

        # Close road between Stop 0 and Stop 1
        closure_res = engine.handle_closure(from_id=0, to_id=1, is_closed=True)
        self.assertTrue(closure_res["is_closed"])

        # Check impact
        is_impacted = engine.is_route_impacted(current_route, from_id=0, to_id=1)
        self.assertTrue(is_impacted)

        # Execute warm-start rapid re-routing
        reroute_res = engine.rapid_reroute(current_route=current_route, disrupted_edge=(0, 1))
        self.assertTrue(reroute_res["reroute_needed"])
        new_route = reroute_res["route_ids"]

        # Ensure new route avoids the closed segment (0, 1)
        edge_used = engine.dm.is_edge_closed(new_route[0], new_route[1])
        self.assertFalse(edge_used)
        self.assertLess(reroute_res["execution_time_ms"], 200.0)  # Very fast execution

        # Reopen road
        engine.handle_closure(from_id=0, to_id=1, is_closed=False)

    def test_api_stops_endpoints(self):
        """Test GET and POST /api/stops including validation."""
        # GET stops
        resp = self.client.get("/api/stops")
        self.assertEqual(resp.status_code, 200)
        stops = resp.get_json()
        self.assertGreater(len(stops), 0)

        # POST invalid stop (negative demand)
        bad_stop_resp = self.client.post(
            "/api/stops",
            json={"name": "Bad Stop", "lat": 12.9, "lng": 77.6, "demand": -5.0},
        )
        self.assertEqual(bad_stop_resp.status_code, 422)

        # POST valid stop
        good_stop_resp = self.client.post(
            "/api/stops",
            json={
                "name": "Warehouse North",
                "lat": 12.98,
                "lng": 77.62,
                "demand": 15.0,
                "tw_start": 30.0,
                "tw_end": 200.0,
                "priority": "HIGH",
            },
        )
        self.assertEqual(good_stop_resp.status_code, 201)
        data = good_stop_resp.get_json()
        self.assertTrue(data["success"])

    def test_api_optimize_capacity_overload_rejection(self):
        """Test that /api/optimize rejects dispatch if single trip enforcement is requested or single package exceeds capacity."""
        overload_resp = self.client.post(
            "/api/optimize",
            json={"algorithm": "aco", "capacity": 50.0, "enforce_single_trip": True},
        )
        self.assertEqual(overload_resp.status_code, 422)
        data = overload_resp.get_json()
        self.assertFalse(data["success"])
        self.assertEqual(data["error"], "Capacity Overload")

        # Multi-trip routing with 80kg capacity should succeed and produce multiple trips
        multitrip_resp = self.client.post(
            "/api/optimize",
            json={"algorithm": "aco", "capacity": 80.0},
        )
        self.assertEqual(multitrip_resp.status_code, 200)
        mt_data = multitrip_resp.get_json()
        self.assertGreaterEqual(mt_data.get("num_trips", 1), 2)

    def test_api_reroute_endpoint(self):
        """Test POST /api/reroute endpoint."""
        current_route = [0, 1, 5, 4, 7, 2, 8, 3, 6, 0]
        resp = self.client.post(
            "/api/reroute",
            json={
                "current_route": current_route,
                "from_id": 0,
                "to_id": 1,
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = resp.get_json()
        self.assertTrue(data["reroute_needed"])
        self.assertIn("route_ids", data)
        self.assertIn("execution_time_ms", data)
        self.assertIn("distance_delta_km", data)

    def test_api_vehicle_endpoint(self):
        """Test GET and POST /api/vehicle."""
        get_resp = self.client.get("/api/vehicle")
        self.assertEqual(get_resp.status_code, 200)
        v = get_resp.get_json()
        self.assertIn("capacity", v)

        post_resp = self.client.post(
            "/api/vehicle",
            json={"capacity": 450.0, "speed": 40.0, "name": "Express Van"},
        )
        self.assertEqual(post_resp.status_code, 200)
        data = post_resp.get_json()
        self.assertTrue(data["success"])
        self.assertEqual(data["vehicle"]["capacity"], 450.0)


if __name__ == "__main__":
    unittest.main()
