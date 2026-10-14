"""An ordered sequence of stops with aggregate distance and time."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from algorithms.engine.models.stop import Stop


@dataclass
class Route:
    stops: list[Stop] = field(default_factory=list)
    total_distance: float = 0.0
    total_time: float = 0.0
    id: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "stops": [s.to_dict() for s in self.stops],
            "total_distance": self.total_distance,
            "total_time": self.total_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Route:
        return cls(
            id=data.get("id"),
            stops=[Stop.from_dict(s) for s in data.get("stops", [])],
            total_distance=float(data.get("total_distance", 0.0)),
            total_time=float(data.get("total_time", 0.0)),
        )
