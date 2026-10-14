"""Per-day analytics summary."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any


@dataclass
class AnalyticsRecord:
    date: date
    distance_saved: float
    success_rate: float  # fraction in [0, 1]

    def __post_init__(self) -> None:
        if not 0.0 <= self.success_rate <= 1.0:
            raise ValueError("success_rate must be between 0 and 1")

    def to_dict(self) -> dict[str, Any]:
        return {
            "date": self.date.isoformat(),
            "distance_saved": self.distance_saved,
            "success_rate": self.success_rate,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> AnalyticsRecord:
        return cls(
            date=date.fromisoformat(data["date"]),
            distance_saved=float(data["distance_saved"]),
            success_rate=float(data["success_rate"]),
        )
