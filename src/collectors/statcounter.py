"""StatCounter CSV downloader using Playwright."""
from __future__ import annotations

import asyncio
import shutil
from pathlib import Path
from typing import Any

from src.config import get_category_url
from .base import BaseCollector
from .models import CollectedDataset


class StatCounterCollector(BaseCollector):
    """Downloads CSV exports from gs.statcounter.com via Playwright."""

    def __init__(self, cfg: dict[str, Any]) -> None:
        super().__init__(cfg)
        self._raw_dir = Path(cfg["output"]["raw_dir"])
        self._raw_dir.mkdir(parents=True, exist_ok=True)
        self._timeout = cfg["statcounter"].get("download_timeout", 30000)
        self._retry_count = cfg["statcounter"].get("retry_count", 3)
        self._retry_backoff = cfg["statcounter"].get("retry_backoff_base", 2)

    async def collect(self, category: str, period: str) -> CollectedDataset:
        url = get_category_url(self.cfg, category, period)
        dest = self._raw_dir / f"{category}_{period}.csv"

        last_error = ""
        for attempt in range(1, self._retry_count + 1):
            try:
                await self._download(url, dest)
                return CollectedDataset(
                    category=category,
                    period=period,
                    csv_path=dest,
                    url=url,
                    success=True,
                )
            except Exception as exc:
                last_error = str(exc)
                if attempt < self._retry_count:
                    wait = self._retry_backoff ** attempt
                    print(
                        f"  [retry {attempt}/{self._retry_count}] {category}: {exc} — waiting {wait}s"
                    )
                    await asyncio.sleep(wait)

        return CollectedDataset(
            category=category,
            period=period,
            csv_path=dest,
            url=url,
            success=False,
            error=last_error,
        )

    async def _download(self, url: str, dest: Path) -> None:
        from playwright.async_api import async_playwright

        # Parse base URL (strip hash) and extract from/to months from hash
        base_url = url.split("#")[0]
        from_month, to_month = self._parse_period_from_url(url)

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(accept_downloads=True)
            page = await context.new_page()

            try:
                await page.goto(base_url, timeout=self._timeout)
                await page.wait_for_load_state("networkidle", timeout=self._timeout)

                # Set the date range via JS (form elements may be hidden)
                await page.evaluate(
                    """([from, to]) => {
                        const f = document.querySelector('#month-year-select');
                        const t = document.querySelector('#month-year-select-to');
                        if (f) f.value = from;
                        if (t) t.value = to;
                    }""",
                    [from_month, to_month],
                )

                # Submit by clicking Update Graph button (via JS to bypass visibility)
                await page.evaluate(
                    "() => { document.getElementById('update-time').click(); }"
                )
                await page.wait_for_load_state("networkidle", timeout=self._timeout)
                await page.wait_for_timeout(1500)

                # Extract CSV data via FusionCharts API (most reliable)
                csv_content = await page.evaluate(
                    """() => {
                        const fc = window.FusionCharts;
                        const items = fc && fc.items;
                        if (!items || Object.keys(items).length === 0)
                            throw new Error('FusionCharts chart not rendered');
                        const key = Object.keys(items)[0];
                        const chart = items[key];
                        if (!chart.getDataAsCSV)
                            throw new Error('getDataAsCSV not available');
                        return chart.getDataAsCSV();
                    }"""
                )

                if not csv_content or csv_content.strip().startswith("<"):
                    raise RuntimeError("Chart data is not available or returned HTML")

                dest.write_text(csv_content, encoding="utf-8")

            finally:
                await context.close()
                await browser.close()

    @staticmethod
    def _parse_period_from_url(url: str) -> tuple[str, str]:
        """Convert hash #monthly-YYMM-YYMM to YYYY-MM format for the form selects."""
        import re
        m = re.search(r"#monthly-(\d{4})-(\d{4})", url)
        if not m:
            raise ValueError(f"Cannot parse period from URL hash: {url}")
        start_yymm, end_yymm = m.group(1), m.group(2)
        # YYMM → 20YY-MM
        start = f"20{start_yymm[:2]}-{start_yymm[2:]}"
        end = f"20{end_yymm[:2]}-{end_yymm[2:]}"
        return start, end

    async def collect_all(
        self, categories: list[str], period: str, concurrency: int = 3
    ) -> list[CollectedDataset]:
        """Collect all categories in parallel with a concurrency limit."""
        semaphore = asyncio.Semaphore(concurrency)

        async def _collect_one(category: str) -> CollectedDataset:
            async with semaphore:
                print(f"Collecting: {category} ...")
                result = await self.collect(category, period)
                if result.failed:
                    print(f"  FAILED: {category} — {result.error}")
                else:
                    print(f"  OK: {category} -> {result.csv_path}")
                return result

        return list(
            await asyncio.gather(*[_collect_one(cat) for cat in categories])
        )
