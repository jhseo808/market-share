"""Data models for collected raw data."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class CollectedDataset:
    category: str
    period: str
    csv_path: Path
    url: str
    success: bool = True
    error: str = ""

    @property
    def failed(self) -> bool:
        return not self.success
