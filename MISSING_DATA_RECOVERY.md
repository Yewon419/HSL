# 누락된 데이터 복구 가이드

2025년 주가 데이터 중 누락된 부분을 수집하기 위한 가이드입니다.

---

## 1. 누락된 날짜 확인

### 누락된 날짜 목록 (총 24일)
```
1월 (신정, 방학 휴장): 1일, 27-30일
3월 (삼일절): 3일
5월 (근로자날, 부처님 오신날): 1일, 5-6일
10월 (DB 마이그레이션 이후): 8-10일, 13-17일, 20-24일, 27-28일
```

### 데이터 확인 쿼리
```sql
-- 수집된 거래일 확인 (2025-10-01 이후)
SELECT date, COUNT(*) as count
FROM stock_prices
WHERE date >= '2025-10-01'
GROUP BY date
ORDER BY date DESC;

-- 예상 기대값: 각 거래일마다 2,700-2,800개 레코드
```

---

## 2. 방법 1: Python 스크립트로 수집 (권장)

### 단계 1: 필수 패키지 설치
```bash
pip install pykrx psycopg2-binary sqlalchemy pandas
```

### 단계 2: 스크립트 작성
파일명: `collect_missing_data.py`

```python
#!/usr/bin/env python3
"""
누락된 날짜 데이터 수동 수집 스크립트
실행: python collect_missing_data.py
"""

import sys
import time
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 수집할 누락된 날짜들
missing_dates = [
    # 1월
    date(2025, 1, 1),
    date(2025, 1, 27),
    date(2025, 1, 28),
    date(2025, 1, 29),
    date(2025, 1, 30),
    # 3월
    date(2025, 3, 3),
    # 5월
    date(2025, 5, 1),
    date(2025, 5, 5),
    date(2025, 5, 6),
    # 10월 (우선순위: 최신 데이터)
    date(2025, 10, 8),
    date(2025, 10, 9),
    date(2025, 10, 10),
    date(2025, 10, 13),
    date(2025, 10, 14),
    date(2025, 10, 15),
    date(2025, 10, 16),
    date(2025, 10, 17),
    date(2025, 10, 20),
    date(2025, 10, 21),
    date(2025, 10, 22),
    date(2025, 10, 23),
    date(2025, 10, 24),
    date(2025, 10, 27),
    date(2025, 10, 28),
]

# DB 설정
DB_CONFIG = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def get_db_connection():
    """DB 연결"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def save_stock_prices(prices_df, target_date):
    """주가 데이터 저장 (UPSERT 방식)"""
    if prices_df.empty:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0

    try:
        for _, row in prices_df.iterrows():
            cursor.execute("""
                INSERT INTO stock_prices
                (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    created_at = NOW()
            """, (
                row['ticker'],
                target_date,
                float(row['시가']),
                float(row['고가']),
                float(row['저가']),
                float(row['종가']),
                int(row['거래량'])
            ))
            saved_count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving prices: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    return saved_count

def is_trading_day(target_date):
    """거래일 확인 (평일)"""
    return target_date.weekday() < 5

def collect_and_save(target_date):
    """데이터 수집 및 저장"""
    if not is_trading_day(target_date):
        print(f"  Skipped (weekend)")
        return 0

    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"Collecting {target_date}...", end=" ", flush=True)

        # 주가 수집
        tickers = pykrx_stock.get_market_ticker_list(date=date_str)
        print(f"({len(tickers)} tickers)", end=" ", flush=True)

        all_prices = []
        for ticker in tickers:
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except:
                continue

        prices_saved = 0
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            prices_saved = save_stock_prices(prices_df, target_date)
            print(f"✓ {prices_saved:,} records")
        else:
            print("✗ No data")

        return prices_saved

    except Exception as e:
        print(f"✗ ERROR: {e}")
        return 0

def main():
    print("="*70)
    print("Collecting missing dates data")
    print("="*70)

    total_prices = 0
    success_count = 0

    for target_date in missing_dates:
        prices = collect_and_save(target_date)
        total_prices += prices
        if prices > 0:
            success_count += 1

        # API 레이트 제한 방지
        time.sleep(1)

    print("="*70)
    print(f"Collection completed!")
    print(f"  ✓ Success: {success_count}/{len(missing_dates)} dates")
    print(f"  ✓ Total records: {total_prices:,}")
    print("="*70)

if __name__ == '__main__':
    main()
```

### 단계 3: 실행
```bash
# 전체 데이터 수집 (약 2시간 소요)
python collect_missing_data.py

# 또는 특정 날짜만 수집
python collect_single_date.py 2025-10-27
```

### 진행 상황 모니터링
```bash
# 별도 터미널에서 실시간 확인
python << 'EOF'
import psycopg2
from datetime import date

DB = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

conn = psycopg2.connect(**DB)
cursor = conn.cursor()

# 최근 10일 현황
cursor.execute("""
    SELECT date, COUNT(*) as count
    FROM stock_prices
    WHERE date >= CURRENT_DATE - INTERVAL '10 days'
    GROUP BY date
    ORDER BY date DESC;
""")

print("Recent collection status:")
for row in cursor.fetchall():
    status = "✓" if row[1] > 2000 else "✗"
    print(f"{status} {row[0]}: {row[1]:,} records")

cursor.close()
conn.close()
EOF
```

---

## 3. 방법 2: Airflow DAG로 수집

### Airflow 백필 기능 사용
```bash
# 특정 날짜 범위로 DAG 재실행
docker exec stock-airflow-scheduler airflow dags backfill \
    daily_collection_dag \
    --start-date 2025-10-27 \
    --end-date 2025-10-28

# 또는 캐치업 실행
docker exec stock-airflow-scheduler airflow dags test \
    daily_collection_dag \
    2025-10-27
```

### 커스텀 백필 DAG
파일명: `backfill_missing_dag.py`

```python
from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.append('/app')

from common_functions import (
    get_db_engine,
    fetch_stock_prices_api,
    save_stock_prices,
    update_collection_log_price,
    logger
)

# 수집할 날짜들
MISSING_DATES = [
    date(2025, 10, 27),
    date(2025, 10, 28),
    # ... 다른 날짜들
]

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 1),
    'email_on_failure': False,
    'retries': 0,
}

dag = DAG(
    dag_id='backfill_missing_prices',
    default_args=default_args,
    description='Backfill missing stock prices',
    schedule_interval=None,  # 수동 실행만
    is_paused_upon_creation=False,
)

def backfill_prices(target_date_str, **context):
    """누락된 날짜 주가 수집"""
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d').date()
    logger.info(f"Backfilling prices for {target_date}")

    try:
        engine = get_db_engine()

        # 주가 수집
        prices_df = fetch_stock_prices_api(target_date, engine)

        if prices_df.empty:
            logger.warning(f"No data for {target_date}")
            return {'status': 'no_data', 'date': target_date_str}

        # 저장
        saved_count = save_stock_prices(prices_df, target_date, engine)
        logger.info(f"Saved {saved_count} prices for {target_date}")

        # 로그 업데이트
        try:
            update_collection_log_price(
                target_date=target_date,
                status='success',
                count=saved_count,
                error=None,
                engine=engine
            )
        except:
            pass

        return {'status': 'success', 'count': saved_count, 'date': target_date_str}

    except Exception as e:
        logger.error(f"Error backfilling {target_date}: {e}")
        return {'status': 'error', 'error': str(e), 'date': target_date_str}

# 각 날짜마다 task 생성
for missing_date in MISSING_DATES:
    task = PythonOperator(
        task_id=f"backfill_{missing_date.strftime('%Y%m%d')}",
        python_callable=backfill_prices,
        op_kwargs={'target_date_str': missing_date.isoformat()},
        dag=dag
    )
```

실행:
```bash
# DAG 등록
cp backfill_missing_dag.py /f/hhstock/stock-trading-system/airflow/dags/

# 수동 실행
docker exec stock-airflow-scheduler airflow dags trigger backfill_missing_prices
```

---

## 4. 수집 후 검증

### 검증 쿼리
```sql
-- 1. 10월 데이터 현황
SELECT date, COUNT(*) as count
FROM stock_prices
WHERE date >= '2025-10-01'
GROUP BY date
ORDER BY date DESC;

-- 2. 누락된 날짜 확인
SELECT date FROM (
    SELECT DATE(day) as date
    FROM generate_series(
        DATE '2025-10-01',
        CURRENT_DATE,
        '1 day'::interval
    ) day
    WHERE EXTRACT(DOW FROM day) NOT IN (0, 6)
) dates
WHERE date NOT IN (
    SELECT DISTINCT date FROM stock_prices WHERE date >= '2025-10-01'
)
ORDER BY date;

-- 3. 수집 통계
SELECT
    COUNT(DISTINCT date) as trading_days,
    COUNT(*) as total_records,
    AVG(price_count) as avg_per_day
FROM (
    SELECT date, COUNT(*) as price_count
    FROM stock_prices
    WHERE date >= '2025-10-01'
    GROUP BY date
) stats;
```

### Python 검증 스크립트
```python
import psycopg2
from datetime import date, timedelta

DB = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

conn = psycopg2.connect(**DB)
cursor = conn.cursor()

# 수집 현황
cursor.execute("""
    SELECT COUNT(DISTINCT date) as trading_days,
           COUNT(*) as total_records,
           MIN(date) as first_date,
           MAX(date) as last_date
    FROM stock_prices
    WHERE date >= '2025-10-01';
""")

stats = cursor.fetchone()
print(f"Statistics (2025-10-01 onwards):")
print(f"  Trading days: {stats[0]}")
print(f"  Total records: {stats[1]:,}")
print(f"  First date: {stats[2]}")
print(f"  Last date: {stats[3]}")

# 누락된 날짜 확인
cursor.execute("""
    SELECT array_agg(DISTINCT date ORDER BY date)
    FROM (
        SELECT DATE(day) as date
        FROM generate_series(
            DATE '2025-10-01',
            CURRENT_DATE,
            '1 day'::interval
        ) day
        WHERE EXTRACT(DOW FROM day) NOT IN (0, 6)
    ) dates
    WHERE date NOT IN (
        SELECT DISTINCT date FROM stock_prices WHERE date >= '2025-10-01'
    );
""")

missing = cursor.fetchone()[0]
if missing:
    print(f"\nMissing dates ({len(missing)}):")
    for d in missing:
        print(f"  - {d}")
else:
    print("\n✓ All trading days have data!")

cursor.close()
conn.close()
```

---

## 5. 지표 계산 재실행

주가 데이터 수집 후 지표를 재계산합니다.

### 방법 1: DAG로 재계산
```bash
# 특정 날짜의 지표 재계산
docker exec stock-airflow-scheduler airflow dags test \
    technical_indicator_dag \
    2025-10-27

docker exec stock-airflow-scheduler airflow dags test \
    technical_indicator_dag \
    2025-10-28
```

### 방법 2: Python 스크립트
파일명: `recalculate_indicators.py`

```python
#!/usr/bin/env python3
from datetime import date
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))
sys.path.append('/app')

from common_functions import (
    get_db_engine,
    get_all_tickers,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_bollinger_bands,
    save_technical_indicators,
    update_indicator_log,
    logger
)
import pandas as pd

def recalculate_indicators(target_date):
    """특정 날짜의 지표 재계산"""
    logger.info(f"Recalculating indicators for {target_date}")

    try:
        engine = get_db_engine()

        # 티커 목록 조회
        tickers = get_all_tickers(target_date, engine)
        logger.info(f"Found {len(tickers)} tickers")

        # 지표 계산
        indicators_list = []
        for ticker in tickers:
            # 200일 역사 데이터 로드
            query = f"""
                SELECT date, close_price
                FROM stock_prices
                WHERE ticker = '{ticker}'
                  AND date <= '{target_date}'
                ORDER BY date DESC
                LIMIT 200;
            """
            prices = pd.read_sql(query, engine)

            if len(prices) < 20:
                continue

            # 지표 계산
            rsi = calculate_rsi(prices['close_price'].values)
            macd_result = calculate_macd(prices['close_price'].values)
            sma_20, sma_50, sma_200 = calculate_sma(prices['close_price'].values)
            bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(prices['close_price'].values)

            indicators_list.append({
                'ticker': ticker,
                'date': target_date,
                'rsi': rsi[-1],
                'macd': macd_result['macd'][-1],
                'macd_signal': macd_result['signal'][-1],
                'macd_histogram': macd_result['histogram'][-1],
                'sma_20': sma_20[-1],
                'sma_50': sma_50[-1],
                'sma_200': sma_200[-1],
                'bollinger_upper': bb_upper[-1],
                'bollinger_middle': bb_middle[-1],
                'bollinger_lower': bb_lower[-1],
            })

        # 저장
        if indicators_list:
            indicators_df = pd.DataFrame(indicators_list)
            saved_count = save_technical_indicators(indicators_df, engine)
            logger.info(f"Saved {saved_count} indicators for {target_date}")

            # 로그 업데이트
            update_indicator_log(
                target_date=target_date,
                status='success',
                indicators_count=saved_count,
                engine=engine
            )
        else:
            logger.warning(f"No indicators calculated for {target_date}")

    except Exception as e:
        logger.error(f"Error recalculating indicators: {e}", exc_info=True)
        raise

if __name__ == '__main__':
    # 재계산할 날짜들
    recalc_dates = [
        date(2025, 10, 27),
        date(2025, 10, 28),
    ]

    for target_date in recalc_dates:
        recalculate_indicators(target_date)
```

실행:
```bash
python recalculate_indicators.py
```

---

## 6. 트러블슈팅

### 문제: API 타임아웃
```python
# 해결책: 요청 간 지연 추가
import time
time.sleep(1)  # 1초 대기
```

### 문제: 중복 데이터
```sql
-- UPSERT 방식으로 자동 처리됨
-- 확인 쿼리:
SELECT ticker, date, COUNT(*) as cnt
FROM stock_prices
WHERE date = '2025-10-27'
GROUP BY ticker, date
HAVING COUNT(*) > 1;
```

### 문제: 메모리 부족
```python
# 배치 처리로 메모리 절약
batch_size = 100
for i in range(0, len(prices_df), batch_size):
    batch = prices_df[i:i+batch_size]
    save_stock_prices(batch, target_date)
```

---

## 7. 자동화 (선택사항)

### Linux/Mac에서 cron 스케줄링
```bash
# crontab -e
# 매주 월요일 밤 11시에 실행
0 23 * * 1 cd /f/hhstock && python collect_missing_data.py >> /tmp/collect.log 2>&1
```

### Windows에서 작업 스케줄러
```batch
REM PowerShell로 실행
powershell -Command "cd 'F:\hhstock'; python collect_missing_data.py"
```

---

**마지막 수정**: 2025-10-29

**참고**:
- 모든 스크립트는 Python 3.8 이상 필요
- pykrx API는 장중 시간에만 정상 작동
- 대량 요청 시 API 레이트 제한 주의
- 데이터 무결성을 위해 UPSERT 방식 사용
