"""Anthropic Claude API analyzer."""
from __future__ import annotations

import json
import re
from typing import Any

import anthropic

from src.config import get_api_key
from src.parsers.models import ParsedDataset
from .base import BaseAnalyzer
from .prompts import build_analysis_prompt


class ClaudeAnalyzer(BaseAnalyzer):
    """Sends market share data to Claude and parses the JSON response."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        self.cfg = cfg
        api_key = get_api_key(cfg)
        self._client = anthropic.Anthropic(api_key=api_key)
        analysis_cfg = cfg.get("analysis", {})
        self._model = analysis_cfg.get("model", "claude-sonnet-4-6")
        self._temperature = analysis_cfg.get("temperature", 0)
        self._max_tokens = analysis_cfg.get("max_tokens", 4096)
        self._top_n = analysis_cfg.get("top_n_items", 10)
        thresholds = cfg.get("thresholds", {})
        self._must_test = thresholds.get("must_test", 10.0)
        self._should_test = thresholds.get("should_test", 3.0)

    def analyze(self, datasets: list[ParsedDataset]) -> dict[str, Any]:
        """Send datasets to Claude and return structured analysis."""
        system_prompt, user_prompt = build_analysis_prompt(
            datasets,
            top_n=self._top_n,
            must_test_threshold=self._must_test,
            should_test_threshold=self._should_test,
        )

        message = self._client.messages.create(
            model=self._model,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )

        raw_text = message.content[0].text
        return self._parse_response(raw_text)

    def _parse_response(self, text: str) -> dict[str, Any]:
        """Extract JSON from Claude's response."""
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(), flags=re.MULTILINE)
        cleaned = re.sub(r"\s*```$", "", cleaned.strip(), flags=re.MULTILINE)

        try:
            return json.loads(cleaned.strip())
        except json.JSONDecodeError as exc:
            # Attempt to find first { ... } block
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise ValueError(f"Claude response is not valid JSON: {exc}\n---\n{text}") from exc
