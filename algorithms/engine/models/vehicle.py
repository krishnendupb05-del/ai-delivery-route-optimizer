"""Delivery vehicle model."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class Vehicle:
    capacity: float
    id: int | None = None

    def __post_init__(self) -> None:
        if self.capacity <= 0:
            raise ValueError("vehicle capacity must be positive")

    def to_dict(self) -> dict[str, Any]:
        return {"id": self.id, "capacity": self.capacity}

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Vehicle:
        return cls(id=data.get("id"), capacity=float(data["capacity"]))
