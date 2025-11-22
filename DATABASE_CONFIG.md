# 데이터베이스 설정 가이드

## 1. 데이터베이스 선택 기준

### 운영 DB (Production Database)
- **IP**: 192.168.219.103
- **포트**: 5432
- **데이터베이스명**: stocktrading
- **사용자**: admin
- **비밀번호**: admin123
- **용도**: 실제 주가 데이터, 지표 저장
- **언제 사용**:
  - Daily collection DAG (실제 주가 수집)
  - Indicator DAG (실제 지표 계산)
  - 데이터 검증/분석
  - 프로덕션 배포 후 쿼리

### Docker 내부 DB (Development Database)
- **위치**: Docker container (stock-db)
- **접속명령**: `docker exec stock-db psql -U admin -d stocktrading`
- **데이터베이스명**: stocktrading
- **사용자**: admin
- **비밀번호**: admin123
- **용도**: DAG 테스트, 로컬 개발
- **언제 사용**:
  - DAG 테스트 (`airflow dags test ...`)
  - Docker 내부에서만 유효
  - 외부에서는 접속 불가

---

## 2. 주요 테이블 스키마

### stock_prices (주가 데이터)
```sql
CREATE TABLE stock_prices (
    ticker VARCHAR(20) NOT NULL,      -- 종목코드
    date DATE NOT NULL,               -- 거래일
    open_price NUMERIC,               -- 시가
    high_price NUMERIC,               -- 고가
    low_price NUMERIC,                -- 저가
    close_price NUMERIC,              -- 종가
    volume BIGINT,                    -- 거래량
    created_at TIMESTAMP,             -- 생성일시
    PRIMARY KEY (ticker, date)
);
```

**용도**: 일일 주가 저장
**레코드 수**: ~3,047,288개
**기간**: 2025-01-01 ~ 2025-10-29

---

### technical_indicators (기술적 지표)
```sql
CREATE TABLE technical_indicators (
    ticker VARCHAR(20) NOT NULL,
    date DATE NOT NULL,
    rsi NUMERIC,                      -- Relative Strength Index
    macd NUMERIC,                     -- MACD
    macd_signal NUMERIC,              -- MACD Signal Line
    macd_histogram NUMERIC,           -- MACD Histogram
    sma_20 NUMERIC,                   -- 20일 이동평균
    sma_50 NUMERIC,                   -- 50일 이동평균
    sma_200 NUMERIC,                  -- 200일 이동평균
    stoch_k NUMERIC,                  -- Stochastic K
    stoch_d NUMERIC,                  -- Stochastic D
    bollinger_upper NUMERIC,          -- Bollinger Bands Upper
    bollinger_middle NUMERIC,         -- Bollinger Bands Middle
    bollinger_lower NUMERIC,          -- Bollinger Bands Lower
    ichimoku_tenkan NUMERIC,          -- Ichimoku Tenkan
    ichimoku_kijun NUMERIC,           -- Ichimoku Kijun
    ichimoku_senkou_a NUMERIC,        -- Ichimoku Senkou A
    ichimoku_senkou_b NUMERIC,        -- Ichimoku Senkou B
    ichimoku_chikou NUMERIC,          -- Ichimoku Chikou
    created_at TIMESTAMP,
    PRIMARY KEY (ticker, date),
    UNIQUE (ticker, date)
);
```

**용도**: 일일 기술적 지표 저장
**레코드 수**: ~2,991,375개
**기간**: 2025-01-01 ~ 2025-10-29

---

### collection_log (수집 로그)
```sql
CREATE TABLE collection_log (
    id SERIAL PRIMARY KEY,
    collection_date DATE NOT NULL UNIQUE,
    overall_status VARCHAR(50),       -- success, partial, failed
    price_status VARCHAR(50),         -- success, failed, pending
    price_count INTEGER,              -- 수집된 주가 수
    indices_count INTEGER,            -- 수집된 지수 수
    retry_count INTEGER DEFAULT 0,
    error TEXT,                       -- 에러 메시지
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP
);
```

**용도**: 주가 수집 상태 기록
**주요 칼럼**:
- overall_status: 전체 수집 상태
- price_count: 수집된 stock_prices 행 수 (약 2,700-2,800개/일)

---

### indicator_log (지표 계산 로그)
```sql
CREATE TABLE indicator_log (
    id SERIAL PRIMARY KEY,
    indicator_date DATE NOT NULL UNIQUE,
    status VARCHAR(50),               -- success, failed, retrying, pending
    indicators_count INTEGER,         -- 계산된 지표 수
    required_prices_count INTEGER,    -- 필요한 주가 수
    collected_prices_count INTEGER,   -- 실제 수집된 주가 수
    retry_count INTEGER DEFAULT 0,
    error_message TEXT,
    last_error TEXT,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    created_at TIMESTAMP
);
```

**용도**: 기술적 지표 계산 상태 기록
**주요 칼럼**:
- indicators_count: 계산된 technical_indicators 행 수 (약 2,770-2,780개/일)

---

## 3. Python에서 DB 연결 코드

### 운영 DB 연결 (권장)
```python
import psycopg2

# 운영 DB 연결
conn = psycopg2.connect(
    host='192.168.219.103',
    port=5432,
    database='stocktrading',
    user='admin',
    password='admin123'
)
cursor = conn.cursor()

# 쿼리 실행
cursor.execute("SELECT COUNT(*) FROM stock_prices;")
result = cursor.fetchone()
print(f"Total records: {result[0]:,}")

cursor.close()
conn.close()
```

### SQLAlchemy 사용 (DAG에서 권장)
```python
from sqlalchemy import create_engine

engine = create_engine(
    "postgresql://admin:admin123@192.168.219.103:5432/stocktrading",
    connect_args={"options": "-c client_encoding=utf8"}
)

# 쿼리 실행
import pandas as pd
df = pd.read_sql("SELECT * FROM stock_prices WHERE date = '2025-10-29'", engine)
print(f"2025-10-29 data: {len(df)} records")
```

---

## 4. 자주 사용하는 쿼리

### 1) 일일 수집 현황 확인
```sql
-- 최근 10일 주가 수집 현황
SELECT date, COUNT(*) as count FROM stock_prices
WHERE date >= CURRENT_DATE - INTERVAL '10 days'
GROUP BY date ORDER BY date DESC;

-- 기대값: 각 날짜마다 2,700-2,800개
```

### 2) 일일 지표 계산 현황 확인
```sql
-- 최근 5일 지표 계산 로그
SELECT indicator_date, status, indicators_count
FROM indicator_log
WHERE indicator_date >= CURRENT_DATE - INTERVAL '5 days'
ORDER BY indicator_date DESC;

-- 기대값: status='success', indicators_count=2,770-2,780개
```

### 3) 수집 실패 날짜 확인
```sql
-- 누락된 거래일 찾기
SELECT DISTINCT trading_day
FROM (
    SELECT DATE(day) as trading_day
    FROM generate_series(
        DATE '2025-10-01',
        CURRENT_DATE,
        '1 day'::interval
    ) day
    WHERE EXTRACT(DOW FROM day) NOT IN (0, 6)  -- 평일만
) trading_days
WHERE trading_day NOT IN (
    SELECT DISTINCT date FROM stock_prices WHERE date >= '2025-10-01'
)
ORDER BY trading_day DESC;
```

### 4) 특정 날짜 데이터 확인
```sql
-- 2025-10-29 수집 현황
SELECT date, COUNT(*) as total,
       COUNT(DISTINCT ticker) as tickers
FROM stock_prices
WHERE date = '2025-10-29'
GROUP BY date;

-- 2025-10-29 지표 계산 현황
SELECT date, COUNT(*) as indicators
FROM technical_indicators
WHERE date = '2025-10-29'
GROUP BY date;
```

### 5) 개별 종목 데이터 조회
```sql
-- 특정 종목의 최근 10일 주가
SELECT ticker, date, close_price
FROM stock_prices
WHERE ticker = '005930'  -- 삼성전자
  AND date >= CURRENT_DATE - INTERVAL '10 days'
ORDER BY date DESC;

-- 특정 종목의 최신 지표
SELECT ticker, date, rsi, macd, sma_20, bollinger_upper, bollinger_lower
FROM technical_indicators
WHERE ticker = '005930'
ORDER BY date DESC
LIMIT 10;
```

---

## 5. 운영 DB vs Docker DB 선택 가이드

| 상황 | 사용 DB | 이유 |
|------|---------|------|
| DAG 테스트 | Docker DB | 테스트 환경 격리 |
| 실제 데이터 수집/계산 | 운영 DB | 프로덕션 데이터 필요 |
| 데이터 검증 | 운영 DB | 실제 수집된 데이터 확인 |
| 쿼리 테스트 | Docker DB | 운영 DB 영향 최소화 |
| 누락 데이터 재수집 | 운영 DB | 실제 저장 필요 |
| DAG 디버깅 | 둘 다 | DAG는 Docker → 수집은 운영 DB |

---

## 6. 트러블슈팅

### Q: DB 연결 안 됨
```bash
# 네트워크 확인
ping 192.168.219.103

# psql로 직접 연결 테스트
psql -h 192.168.219.103 -U admin -d stocktrading -c "SELECT 1;"
```

### Q: 쿼리 결과 없음 (0개)
- 확인사항:
  1. 올바른 DB에 접속했나? (운영 vs Docker)
  2. 날짜 범위는? (과거 데이터 확인)
  3. 테이블 존재하나? `SELECT * FROM information_schema.tables WHERE table_name='stock_prices';`

### Q: 시간초과(timeout)
- 대량 쿼리는 제한 필요
- 인덱스 확인: `SELECT * FROM pg_indexes WHERE tablename='stock_prices';`

---

## 7. 접속 예제 스크립트

파일: `/f/hhstock/db_check.py`

```bash
python /f/hhstock/db_check.py
```

이 스크립트로 운영 DB 상태를 빠르게 확인할 수 있습니다.
