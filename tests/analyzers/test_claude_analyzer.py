"""Unit tests for ClaudeAnalyzer (mocked Anthropic client)."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from src.analyzers.claude_analyzer import ClaudeAnalyzer
from src.analyzers.prompts import build_analysis_prompt
from src.parsers.models import ParsedDataset


MOCK_ANALYSIS = {
    "browser_matrix": {
        "must_test": ["Chrome (67.5%)", "Samsung Internet (17.5%)"],
        "should_test": ["Safari (8.0%)"],
        "low_priority": ["Firefox (3.1%)", "Edge (2.4%)"],
    },
    "device_matrix": {
        "must_test": ["Mobile (65%)"],
        "should_test": ["Desktop (30%)"],
        "low_priority": ["Tablet (5%)"],
    },
    "os_coverage": {
        "must_test": ["Android (60%)"],
        "should_test": ["Windows (25%)", "iOS (12%)"],
        "low_priority": [],
    },
    "risk_analysis": [
        {
            "area": "Samsung Internet",
            "risk": "독자적인 렌더링 엔진 사용",
            "action": "Samsung Internet 전용 테스트 케이스 필요",
        }
    ],
    "recommendations": ["Chrome + Samsung Internet 조합 필수 테스트"],
}


@pytest.fixture
def analyzer(sample_cfg):
    return ClaudeAnalyzer(sample_cfg)


class TestClaudeAnalyzer:
    def _make_mock_response(self, content: str) -> MagicMock:
        msg = MagicMock()
        msg.content = [MagicMock(text=content)]
        return msg

    def test_analyze_returns_dict(self, analyzer: ClaudeAnalyzer, sample_parsed_dataset: ParsedDataset):
        json_str = json.dumps(MOCK_ANALYSIS)
        mock_response = self._make_mock_response(json_str)

        with patch.object(analyzer._client.messages, "create", return_value=mock_response):
            result = analyzer.analyze([sample_parsed_dataset])

        assert isinstance(result, dict)
        assert "browser_matrix" in result

    def test_analyze_with_markdown_fences(self, analyzer: ClaudeAnalyzer, sample_parsed_dataset: ParsedDataset):
        fenced = f"```json\n{json.dumps(MOCK_ANALYSIS)}\n```"
        mock_response = self._make_mock_response(fenced)

        with patch.object(analyzer._client.messages, "create", return_value=mock_response):
            result = analyzer.analyze([sample_parsed_dataset])

        assert result["browser_matrix"]["must_test"][0] == "Chrome (67.5%)"

    def test_analyze_invalid_json_raises(self, analyzer: ClaudeAnalyzer, sample_parsed_dataset: ParsedDataset):
        mock_response = self._make_mock_response("This is not JSON at all.")

        with patch.object(analyzer._client.messages, "create", return_value=mock_response):
            with pytest.raises(ValueError, match="not valid JSON"):
                analyzer.analyze([sample_parsed_dataset])


class TestBuildAnalysisPrompt:
    def test_returns_tuple(self, sample_parsed_dataset: ParsedDataset):
        result = build_analysis_prompt([sample_parsed_dataset])
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_system_prompt_contains_qa(self, sample_parsed_dataset: ParsedDataset):
        system, _ = build_analysis_prompt([sample_parsed_dataset])
        assert "QA" in system

    def test_user_prompt_contains_data(self, sample_parsed_dataset: ParsedDataset):
        _, user = build_analysis_prompt([sample_parsed_dataset])
        assert "Chrome" in user
        assert "browser" in user

    def test_skips_failed_datasets(self):
        failed = ParsedDataset(
            category="browser", period="x", parse_error="failed"
        )
        _, user = build_analysis_prompt([failed])
        # Failed dataset should not appear in JSON data
        assert '"browser"' not in user or "Chrome" not in user
