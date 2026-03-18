"""CLI entry point for Market Share QA Tool."""
from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

import click

from src.config import load_config, validate_config, get_category_url
from src.collectors.statcounter import StatCounterCollector
from src.parsers.csv_parser import CsvParser
from src.analyzers.claude_analyzer import ClaudeAnalyzer
from src.reporters.base import ReportContext
from src.reporters.registry import get_reporter


def _all_categories(cfg: dict) -> list[str]:
    return list(cfg["categories"].keys())


def _parse_categories(cfg: dict, categories_str: Optional[str]) -> list[str]:
    all_cats = _all_categories(cfg)
    if not categories_str:
        return all_cats
    requested = [c.strip() for c in categories_str.split(",") if c.strip()]
    unknown = [c for c in requested if c not in cfg["categories"]]
    if unknown:
        raise click.BadParameter(
            f"Unknown categories: {', '.join(unknown)}. "
            f"Available: {', '.join(all_cats)}"
        )
    return requested


@click.group()
@click.option("--config", "config_path", default=None, help="Path to config.yaml")
@click.pass_context
def cli(ctx: click.Context, config_path: Optional[str]) -> None:
    """Market Share QA Tool — 한국 시장 브라우저/디바이스 점유율 분석."""
    ctx.ensure_object(dict)
    path = Path(config_path) if config_path else None
    ctx.obj["cfg"] = load_config(path)


@cli.command()
@click.option("--period", required=True, help="기간 (예: 202502-202602)")
@click.option("--categories", default=None, help="쉼표 구분 카테고리 (기본: 전체)")
@click.option("--skip-analysis", is_flag=True, default=False, help="AI 분석 건너뛰기")
@click.option("--reporter", default="markdown", help="리포터 종류 (기본: markdown)")
@click.pass_context
def run(
    ctx: click.Context,
    period: str,
    categories: Optional[str],
    skip_analysis: bool,
    reporter: str,
) -> None:
    """전체 파이프라인 실행: 수집 → 파싱 → 분석 → 리포트."""
    cfg = ctx.obj["cfg"]
    cats = _parse_categories(cfg, categories)

    click.echo(f"[1/4] 데이터 수집 시작 — 카테고리: {', '.join(cats)}, 기간: {period}")

    # Step 1: Collect
    collector = StatCounterCollector(cfg)
    datasets_raw = asyncio.run(collector.collect_all(cats, period))

    failed = [d for d in datasets_raw if d.failed]
    if failed:
        click.echo(f"  경고: {len(failed)}개 카테고리 수집 실패 — {[d.category for d in failed]}")

    # Step 2: Parse
    click.echo("[2/4] CSV 파싱 ...")
    parser = CsvParser(trend_delta=cfg.get("trend", {}).get("delta_pp", 2.0))
    datasets_parsed = []
    for raw in datasets_raw:
        if raw.failed:
            from src.parsers.models import ParsedDataset
            datasets_parsed.append(
                ParsedDataset(
                    category=raw.category,
                    period=raw.period,
                    parse_error=f"수집 실패: {raw.error}",
                )
            )
        else:
            parsed = parser.parse(raw.csv_path, raw.category, raw.period)
            if not parsed.success:
                click.echo(f"  경고: {raw.category} 파싱 실패 — {parsed.parse_error}")
            datasets_parsed.append(parsed)

    # Step 3: Analyze
    analysis: dict = {}
    if not skip_analysis:
        click.echo("[3/4] Claude AI 분석 중 ...")
        try:
            analyzer = ClaudeAnalyzer(cfg)
            analysis = analyzer.analyze(datasets_parsed)
        except Exception as exc:
            click.echo(f"  경고: AI 분석 실패 — {exc}", err=True)
    else:
        click.echo("[3/4] AI 분석 건너뜀 (--skip-analysis)")

    # Step 4: Report
    click.echo(f"[4/4] 리포트 생성 ({reporter}) ...")
    category_urls = {cat: get_category_url(cfg, cat, period) for cat in cats}
    context = ReportContext(
        period=period,
        datasets=datasets_parsed,
        analysis=analysis,
        generated_at=datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        category_urls=category_urls,
    )
    rep = get_reporter(reporter, cfg)
    output = rep.report(context)
    click.echo(f"\n리포트 생성 완료: {output}")


@cli.command("list-categories")
@click.pass_context
def list_categories(ctx: click.Context) -> None:
    """설정된 수집 카테고리 목록을 출력합니다."""
    cfg = ctx.obj["cfg"]
    click.echo("사용 가능한 카테고리:")
    for key, val in cfg["categories"].items():
        click.echo(f"  {key:<20} {val['description']}")


@cli.command("validate-config")
@click.pass_context
def validate_config_cmd(ctx: click.Context) -> None:
    """환경 및 설정 유효성을 검증합니다."""
    cfg = ctx.obj["cfg"]
    errors = validate_config(cfg)
    if errors:
        click.echo("설정 오류:", err=True)
        for err in errors:
            click.echo(f"  [FAIL] {err}", err=True)
        sys.exit(1)
    else:
        click.echo("[OK] 설정이 유효합니다.")
        click.echo(f"  모델: {cfg['analysis']['model']}")
        click.echo(f"  카테고리 수: {len(cfg['categories'])}")
        click.echo(f"  출력 디렉토리: {cfg['output']['reports_dir']}")


if __name__ == "__main__":
    cli(obj={})
