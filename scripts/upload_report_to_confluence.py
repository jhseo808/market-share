"""마크다운 리포트를 Confluence 하위 페이지로 업로드하는 스크립트."""
from __future__ import annotations

import base64
import sys
from pathlib import Path

import markdown
import requests
from dotenv import load_dotenv
import os

load_dotenv()

CONFLUENCE_URL = os.environ["CONFLUENCE_URL"].rstrip("/")
CONFLUENCE_USER = os.environ["CONFLUENCE_USER"]
CONFLUENCE_API_TOKEN = os.environ["CONFLUENCE_API_TOKEN"]
PARENT_PAGE_ID = os.environ["CONFLUENCE_PAGE_ID"]

credentials = base64.b64encode(f"{CONFLUENCE_USER}:{CONFLUENCE_API_TOKEN}".encode()).decode()
HEADERS = {
    "Authorization": f"Basic {credentials}",
    "Content-Type": "application/json",
    "Accept": "application/json",
}


def md_to_storage(md_text: str) -> str:
    """마크다운 → HTML (Confluence storage format으로 사용)."""
    html = markdown.markdown(
        md_text,
        extensions=["tables", "nl2br", "sane_lists"],
    )
    return html


def get_parent_page_space() -> str:
    """부모 페이지의 space key를 조회."""
    resp = requests.get(
        f"{CONFLUENCE_URL}/wiki/rest/api/content/{PARENT_PAGE_ID}",
        headers=HEADERS,
        params={"expand": "space"},
    )
    resp.raise_for_status()
    return resp.json()["space"]["key"]


def create_child_page(title: str, body_html: str, space_key: str) -> dict:
    """하위 페이지 생성."""
    payload = {
        "type": "page",
        "title": title,
        "space": {"key": space_key},
        "ancestors": [{"id": PARENT_PAGE_ID}],
        "body": {
            "storage": {
                "value": body_html,
                "representation": "storage",
            }
        },
    }
    resp = requests.post(
        f"{CONFLUENCE_URL}/wiki/rest/api/content",
        headers=HEADERS,
        json=payload,
    )
    resp.raise_for_status()
    return resp.json()


def extract_title(md_text: str) -> str:
    """마크다운 첫 번째 H1을 제목으로 추출."""
    for line in md_text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return "Market Share Report"


def main(report_path: str) -> None:
    path = Path(report_path)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {report_path}")
        sys.exit(1)

    md_text = path.read_text(encoding="utf-8")
    title = extract_title(md_text)
    body_html = md_to_storage(md_text)

    print(f"제목: {title}")
    print(f"부모 페이지 ID: {PARENT_PAGE_ID}")
    print("space key 조회 중...")

    space_key = get_parent_page_space()
    print(f"space key: {space_key}")

    print("하위 페이지 생성 중...")
    result = create_child_page(title, body_html, space_key)

    page_id = result["id"]
    page_url = f"{CONFLUENCE_URL}/wiki/spaces/{space_key}/pages/{page_id}"
    print(f"\n[완료] 업로드 성공!")
    print(f"페이지 ID: {page_id}")
    print(f"URL: {page_url}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python upload_report_to_confluence.py <report.md>")
        sys.exit(1)
    main(sys.argv[1])
