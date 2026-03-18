"""Reporter plugin interface."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from src.parsers.models import ParsedDataset


@dataclass
class ReportContext:
    period: str
    datasets: list[ParsedDataset]
    analysis: dict[str, Any] = field(default_factory=dict)
    generated_at: str = ""
    category_urls: dict[str, str] = field(default_factory=dict)


class BaseReporter(ABC):
    @property
    @abstractmethod
    def name(self) -> str:
        ...

    @abstractmethod
    def report(self, context: ReportContext) -> str:
        """Generate and persist the report. Returns output location/identifier."""
        ...
