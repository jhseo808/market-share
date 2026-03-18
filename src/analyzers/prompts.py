"""Prompt template functions for Claude analysis."""
from __future__ import annotations

import json
from typing import Any

from src.parsers.models import ParsedDataset


def _entry_to_dict(entry: Any) -> dict[str, Any]:
    return {
        "item": entry.item,
        "latest_share": entry.latest_share,
        "average_share": entry.average_share,
        "trend": entry.trend,
    }


def build_analysis_prompt(
    datasets: list[ParsedDataset],
    top_n: int = 10,
    must_test_threshold: float = 10.0,
    should_test_threshold: float = 3.0,
) -> str:
    """Build the system + user prompt for Claude QA analysis."""

    data_summary: dict[str, list[dict[str, Any]]] = {}
    for ds in datasets:
        if ds.success:
            data_summary[ds.category] = [
                _entry_to_dict(e) for e in ds.top_n(top_n)
            ]

    data_json = json.dumps(data_summary, ensure_ascii=False, indent=2)

    system_prompt = (
        "You are a QA strategy expert specializing in cross-browser and cross-device testing "
        "for Korean web and mobile applications. "
        "You analyze real market share data and produce actionable test prioritization matrices. "
        "Be concise: use short phrases only, no explanations or full sentences."
    )

    user_prompt = f"""아래는 대한민국 시장의 최신 브라우저/디바이스/OS 점유율 데이터입니다.
QA 테스트 우선순위를 도출해 주세요.

**임계값**
- must_test: >{must_test_threshold}% / should_test: {should_test_threshold}~{must_test_threshold}% / low_priority: <{should_test_threshold}%

**데이터 (상위 {top_n}개)**
```json
{data_json}
```

**응답 규칙**
- 순수 JSON만 반환 (코드블록 없이)
- 각 항목: "이름 (점유율%)" 형식, 추가 설명 없음
- risk_analysis: 핵심 위험 5개 이내, area/risk/action 각 30자 이내
- recommendations: 5개 이내, 각 30자 이내 한 줄 요약

{{
  "browser_matrix": {{
    "must_test": ["항목명 (점유율%)"],
    "should_test": ["항목명 (점유율%)"],
    "low_priority": ["항목명 (점유율%)"]
  }},
  "device_matrix": {{
    "must_test": ["항목명 (점유율%)"],
    "should_test": ["항목명 (점유율%)"],
    "low_priority": ["항목명 (점유율%)"]
  }},
  "os_coverage": {{
    "must_test": ["항목명 (점유율%)"],
    "should_test": ["항목명 (점유율%)"],
    "low_priority": ["항목명 (점유율%)"]
  }},
  "risk_analysis": [
    {{"area": "영역", "risk": "위험", "action": "조치"}}
  ],
  "recommendations": ["권장사항"]
}}
"""

    return system_prompt, user_prompt
