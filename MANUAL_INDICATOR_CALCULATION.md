# 수동 기술 지표 계산 가이드

## 개요
자동 기술 지표 계산(Airflow DAG)이 실패했을 때 수동으로 지표를 계산하는 방법입니다.

**최종 수정**: 2025-10-23 20:50
**상태**: 검증됨 (2,775개 지표 저장 완료)

## 선행 조건
- Docker 컨테이너 실행 중
- stock-db, stock-backend 또는 stock-airflow-scheduler 컨테이너 필요
- 기술 지표 계산 대상 날짜의 주가 데이터 필요 (200일 역사 데이터 포함)

## 스키마 정보

### technical_indicators 테이블 컬럼명
반드시 다음 컬럼명을 사용하세요:
- `ma_20` (NOT `sma_20`)
- `ma_50` (NOT `sma_50`)
- `ma_200` (NOT `sma_200`)
- `bollinger_upper` (NOT `bb_upper`)
- `bollinger_lower` (NOT `bb_lower`)

**자주 발생하는 오류**:
```
ERROR: column "sma_20" does not exist
```
→ 해결: 위 컬럼명 매핑을 확인하세요

## 방법 1: Airflow 컨테이너에서 수동 실행 (권장)

### 1.1 기본 스크립트
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

# ===== 설정 =====
target_date = date(2025, 10, 24)  # 수정: 계산할 날짜
# ================

logger.info(f'Starting calculation for {target_date}')

try:
    engine = get_db_engine()
    start_date = target_date - timedelta(days=200)

    # 200일 역사 데이터 로드
    query = f'''
        SELECT ticker, date, close_price
        FROM stock_prices
        WHERE date >= '{start_date}' AND date <= '{target_date}'
        ORDER BY ticker, date
    '''

    stock_data = pd.read_sql(query, engine)
    logger.info(f'Loaded {len(stock_data)} records')

    if stock_data.empty:
        logger.error('No historical data found')
        raise Exception('No stock data')

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

        # 지표 계산
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
        # save_technical_indicators 함수가 컬럼명 매핑을 자동으로 수행합니다
        # (sma_20 → ma_20, bb_upper → bollinger_upper, 등)
        saved_count = save_technical_indicators(indicators_list, engine)
        logger.info(f'Saved {saved_count} indicators')

        update_indicator_log(target_date, 'success', saved_count, engine=engine)
        print(f'✅✅✅ 지표 계산 완료: {saved_count}개 지표 저장 ({target_date}) ✅✅✅')
    else:
        logger.error('No indicators to save')
        print(f'❌ No indicators calculated')

except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    print(f'❌ Error: {e}')
    raise

PYEOF
"
```

### 1.2 실행 후 확인
```bash
# indicator_log 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT indicator_date, status, indicators_count
FROM indicator_log
WHERE indicator_date = '2025-10-24'
ORDER BY updated_at DESC LIMIT 1;
"

# technical_indicators 샘플 확인
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT ticker, date, rsi, macd, ma_20, ma_50, ma_200
FROM technical_indicators
WHERE date = '2025-10-24'
LIMIT 5;
"
```

## 방법 2: Backend 컨테이너에서 수동 실행

```bash
docker exec stock-backend python3 << 'PYEOF'
import sys
sys.path.insert(0, '/app')
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

target_date = date(2025, 10, 24)  # 수정: 계산할 날짜

# 위의 Airflow 스크립트와 동일한 로직
# (공통 함수를 사용하므로 동일)
PYEOF
```

## 방법 3: Airflow DAG 즉시 실행

```bash
# DAG를 즉시 실행 (catchup 모드로 과거 날짜 처리)
docker exec stock-airflow-scheduler \
  airflow dags trigger \
  --exec-date 2025-10-24 \
  technical_indicator_dag
```

## 문제 해결

### Q1: "column "sma_20" does not exist" 에러
**원인**: 코드와 DB 스키마의 컬럼명 불일치

**해결 방법**:
1. `common_functions.py`가 최신 버전인지 확인
   ```bash
   docker exec stock-backend grep "ma_20" /app/common_functions.py | head -3
   ```
2. 최신 버전이 아니면 Docker 컨테이너로 복사
   ```bash
   docker cp /f/hhstock/stock-trading-system/backend/common_functions.py stock-backend:/app/
   docker cp /f/hhstock/stock-trading-system/airflow/dags/common_functions.py stock-airflow-scheduler:/opt/airflow/dags/
   ```

### Q2: "No historical data found" 에러
**원인**: 계산 대상 날짜의 주가 데이터가 없음

**해결 방법**:
1. 주가 데이터 수집 확인
   ```bash
   docker exec stock-db psql -U admin -d stocktrading -c "
   SELECT COUNT(*) FROM stock_prices WHERE date = '2025-10-24';
   "
   ```
2. 주가 데이터가 없으면 먼저 수집해야 함
   - [수동 주가 수집 가이드](./MANUAL_DATA_COLLECTION_GUIDE.md) 참조

### Q3: 계산이 느린 경우 (2000+ 주식)
- 예상 시간: 60~90초
- 200일 × 2700개 주식 = 계산량 많음
- CPU와 DB 부하 확인: `docker stats`

## 예상 결과

성공적인 실행 시:
```
✅✅✅ 지표 계산 완료: 2775개 지표 저장 (2025-10-23) ✅✅✅
```

수동 지표 계산 후:
- `indicator_log.status = 'success'`
- `indicator_log.indicators_count = 계산된 개수`
- `technical_indicators` 테이블에 새로운 레코드 저장

## 최신 수정 사항

### 2025-10-23
- ✅ 컬럼명 매핑 수정 (sma_20 → ma_20, 등)
- ✅ 누락된 컬럼 추가 (ma_50, ma_200)
- ✅ 200일 역사 데이터 로드 구현
- ✅ 2,775개 지표 저장 검증 완료

---

**문의 또는 추가 도움이 필요하면 start_hsl.md를 참조하세요.**
