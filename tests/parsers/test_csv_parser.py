"""Unit tests for CsvParser."""
from __future__ import annotations

from pathlib import Path

import pytest

from src.parsers.csv_parser import CsvParser, _determine_trend, _safe_float
from src.parsers.models import ParsedDataset


class TestHelpers:
    def test_safe_float_plain(self):
        assert _safe_float("72.5") == 72.5

    def test_safe_float_with_percent(self):
        assert _safe_float("72.5%") == 72.5

    def test_safe_float_invalid(self):
        assert _safe_float("N/A") == 0.0

    def test_safe_float_none(self):
        assert _safe_float(None) == 0.0

    def test_trend_growing(self):
        assert _determine_trend(10.0, 13.0) == "growing"

    def test_trend_declining(self):
        assert _determine_trend(13.0, 10.0) == "declining"

    def test_trend_stable(self):
        assert _determine_trend(10.0, 11.0) == "stable"

    def test_trend_exact_boundary_growing(self):
        assert _determine_trend(10.0, 12.0) == "growing"

    def test_trend_exact_boundary_declining(self):
        assert _determine_trend(12.0, 10.0) == "declining"


class TestCsvParser:
    def setup_method(self):
        self.parser = CsvParser()

    def test_parse_valid_csv(self, sample_csv_file: Path):
        result = self.parser.parse(sample_csv_file, "browser", "202501-202603")
        assert result.success
        assert result.category == "browser"
        assert len(result.entries) == 6

    def test_parse_entry_values(self, sample_csv_file: Path):
        result = self.parser.parse(sample_csv_file, "browser", "202501-202603")
        chrome = next(e for e in result.entries if e.item == "Chrome")
        assert chrome.latest_share == 67.5
        assert chrome.trend == "growing"
        assert chrome.monthly_values["Jan-25"] == 65.2

    def test_parse_declining_trend(self, tmp_path: Path):
        # Drop >2pp to trigger "declining": 20.0 → 17.5
        csv = tmp_path / "declining.csv"
        csv.write_text(
            "Browser,Jan-25,Feb-25,Mar-25\nSamsung Internet,20.0,18.5,17.5\n",
            encoding="utf-8",
        )
        result = self.parser.parse(csv, "browser", "202501-202603")
        samsung = next(e for e in result.entries if e.item == "Samsung Internet")
        assert samsung.trend == "declining"

    def test_parse_stable_trend(self, sample_csv_file: Path):
        result = self.parser.parse(sample_csv_file, "browser", "202501-202603")
        safari = next(e for e in result.entries if e.item == "Safari")
        assert safari.trend == "stable"

    def test_parse_missing_file(self, tmp_path: Path):
        result = self.parser.parse(tmp_path / "nonexistent.csv", "browser", "x")
        assert not result.success
        assert result.parse_error != ""

    def test_parse_empty_csv(self, tmp_path: Path):
        p = tmp_path / "empty.csv"
        p.write_text("Browser\n", encoding="utf-8")
        result = self.parser.parse(p, "browser", "x")
        assert not result.success

    def test_top_n(self, sample_csv_file: Path):
        result = self.parser.parse(sample_csv_file, "browser", "202501-202603")
        top3 = result.top_n(3)
        assert len(top3) == 3
        # Sorted by latest_share descending
        assert top3[0].latest_share >= top3[1].latest_share


class TestParsedDataset:
    def test_success_when_no_error(self, sample_parsed_dataset):
        assert sample_parsed_dataset.success is True

    def test_failed_when_error(self):
        ds = ParsedDataset(category="x", period="y", parse_error="boom")
        assert ds.success is False

    def test_top_n_sorted(self, sample_parsed_dataset):
        top = sample_parsed_dataset.top_n(2)
        assert top[0].latest_share >= top[1].latest_share
