"""Confluence reporter — stub (not yet implemented)."""
from __future__ import annotations

from typing import Any

from .base import BaseReporter, ReportContext


class ConfluenceReporter(BaseReporter):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg

    @property
    def name(self) -> str:
        return "confluence"

    def report(self, context: ReportContext) -> str:
        raise NotImplementedError("ConfluenceReporter is not yet implemented.")
