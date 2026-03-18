"""Abstract base collector."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from .models import CollectedDataset


class BaseCollector(ABC):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg

    @abstractmethod
    async def collect(self, category: str, period: str) -> CollectedDataset:
        """Collect data for a single category and period."""
        ...

    async def collect_all(
        self, categories: list[str], period: str
    ) -> list[CollectedDataset]:
        """Collect all categories, isolating errors per category."""
        results: list[CollectedDataset] = []
        for category in categories:
            result = await self.collect(category, period)
            results.append(result)
        return results
