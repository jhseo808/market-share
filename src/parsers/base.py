"""Abstract base parser."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from .models import ParsedDataset


class BaseParser(ABC):
    @abstractmethod
    def parse(self, path: Path, category: str, period: str) -> ParsedDataset:
        ...
