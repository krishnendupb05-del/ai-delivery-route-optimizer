"""Output of one ACO or GA run."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from algorithms.engine.models.route import Route


class Algorithm(str, Enum):
    ACO = "ACO"
    GA = "GA"


@dataclass
class OptimizationResult:
    """`history` (best cost per iteration/generation) is not in the class
    diagram but is needed to draw the convergence chart."""

    algorithm: Algorithm
    route: Route
    cost: float
    iterations: int
    history: list[float] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not isinstance(self.algorithm, Algorithm):
            self.algorithm = Algorithm(self.algorithm)
        if self.iterations < 0:
            raise ValueError("iterations must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return {
            "algorithm": self.algorithm.value,
            "route": self.route.to_dict(),
            "cost": self.cost,
            "iterations": self.iterations,
            "history": list(self.history),
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> OptimizationResult:
        return cls(
            algorithm=Algorithm(data["algorithm"]),
            route=Route.from_dict(data["route"]),
            cost=float(data["cost"]),
            iterations=int(data["iterations"]),
            history=[float(c) for c in data.get("history", [])],
        )
