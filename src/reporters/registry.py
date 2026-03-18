"""Reporter registry — add new reporters here."""
from __future__ import annotations

from typing import Any

from .base import BaseReporter
from .markdown_reporter import MarkdownReporter
from .slack_reporter import SlackReporter
from .confluence_reporter import ConfluenceReporter

REPORTER_REGISTRY: dict[str, type[BaseReporter]] = {
    "markdown": MarkdownReporter,
    "slack": SlackReporter,
    "confluence": ConfluenceReporter,
}


def get_reporter(name: str, cfg: dict[str, Any]) -> BaseReporter:
    cls = REPORTER_REGISTRY.get(name)
    if cls is None:
        available = ", ".join(REPORTER_REGISTRY.keys())
        raise ValueError(f"Unknown reporter '{name}'. Available: {available}")
    return cls(cfg)
