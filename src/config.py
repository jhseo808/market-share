"""Configuration loader: config.yaml + .env"""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

_ROOT = Path(__file__).parent.parent


def _find_root() -> Path:
    """Find project root by locating config.yaml."""
    candidate = Path.cwd()
    for _ in range(5):
        if (candidate / "config.yaml").exists():
            return candidate
        candidate = candidate.parent
    return _ROOT


def load_config(config_path: Path | None = None) -> dict[str, Any]:
    """Load config.yaml and merge environment variables."""
    load_dotenv(_ROOT / ".env", override=False)

    root = _find_root()
    path = config_path or root / "config.yaml"

    if not path.exists():
        raise FileNotFoundError(f"config.yaml not found at {path}")

    with path.open("r", encoding="utf-8") as f:
        cfg: dict[str, Any] = yaml.safe_load(f)

    # Inject ANTHROPIC_API_KEY from env
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    cfg.setdefault("anthropic", {})["api_key"] = api_key

    # Inject Confluence credentials from env
    confluence = cfg.setdefault("confluence", {})
    confluence["url"] = os.environ.get("CONFLUENCE_URL", confluence.get("url", ""))
    confluence["user"] = os.environ.get("CONFLUENCE_USER", confluence.get("user", ""))
    confluence["api_token"] = os.environ.get("CONFLUENCE_API_TOKEN", confluence.get("api_token", ""))
    confluence["page_id"] = os.environ.get("CONFLUENCE_PAGE_ID", confluence.get("page_id", ""))

    # Resolve relative paths to absolute
    output = cfg.get("output", {})
    for key in ("raw_dir", "reports_dir"):
        if key in output and not Path(output[key]).is_absolute():
            output[key] = str(root / output[key])

    return cfg


def get_api_key(cfg: dict[str, Any]) -> str:
    key = cfg.get("anthropic", {}).get("api_key", "")
    if not key:
        raise ValueError(
            "ANTHROPIC_API_KEY is not set. Add it to .env or export it as an environment variable."
        )
    return key


def get_category_url(cfg: dict[str, Any], category: str, period: str) -> str:
    """Build StatCounter URL for a category and period.

    period format: YYYYMM-YYYYMM  e.g. 202502-202602
    StatCounter monthly hash: monthly-YYMM-YYMM
    """
    base = cfg["statcounter"]["base_url"]
    path = cfg["categories"][category]["path"]

    # Convert YYYYMM-YYYYMM → YYMM-YYMM
    start, end = period.split("-")
    sc_period = f"monthly-{start[2:]}-{end[2:]}"

    return f"{base}{path}#{sc_period}"


def validate_config(cfg: dict[str, Any]) -> list[str]:
    """Return a list of validation errors (empty = valid)."""
    errors: list[str] = []

    if not cfg.get("anthropic", {}).get("api_key"):
        errors.append("ANTHROPIC_API_KEY is missing")

    if "categories" not in cfg or not cfg["categories"]:
        errors.append("No categories defined in config.yaml")

    if "statcounter" not in cfg:
        errors.append("statcounter section missing from config.yaml")

    return errors
