# 주가 및 지수 수동 수집 - 2025-10-23 검증 완료

**작성일**: 2025-10-23
**상태**: ✅ 검증됨
**목적**: Airflow DAG 실패 시 수동으로 주가 및 지수 데이터를 수집하는 방법

---

## 빠른 실행

아래 스크립트를 그대로 복사하여 터미널에 붙여넣으면 됩니다.

### 오늘(2025-10-23) 데이터 수집
```bash
docker exec stock-airflow-scheduler sh -c "
cd /opt/airflow && \
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/airflow/dags')
from datetime import date
from common_functions import (
    get_db_engine,
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices,
    update_collection_log_price,
    update_collection_log_indices,
    logger
)

target_date = date(2025, 10, 23)
logger.info(f'Manual data collection for {target_date}')

try:
    engine = get_db_engine()

    # 주가 수집
    logger.info(f'Fetching stock prices for {target_date}...')
    prices_df = fetch_stock_prices_api(target_date)

    if prices_df.empty:
        logger.warning('No prices fetched')
        update_collection_log_price(target_date, 'failed', 0, 'No data from API', engine)
        print('❌ 주가 수집 실패')
    else:
        saved_prices = save_stock_prices(prices_df, target_date, engine)
        logger.info(f'Saved {saved_prices} stock prices')
        update_collection_log_price(target_date, 'success', saved_prices, None, engine)
        print(f'✅ 주가 수집 완료: {saved_prices}개')

    # 지수 수집
    logger.info(f'Fetching market indices for {target_date}...')
    indices_df = fetch_market_indices_api(target_date)

    if indices_df.empty:
        logger.warning('No indices fetched')
        update_collection_log_indices(target_date, 'failed', 0, 'No data from API', engine)
        print('❌ 지수 수집 실패')
    else:
        saved_indices = save_market_indices(indices_df, target_date, engine)
        logger.info(f'Saved {saved_indices} market indices')
        update_collection_log_indices(target_date, 'success', saved_indices, None, engine)
        print(f'✅ 지수 수집 완료: {saved_indices}개')

    print(f'✅✅✅ 데이터 수집 완료: {target_date} ✅✅✅')

except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    print(f'❌ 수집 실패: {e}')
    raise

PYEOF
"
```

### 특정 날짜 데이터 수집 (날짜 수정)
```bash
docker exec stock-airflow-scheduler sh -c "
cd /opt/airflow && \
python3 << 'PYEOF'
import sys
sys.path.insert(0, '/opt/airflow/dags')
from datetime import date
from common_functions import (
    get_db_engine,
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices,
    update_collection_log_price,
    update_collection_log_indices,
    logger
)

# ⬇️ 여기서 날짜를 수정하세요
target_date = date(2025, 10, 24)  # 예: date(2025, 10, 24)
# ⬆️ 여기서 날짜를 수정하세요

logger.info(f'Manual data collection for {target_date}')

try:
    engine = get_db_engine()

    # 주가 수집
    logger.info(f'Fetching stock prices for {target_date}...')
    prices_df = fetch_stock_prices_api(target_date)

    if prices_df.empty:
        logger.warning('No prices fetched')
        update_collection_log_price(target_date, 'failed', 0, 'No data from API', engine)
        print('❌ 주가 수집 실패')
    else:
        saved_prices = save_stock_prices(prices_df, target_date, engine)
        logger.info(f'Saved {saved_prices} stock prices')
        update_collection_log_price(target_date, 'success', saved_prices, None, engine)
        print(f'✅ 주가 수집 완료: {saved_prices}개')

    # 지수 수집
    logger.info(f'Fetching market indices for {target_date}...')
    indices_df = fetch_market_indices_api(target_date)

    if indices_df.empty:
        logger.warning('No indices fetched')
        update_collection_log_indices(target_date, 'failed', 0, 'No data from API', engine)
        print('❌ 지수 수집 실패')
    else:
        saved_indices = save_market_indices(indices_df, target_date, engine)
        logger.info(f'Saved {saved_indices} market indices')
        update_collection_log_indices(target_date, 'success', saved_indices, None, engine)
        print(f'✅ 지수 수집 완료: {saved_indices}개')

    print(f'✅✅✅ 데이터 수집 완료: {target_date} ✅✅✅')

except Exception as e:
    logger.error(f'Error: {e}', exc_info=True)
    print(f'❌ 수집 실패: {e}')
    raise

PYEOF
"
```

---

## 실행 후 확인

### 수집 완료 확인
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT collection_date, overall_status, price_count, indices_count,
       price_status, indices_status
FROM collection_log
WHERE collection_date = '2025-10-23'
ORDER BY updated_at DESC LIMIT 1;
"
```

**예상 결과**:
```
collection_date | overall_status | price_count | indices_count | price_status | indices_status
-----------------+----------------+-------------+---------------+--------------+----------------
 2025-10-23      | success        |        2760 |             2 | success      | success
```

### 주가 데이터 확인
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT COUNT(*) as price_count, MIN(ticker) as first_ticker, MAX(ticker) as last_ticker
FROM stock_prices
WHERE date = '2025-10-23';
"
```

### 지수 데이터 확인
```bash
docker exec stock-db psql -U admin -d stocktrading -c "
SELECT index_name, close_value, volume
FROM market_indices
WHERE date = '2025-10-23'
ORDER BY index_name;
"
```

---

## 수집되는 데이터

### 주가 데이터
- **API 소스**: pykrx (한국거래소)
- **수집 항목**: 개별 주식 전체
  - Ticker (종목 코드)
  - 시가, 고가, 저가, 종가
  - 거래량
- **데이터 개수**: ~2,700~2,800개 주식

### 지수 데이터
- **API 소스**: pykrx
- **수집 지수**:
  - KOSPI (코스피)
  - KOSDAQ (코스닥)
- **데이터 개수**: 2개

---

## 주의사항

### 거래일 확인
- 주말, 공휴일에는 데이터가 없습니다
- 장 마감 시간(오후 3시 30분 KST) 이후에 수집 권장

### API 제한
- pykrx는 무료이지만 응답 시간이 걸릴 수 있음
- 대량의 동시 요청은 제한될 수 있음

### 기존 데이터 덮어쓰기
- 같은 날짜로 다시 수집하면 기존 데이터가 **덮어씌워집니다**
- 이는 정상 동작입니다 (update 쿼리 사용)

---

## 예상 실행 시간

| 항목 | 예상 시간 |
|------|---------|
| 주가 수집 | 20~30초 |
| 지수 수집 | 5~10초 |
| DB 저장 | 10~15초 |
| **총 소요 시간** | **35~55초** |

---

## 오류 해결

### "No data returned from API" 에러
**원인**: 다음날 또는 휴장일일 수 있음

**확인**:
```bash
# 오늘이 거래일인지 확인
python3 << 'EOF'
from datetime import date
import datetime

today = date.today()
# 월요일(0) ~ 금요일(4)이면 거래일
if today.weekday() < 5:
    print(f'{today}: 거래일 (평일)')
else:
    print(f'{today}: 휴장일 (주말)')
EOF
```

### "API 응답 시간 초과" 에러
**해결**: 몇 분 후 다시 시도

### "Connection refused" 에러
**해결**:
```bash
# Docker 컨테이너 상태 확인
docker ps | grep stock-airflow

# 컨테이너 재시작
docker restart stock-airflow-scheduler
```

---

## 검증 결과 (2025-10-23)

✅ **성공적으로 검증됨**

| 항목 | 결과 |
|------|------|
| 주가 수집 | 2,760개 ✅ |
| 지수 수집 | 2개 (KOSPI, KOSDAQ) ✅ |
| DB 저장 | 완료 ✅ |
| Status | success ✅ |

---

**마지막 업데이트**: 2025-10-23 KST
