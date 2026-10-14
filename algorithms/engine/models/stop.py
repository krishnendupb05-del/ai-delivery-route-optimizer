"""Delivery stop model."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class Priority(str, Enum):
    CRITICAL = "Critical"
    HIGH = "High"
    NORMAL = "Normal"
    LOW = "Low"


MINUTES_PER_DAY = 1440


@dataclass(frozen=True)
class TimeWindow:
    """Delivery window in minutes since midnight (10:00-10:30 = 600-630)."""

    start: float
    end: float

    def __post_init__(self) -> None:
        if not (0 <= self.start <= MINUTES_PER_DAY and 0 <= self.end <= MINUTES_PER_DAY):
            raise ValueError(f"time window bounds must be within 0-{MINUTES_PER_DAY} minutes")
        if self.end <= self.start:
            raise ValueError("time window end must be after start (zero-length windows are not allowed)")

    def to_dict(self) -> dict[str, float]:
        return {"start": self.start, "end": self.end}



@dataclass
class Stop:
    name: str
    lat: float
    lng: float
    weight: float
    time_window: TimeWindow
    priority: Priority = Priority.NORMAL
    id: int | None = None
    service_time: float = 10.0

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("stop name must not be empty")
        if not -90 <= self.lat <= 90:
            raise ValueError("lat must be between -90 and 90")
        if not -180 <= self.lng <= 180:
            raise ValueError("lng must be between -180 and 180")
        if self.weight < 0:
            raise ValueError("weight must be non-negative")
        if self.service_time < 0:
            raise ValueError("service_time must be non-negative")
        if not isinstance(self.priority, Priority):
            self.priority = Priority(self.priority)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "lat": self.lat,
            "lng": self.lng,
            "weight": self.weight,
            "time_window": self.time_window.to_dict(),
            "priority": self.priority.value,
            "service_time": self.service_time,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Stop:
        tw = data["time_window"]
        return cls(
            id=data.get("id"),
            name=data["name"],
            lat=float(data["lat"]),
            lng=float(data["lng"]),
            weight=float(data["weight"]),
            time_window=TimeWindow(float(tw["start"]), float(tw["end"])),
            priority=Priority(data.get("priority", Priority.NORMAL.value)),
            service_time=float(data.get("service_time", 10.0)),
        )
