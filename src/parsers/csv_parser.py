"""Pandas-based CSV parser for StatCounter exports."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from .base import BaseParser
from .models import MarketShareEntry, ParsedDataset, TrendType

_TREND_DELTA = 2.0  # pp


def _determine_trend(first: float, last: float, delta: float = _TREND_DELTA) -> TrendType:
    diff = last - first
    if diff >= delta:
        return "growing"
    if diff <= -delta:
        return "declining"
    return "stable"


def _safe_float(val: object) -> float:
    try:
        return float(str(val).replace("%", "").strip())
    except (ValueError, TypeError):
        return 0.0


class CsvParser(BaseParser):
    """Parses StatCounter CSV exports into MarketShareEntry objects.

    StatCounter actual CSV format (wide / transposed):
        - First column: "Date" or "Label" — each row is a month
        - Remaining columns: item names (e.g. "Chrome", "iOS 18.4")
        - Values are percentages (no % suffix)
        - First data row may have an empty date (aggregate) — skipped

    Also handles the legacy tall format (item as first column) for tests.
    """

    def __init__(self, trend_delta: float = _TREND_DELTA) -> None:
        self._trend_delta = trend_delta

    def parse(self, path: Path, category: str, period: str) -> ParsedDataset:
        try:
            df = self._load(path)
            entries = self._build_entries(df, category)
            return ParsedDataset(category=category, period=period, entries=entries)
        except Exception as exc:
            return ParsedDataset(
                category=category,
                period=period,
                entries=[],
                parse_error=str(exc),
            )

    def _load(self, path: Path) -> pd.DataFrame:
        df = pd.read_csv(path, header=0)
        df.columns = [str(c).strip() for c in df.columns]
        return df

    def _is_wide_format(self, df: pd.DataFrame) -> bool:
        """True if first column is a date/label column (wide format)."""
        first_col = df.columns[0].lower()
        return first_col in ("date", "label")

    def _build_entries(
        self, df: pd.DataFrame, category: str
    ) -> list[MarketShareEntry]:
        if df.empty or len(df.columns) < 2:
            raise ValueError("CSV has fewer than 2 columns — unexpected format")

        if self._is_wide_format(df):
            return self._build_entries_wide(df, category)
        return self._build_entries_tall(df, category)

    def _build_entries_wide(
        self, df: pd.DataFrame, category: str
    ) -> list[MarketShareEntry]:
        """Wide format: rows = months, columns = items."""
        date_col = df.columns[0]
        item_cols = list(df.columns[1:])

        # Drop rows with empty/NaN date (aggregate row)
        df = df[df[date_col].notna() & (df[date_col].astype(str).str.strip() != "")]

        entries: list[MarketShareEntry] = []
        for item in item_cols:
            item_name = str(item).strip()
            if not item_name or item_name.lower() == "nan":
                continue

            monthly: dict[str, float] = {}
            for _, row in df.iterrows():
                month_label = str(row[date_col]).strip()
                monthly[month_label] = _safe_float(row[item])

            values = list(monthly.values())
            if not values:
                continue

            avg = sum(values) / len(values)
            latest = values[-1]
            first = values[0]
            trend = _determine_trend(first, latest, self._trend_delta)

            entries.append(
                MarketShareEntry(
                    category=category,
                    item=item_name,
                    monthly_values=monthly,
                    average_share=round(avg, 2),
                    latest_share=round(latest, 2),
                    trend=trend,
                )
            )

        return entries

    def _build_entries_tall(
        self, df: pd.DataFrame, category: str
    ) -> list[MarketShareEntry]:
        """Tall format: rows = items, columns = months (legacy / test format)."""
        item_col = df.columns[0]
        month_cols = list(df.columns[1:])

        entries: list[MarketShareEntry] = []
        for _, row in df.iterrows():
            item = str(row[item_col]).strip()
            if not item or item.lower() in ("", "nan"):
                continue

            monthly: dict[str, float] = {}
            for col in month_cols:
                monthly[col] = _safe_float(row[col])

            values = list(monthly.values())
            if not values:
                continue

            avg = sum(values) / len(values)
            latest = values[-1]
            first = values[0]
            trend = _determine_trend(first, latest, self._trend_delta)

            entries.append(
                MarketShareEntry(
                    category=category,
                    item=item,
                    monthly_values=monthly,
                    average_share=round(avg, 2),
                    latest_share=round(latest, 2),
                    trend=trend,
                )
            )

        return entries
