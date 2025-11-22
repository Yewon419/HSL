# 기술 지표 수동 계산 - 2025-10-23 검증 완료

**작성일**: 2025-10-23 20:50
**상태**: ✅ 검증됨 (2,775개 지표 저장 성공)
**목적**: Airflow DAG 실패 시 수동으로 기술 지표를 계산하는 방법

---

## 빠른 실행

아래 스크립트를 그대로 복사하여 터미널에 붙여넣으면 됩니다.

### 오늘(2025-10-23) 지표 계산
```bash
docker exec stock-airflow-scheduler sh -c "
cd /opt/airflow && \
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/airflow/dags')
from datetime import date, timedelta
from common_functions import (
    get_db_engine,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_bollinger_bands,
    save_technical_indicators,
    update_indicator_log,
    logger
)
import pandas as pd

target_date = date(2025, 10, 23)
logger.info(f'Starting indicator calculation for {target_date}')

try:
    engine = get_db_engine()
    start_date = target_date - timedelta(days=200)

    query = f'''
        SELECT ticker, date, close_price
        FROM stock_prices
        WHERE date >= '{start_date}' AND date <= '{target_date}'
        ORDER BY ticker, date
    '''

    stock_data = pd.read_sql(query, engine)
    logger.info(f'Loaded {len(stock_data)} records')

    if stock_data.empty:
        raise Exception('No historical data found')

    tickers = stock_data['ticker'].unique()
    logger.info(f'Processing {len(tickers)} tickers')

    indicators_list = []
    skipped = 0

    for ticker in tickers:
        ticker_data = stock_data[stock_data['ticker'] == ticker].copy()

        if len(ticker_data) < 20:
            skipped += 1
            continue

        prices = ticker_data.sort_values('date')['close_price'].astype(float)

        rsi = calculate_rsi(prices, period=14)
        macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)
        sma_20 = calculate_sma(prices, period=20)
        sma_50 = calculate_sma(prices, period=50)
        sma_200 = calculate_sma(prices, period=200)
        bb_upper, bb_lower = calculate_bollinger_bands(prices, period=20, std_dev=2)

        indicators = {
            'ticker': ticker,
            'date': target_date,
            'rsi': float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
            'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
            'macd_signal': float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None,
            'sma_20': float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None,
            'sma_50': float(sma_50.iloc[-1]) if pd.notna(sma_50.iloc[-1]) else None,
            'sma_200': float(sma_200.iloc[-1]) if pd.notna(sma_200.iloc[-1]) else None,
            'bb_upper': float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None,
            'bb_lower': float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None,
        }

        indicators_list.append(indicators)

    logger.info(f'Calculated: {len(indicators_list)}, Skipped: {skipped}')

    if indicators_list:
        saved_count = save_technical_indicators(indicators_list, engine)
        logger.info(f'Saved {saved_count} indicators')
        update_indicator_log(target_date, 'success', saved_count, engine=engine)
        print(f'✅✅✅ 지표 계산 완료: {saved_count}개 지표 저장 ({target_date}) ✅✅✅')
    else:
        raise Exception('No indicators calculated')

except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    print(f'❌ Error: {e}')
    raise

PYEOF
"
```

### 특정 날짜 지표 계산 (날짜 수정)
```bash
docker exec stock-airflow-scheduler sh -c "
cd /opt/airflow && \
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/airflow/dags')
from datetime import date, timedelta
from common_functions import (
    get_db_engine,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_bollinger_bands,
    save_technical_indicators,
    update_indicator_log,
    logger
)
import pandas as pd

# ⬇️ 여기서 날짜를 수정하세요
target_date = date(2025, 10, 24)  # 예: date(2025, 10, 24)
# ⬆️ 여기서 날짜를 수정하세요

logger.info(f'Starting indicator calculation for {target_date}')

try:
    engine = get_db_engine()
    start_date = target_date - timedelta(days=200)

    query = f'''
        SELECT ticker, date, close_price
        FROM stock_prices
        WHERE date >= '{start_date}' AND date <= '{target_date}'
        ORDER BY ticker, date
    '''

    stock_data = pd.read_sql(query, engine)
    logger.info(f'Loaded {len(stock_data)} records')

    if stock_data.empty:
        raise Exception('No historical data found')

    tickers = stock_data['ticker'].unique()
    logger.info(f'Processing {len(tickers)} tickers')

    indicators_list = []
    skipped = 0

    for ticker in tickers:
        ticker_data = stock_data[stock_data['ticker'] == ticker].copy()

        if len(ticker_data) < 20:
            skipped += 1
            continue

        prices = ticker_data.sort_values('date')['close_price'].astype(float)

        rsi = calculate_rsi(prices, period=14)
        macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)
        sma_20 = calculate_sma(prices, period=20)
        sma_50 = calculate_sma(prices, period=50)
        sma_200 = calculate_sma(prices, period=200)
        bb_upper, bb_lower = calculate_bollinger_bands(prices, period=20, std_dev=2)

        indicators = {
            'ticker': ticker,
            'date': target_date,
            'rsi': float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
            'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
            'macd_signal': float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None,
            'sma_20': float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None,
            'sma_50': float(sma_50.iloc[-1]) if pd.notna(sma_50.iloc[-1]) else None,
            'sma_200': float(sma_200.iloc[-1]) if pd.notna(sma_200.iloc[-1]) else None,
            'bb_upper': float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None,
            'bb_lower': float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None,
        }

        indicators_list.append(indicators)

    logger.info(f'Calculated: {len(indicators_list)}, Skipped: {skipped}')

    if indicators_list:
        saved_count = save_technical_indicators(indicators_list, engine)
        logger.info(f'Saved {saved_count} indicators')
        update_indicator_log(target_date, 'success', saved_count, engine=engine)
        print(f'✅✅✅ 지표 계산 완료: {saved_count}개 지표 저장 ({target_date}) ✅✅✅')
    else:
        raise Exception('No indicators calculated')

except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    print(f'❌ Error: {e}')
    raise

PYEOF
"
```

---

## 실행 후 확인

### 지표 계산 완료 확인
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT indicator_date, status, indicators_count
FROM indicator_log
WHERE indicator_date = '2025-10-23'
ORDER BY updated_at DESC LIMIT 1;
"
```

**예상 결과**:
```
indicator_date | status  | indicators_count
----------------+---------+------------------
 2025-10-23     | success |             2775
```

### 저장된 지표 샘플 확인
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT ticker, date, rsi, macd, ma_20, ma_50, ma_200,
       bollinger_upper, bollinger_lower
FROM technical_indicators
WHERE date = '2025-10-23'
LIMIT 5;
"
```

---

## 핵심 정보

### 계산되는 지표
| 지표 | 설명 | DB 컬럼명 |
|------|------|---------|
| RSI | Relative Strength Index (14-period) | `rsi` |
| MACD | Moving Average Convergence Divergence | `macd` |
| MACD Signal | MACD Signal Line (9-period) | `macd_signal` |
| SMA 20 | Simple Moving Average 20-day | `ma_20` |
| SMA 50 | Simple Moving Average 50-day | `ma_50` |
| SMA 200 | Simple Moving Average 200-day | `ma_200` |
| Bollinger Upper | Bollinger Bands Upper (20-day, 2-std) | `bollinger_upper` |
| Bollinger Lower | Bollinger Bands Lower (20-day, 2-std) | `bollinger_lower` |

### 필수 조건
- ✅ Docker 컨테이너 실행 중 (stock-airflow-scheduler)
- ✅ 계산 대상 날짜의 주가 데이터 존재
- ✅ 200일 이상의 역사 데이터 존재

### 자동 컬럼명 매핑
코드에서는 다음과 같이 계산하지만, DB 저장 시 자동으로 매핑됩니다:
```
계산 결과        →  DB에 저장
sma_20          →  ma_20
sma_50          →  ma_50
sma_200         →  ma_200
bb_upper        →  bollinger_upper
bb_lower        →  bollinger_lower
```

이는 `common_functions.py`의 `save_technical_indicators()` 함수에서 자동으로 처리됩니다.

---

## 예상 실행 시간

- 2,700+ 개 주식 계산: **60~90초**
- 메모리 사용: **500MB~1GB**
- DB 부하: 중간 수준

---

## 오류 해결

### "No historical data found" 에러
**원인**: 200일 역사 데이터가 없음

**확인**:
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT MIN(date), MAX(date), COUNT(DISTINCT date) as days
FROM stock_prices;
"
```

### "column ma_20 does not exist" 에러
**원인**: DB 스키마 불일치

**해결**:
```bash
docker cp /f/hhstock/stock-trading-system/airflow/dags/common_functions.py stock-airflow-scheduler:/opt/airflow/dags/
docker restart stock-airflow-scheduler
```

---

## 검증 결과 (2025-10-23)

✅ **성공적으로 검증됨**

| 항목 | 결과 |
|------|------|
| 로드된 레코드 | 365,817개 (200일 × 2,700개 주식) |
| 계산된 지표 | 2,775개 |
| 저장된 지표 | 2,775개 ✅ |
| 소요 시간 | ~60초 |
| DB 컬럼명 | 모두 정상 ✅ |
| Status | success ✅ |

---

**마지막 업데이트**: 2025-10-23 20:50 KST
