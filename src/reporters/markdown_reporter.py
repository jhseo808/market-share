"""Markdown report generator."""
from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .base import BaseReporter, ReportContext


class MarkdownReporter(BaseReporter):
    def __init__(self, cfg: dict[str, Any]) -> None:
        self._reports_dir = Path(cfg["output"]["reports_dir"])
        self._reports_dir.mkdir(parents=True, exist_ok=True)
        self._prefix = cfg["output"].get("report_prefix", "market-share-report")

    @property
    def name(self) -> str:
        return "markdown"

    def report(self, context: ReportContext) -> str:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"{self._prefix}_{context.period}_{ts}.md"
        path = self._reports_dir / filename

        content = self._render(context)
        path.write_text(content, encoding="utf-8")
        return str(path)

    def _render(self, ctx: ReportContext) -> str:
        lines: list[str] = []
        generated = ctx.generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines += [
            f"# 한국 시장 브라우저/디바이스/OS 점유율 분석 리포트",
            f"",
            f"**기간:** {ctx.period}  ",
            f"**생성일시:** {generated}  ",
            f"",
            f"---",
            f"",
        ]

        # --- Raw Data Summary ---
        lines += ["## 수집된 데이터 요약", ""]
        for ds in ctx.datasets:
            if not ds.success:
                lines.append(f"- **{ds.category}**: 파싱 실패 — {ds.parse_error}")
                continue
            url = ctx.category_urls.get(ds.category)
            heading = f"[{ds.category}]({url})" if url else ds.category
            lines.append(f"### {heading}")
            lines.append("")
            lines.append("| 항목 | 최신 점유율 | 평균 점유율 | 트렌드 |")
            lines.append("|------|------------|------------|--------|")
            for entry in ds.top_n(10):
                trend_icon = {"growing": "📈", "declining": "📉", "stable": "➡️"}.get(
                    entry.trend, ""
                )
                lines.append(
                    f"| {entry.item} | {entry.latest_share:.1f}% "
                    f"| {entry.average_share:.1f}% | {trend_icon} {entry.trend} |"
                )
            lines.append("")

        lines += ["---", ""]

        # --- AI Analysis ---
        if ctx.analysis:
            lines += ["## AI 분석 결과 (Claude)", ""]
            self._render_matrix(lines, "브라우저 테스트 매트릭스", ctx.analysis.get("browser_matrix", {}))
            self._render_matrix(lines, "디바이스 테스트 매트릭스", ctx.analysis.get("device_matrix", {}))
            self._render_matrix(lines, "OS 커버리지", ctx.analysis.get("os_coverage", {}))

            risk = ctx.analysis.get("risk_analysis", [])
            if risk:
                lines += ["### 위험 분석", ""]
                lines.append("| 영역 | 위험 | 권장 조치 |")
                lines.append("|------|------|----------|")
                for r in risk:
                    lines.append(
                        f"| {r.get('area','')} | {r.get('risk','')} | {r.get('action','')} |"
                    )
                lines.append("")

            recs = ctx.analysis.get("recommendations", [])
            if recs:
                lines += ["### 권장사항", ""]
                for i, rec in enumerate(recs, 1):
                    lines.append(f"{i}. {rec}")
                lines.append("")
        else:
            lines += ["## AI 분석", "", "_AI 분석을 건너뛰었습니다 (`--skip-analysis`)._", ""]

        lines += ["---", "", "_이 리포트는 Market Share QA Tool에 의해 자동 생성되었습니다._", ""]
        return "\n".join(lines)

    def _render_matrix(
        self, lines: list[str], title: str, matrix: dict[str, Any]
    ) -> None:
        if not matrix:
            return
        lines += [f"### {title}", ""]
        priority_labels = {
            "must_test": "🔴 Must Test",
            "should_test": "🟡 Should Test",
            "low_priority": "🟢 Low Priority",
        }
        for key, label in priority_labels.items():
            items = matrix.get(key, [])
            if items:
                lines.append(f"**{label}**")
                for item in items:
                    lines.append(f"- {item}")
                lines.append("")
