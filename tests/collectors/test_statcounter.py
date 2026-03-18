"""Unit tests for StatCounterCollector (mocked Playwright)."""
from __future__ import annotations

import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.collectors.statcounter import StatCounterCollector
from src.collectors.models import CollectedDataset


@pytest.fixture
def collector(sample_cfg):
    return StatCounterCollector(sample_cfg)


class TestStatCounterCollector:
    @pytest.mark.asyncio
    async def test_collect_success(self, collector: StatCounterCollector, tmp_path: Path):
        fake_csv = tmp_path / "fake.csv"
        fake_csv.write_text("Browser,Jan-25\nChrome,65\n")

        with patch("src.collectors.statcounter.StatCounterCollector._download", new_callable=AsyncMock) as mock_dl:
            async def side_effect(url, dest):
                shutil.copy(fake_csv, dest)
            mock_dl.side_effect = side_effect

            result = await collector.collect("browser", "202502-202602")

        assert result.success
        assert result.category == "browser"
        assert result.period == "202502-202602"

    @pytest.mark.asyncio
    async def test_collect_retries_on_failure(self, collector: StatCounterCollector):
        call_count = 0

        with patch("src.collectors.statcounter.StatCounterCollector._download", new_callable=AsyncMock) as mock_dl:
            async def failing_side_effect(url, dest):
                nonlocal call_count
                call_count += 1
                raise RuntimeError("network error")
            mock_dl.side_effect = failing_side_effect

            # Speed up retries
            collector._retry_backoff = 0
            result = await collector.collect("browser", "202502-202602")

        assert not result.success
        assert call_count == collector._retry_count
        assert "network error" in result.error

    @pytest.mark.asyncio
    async def test_collect_all_isolates_errors(self, collector: StatCounterCollector, tmp_path: Path):
        fake_csv = tmp_path / "fake.csv"
        fake_csv.write_text("Browser,Jan-25\nChrome,65\n")

        call_count = {"n": 0}

        with patch("src.collectors.statcounter.StatCounterCollector._download", new_callable=AsyncMock) as mock_dl:
            async def mixed_side_effect(url, dest):
                call_count["n"] += 1
                if "browser" in url and "version" not in url:
                    shutil.copy(fake_csv, dest)
                else:
                    raise RuntimeError("fail")
            mock_dl.side_effect = mixed_side_effect
            collector._retry_backoff = 0

            results = await collector.collect_all(["browser", "device-type"], "202502-202602")

        assert len(results) == 2
        browser_r = next(r for r in results if r.category == "browser")
        device_r = next(r for r in results if r.category == "device-type")
        assert browser_r.success
        assert not device_r.success
