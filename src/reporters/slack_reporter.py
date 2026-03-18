"""Slack reporter — stub (not yet implemented)."""
from __future__ import annotations

from typing import Any

from .base import BaseReporter, ReportContext


class SlackReporter(BaseReporter):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg

    @property
    def name(self) -> str:
        return "slack"

    def report(self, context: ReportContext) -> str:
        raise NotImplementedError("SlackReporter is not yet implemented.")
