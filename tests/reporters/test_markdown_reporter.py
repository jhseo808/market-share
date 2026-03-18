"""Unit tests for MarkdownReporter."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.reporters.base import ReportContext
from src.reporters.markdown_reporter import MarkdownReporter


@pytest.fixture
def reporter(sample_cfg) -> MarkdownReporter:
    return MarkdownReporter(sample_cfg)


class TestMarkdownReporter:
    def test_report_creates_file(self, reporter: MarkdownReporter, sample_parsed_dataset, sample_cfg):
        ctx = ReportContext(
            period="202501-202603",
            datasets=[sample_parsed_dataset],
            generated_at="2026-03-17 12:00:00",
        )
        output_path = reporter.report(ctx)
        assert Path(output_path).exists()

    def test_report_filename_contains_period(self, reporter: MarkdownReporter, sample_parsed_dataset):
        ctx = ReportContext(
            period="202501-202603",
            datasets=[sample_parsed_dataset],
        )
        output_path = reporter.report(ctx)
        assert "202501-202603" in Path(output_path).name

    def test_report_contains_category(self, reporter: MarkdownReporter, sample_parsed_dataset):
        ctx = ReportContext(
            period="202501-202603",
            datasets=[sample_parsed_dataset],
        )
        output_path = reporter.report(ctx)
        content = Path(output_path).read_text(encoding="utf-8")
        assert "browser" in content
        assert "Chrome" in content

    def test_report_with_analysis(self, reporter: MarkdownReporter, sample_parsed_dataset):
        analysis = {
            "browser_matrix": {
                "must_test": ["Chrome (67.5%)"],
                "should_test": [],
                "low_priority": [],
            },
            "device_matrix": {},
            "os_coverage": {},
            "risk_analysis": [],
            "recommendations": ["Samsung Internet 별도 테스트 필요"],
        }
        ctx = ReportContext(
            period="202501-202603",
            datasets=[sample_parsed_dataset],
            analysis=analysis,
        )
        output_path = reporter.report(ctx)
        content = Path(output_path).read_text(encoding="utf-8")
        assert "Must Test" in content
        assert "Chrome (67.5%)" in content
        assert "Samsung Internet 별도 테스트 필요" in content

    def test_report_skip_analysis(self, reporter: MarkdownReporter, sample_parsed_dataset):
        ctx = ReportContext(
            period="202501-202603",
            datasets=[sample_parsed_dataset],
            analysis={},
        )
        output_path = reporter.report(ctx)
        content = Path(output_path).read_text(encoding="utf-8")
        assert "--skip-analysis" in content

    def test_reporter_name(self, reporter: MarkdownReporter):
        assert reporter.name == "markdown"

    def test_failed_dataset_shows_error(self, reporter: MarkdownReporter, sample_cfg):
        from src.parsers.models import ParsedDataset
        failed = ParsedDataset(
            category="device-type",
            period="202501-202603",
            parse_error="수집 실패: network error",
        )
        ctx = ReportContext(period="202501-202603", datasets=[failed])
        output_path = reporter.report(ctx)
        content = Path(output_path).read_text(encoding="utf-8")
        assert "파싱 실패" in content
