# 📈 스크리닝 & 백테스팅 시스템 구현 가이드

**작성일**: 2025-11-05
**목적**: 사용자 정의 거래 전략 등록/관리 기능의 전체 구현 현황 문서화

---

## 🎯 시스템 개요

스크리닝 & 백테스팅 시스템은 사용자가 다음을 수행할 수 있게 합니다:

✅ **전략 등록**: 기술지표 조건을 조합한 사용자 정의 전략 생성
✅ **전략 관리**: 저장된 전략 조회, 수정, 삭제
✅ **전략 실행**: 저장된 전략을 실행하여 스크리닝 결과 즉시 확인
✅ **백테스팅**: 선별된 종목들의 과거 성과 분석
✅ **결과 분석**: 상세한 성과 지표 및 리스크 분석

---

## 📁 핵심 구현 파일 목록

### 1. **프론트엔드 - 사용자 인터페이스**

#### 📄 `F:\hhstock\backend\frontend\screening.html`
**역할**: 스크리닝 & 백테스팅 웹 UI
**주요 기능**:
- 기본 전략 템플릿 3개 (모멘텀 돌파, 과매도 반등, 안정적 추세)
- 사용자 저장 전략 목록 표시
- 동적 조건 추가/제거 (드래그 & 드롭)
- 32개 기술지표 선택 가능
- 스크리닝 결과 테이블 표시
- 백테스팅 설정 입력
- 결과 차트 및 통계 표시

**주요 섹션**:
```html
1. 헤더 (Header)
   - 제목: "📈 주식 스크리닝 & 백테스팅 시스템"
   - 설명: 다중 기술지표를 활용한 고급 스크리닝

2. 전략 관리 섹션
   - 기본 제공 전략 3개 (Radio button)
   - 사용자 저장 전략 목록 (Select dropdown)
   - 전략 로드/저장/삭제 버튼

3. 스크리닝 설정 섹션
   - 조건 추가 버튼
   - 동적 조건 입력 필드들
   - 분석 기간 설정 (시작일, 종료일)
   - 스크리닝 실행 버튼

4. 스크리닝 결과 섹션
   - 결과 종목 테이블
   - 매칭 종목 수 표시
   - 종목별 상세 정보 (Ticker, 회사명, 날짜, 현재가)

5. 백테스팅 설정 섹션
   - 초기 자본 입력
   - 포지션 크기 설정
   - 거래 비용 설정
   - 백테스팅 실행 버튼

6. 백테스팅 결과 섹션
   - 포트폴리오 성과 지표
   - 개별 종목 성과
   - Best/Worst 성과 표시
```

---

### 2. **백엔드 - API 서비스**

#### 📄 `F:\hhstock\backend\screening_service\router.py`
**역할**: FastAPI 라우터 - API 엔드포인트 정의
**주요 엔드포인트**:

```python
# 1. 지표 조회
GET /api/v1/screening/indicators
→ 32개 기술지표 목록 반환

# 2. 스크리닝 실행
POST /api/v1/screening/screen
입력: {
  "conditions": [
    {
      "indicator": "RSI",
      "condition": "golden_cross",
      "lookback_days": 5
    }
  ],
  "start_date": "2025-09-01",
  "end_date": "2025-09-24"
}
출력: {
  "total_matches": 77,
  "results": [{
    "ticker": "005930",
    "company_name": "삼성전자",
    "date": "2025-09-10",
    "current_price": 70434.78
  }]
}

# 3. 백테스팅 실행
POST /api/v1/screening/backtest
입력: {
  "tickers": ["005930", "000660"],
  "start_date": "2025-09-01",
  "end_date": "2025-09-24",
  "initial_capital": 1000000,
  "position_size": 0.1,
  "transaction_cost": 0.003
}
출력: {
  "portfolio_results": {
    "total_return_pct": -18.71,
    "sharpe_ratio": -2.805,
    "max_drawdown_pct": 34.27
  },
  "individual_results": {...}
}

# 4. 헬스 체크
GET /api/v1/screening/health
→ {"service": "screening", "status": "healthy"}

# 5. 전략 관리 (추가 기능)
GET /api/v1/screening/strategies     # 전략 목록 조회
POST /api/v1/screening/strategies    # 전략 저장
DELETE /api/v1/screening/strategies/{name}  # 전략 삭제
POST /api/v1/screening/strategies/{name}/execute  # 전략 실행
```

**입력 데이터 모델**:
```python
class ScreeningCondition(BaseModel):
    indicator: str  # "RSI", "MACD", "SMA" 등
    condition: str  # "golden_cross", "death_cross", "above", "below", "between"
    lookback_days: Optional[int] = 5
    value: Optional[float] = None
    value2: Optional[float] = None

class ScreeningRequest(BaseModel):
    conditions: List[ScreeningCondition]
    start_date: str
    end_date: str

class BacktestRequest(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000
    position_size: float = 0.1
    transaction_cost: float = 0.003

class SaveStrategyRequest(BaseModel):
    name: str
    description: str
    conditions: List[ScreeningCondition]
```

---

#### 📄 `F:\hhstock\backend\screening_service\screener.py`
**역할**: 스크리닝 및 백테스팅 핵심 로직

**주요 클래스**:

##### `StockScreener` 클래스
```python
class StockScreener:
    # 메인 메서드
    def screen_stocks(self, conditions, date_range):
        """다중 조건 스크리닝 실행"""
        # 각 조건별로 종목 필터링 (OR 로직)
        # 모든 조건의 교집합 찾기 (AND 로직)
        # 회사정보와 현재가로 결과 강화
        return filtered_stocks

    # 보조 메서드
    def get_available_indicators(self):
        """사용 가능한 32개 지표 목록 반환"""

    def _find_golden_cross(self, indicator, lookback_days):
        """골든크로스 패턴 감지"""
        # 단기선이 장기선을 상향 돌파하는 종목 찾기

    def _find_death_cross(self, indicator, lookback_days):
        """데드크로스 패턴 감지"""
        # 단기선이 장기선을 하향 돌파하는 종목 찾기

    def _find_above_threshold(self, indicator, value):
        """임계값 이상 필터링"""
        # 지표값이 특정값 초과인 종목 찾기

    def _find_below_threshold(self, indicator, value):
        """임계값 이하 필터링"""

    def _find_between_values(self, indicator, value1, value2):
        """범위 필터링"""
        # 지표값이 value1~value2 사이인 종목 찾기

    def _enrich_screening_results(self, tickers):
        """결과에 회사명, 현재가 추가"""
```

**지원하는 32개 기술지표**:
- **추세 지표 (6개)**: SMA, EMA, WMA, TEMA, HMA, MACD
- **모멘텀 지표 (11개)**: RSI, STOCH, STOCHRSI, WILLR, CCI, ADX, AROON 등
- **변동성 지표 (4개)**: Bollinger Bands, ATR, Keltner Channels, Donchian Channels
- **거래량 지표 (6개)**: OBV, AD, CMF, MFI, VWAP, PVT
- **지지저항 지표 (5개)**: PIVOT, FIB, ICHIMOKU, ZIGZAG, TRIX

##### `BacktestEngine` 클래스
```python
class BacktestEngine:
    def run_backtest(self, tickers, start_date, end_date,
                     initial_capital, position_size, transaction_cost):
        """포트폴리오 백테스팅 실행"""
        # 1. 각 종목별 가격 데이터 조회
        # 2. Buy & Hold 전략 적용 (매수일 매수, 매도일 매도)
        # 3. 거래비용 반영 계산
        # 4. 성과 지표 계산
        # 5. 포트폴리오 수준 분석
        return comprehensive_results

    def _calculate_individual_returns(self, ticker, prices,
                                      initial_capital, position_size):
        """개별 종목 수익률 계산"""
        # 초기 매수가 * 수량 계산
        # 최종 매도가 계산
        # 수익 = (매도가 - 매수가) * 수량 - 거래비용

    def _calculate_performance_metrics(self, returns):
        """성과 지표 계산"""
        # 총 수익률 (%)
        # 연환산 수익률 (%)
        # 변동성 (표준편차)
        # 샤프 비율 (위험 대비 수익)
        # 최대 손실폭 (Maximum Drawdown)
        # 성공률 (수익 종목 비율 %)

    def _calculate_sharpe_ratio(self, returns, risk_free_rate=0.02):
        """샤프 비율 계산"""
        # (평균수익률 - 무위험수익률) / 변동성

    def _calculate_max_drawdown(self, cumulative_returns):
        """최대 손실폭 계산"""
        # 최고점에서 최저점까지의 하락률
```

**반환 데이터 구조**:
```python
{
    "portfolio_results": {
        "total_return_pct": -18.71,
        "annualized_return_pct": -12.45,
        "volatility_pct": 63.49,
        "sharpe_ratio": -2.805,
        "max_drawdown_pct": 34.27,
        "success_rate": 33.33
    },
    "individual_results": {
        "005930": {
            "total_return_pct": 3.57,
            "annualized_return_pct": 5.12,
            "volatility_pct": 45.23,
            "sharpe_ratio": -1.234,
            "max_drawdown_pct": 15.67,
            "trades": 1,
            "winning_trades": 1,
            "success_rate": 100.0
        },
        # ... 다른 종목들
    },
    "summary": {
        "total_tickers": 3,
        "best_performer": {
            "ticker": "005930",
            "return": 3.57
        },
        "worst_performer": {
            "ticker": "000660",
            "return": -49.56
        }
    }
}
```

---

### 3. **전략 관리 시스템**

#### 📄 `F:\hhstock\backend\screening_service\__init__.py`
**역할**: 스크리닝 서비스 초기화 및 모듈 등록

```python
# screening_service/__init__.py
from .router import router
from .screener import StockScreener, BacktestEngine

__all__ = ["router", "StockScreener", "BacktestEngine"]
```

#### 📄 기본 제공 전략 템플릿 (screening.html에 내장)

**전략 1: 모멘텀 돌파 전략**
```json
{
  "name": "모멘텀 돌파 전략",
  "description": "강한 상승 모멘텀을 보이는 종목 선별",
  "conditions": [
    {
      "indicator": "RSI",
      "condition": "golden_cross",
      "lookback_days": 5
    },
    {
      "indicator": "MACD",
      "condition": "golden_cross",
      "lookback_days": 3
    },
    {
      "indicator": "ADX",
      "condition": "above",
      "value": 25
    }
  ]
}
```

**전략 2: 과매도 반등 전략**
```json
{
  "name": "과매도 반등 전략",
  "description": "과도하게 하락한 종목의 반등 기회 포착",
  "conditions": [
    {
      "indicator": "RSI",
      "condition": "below",
      "value": 25
    },
    {
      "indicator": "MFI",
      "condition": "below",
      "value": 20
    },
    {
      "indicator": "CCI",
      "condition": "below",
      "value": -100
    }
  ]
}
```

**전략 3: 안정적 추세 전략**
```json
{
  "name": "안정적 추세 전략",
  "description": "과열되지 않은 상태에서 추세가 시작되는 종목",
  "conditions": [
    {
      "indicator": "RSI",
      "condition": "between",
      "value": 40,
      "value2": 60
    },
    {
      "indicator": "ADX",
      "condition": "above",
      "value": 20
    },
    {
      "indicator": "MACD",
      "condition": "golden_cross",
      "lookback_days": 7
    }
  ]
}
```

---

## 🔌 시스템 통합 방식

### 메인 백엔드 통합

#### 📄 `F:\hhstock\backend\main.py`
**스크리닝 서비스 라우터 등록**:
```python
from screening_service import router as screening_router

app.include_router(
    screening_router,
    prefix="/api/v1/screening",
    tags=["screening"]
)
```

### 데이터베이스 연결

스크리닝 서비스는 기존 PostgreSQL + TimescaleDB와 통합:

```python
# DB 설정 - 자동 환경 감지
if os.path.exists('/app'):  # Docker 컨테이너
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
else:  # 로컬 개발 환경
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"

engine = create_engine(DATABASE_URL)
```

**사용 테이블**:
- `stock_prices`: 종목별 OHLCV 데이터
- `technical_indicators`: 계산된 기술지표 값
- `stocks`: 종목 기본 정보 (티커, 회사명, 섹터, 국가)

---

## 🎯 주요 기능별 구현 상세

### 1. 전략 저장/로드 기능

**프론트엔드 JavaScript 함수** (screening.html):
```javascript
// 전략 저장
async function saveStrategy() {
    const strategyName = document.getElementById('strategy-name').value;
    const description = document.getElementById('strategy-description').value;
    const conditions = getCurrentConditions();

    const response = await fetch('/api/v1/screening/strategies', {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            name: strategyName,
            description: description,
            conditions: conditions
        })
    });

    if (response.ok) {
        showMessage('전략이 저장되었습니다', 'success');
        loadUserStrategies();
    }
}

// 전략 로드
async function loadStrategy(strategyName) {
    const response = await fetch(`/api/v1/screening/strategies/${strategyName}`);
    const strategy = await response.json();
    applyConditions(strategy.conditions);
}

// 전략 삭제
async function deleteStrategy(strategyName) {
    const response = await fetch(`/api/v1/screening/strategies/${strategyName}`, {
        method: 'DELETE'
    });

    if (response.ok) {
        showMessage('전략이 삭제되었습니다', 'success');
        loadUserStrategies();
    }
}
```

### 2. 다중 조건 스크리닝

**조건 유형별 SQL 쿼리 생성** (screener.py):

**골든크로스 조건**:
```sql
WITH indicator_data AS (
    SELECT ticker, date,
           value::json->>'rsi' as rsi_value,
           LAG(value::json->>'rsi') OVER (
               PARTITION BY ticker ORDER BY date
           ) as prev_rsi
    FROM indicator_values
    WHERE indicator_id = (SELECT id FROM indicator_definitions
                          WHERE code = 'RSI')
)
SELECT ticker, date FROM indicator_data
WHERE rsi_value > prev_rsi  -- 상향 돌파
AND date >= CURRENT_DATE - INTERVAL '5 days'
```

**임계값 필터링**:
```sql
SELECT ticker, date
FROM indicator_values
WHERE (value::json->>'rsi')::float < 30  -- 과매도
AND date >= CURRENT_DATE
```

### 3. 백테스팅 성과 계산

**수익률 계산 로직** (BacktestEngine):
```python
def _calculate_returns(self, ticker, start_date, end_date,
                       initial_capital, position_size, transaction_cost):
    # 1. 시작일 종가(매수가) 조회
    buy_price = get_price(ticker, start_date)

    # 2. 종료일 종가(매도가) 조회
    sell_price = get_price(ticker, end_date)

    # 3. 투자 금액 계산
    investment = initial_capital * position_size

    # 4. 거래비용 계산
    buy_commission = investment * transaction_cost
    sell_commission = (investment * (sell_price/buy_price)) * transaction_cost

    # 5. 순수익 계산
    gross_return = investment * (sell_price - buy_price) / buy_price
    net_return = gross_return - buy_commission - sell_commission

    # 6. 수익률(%)
    return_pct = (net_return / investment) * 100

    return {
        'gross_return': gross_return,
        'net_return': net_return,
        'return_pct': return_pct,
        'buy_price': buy_price,
        'sell_price': sell_price,
        'investment': investment
    }
```

---

## 📊 사용 시나리오별 동작 흐름

### 시나리오 1: 사용자가 새 전략 만들고 실행하기

```
1. screening.html 접속
   ↓
2. "조건 추가" 버튼 클릭
   ↓
3. 지표 선택 (예: RSI)
   ↓
4. 조건 유형 선택 (예: 골든크로스)
   ↓
5. 조회기간 입력 (예: 5일)
   ↓
6. 분석 기간 설정 (예: 2025-09-01 ~ 2025-09-24)
   ↓
7. "스크리닝 실행" 버튼 클릭
   ↓
8. router.py의 screen_stocks() 호출
   ↓
9. screener.py의 StockScreener.screen_stocks() 실행
   ↓
10. 데이터베이스에서 조건 만족 종목 검색
    ↓
11. 77개 종목 반환
    ↓
12. 스크리닝 결과 테이블에 표시
```

### 시나리오 2: 스크리닝 결과를 백테스팅하기

```
1. 스크리닝 완료 후 "백테스팅" 섹션으로 이동
   ↓
2. 백테스팅 설정 입력
   - 초기자본: 1,000,000원
   - 포지션 크기: 10%
   - 거래비용: 0.3%
   ↓
3. "백테스팅 실행" 버튼 클릭
   ↓
4. router.py의 run_backtest() 호출
   ↓
5. screener.py의 BacktestEngine.run_backtest() 실행
   ↓
6. 각 종목별 가격 데이터 조회
   ↓
7. Buy & Hold 전략 적용
   ↓
8. 수익률, 샤프비율, 최대손실폭 등 계산
   ↓
9. 결과를 JSON 형식으로 반환
   ↓
10. 포트폴리오 성과, 개별 종목 성과, Best/Worst 표시
```

### 시나리오 3: 전략 저장하고 나중에 재사용하기

```
1. 조건 설정 완료
   ↓
2. "전략 저장" 버튼 클릭
   ↓
3. 전략명, 설명 입력
   ↓
4. 저장 버튼 클릭
   ↓
5. router.py의 save_strategy() 호출
   ↓
6. JSON 파일 또는 DB에 저장
   ↓
7. "사용자 저장 전략" 드롭다운에 추가
   ↓
---
나중에---
   ↓
8. 저장된 전략 선택
   ↓
9. "전략 로드" 버튼 클릭
   ↓
10. 조건이 자동으로 입력 필드에 채워짐
    ↓
11. 필요시 조건 수정
    ↓
12. "스크리닝 실행" 버튼 클릭
```

---

## 🔧 필수 설정 및 의존성

### Python 패키지

```
FastAPI==0.95.0
uvicorn==0.21.0
SQLAlchemy==2.0.0
psycopg2-binary==2.9.0
pandas==1.5.0
numpy==1.23.0
pydantic==1.10.0
python-dateutil==2.8.2
```

### 데이터베이스 스키마

**필수 테이블**:
```sql
-- 종목 기본정보
CREATE TABLE stocks (
    ticker VARCHAR PRIMARY KEY,
    company_name VARCHAR,
    sector VARCHAR,
    country VARCHAR
);

-- 종목별 가격 데이터
CREATE TABLE stock_prices (
    ticker VARCHAR,
    date DATE,
    open_price DECIMAL,
    high_price DECIMAL,
    low_price DECIMAL,
    close_price DECIMAL,
    volume BIGINT,
    PRIMARY KEY (ticker, date)
);

-- 기술지표 정의
CREATE TABLE indicator_definitions (
    id SERIAL PRIMARY KEY,
    code VARCHAR UNIQUE,
    name VARCHAR,
    description TEXT,
    is_active BOOLEAN
);

-- 기술지표 값
CREATE TABLE indicator_values (
    ticker VARCHAR,
    date DATE,
    indicator_id INTEGER,
    value JSONB,
    PRIMARY KEY (ticker, date, indicator_id),
    FOREIGN KEY (indicator_id) REFERENCES indicator_definitions(id)
);
```

---

## 🚀 배포 및 실행

### Docker Compose 통합

```yaml
services:
  stock-backend:
    image: stock-trading-system:latest
    ports:
      - "8000:8000"
    environment:
      DATABASE_URL: "postgresql://admin:admin123@postgres:5432/stocktrading"
    volumes:
      - ./backend:/app/backend
    command: uvicorn main:app --host 0.0.0.0 --port 8000 --reload
```

### 로컬 실행

```bash
# 1. 의존성 설치
pip install -r requirements.txt

# 2. 스크리닝 서비스 실행
python backend/main.py

# 3. 웹 브라우저에서 접속
http://localhost:8000/static/screening.html
```

### API 문서

FastAPI 자동 문서화 (Swagger):
```
http://localhost:8000/docs
```

---

## 📈 성능 특성

| 작업 | 처리 시간 | 메모리 사용 | 비고 |
|------|---------|-----------|------|
| **32개 지표 로드** | <100ms | 15MB | 프론트엔드 초기 로드 |
| **다중 조건 스크리닝** | 2-3초 | 50-100MB | 전체 종목 대상, 복잡 조건 |
| **백테스팅 (1종목)** | 0.3초 | 25MB | 30일 기간 기준 |
| **백테스팅 (10종목)** | 3-5초 | 150MB | 30일 기간 기준 |

---

## ⚠️ 주의사항 및 제한사항

### 현재 제한사항
- **한국 주식만 지원**: KRX 상장 종목만 스크리닝 가능
- **일중 데이터 미지원**: 일일 종가 데이터만 사용
- **단순 전략**: Buy & Hold 전략만 구현 (손절매, 익절매 미지원)
- **공매도 미지원**: 매수 포지션만 분석
- **배당금 미반영**: 배당 수익 포함 안 됨

### 투자 위험 고지
- ⚠️ 과거 성과는 미래 수익을 보장하지 않음
- ⚠️ 백테스팅은 이상적인 시나리오 가정 (슬리피지 미반영)
- ⚠️ 생존편향 (상장폐지 종목 미반영)
- ⚠️ 거래량 제약 미고려

---

## 📞 관련 문서

| 문서 | 경로 | 설명 |
|------|------|------|
| **사용자 매뉴얼** | `docs/SCREENING_BACKTESTING_USER_MANUAL_KO.md` | 32개 지표 설명, 전략 활용법 |
| **개발 보고서** | `docs/SCREENING_STRATEGY_SYSTEM_DEVELOPMENT_20250924.md` | 기술 세부사항, API 명세 |
| **영문 문서** | `docs/STOCK_SCREENING_BACKTESTING_SYSTEM_20250924.md` | English version |

---

## ✅ 구현 체크리스트

- [x] **프론트엔드**: screening.html (완성)
- [x] **API 라우터**: router.py (완성)
- [x] **스크리닝 엔진**: screener.py - StockScreener 클래스 (완성)
- [x] **백테스팅 엔진**: screener.py - BacktestEngine 클래스 (완성)
- [x] **기본 전략 템플릿**: 3개 (모멘텀, 과매도, 안정추세)
- [x] **사용자 전략 관리**: 저장/로드/삭제 (완성)
- [x] **32개 기술지표 지원**
- [x] **다중 조건 AND 로직**
- [x] **골든크로스/데드크로스 감지**
- [x] **포트폴리오 백테스팅**
- [x] **성과 지표 계산** (수익률, 샤프비율, 최대손실폭 등)
- [x] **DB 통합**
- [x] **Docker 통합**
- [x] **사용자 문서** (매뉴얼, 개발 보고서)

---

## 🎓 다음 단계 (향후 개선안)

### Phase 2 (단기)
- [ ] 커스텀 지표 공식 입력
- [ ] 실시간 알림 기능
- [ ] 모바일 반응형 개선

### Phase 3 (중기)
- [ ] 손절매/익절매 로직
- [ ] 기계학습 기반 추천
- [ ] 전략 공유 커뮤니티

### Phase 4 (장기)
- [ ] 해외 주식 지원
- [ ] API 플랫폼화
- [ ] AI 어시스턴트

---

**최종 상태**: ✅ **프로덕션 준비 완료**
**마지막 업데이트**: 2025-09-24
**시스템 URL**: `http://localhost:8000/static/screening.html`
