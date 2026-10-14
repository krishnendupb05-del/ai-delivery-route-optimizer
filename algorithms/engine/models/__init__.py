"""Data classes: Stop, Vehicle, Route, OptimizationResult, AnalyticsRecord."""
from algorithms.engine.models.analytics import AnalyticsRecord
from algorithms.engine.models.optimization_result import Algorithm, OptimizationResult
from algorithms.engine.models.route import Route
from algorithms.engine.models.stop import Priority, Stop, TimeWindow
from algorithms.engine.models.vehicle import Vehicle

__all__ = [
    "Algorithm",
    "AnalyticsRecord",
    "OptimizationResult",
    "Priority",
    "Route",
    "Stop",
    "TimeWindow",
    "Vehicle",
]
