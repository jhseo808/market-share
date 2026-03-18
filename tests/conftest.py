"""Shared pytest fixtures."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Any

import pytest

from src.parsers.models import MarketShareEntry, ParsedDataset


@pytest.fixture
def sample_cfg(tmp_path: Path) -> dict[str, Any]:
    raw_dir = tmp_path / "raw"
    reports_dir = tmp_path / "reports"
    raw_dir.mkdir()
    reports_dir.mkdir()
    return {
        "statcounter": {
            "base_url": "https://gs.statcounter.com",
            "download_timeout": 30000,
            "retry_count": 3,
            "retry_backoff_base": 2,
        },
        "categories": {
            "browser": {
                "path": "/browser-market-share/all/south-korea/",
                "description": "브라우저 (전체 기기)",
            },
            "device-type": {
                "path": "/device-market-share/all/south-korea/",
                "description": "디바이스 타입",
            },
        },
        "analysis": {
            "model": "claude-sonnet-4-6",
            "temperature": 0,
            "max_tokens": 4096,
            "top_n_items": 10,
        },
        "thresholds": {"must_test": 10.0, "should_test": 3.0},
        "trend": {"delta_pp": 2.0},
        "output": {
            "raw_dir": str(raw_dir),
            "reports_dir": str(reports_dir),
            "report_prefix": "market-share-report",
        },
        "anthropic": {"api_key": "sk-ant-test-key"},
    }


@pytest.fixture
def sample_csv_content() -> str:
    """Minimal StatCounter-style CSV content."""
    return (
        "Browser,Jan-25,Feb-25,Mar-25\n"
        "Chrome,65.2,66.1,67.5\n"
        "Samsung Internet,18.3,17.9,17.5\n"
        "Safari,8.1,8.3,8.0\n"
        "Firefox,3.5,3.2,3.1\n"
        "Edge,2.1,2.3,2.4\n"
        "Other,2.8,2.2,1.5\n"
    )


@pytest.fixture
def sample_csv_file(tmp_path: Path, sample_csv_content: str) -> Path:
    p = tmp_path / "browser_202501-202603.csv"
    p.write_text(sample_csv_content, encoding="utf-8")
    return p


@pytest.fixture
def sample_entries() -> list[MarketShareEntry]:
    return [
        MarketShareEntry(
            category="browser",
            item="Chrome",
            monthly_values={"Jan-25": 65.2, "Feb-25": 66.1, "Mar-25": 67.5},
            average_share=66.27,
            latest_share=67.5,
            trend="growing",
        ),
        MarketShareEntry(
            category="browser",
            item="Samsung Internet",
            monthly_values={"Jan-25": 18.3, "Feb-25": 17.9, "Mar-25": 17.5},
            average_share=17.9,
            latest_share=17.5,
            trend="declining",
        ),
        MarketShareEntry(
            category="browser",
            item="Safari",
            monthly_values={"Jan-25": 8.1, "Feb-25": 8.3, "Mar-25": 8.0},
            average_share=8.13,
            latest_share=8.0,
            trend="stable",
        ),
    ]


@pytest.fixture
def sample_parsed_dataset(sample_entries: list[MarketShareEntry]) -> ParsedDataset:
    return ParsedDataset(
        category="browser",
        period="202501-202603",
        entries=sample_entries,
    )
