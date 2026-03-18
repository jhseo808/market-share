# Market Share QA Tool

한국 시장의 브라우저/디바이스/OS 점유율 데이터를 자동으로 수집하고, Claude AI로 분석하여 **테스트 우선순위 리포트**를 생성하는 QA 전용 CLI 도구입니다.

---

## 왜 만들었나?

QA 엔지니어가 테스트 계획을 세울 때 가장 먼저 해야 할 일 중 하나는 **"어떤 브라우저와 디바이스를 얼마나 테스트해야 하는가?"** 를 결정하는 것입니다.

기존 방식의 문제:
- StatCounter 등 점유율 사이트를 수동으로 접속해 데이터를 확인
- 각 카테고리(브라우저, OS, 디바이스 등)별로 따로 수집
- 수집한 데이터를 보고 테스트 우선순위를 직접 판단
- 매번 반복되는 단순 작업에 시간 소요

이 도구는 위 과정을 **완전 자동화**합니다:

1. StatCounter(한국 시장) 에서 7개 카테고리 점유율 데이터를 자동 수집
2. 수집된 데이터를 정규화하여 트렌드 분석 (성장/하락/안정)
3. Claude AI가 QA 관점에서 분석 — Must Test / Should Test / Low Priority 매트릭스 생성
4. 팀에서 바로 활용 가능한 Markdown 리포트 자동 생성

---

## QA 엔지니어에게 어떤 도움이 되나?

### 테스트 우선순위 자동 결정

| 등급 | 기준 | 의미 |
|------|------|------|
| Must Test (필수) | 점유율 >10% | 반드시 테스트해야 하는 환경 |
| Should Test (권장) | 점유율 3~10% | 가능하면 테스트하는 것이 좋은 환경 |
| Low Priority (선택) | 점유율 <3% | 리소스 여유가 있을 때 테스트 |

### 트렌드 기반 리스크 파악

단순 현재 점유율뿐 아니라 **상승/하락 트렌드**를 파악합니다. 빠르게 성장 중인 환경(예: 새 iOS 버전, 새 브라우저 버전)은 현재 점유율이 낮아도 사전 대응이 필요할 수 있습니다.

### 반복 작업 제거

테스트 계획 시마다 동일한 데이터 수집 작업을 CLI 명령어 하나로 대체합니다.

```bash
python -m src.main run --period 202502-202602
```

실행 결과 예시 (실제 생성된 리포트 데이터):

```
브라우저 (2025.02~2026.02 기준)
- Chrome          55.0%  (Must Test)
- Safari          12.8%  (Must Test)
- Samsung Internet 12.2% (Must Test)
- Whale Browser    9.2%  (Should Test)
- Edge             8.5%  (Should Test)
```

---

## 설치 및 환경 설정

### 사전 요구사항

- Python 3.11+
- Anthropic API 키

### 설치

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. Playwright 브라우저 설치 (최초 1회)
playwright install chromium

# 3. API 키 설정
cp .env.example .env
# .env 파일에 ANTHROPIC_API_KEY 값 입력
```

### .env 파일

```
ANTHROPIC_API_KEY=sk-ant-api03-...
```

---

## 실행 방법

### 전체 파이프라인 (수집 → 파싱 → AI 분석 → 리포트)

```bash
# 기본 실행 — 전체 7개 카테고리
python -m src.main run --period 202502-202602

# 특정 카테고리만 실행
python -m src.main run --period 202502-202602 --categories browser,browser-version

# AI 분석 없이 데이터 수집/요약만
python -m src.main run --period 202502-202602 --skip-analysis
```

**기간 형식:** `YYYYMM-YYYYMM` (예: `202502-202602` = 2025년 2월 ~ 2026년 2월)

### 기타 명령어

```bash
# 사용 가능한 카테고리 목록 확인
python -m src.main list-categories

# 환경 및 설정 유효성 검증
python -m src.main validate-config
```

### 실행 흐름

```
[1/4] 데이터 수집 — StatCounter에서 CSV 다운로드 (Playwright, 병렬)
[2/4] CSV 파싱    — 점유율 정규화 및 트렌드 계산
[3/4] AI 분석     — Claude가 QA 매트릭스 및 리스크 분석
[4/4] 리포트 생성 — data/reports/ 에 Markdown 파일 저장
```

### 병렬 수집

카테고리 수집은 `asyncio`를 사용해 **병렬로 처리**됩니다. 기본 동시 실행 수는 3개로, 7개 카테고리 기준 3개 → 3개 → 1개 묶음으로 실행됩니다.

```
병렬 처리 (현재): [cat1, cat2, cat3] → [cat4, cat5, cat6] → [cat7]
```

동시 실행 수를 조절하고 싶은 경우 `src/collectors/statcounter.py`의 `collect_all(concurrency=3)` 값을 변경합니다.

> **참고:** 동시 실행 수를 4 이상으로 높이면 StatCounter 서버에서 동시 접속을 차단할 수 있습니다. 3이 안정적인 기본값입니다.

---

## 수집 카테고리

`config.yaml` 에 정의된 7개 카테고리:

| 카테고리 키 | 설명 |
|------------|------|
| `browser` | 브라우저 (전체 기기) |
| `browser-version` | 브라우저 버전 상세 |
| `ios-version` | iOS 버전 (모바일+태블릿) |
| `android-version` | Android 버전 (모바일+태블릿) |
| `device-vendor` | 디바이스 제조사 (Samsung, Apple 등) |
| `desktop-os` | 데스크탑 OS (Windows, macOS 등) |
| `device-type` | 디바이스 타입 (모바일/태블릿/데스크탑) |

---

## 폴더 및 파일 구조

```
market-share/
├── .env                        # API 키 (git 제외)
├── .env.example                # API 키 템플릿
├── config.yaml                 # 수집 URL, 임계값, 모델 설정
├── requirements.txt            # 의존성 목록
├── pytest.ini                  # 테스트 설정
│
├── src/                        # 소스 코드
│   ├── main.py                 # CLI 진입점 (Click)
│   ├── config.py               # config.yaml + .env 로더
│   │
│   ├── collectors/             # 데이터 수집 레이어
│   │   ├── statcounter.py      # Playwright로 StatCounter CSV 수집
│   │   ├── base.py             # 추상 베이스 클래스
│   │   └── models.py           # CollectedDataset 데이터 모델
│   │
│   ├── parsers/                # CSV 파싱 레이어
│   │   ├── csv_parser.py       # Wide/Tall 포맷 파싱, 트렌드 계산
│   │   ├── base.py
│   │   └── models.py           # MarketShareEntry 데이터 모델
│   │
│   ├── analyzers/              # AI 분석 레이어
│   │   ├── claude_analyzer.py  # Anthropic API 연동
│   │   ├── prompts.py          # Claude 프롬프트 템플릿
│   │   └── base.py
│   │
│   └── reporters/              # 리포트 출력 레이어
│       ├── markdown_reporter.py # Markdown 리포트 생성
│       ├── registry.py          # 리포터 플러그인 레지스트리
│       ├── base.py              # BaseReporter 인터페이스
│       ├── slack_reporter.py    # Stub (미구현)
│       └── confluence_reporter.py  # Stub (미구현)
│
├── data/
│   ├── raw/                    # 수집된 원본 CSV 파일
│   │   └── {category}_{period}.csv
│   └── reports/                # 생성된 Markdown 리포트
│       └── market-share-report_{period}_{timestamp}.md
│
└── tests/                      # 단위 테스트
    ├── conftest.py             # 공통 픽스처
    ├── collectors/test_statcounter.py
    ├── parsers/test_csv_parser.py
    ├── analyzers/test_claude_analyzer.py
    └── reporters/test_markdown_reporter.py
```

### 주요 파일 설명

| 파일 | 역할 | 수정이 필요한 경우 |
|------|------|--------------------|
| `config.yaml` | 수집 카테고리, URL, 임계값 설정 | 카테고리 추가/변경, 임계값 조정 |
| `src/collectors/statcounter.py` | StatCounter 웹 스크래핑 | StatCounter UI 변경 시 |
| `src/parsers/csv_parser.py` | CSV 데이터 정규화 | CSV 포맷 변경 시 |
| `src/analyzers/prompts.py` | Claude AI 프롬프트 | 분석 관점 변경, 한/영 전환 시 |
| `src/reporters/markdown_reporter.py` | Markdown 리포트 템플릿 | 리포트 형식 변경 시 |

### 결과물 확인

실행 후 생성된 리포트는 `data/reports/` 디렉토리에서 확인합니다:

```
data/reports/market-share-report_202502-202602_20260317_181232.md
```

파일명 형식: `market-share-report_{기간}_{생성일시}.md`

---

## 테스트 실행

```bash
# 전체 단위 테스트 (네트워크 불필요)
pytest tests/ -v

# 커버리지 포함
pytest tests/ -v --cov=src

# E2E 테스트 제외
pytest tests/ -v -m "not e2e"
```

---

## 설정 파일 (`config.yaml`) 주요 항목

```yaml
thresholds:
  must_test: 10.0    # >10% → 필수 테스트 대상
  should_test: 3.0   # 3~10% → 권장 테스트 대상

trend:
  delta_pp: 2.0      # ±2pp 이상 변화 시 성장/하락으로 분류

analysis:
  model: "claude-sonnet-4-6"
  top_n_items: 10    # 카테고리별 상위 N개 항목만 AI 분석에 사용
```

---

## 기술 스택

| 역할 | 라이브러리 |
|------|-----------|
| 웹 자동화 (데이터 수집) | Playwright 1.49 |
| 데이터 처리 | pandas 2.2 |
| AI 분석 | Anthropic SDK (claude-sonnet-4-6) |
| CLI | Click 8.1 |
| 설정 관리 | PyYAML + python-dotenv |
| 테스트 | pytest + pytest-asyncio + pytest-mock |
