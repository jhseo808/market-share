"""Abstract base analyzer."""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from src.parsers.models import ParsedDataset


class BaseAnalyzer(ABC):
    @abstractmethod
    def analyze(self, datasets: list[ParsedDataset]) -> dict[str, Any]:
        ...
