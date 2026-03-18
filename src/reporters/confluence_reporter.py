"""Confluence reporter — appends market share report to a Confluence page."""
from __future__ import annotations

import base64
from datetime import datetime
from typing import Any

import requests

from .base import BaseReporter, ReportContext


class ConfluenceReporter(BaseReporter):
    def __init__(self, cfg: dict[str, Any]) -> None:
        conf = cfg.get("confluence", {})
        self._url = conf.get("url", "").rstrip("/")
        self._user = conf.get("user", "")
        self._token = conf.get("api_token", "")
        self._page_id = str(conf.get("page_id", ""))

        credentials = base64.b64encode(f"{self._user}:{self._token}".encode()).decode()
        self._headers = {
            "Authorization": f"Basic {credentials}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    @property
    def name(self) -> str:
        return "confluence"

    def report(self, context: ReportContext) -> str:
        page = self._get_page()
        current_body = page["body"]["storage"]["value"]
        version = page["version"]["number"]
        title = page["title"]

        new_section = self._render_html(context)
        updated_body = current_body + new_section

        self._update_page(title, version + 1, updated_body)
        page_url = f"{self._url}/wiki/pages/{self._page_id}"
        return page_url

    def _get_page(self) -> dict[str, Any]:
        resp = requests.get(
            f"{self._url}/wiki/rest/api/content/{self._page_id}",
            headers=self._headers,
            params={"expand": "body.storage,version"},
        )
        resp.raise_for_status()
        return resp.json()

    def _update_page(self, title: str, version: int, body: str) -> None:
        payload = {
            "version": {"number": version},
            "title": title,
            "type": "page",
            "body": {
                "storage": {
                    "value": body,
                    "representation": "storage",
                }
            },
        }
        resp = requests.put(
            f"{self._url}/wiki/rest/api/content/{self._page_id}",
            headers=self._headers,
            json=payload,
        )
        resp.raise_for_status()

    def _render_html(self, ctx: ReportContext) -> str:
        generated = ctx.generated_at or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        parts: list[str] = []

        parts.append(
            f'<h2>점유율 분석 — {ctx.period}</h2>'
            f'<p><strong>생성일시:</strong> {generated}</p>'
            f'<hr />'
        )

        # Raw data tables
        parts.append("<h3>수집된 데이터 요약</h3>")
        for ds in ctx.datasets:
            if not ds.success:
                parts.append(f"<p><strong>{ds.category}</strong>: 파싱 실패 — {ds.parse_error}</p>")
                continue

            url = ctx.category_urls.get(ds.category)
            heading = f'<a href="{url}">{ds.category}</a>' if url else ds.category
            parts.append(f"<h4>{heading}</h4>")
            parts.append(
                "<table><tbody>"
                "<tr><th>항목</th><th>최신 점유율</th><th>평균 점유율</th><th>트렌드</th></tr>"
            )
            for entry in ds.top_n(10):
                trend_icon = {"growing": "📈", "declining": "📉", "stable": "➡️"}.get(entry.trend, "")
                parts.append(
                    f"<tr>"
                    f"<td>{entry.item}</td>"
                    f"<td>{entry.latest_share:.1f}%</td>"
                    f"<td>{entry.average_share:.1f}%</td>"
                    f"<td>{trend_icon} {entry.trend}</td>"
                    f"</tr>"
                )
            parts.append("</tbody></table>")

        parts.append("<hr />")

        # AI analysis
        if ctx.analysis:
            parts.append("<h3>AI 분석 결과 (Claude)</h3>")
            self._render_matrix_html(parts, "브라우저 테스트 매트릭스", ctx.analysis.get("browser_matrix", {}))
            self._render_matrix_html(parts, "디바이스 테스트 매트릭스", ctx.analysis.get("device_matrix", {}))
            self._render_matrix_html(parts, "OS 커버리지", ctx.analysis.get("os_coverage", {}))

            risk = ctx.analysis.get("risk_analysis", [])
            if risk:
                parts.append("<h4>위험 분석</h4>")
                parts.append("<table><tbody><tr><th>영역</th><th>위험</th><th>권장 조치</th></tr>")
                for r in risk:
                    parts.append(
                        f"<tr><td>{r.get('area','')}</td>"
                        f"<td>{r.get('risk','')}</td>"
                        f"<td>{r.get('action','')}</td></tr>"
                    )
                parts.append("</tbody></table>")

            recs = ctx.analysis.get("recommendations", [])
            if recs:
                parts.append("<h4>권장사항</h4><ol>")
                for rec in recs:
                    parts.append(f"<li>{rec}</li>")
                parts.append("</ol>")
        else:
            parts.append("<h3>AI 분석</h3><p><em>AI 분석을 건너뛰었습니다.</em></p>")

        parts.append("<hr />")
        return "\n".join(parts)

    def _render_matrix_html(self, parts: list[str], title: str, matrix: dict[str, Any]) -> None:
        if not matrix:
            return
        parts.append(f"<h4>{title}</h4>")
        labels = {
            "must_test": "🔴 Must Test",
            "should_test": "🟡 Should Test",
            "low_priority": "🟢 Low Priority",
        }
        for key, label in labels.items():
            items = matrix.get(key, [])
            if items:
                parts.append(f"<p><strong>{label}</strong></p><ul>")
                for item in items:
                    parts.append(f"<li>{item}</li>")
                parts.append("</ul>")
