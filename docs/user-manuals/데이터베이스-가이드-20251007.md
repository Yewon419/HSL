# 📊 데이터베이스 사용자 매뉴얼

주식 거래 시스템의 PostgreSQL 데이터베이스에 직접 접속하여 데이터를 조회하고 분석하는 방법을 안내합니다.

## 🗄️ 데이터베이스 접속 정보

### 📋 PostgreSQL 연결 설정

```
호스트(Host): localhost
포트(Port): 5435
데이터베이스(Database): stocktrading
사용자명(Username): admin
비밀번호(Password): admin123
```

### ⚙️ DBeaver 연결 설정 단계

1. **새 연결 생성**
   - Database → New Database Connection
   - PostgreSQL 선택

2. **연결 정보 입력**
   - Server Host: `localhost`
   - Port: `5435` ⚠️ (기본 5432가 아님!)
   - Database: `stocktrading`
   - Username: `admin`
   - Password: `admin123`

3. **고급 설정 (선택사항)**
   - SSL: Disable
   - Show all databases: 체크

## 📊 주요 테이블 구조

### 📈 stock_prices (주가 데이터)
주식의 일별 가격 정보를 저장하는 메인 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| ticker | varchar(10) | 종목코드 (005930 = 삼성전자) |
| date | date | 거래 날짜 |
| open_price | numeric(10,2) | 시가 |
| high_price | numeric(10,2) | 고가 |
| low_price | numeric(10,2) | 저가 |
| close_price | numeric(10,2) | 종가 |
| volume | bigint | 거래량 |
| created_at | timestamp | 데이터 생성 시간 |

### 📊 technical_indicators (기술적 지표)
각종 기술적 분석 지표를 저장하는 테이블입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| ticker | varchar(10) | 종목코드 |
| date | date | 기준 날짜 |
| rsi | numeric(5,2) | 상대강도지수 (0-100) |
| macd | numeric(10,4) | MACD 값 |
| macd_signal | numeric(10,4) | MACD 신호선 |
| macd_histogram | numeric(10,4) | MACD 히스토그램 |
| stoch_k | numeric(5,2) | 스토캐스틱 %K |
| stoch_d | numeric(5,2) | 스토캐스틱 %D |
| ma_20 | numeric(10,2) | 20일 이동평균 |
| ma_50 | numeric(10,2) | 50일 이동평균 |
| ma_200 | numeric(10,2) | 200일 이동평균 |
| bollinger_upper | numeric(10,2) | 볼린저 밴드 상한선 |
| bollinger_middle | numeric(10,2) | 볼린저 밴드 중간선 |
| bollinger_lower | numeric(10,2) | 볼린저 밴드 하한선 |

### 🏢 stocks (종목 정보)
등록된 주식 종목의 기본 정보를 저장합니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| ticker | varchar(10) | 종목코드 (Primary Key) |
| company_name | varchar(255) | 회사명 |
| market_type | varchar(50) | 시장구분 (KOSPI/KOSDAQ) |
| currency | varchar(3) | 통화 (KRW/USD) |
| is_active | boolean | 활성 상태 |

### 🎨 indicator_values (Grafana용 지표)
Grafana 대시보드에서 사용하는 JSON 형태의 지표 데이터입니다.

| 컬럼명 | 타입 | 설명 |
|--------|------|------|
| ticker | varchar(10) | 종목코드 |
| date | date | 기준 날짜 |
| indicator_id | integer | 지표 유형 ID |
| value | jsonb | JSON 형태의 지표 값 |
| parameters | jsonb | 지표 계산 파라미터 |

## 📋 기본 쿼리 예시

### 1️⃣ 테이블 구조 확인

```sql
-- 모든 테이블 목록 확인
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
ORDER BY table_name;

-- 특정 테이블 구조 확인
SELECT column_name, data_type, is_nullable
FROM information_schema.columns
WHERE table_name = 'stock_prices'
ORDER BY ordinal_position;
```

### 2️⃣ 주가 데이터 조회

```sql
-- 최신 주가 데이터 확인 (모든 종목)
SELECT ticker, date, close_price, volume, created_at
FROM stock_prices
WHERE date >= '2025-09-22'
ORDER BY date DESC, ticker;

-- 삼성전자 최근 1주일 주가
SELECT date, open_price, high_price, low_price, close_price, volume
FROM stock_prices
WHERE ticker = '005930'
  AND date >= CURRENT_DATE - INTERVAL '7 days'
ORDER BY date DESC;

-- 종목별 최신 데이터 날짜 확인
SELECT ticker, MAX(date) as latest_date, COUNT(*) as data_count
FROM stock_prices
GROUP BY ticker
ORDER BY latest_date DESC, ticker;
```

### 3️⃣ 기술적 지표 조회

```sql
-- 최신 기술적 지표
SELECT ticker, date, rsi, macd, stoch_k, stoch_d, ma_20, ma_50
FROM technical_indicators
WHERE date >= '2025-09-22'
ORDER BY ticker, date DESC;

-- 삼성전자 RSI 추이 및 매매 신호
SELECT date, rsi,
  CASE
    WHEN rsi < 30 THEN '과매도'
    WHEN rsi > 70 THEN '과매수'
    ELSE '중립'
  END as rsi_signal
FROM technical_indicators
WHERE ticker = '005930'
  AND date >= '2025-09-20'
ORDER BY date DESC;

-- 모든 종목의 최신 RSI 현황
SELECT ti.ticker, s.company_name, ti.date, ti.rsi,
  CASE
    WHEN ti.rsi < 30 THEN '과매도'
    WHEN ti.rsi > 70 THEN '과매수'
    ELSE '중립'
  END as signal
FROM technical_indicators ti
JOIN stocks s ON ti.ticker = s.ticker
WHERE ti.date = (SELECT MAX(date) FROM technical_indicators ti2 WHERE ti2.ticker = ti.ticker)
  AND ti.rsi IS NOT NULL
ORDER BY ti.rsi;
```

### 4️⃣ Grafana 호환 지표 조회

```sql
-- Grafana에서 사용하는 지표 데이터 확인
SELECT iv.ticker, iv.date, id.name as indicator_name, iv.value
FROM indicator_values iv
JOIN indicator_definitions id ON iv.indicator_id = id.id
WHERE iv.ticker = '005930'
  AND iv.date >= '2025-09-22'
  AND id.code IN ('RSI', 'MACD', 'SMA', 'BB')
ORDER BY iv.date DESC, id.name;

-- RSI 값만 추출 (JSON에서)
SELECT ticker, date, (value::json->>'rsi')::float as rsi_value
FROM indicator_values iv
JOIN indicator_definitions id ON iv.indicator_id = id.id
WHERE id.code = 'SMA'  -- SMA 레코드에 RSI가 함께 저장됨
  AND date >= '2025-09-22'
ORDER BY ticker, date DESC;

-- 볼린저 밴드 데이터 추출
SELECT ticker, date,
  (value::json->>'bb_upper')::float as bb_upper,
  (value::json->>'bb_middle')::float as bb_middle,
  (value::json->>'bb_lower')::float as bb_lower
FROM indicator_values iv
JOIN indicator_definitions id ON iv.indicator_id = id.id
WHERE id.code = 'BB'
  AND date >= '2025-09-22'
ORDER BY ticker, date DESC;
```

### 5️⃣ 종목 정보 조회

```sql
-- 등록된 모든 종목 목록
SELECT ticker, company_name, market_type, currency, is_active
FROM stocks
WHERE is_active = true
ORDER BY ticker;

-- 한국 주식만
SELECT ticker, company_name, market_type
FROM stocks
WHERE currency = 'KRW' AND is_active = true
ORDER BY company_name;

-- 최근 거래량 높은 종목들
SELECT s.ticker, s.company_name, sp.date, sp.volume, sp.close_price
FROM stocks s
JOIN stock_prices sp ON s.ticker = sp.ticker
WHERE sp.date = (SELECT MAX(date) FROM stock_prices sp2 WHERE sp2.ticker = s.ticker)
  AND s.currency = 'KRW'
ORDER BY sp.volume DESC
LIMIT 10;
```

### 6️⃣ 데이터 품질 체크

```sql
-- 전체 데이터 개요
SELECT
  COUNT(DISTINCT ticker) as total_stocks,
  COUNT(DISTINCT date) as total_dates,
  COUNT(*) as total_records,
  MIN(date) as earliest_date,
  MAX(date) as latest_date
FROM stock_prices;

-- 종목별 데이터 완성도
SELECT ticker,
  COUNT(*) as record_count,
  MIN(date) as first_date,
  MAX(date) as last_date,
  MAX(date) - MIN(date) as date_range_days
FROM stock_prices
GROUP BY ticker
ORDER BY record_count DESC;

-- 기술적 지표 완성도 확인
SELECT ticker,
  COUNT(*) as indicator_records,
  COUNT(CASE WHEN rsi IS NOT NULL THEN 1 END) as rsi_count,
  COUNT(CASE WHEN macd IS NOT NULL THEN 1 END) as macd_count,
  MAX(date) as latest_indicator_date
FROM technical_indicators
GROUP BY ticker
ORDER BY latest_indicator_date DESC;
```

### 7️⃣ 실시간 모니터링 쿼리

```sql
-- 오늘 업데이트된 데이터 확인
SELECT
  'stock_prices' as table_name,
  COUNT(*) as today_count,
  MAX(created_at) as last_update
FROM stock_prices
WHERE DATE(created_at) = CURRENT_DATE

UNION ALL

SELECT
  'technical_indicators' as table_name,
  COUNT(*) as today_count,
  MAX(created_at) as last_update
FROM technical_indicators
WHERE DATE(created_at) = CURRENT_DATE;

-- 시스템 상태 종합 확인
SELECT
  'Stock Data' as metric,
  CONCAT(COUNT(DISTINCT ticker), ' stocks, latest: ', MAX(date)) as status
FROM stock_prices

UNION ALL

SELECT
  'Technical Indicators' as metric,
  CONCAT(COUNT(DISTINCT ticker), ' stocks, latest: ', MAX(date)) as status
FROM technical_indicators

UNION ALL

SELECT
  'Grafana Indicators' as metric,
  CONCAT(COUNT(DISTINCT ticker), ' stocks, latest: ', MAX(date)) as status
FROM indicator_values;
```

## 🔧 유용한 분석 쿼리

### 📈 기술적 분석

```sql
-- 골든크로스/데드크로스 확인 (MA20이 MA50을 상향/하향 돌파)
SELECT ticker, date, ma_20, ma_50,
  CASE
    WHEN ma_20 > ma_50 AND LAG(ma_20) OVER (PARTITION BY ticker ORDER BY date) <= LAG(ma_50) OVER (PARTITION BY ticker ORDER BY date) THEN '골든크로스'
    WHEN ma_20 < ma_50 AND LAG(ma_20) OVER (PARTITION BY ticker ORDER BY date) >= LAG(ma_50) OVER (PARTITION BY ticker ORDER BY date) THEN '데드크로스'
    ELSE NULL
  END as signal
FROM technical_indicators
WHERE date >= '2025-09-01'
  AND ma_20 IS NOT NULL AND ma_50 IS NOT NULL
  AND ticker IN ('005930', '000660', '035420')
ORDER BY ticker, date DESC;

-- MACD 매매 신호
SELECT ticker, date, macd, macd_signal,
  CASE
    WHEN macd > macd_signal AND LAG(macd) OVER (PARTITION BY ticker ORDER BY date) <= LAG(macd_signal) OVER (PARTITION BY ticker ORDER BY date) THEN '매수신호'
    WHEN macd < macd_signal AND LAG(macd) OVER (PARTITION BY ticker ORDER BY date) >= LAG(macd_signal) OVER (PARTITION BY ticker ORDER BY date) THEN '매도신호'
    ELSE NULL
  END as signal
FROM technical_indicators
WHERE date >= '2025-09-01'
  AND macd IS NOT NULL AND macd_signal IS NOT NULL
ORDER BY ticker, date DESC;
```

### 💹 성과 분석

```sql
-- 종목별 수익률 계산 (최근 30일)
WITH price_comparison AS (
  SELECT
    ticker,
    close_price as current_price,
    LAG(close_price, 30) OVER (PARTITION BY ticker ORDER BY date) as price_30d_ago,
    date
  FROM stock_prices
  WHERE date >= CURRENT_DATE - INTERVAL '30 days'
)
SELECT
  ticker,
  current_price,
  price_30d_ago,
  ROUND(((current_price - price_30d_ago) / price_30d_ago * 100)::numeric, 2) as return_30d
FROM price_comparison
WHERE price_30d_ago IS NOT NULL
  AND date = (SELECT MAX(date) FROM stock_prices)
ORDER BY return_30d DESC;
```

## ⚠️ 연결 시 주의사항

1. **포트 번호**: 5435 (기본 PostgreSQL 포트 5432가 아님)
2. **Docker 환경**: 컨테이너가 실행 중이어야 접속 가능
3. **TimescaleDB**: 시계열 데이터베이스 확장 기능 사용됨
4. **인코딩**: UTF-8 사용 권장
5. **읽기 전용**: 데이터 수정 시 주의 필요 (시스템에 영향 가능)

## 📚 참고 정보

- **TimescaleDB 문서**: https://docs.timescale.com/
- **PostgreSQL 문서**: https://postgresql.org/docs/
- **주식 종목코드**: KRX 종목코드 체계 따름 (예: 005930 = 삼성전자)

---

⚠️ **면책조항**: 이 시스템의 데이터는 교육 및 연구 목적입니다. 실제 투자 결정에 사용하기 전에 충분한 검토가 필요합니다.