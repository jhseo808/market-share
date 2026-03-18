"""Data models for parsed market share data."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal


TrendType = Literal["growing", "declining", "stable"]


@dataclass
class MarketShareEntry:
    category: str
    item: str
    monthly_values: dict[str, float]  # {"Feb-25": 72.5, ...}
    average_share: float
    latest_share: float
    trend: TrendType  # "growing" | "declining" | "stable"


@dataclass
class ParsedDataset:
    category: str
    period: str
    entries: list[MarketShareEntry] = field(default_factory=list)
    parse_error: str = ""

    @property
    def success(self) -> bool:
        return not self.parse_error

    def top_n(self, n: int = 10) -> list[MarketShareEntry]:
        return sorted(self.entries, key=lambda e: e.latest_share, reverse=True)[:n]
