# coin-trader

실시간 AI 코인 트레이딩 봇. Opus 4.6 전략 판단 + Codex 5.3 코드 생성으로 자동화된 암호화폐 거래를 수행합니다.

## 아키텍처

```
[Upbit WebSocket] ─tick─→ [Redis pub/sub] ─→ [Strategy Evaluator]
                               │                      │
[Notice Fetcher] ─5min─→──────→│               ┌──────┴──────┐
[Fear & Greed]  ─5min─→───────→│               │   Signal    │
[CoinGecko]    ─30min─→───────→│               └──────┬──────┘
                                                       │
                                               [Opus 4.6 판단]
                                                       │
                                               [Risk Manager]
                                                       │
                                                [Executor]
                                                  │    │
                                    ┌─────────────┘    └──────────────┐
                                    │                                 │
                              [PostgreSQL]                      [FalkorDB]
                              거래 기록 저장                   전략 계보 업데이트
```

### 기술 스택

| 컴포넌트 | 기술 | 역할 |
|----------|------|------|
| 런타임 | Python 3.9+ | 비동기 이벤트 드리븐 |
| AI (전략) | Claude Opus 4.6 | 시그널 판단, 시장 분석 |
| AI (공학) | Codex 5.3 | 백테스트 생성, 파라미터 최적화 |
| DB | PostgreSQL 16 | 거래 기록, 전략 상태, AI 판단 |
| 캐시 | Redis 7 | 실시간 가격 캐시, pub/sub 이벤트 버스 |
| 그래프 | FalkorDB | 전략 계보, 코인 상관관계, 이벤트 전파 |
| 거래소 | Upbit | WebSocket 실시간 + REST API |

---

## 빠른 시작

### 1. 인프라 실행

```bash
docker-compose up -d
```

PostgreSQL (5432), Redis (6379), FalkorDB (6380) 이 시작됩니다.

### 2. 환경 설정

```bash
cp .env.example .env
# .env 파일에 API 키 입력
```

```
UPBIT_ACCESS_KEY=your_key
UPBIT_SECRET_KEY=your_secret
ANTHROPIC_API_KEY=your_key
OPENAI_API_KEY=your_key       # Codex용
LUNARCRUSH_API_KEY=your_key   # 선택
```

### 3. 설치

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 4. 실행

```bash
# 페이퍼 트레이딩 (기본)
python -m coin_trader run --mode paper

# 단일 사이클 실행
python -m coin_trader run --mode paper --once
```

---

## CLI 명령어

| 명령어 | 설명 |
|--------|------|
| `run --mode paper` | 페이퍼 트레이딩 실행 |
| `run --mode live` | 실매매 (Phase 2, 검증 후) |
| `leaderboard --top 10` | 전략 성과 순위표 |
| `report` | 일일 성과 리포트 |
| `evolve dip_buy --generations 5` | 전략 파라미터 진화 |
| `ai discuss "시장 분석해줘"` | Opus AI와 대화 |
| `ai market` | AI 시장 분석 |
| `graph lineage --strategy dip_buy` | 전략 계보 조회 |
| `graph correlations --ticker KRW-BTC` | 코인 상관관계 조회 |
| `version` | 버전 확인 |

---

## 전략

### 활성 전략 (6개)

#### 1. Dip Buy (`dip_buy`) — 검증 완료

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `drop_pct` | -7% | 매수 진입 하락폭 |
| `recovery_pct` | +2% | 매도 회복폭 |
| `timeframe_hours` | 24h | 관찰 기간 |

**v1 실적**: +23.82% 수익률, 100% 승률 (10거래)

**로직**: 24시간 내 7% 이상 하락 시 매수 → 진입가 대비 2% 회복 시 매도

#### 2. Momentum (`momentum`)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `lookback_hours` | 12 | 모멘텀 관찰 기간 |
| `entry_threshold` | +5% | 매수 진입 상승폭 |
| `exit_threshold` | -3% | 매도 손절 기준 |

**로직**: 12시간 내 5% 이상 상승 추세 시 진입 → 진입가 대비 3% 하락 시 청산

#### 3. Volatility Breakout (`volatility_breakout`)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `k_factor` | 0.5 | 변동성 돌파 계수 (Larry Williams) |

**로직**: `현재가 > 시가 + k × (전일고가 - 전일저가)` 충족 시 매수

#### 4. Fear & Greed (`fear_greed`)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `buy_threshold` | 25 | 극단적 공포 매수 |
| `sell_threshold` | 75 | 극단적 탐욕 매도 |

**로직**: Fear & Greed Index 25 이하 → 매수, 75 이상 → 매도 (역발상)

#### 5. Volume Surge (`volume_surge`)

| 파라미터 | 값 | 설명 |
|---------|-----|------|
| `lookback_hours` | 24 | 평균 거래량 기간 |
| `volume_multiplier` | 3.0 | 급등 배수 |

**로직**: 24시간 평균 대비 3배 이상 거래량 + 양봉 시 매수

#### 6. Notice Alpha (`notice_alpha`)

| 키워드 | 설명 |
|--------|------|
| 신규 | 신규 거래 지원 |
| 상장 | 신규 상장 |
| 에어드롭 | 에어드롭 이벤트 |

**로직**: 업비트 공시에서 키워드 감지 → 해당 코인 매수

### 비활성 전략 (v1 실패)

| 전략 | v1 수익률 | 비활성 사유 |
|------|-----------|------------|
| RSI | -58% | 과매도 진입 실패 |
| MA Cross | -34% | 골든/데드크로스 휩소 |
| Bollinger | -75% | 밴드 엣지 과잉매매 |

---

## 리스크 관리

| 규칙 | 값 | 설명 |
|------|-----|------|
| 손절 (Stop-Loss) | -5% | 진입가 대비 5% 하락 시 자동 청산 |
| 익절 (Take-Profit) | +10% | 진입가 대비 10% 상승 시 자동 청산 |
| 트레일링 스탑 | 3% | 최고가 대비 3% 하락 시 청산 |
| 일 최대 손실 | -3% | 당일 누적 손실 3% 도달 시 매수 중단 |
| 최대 낙폭 | -15% | 전체 포트폴리오 -15% 시 전면 중단 |
| 최대 포지션 | 5 | 동시 보유 최대 5개 코인 |
| 수수료 | 0.05% | Upbit 거래 수수료 |

### 리스크 체크 순서

```
1. 일일 손실 한도 확인
2. 최대 낙폭 확인
3. 최대 포지션 수 확인
4. 잔고 충분 여부 확인
5. 중복 포지션 확인
6. ─── 매수 허가 ───
```

---

## FalkorDB 그래프 활용

### 1. 전략 계보 (Strategy Lineage)

전략 파라미터 변이를 추적하여 어떤 진화 방향이 성공적인지 분석:

```cypher
// 성과 좋은 전략의 공통 조상 파라미터 찾기
MATCH (ancestor:Strategy)-[:MUTATED_TO*]->(good:Strategy)
WHERE good.return_pct > 10
RETURN ancestor.params, count(good) AS descendants
ORDER BY descendants DESC
```

### 2. 코인 상관관계

BTC 급락 시 영향받는 코인 사전 파악:

```cypher
// BTC와 상관계수 0.7+, 15분 내 영향 코인
MATCH (btc:Coin {ticker:'KRW-BTC'})-[r:CORRELATES]->(alt)
WHERE r.coefficient > 0.7 AND r.lag_minutes <= 15
RETURN alt.ticker, r.coefficient
```

### 3. 이벤트 전파

공시/이벤트의 과거 가격 영향 패턴 학습:

```cypher
// 신규 상장 공시의 평균 가격 영향
MATCH (e:MarketEvent {type:'NEW_LISTING'})-[:TRIGGERED]->(p:PriceMove)
RETURN avg(p.change_pct), avg(r.lag_minutes)
```

---

## AI 오케스트레이션

### Opus 4.6 (전략 판단)
- 시그널 실행 여부 판단 (EXECUTE / SKIP / MODIFY)
- 시장 상황 분석 (공포/탐욕, BTC 도미넌스, 상관관계)
- 주간 전략 리뷰 (FalkorDB 계보 참조)
- 대화형 전략 토론

### Codex 5.3 (엔지니어링)
- 백테스트 코드 자동 생성
- 전략 파라미터 돌연변이 제안
- 성과 분석 스크립트

### AI 판단 흐름

```
Strategy Signal → Opus 평가 → {
  EXECUTE: 즉시 실행
  SKIP: 무시 (이유 기록)
  MODIFY: 파라미터 조정 후 재평가
} → Risk Manager → 최종 실행
```

---

## 프로젝트 구조

```
coin-trader/
├── config/default.toml          # 설정 파일
├── docker-compose.yml           # PostgreSQL + Redis + FalkorDB
├── src/coin_trader/
│   ├── cli.py                   # Typer CLI
│   ├── config.py                # TOML + .env 설정 로더
│   ├── domain/                  # 핵심 비즈니스 로직
│   │   ├── models.py            # Pydantic 모델
│   │   ├── risk.py              # 리스크 관리
│   │   ├── portfolio.py         # 포트폴리오 관리
│   │   ├── strategy.py          # 전략 프로토콜
│   │   └── evolution.py         # AI 보조 전략 진화
│   ├── strategies/              # 전략 구현 (6개)
│   ├── stream/                  # WebSocket + Redis 이벤트 버스
│   ├── data/                    # 외부 데이터 소스 (5개)
│   ├── execution/               # 매매 실행 (paper/live)
│   ├── ai/                      # AI 오케스트레이션
│   ├── graph/                   # FalkorDB 그래프 레이어
│   ├── persistence/             # PostgreSQL + Redis
│   └── reporting/               # 리포트 + 리더보드
├── tests/                       # 165개 테스트
│   ├── unit/                    # 유닛 테스트
│   ├── integration/             # 통합 테스트
│   └── e2e/                     # E2E 풀사이클 테스트
└── scripts/
    └── migrate_v1_data.py       # v1 데이터 마이그레이션
```

---

## 테스트

```bash
# 전체 테스트 실행
pytest tests/ -v

# 커버리지 포함
pytest tests/ --cov=src/coin_trader --cov-report=term-missing

# E2E 테스트만
pytest tests/e2e/ -v

# 특정 전략 테스트
pytest tests/unit/strategies/test_dip_buy.py -v
```

현재: **165개 테스트, 62% 커버리지**

---

## v1 데이터 마이그레이션

기존 `/clawd/trading-bot/` 데이터를 PostgreSQL로 이관:

```bash
# docker-compose가 실행된 상태에서
python scripts/migrate_v1_data.py
```

---

## 설정 (config/default.toml)

```toml
[app]
mode = "paper"                    # paper | live

[trading]
initial_krw = 1_000_000          # 초기 자본금
buy_amount = 100_000             # 1회 매수 금액
target_coins = ["KRW-BTC", "KRW-ETH", ...]  # 대상 코인 10개

[risk]
stop_loss_pct = -5.0             # 손절 라인
take_profit_pct = 10.0           # 익절 라인
trailing_stop_pct = 3.0          # 트레일링 스탑
max_positions = 5                # 최대 동시 포지션

[strategies.dip_buy]
enabled = true
params = { drop_pct = -7, recovery_pct = 2, timeframe_hours = 24 }
```

전체 설정은 `config/default.toml` 참조.

---

## 배포 전략

```
Phase 1 (현재): 페이퍼 트레이딩
  → dip_buy v1 시그널과 비교 검증
  → 최소 2주 페이퍼 검증

Phase 2: 소액 실매매
  → 초기 자본금 100,000 KRW
  → dip_buy 전략만 활성화
  → 리스크 파라미터 강화

Phase 3: 전체 전략 활성화
  → AI 판단 통합
  → 전략 진화 자동화
```
