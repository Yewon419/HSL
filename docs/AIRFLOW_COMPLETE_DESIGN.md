# Airflow 완전 설계 문서
**최종 구현 기준 - 오늘 완료**

---

## 📋 목차
1. [데이터베이스 스키마](#데이터베이스-스키마)
2. [상태 추적 테이블](#상태-추적-테이블)
3. [공통 함수 (Common Functions)](#공통-함수-common-functions)
4. [DAG 1: generate_daily_collection_dag](#dag-1-generate_daily_collection_dag)
5. [DAG 2: daily_collection_dag](#dag-2-daily_collection_dag)
6. [DAG 3: technical_indicator_dag](#dag-3-technical_indicator_dag)
7. [DAG 4: manual_collection_dag](#dag-4-manual_collection_dag)
8. [실행 흐름 및 시나리오](#실행-흐름-및-시나리오)

---

## 데이터베이스 스키마

### 기존 비즈니스 테이블

#### `stock_prices` (주가 데이터)
```sql
Column      | Type                     | Nullable | Default
------------|--------------------------|----------|------------------
ticker      | VARCHAR(10)              | NOT NULL |
date        | DATE                     | NOT NULL |
open_price  | NUMERIC(10,2)            | NULL     |
high_price  | NUMERIC(10,2)            | NULL     |
low_price   | NUMERIC(10,2)            | NULL     |
close_price | NUMERIC(10,2)            | NOT NULL |
volume      | BIGINT                   | NULL     |
created_at  | TIMESTAMP WITH TIME ZONE | NULL     | CURRENT_TIMESTAMP
PK: (ticker, date)
FK: ticker → stocks(ticker)
```

#### `market_indices` (시장 지수)
```sql
Column           | Type                     | Nullable | Default
-----------------|--------------------------|----------|------------------
id               | INTEGER                  | NOT NULL | nextval(...)
index_name       | VARCHAR(20)              | NOT NULL |
date             | DATE                     | NOT NULL |
index_value      | NUMERIC(15,2)            | NULL     |
stock_count      | INTEGER                  | NULL     |
total_volume     | BIGINT                   | NULL     |
total_market_cap | BIGINT                   | NULL     |
created_at       | TIMESTAMP                | NULL     | now()
PK: id
UNIQUE: (index_name, date)
```

#### `technical_indicators` (기술적 지표)
```sql
Column             | Type                     | Nullable | Default
-------------------|--------------------------|----------|------------------
ticker             | VARCHAR(10)              | NOT NULL |
date               | DATE                     | NOT NULL |
stoch_k            | NUMERIC(6,2)             | NULL     |
stoch_d            | NUMERIC(6,2)             | NULL     |
macd               | NUMERIC(10,4)            | NULL     |
macd_signal        | NUMERIC(10,4)            | NULL     |
macd_histogram     | NUMERIC(10,4)            | NULL     |
rsi                | NUMERIC(6,2)             | NULL     |
ma_20              | NUMERIC(10,2)            | NULL     |
ma_50              | NUMERIC(10,2)            | NULL     |
ma_200             | NUMERIC(10,2)            | NULL     |
bollinger_upper    | NUMERIC(10,2)            | NULL     |
bollinger_middle   | NUMERIC(10,2)            | NULL     |
bollinger_lower    | NUMERIC(10,2)            | NULL     |
ichimoku_tenkan    | NUMERIC(10,2)            | NULL     |
ichimoku_kijun     | NUMERIC(10,2)            | NULL     |
ichimoku_senkou_a  | NUMERIC(10,2)            | NULL     |
ichimoku_senkou_b  | NUMERIC(10,2)            | NULL     |
ichimoku_chikou    | NUMERIC(10,2)            | NULL     |
created_at         | TIMESTAMP WITH TIME ZONE | NULL     | CURRENT_TIMESTAMP
PK: (ticker, date)
FK: ticker → stocks(ticker)
```

---

## 상태 추적 테이블

### `collection_log` (수집 상태 추적)
**목적**: 매일 주가/지수 수집 현황 기록

```sql
CREATE TABLE collection_log (
    id SERIAL PRIMARY KEY,

    -- 날짜
    collection_date DATE NOT NULL UNIQUE,  -- 수집 대상 날짜 (2025-10-20)

    -- 주가 상태
    price_status VARCHAR(20) DEFAULT 'pending',  -- pending, success, failed, retrying
    price_count INTEGER,                          -- 수집된 주가 레코드 수
    price_last_error TEXT,                        -- 마지막 에러 메시지
    price_completed_at TIMESTAMP,                 -- 완료 시간
    price_retry_count INTEGER DEFAULT 0,          -- 재시도 횟수

    -- 지수 상태
    indices_status VARCHAR(20) DEFAULT 'pending', -- pending, success, failed, retrying
    indices_count INTEGER,                        -- 수집된 지수 레코드 수
    indices_last_error TEXT,                      -- 마지막 에러 메시지
    indices_completed_at TIMESTAMP,               -- 완료 시간
    indices_retry_count INTEGER DEFAULT 0,        -- 재시도 횟수

    -- 전체 상태
    overall_status VARCHAR(20) DEFAULT 'pending', -- pending, partial, success, failed

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT check_price_retry CHECK (price_retry_count <= 3),
    CONSTRAINT check_indices_retry CHECK (indices_retry_count <= 3)
);

-- 인덱스
CREATE INDEX idx_collection_log_date ON collection_log(collection_date);
CREATE INDEX idx_collection_log_status ON collection_log(overall_status);
```

### `indicator_log` (지표 계산 상태 추적)
**목적**: 기술적 지표 계산 현황 기록

```sql
CREATE TABLE indicator_log (
    id SERIAL PRIMARY KEY,

    -- 날짜
    indicator_date DATE NOT NULL UNIQUE,  -- 지표 대상 날짜 (2025-10-20)

    -- 지표 상태
    status VARCHAR(20) DEFAULT 'pending',  -- pending, success, failed, retrying
    indicators_count INTEGER,              -- 계산된 지표 레코드 수
    last_error TEXT,                       -- 마지막 에러 메시지
    completed_at TIMESTAMP,                -- 완료 시간
    retry_count INTEGER DEFAULT 0,         -- 재시도 횟수

    -- 의존성 확인
    required_prices_count INTEGER,         -- 필요한 주가 수
    collected_prices_count INTEGER,        -- 실제 수집된 주가 수

    -- 메타데이터
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),

    CONSTRAINT check_retry CHECK (retry_count <= 3)
);

-- 인덱스
CREATE INDEX idx_indicator_log_date ON indicator_log(indicator_date);
CREATE INDEX idx_indicator_log_status ON indicator_log(status);
```

---

## 공통 함수 (Common Functions)

### 파일: `common_dag_functions.py`

#### 1. 데이터베이스 연결
```python
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def get_db_engine():
    """PostgreSQL 엔진 생성"""
    database_url = "postgresql://admin:admin123@stock-db:5432/stocktrading"
    return create_engine(database_url)

def get_db_session():
    """DB 세션 생성"""
    engine = get_db_engine()
    Session = sessionmaker(bind=engine)
    return Session()
```

#### 2. pykrx 데이터 수집
```python
from pykrx import stock
from datetime import date
import pandas as pd
import logging

logger = logging.getLogger(__name__)

def fetch_stock_prices(target_date: date) -> pd.DataFrame:
    """
    pykrx로 주가 데이터 수집

    Returns:
        DataFrame with columns: [ticker, date, open_price, high_price, low_price, close_price, volume]
    """
    try:
        date_str = target_date.strftime('%Y%m%d')
        tickers = stock.get_market_ticker_list(date=date_str)
        logger.info(f"Found {len(tickers)} tickers for {target_date}")

        all_prices = []
        for ticker in tickers:
            try:
                df = stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    for idx, row in df.iterrows():
                        all_prices.append({
                            'ticker': ticker,
                            'date': target_date,
                            'open_price': float(row['시가']),
                            'high_price': float(row['고가']),
                            'low_price': float(row['저가']),
                            'close_price': float(row['종가']),
                            'volume': int(row['거래량'])
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch {ticker}: {e}")
                continue

        result_df = pd.DataFrame(all_prices)
        logger.info(f"Collected {len(result_df)} stock prices for {target_date}")
        return result_df

    except Exception as e:
        logger.error(f"Error fetching stock prices: {e}")
        raise

def fetch_market_indices(target_date: date) -> pd.DataFrame:
    """
    pykrx로 시장 지수 데이터 수집

    Returns:
        DataFrame with columns: [index_name, date, index_value]
    """
    try:
        date_str = target_date.strftime('%Y%m%d')
        all_indices = []

        for index_name in ['KOSPI', 'KOSDAQ']:
            try:
                df = stock.get_index_ohlcv(date_str, date_str, index_name)
                if not df.empty:
                    for idx, row in df.iterrows():
                        all_indices.append({
                            'index_name': index_name,
                            'date': target_date,
                            'index_value': float(row['종가']),
                            'stock_count': None,
                            'total_volume': int(row['거래량']),
                            'total_market_cap': None
                        })
            except Exception as e:
                logger.warning(f"Failed to fetch {index_name}: {e}")
                continue

        result_df = pd.DataFrame(all_indices)
        logger.info(f"Collected {len(result_df)} market indices for {target_date}")
        return result_df

    except Exception as e:
        logger.error(f"Error fetching market indices: {e}")
        raise
```

#### 3. DB 저장
```python
def save_stock_prices(prices_df: pd.DataFrame, target_date: date) -> int:
    """
    주가 데이터 DB 저장

    Returns:
        저장된 레코드 수
    """
    session = None
    try:
        session = get_db_session()
        from models import StockPrice

        # 기존 데이터 삭제
        session.query(StockPrice).filter(StockPrice.date == target_date).delete()
        session.commit()
        logger.info(f"Deleted existing stock prices for {target_date}")

        # 새 데이터 저장
        count = 0
        for _, row in prices_df.iterrows():
            price = StockPrice(
                ticker=row['ticker'],
                date=row['date'],
                open_price=row['open_price'],
                high_price=row['high_price'],
                low_price=row['low_price'],
                close_price=row['close_price'],
                volume=row['volume']
            )
            session.add(price)
            count += 1

        session.commit()
        logger.info(f"Saved {count} stock prices for {target_date}")
        return count

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error saving stock prices: {e}")
        raise
    finally:
        if session:
            session.close()

def save_market_indices(indices_df: pd.DataFrame, target_date: date) -> int:
    """
    시장 지수 DB 저장

    Returns:
        저장된 레코드 수
    """
    session = None
    try:
        session = get_db_session()
        from models import MarketIndex

        # 기존 데이터 삭제
        session.query(MarketIndex).filter(MarketIndex.date == target_date).delete()
        session.commit()
        logger.info(f"Deleted existing market indices for {target_date}")

        # 새 데이터 저장
        count = 0
        for _, row in indices_df.iterrows():
            index = MarketIndex(
                index_name=row['index_name'],
                date=row['date'],
                index_value=row['index_value'],
                stock_count=row.get('stock_count'),
                total_volume=row.get('total_volume'),
                total_market_cap=row.get('total_market_cap')
            )
            session.add(index)
            count += 1

        session.commit()
        logger.info(f"Saved {count} market indices for {target_date}")
        return count

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error saving market indices: {e}")
        raise
    finally:
        if session:
            session.close()
```

#### 4. 상태 추적
```python
def update_collection_log_price(target_date: date, status: str, count: int = None, error: str = None):
    """주가 수집 상태 업데이트 → collection_log"""
    session = None
    try:
        session = get_db_session()

        log_entry = session.query(CollectionLog).filter(
            CollectionLog.collection_date == target_date
        ).first()

        if not log_entry:
            log_entry = CollectionLog(collection_date=target_date)
            session.add(log_entry)

        log_entry.price_status = status
        if count is not None:
            log_entry.price_count = count
        if error:
            log_entry.price_last_error = error
        if status == 'success':
            log_entry.price_completed_at = datetime.now()
        elif status == 'retrying':
            log_entry.price_retry_count += 1

        # overall_status 업데이트
        if log_entry.price_status == 'success' and log_entry.indices_status == 'success':
            log_entry.overall_status = 'success'
        elif log_entry.price_status == 'success' or log_entry.indices_status == 'success':
            log_entry.overall_status = 'partial'
        else:
            log_entry.overall_status = log_entry.price_status or 'pending'

        session.commit()
        logger.info(f"Updated collection_log for {target_date}: price={status}")

    except Exception as e:
        if session:
            session.rollback()
        logger.error(f"Error updating collection_log: {e}")
        raise
    finally:
        if session:
            session.close()

def get_collection_status(target_date: date) -> dict:
    """수집 상태 조회"""
    session = None
    try:
        session = get_db_session()

        log_entry = session.query(CollectionLog).filter(
            CollectionLog.collection_date == target_date
        ).first()

        if not log_entry:
            return {
                'status': 'not_found',
                'overall_status': None,
                'price_status': None,
                'indices_status': None
            }

        return {
            'status': 'found',
            'overall_status': log_entry.overall_status,
            'price_status': log_entry.price_status,
            'indices_status': log_entry.indices_status,
            'price_retry_count': log_entry.price_retry_count,
            'indices_retry_count': log_entry.indices_retry_count
        }

    except Exception as e:
        logger.error(f"Error getting collection_status: {e}")
        raise
    finally:
        if session:
            session.close()
```

#### 5. 검증 함수
```python
def verify_stock_prices_saved(target_date: date) -> bool:
    """주가가 정확히 저장되었는지 확인"""
    session = None
    try:
        session = get_db_session()
        from models import StockPrice

        count = session.query(StockPrice).filter(
            StockPrice.date == target_date
        ).count()

        if count > 0:
            logger.info(f"Verified: {count} stock prices saved for {target_date}")
            return True
        else:
            logger.warning(f"Verification failed: No stock prices found for {target_date}")
            return False

    except Exception as e:
        logger.error(f"Error verifying stock prices: {e}")
        raise
    finally:
        if session:
            session.close()
```

---

## DAG 1: generate_daily_collection_dag
**목적**: 매일 1개의 task job 생성 (16시)

**스케줄**: `0 16 * * 1-5` (매일 16:00 UTC = 오전 1시)

**코드 개요**:
```python
from airflow import DAG
from airflow.operators.python import PythonOperator
from datetime import datetime, timedelta

default_args = {
    'owner': 'stock-system',
    'start_date': datetime(2025, 10, 20),
    'retries': 0,
}

dag = DAG(
    'generate_daily_collection_dag',
    default_args=default_args,
    description='Generate daily collection DAG',
    schedule_interval='0 16 * * 1-5',  # 매일 16시
    catchup=False,
)

@task
def generate_daily_collection():
    """
    오늘 task job 생성
    → dynamic_daily_collection_dag_2025-10-20 생성
    → collection_log INSERT (status=pending)
    """
    target_date = date.today()
    # DAG 생성 로직
    # collection_log 생성

dag >> generate_daily_collection()
```

---

## DAG 2: daily_collection_dag
**목적**: 16시~23시 매시간 체크하며 17시부터 수집

**스케줄**: `0 16-23 * * 1-5` (매일 16시~23시 매시간)

**코드 개요**:
```python
dag = DAG(
    'daily_collection_dag',
    schedule_interval='0 16-23 * * 1-5',  # 매시간
    ...
)

@task
def check_and_collect():
    """
    1. 현재 시간 >= 17시?
    2. collection_log 확인
    3. 미완료면 실행, 완료면 스킵
    """
    current_hour = datetime.now().hour
    if current_hour < 17:
        return {'status': 'skipped', 'reason': 'before_collection_time'}

    status = get_collection_status(date.today())

    if status['overall_status'] == 'success':
        return {'status': 'skipped', 'reason': 'already_complete'}

    # 실행 트리거

@task.task_group
def price_task_group():
    """주가 수집 task group"""
    # fetch_stock_prices
    # save_stock_prices
    # verify_stock_prices

@task.task_group
def indices_task_group():
    """지수 수집 task group"""
    # fetch_market_indices
    # save_market_indices
    # verify_market_indices

check_and_collect() >> [price_task_group(), indices_task_group()]
```

---

## DAG 3: technical_indicator_dag
**목적**: 18시~23시 매시간 체크하며 지표 계산

**스케줄**: `0 18-23 * * 1-5` (매일 18시~23시 매시간)

**코드 개요**:
```python
dag = DAG(
    'technical_indicator_dag',
    schedule_interval='0 18-23 * * 1-5',  # 매시간
    ...
)

@task
def check_and_calculate_indicators():
    """
    1. 현재 시간 >= 18시?
    2. collection_log에서 overall_status == 'success'?
    3. 완료면 스킵, 미완료면 실행
    """
    current_hour = datetime.now().hour
    if current_hour < 18:
        return {'status': 'skipped', 'reason': 'before_indicator_time'}

    collection_status = get_collection_status(date.today())

    if collection_status['overall_status'] != 'success':
        return {'status': 'skipped', 'reason': 'collection_not_complete'}

    indicator_status = get_indicator_status(date.today())
    if indicator_status['status'] == 'success':
        return {'status': 'skipped', 'reason': 'already_complete'}

    # 지표 계산 트리거

@task
def calculate_indicators():
    """기술적 지표 계산"""
    # RSI, MACD, SMA, Bollinger Bands, Ichimoku 등

check_and_calculate_indicators() >> calculate_indicators()
```

---

## DAG 4: manual_collection_dag
**목적**: 수동 트리거용 (자동 실패 시 사용)

**스케줄**: None (수동만)

**코드 개요**:
```python
dag = DAG(
    'manual_collection_dag',
    schedule_interval=None,  # 수동만
    ...
)

@task
def manual_collect_and_calculate():
    """
    Execution date로 지정된 날짜의 데이터 수집 및 지표 계산
    """
    # execution_date로 target_date 추출
    # 주가 수집 → 지수 수집 → 지표 계산

manual_collect_and_calculate()
```

---

## 실행 흐름 및 시나리오

### 정상 시나리오 (2025-10-20, 월요일)

```
16:00 → generate_daily_collection_dag 실행
  └─ dynamic_daily_collection_dag_2025-10-20 생성
  └─ collection_log INSERT: collection_date=2025-10-20, overall_status=pending

16:00 → daily_collection_dag 매시간 체크 시작
16:01~16:59 → 현재 시간 < 17시 → 스킵

17:00 → daily_collection_dag 실행
  ├─ price_task_group:
  │  ├─ fetch_stock_prices (959개)
  │  ├─ save_stock_prices
  │  └─ verify_stock_prices + collection_log UPDATE (price_status=success, price_count=959)
  │
  └─ indices_task_group:
     ├─ fetch_market_indices (2개: KOSPI, KOSDAQ)
     ├─ save_market_indices
     └─ verify_market_indices + collection_log UPDATE (indices_status=success, indices_count=2)

  └─ collection_log UPDATE: overall_status=success

18:00 → technical_indicator_dag 매시간 체크 시작
  └─ collection_status 확인 → overall_status=success ✓
  └─ indicator_calculation 실행
     ├─ calculate_indicators (모든 주식 기술적 지표)
     └─ indicator_log UPDATE: status=success, indicators_count=N
```

### 실패 시나리오 (예: 17시 주가 수집 API 에러)

```
17:00 → daily_collection_dag 실행
  ├─ price_task_group:
  │  ├─ fetch_stock_prices → API 에러 발생
  │  └─ collection_log UPDATE: price_status=failed, price_retry_count=1, last_error="..."
  │
  └─ indices_task_group:
     ├─ fetch_market_indices (성공)
     ├─ save_market_indices
     └─ collection_log UPDATE: indices_status=success, indices_count=2

  └─ collection_log UPDATE: overall_status=partial

18:00 → daily_collection_dag 매시간 체크
  └─ collection_status 확인 → price_status=failed → 재실행 시작
  └─ price_task_group 재실행 (price_retry_count=2)
  └─ 성공 → collection_log UPDATE: price_status=success, price_retry_count=2

18:00 → technical_indicator_dag 매시간 체크
  └─ collection_status 확인 → overall_status=success ✓ (partial → success 업데이트됨)
  └─ indicator_calculation 실행
```

### 최대 재시도 초과

```
17:00 → fetch_stock_prices 실패
18:00 → 재시도 1 실패
19:00 → 재시도 2 실패
20:00 → 재시도 3 실패 (max_retry=3 도달)

→ collection_log: price_status=failed, price_retry_count=3 (재시도 불가)

→ manual_collection_dag 수동 트리거 필요
  execution_date=2025-10-20 지정
  → 수동 수집 실행
```

---

## 구현 체크리스트

### 테이블 생성
- [ ] `collection_log` 테이블 생성
- [ ] `indicator_log` 테이블 생성
- [ ] 인덱스 생성

### 공통 함수 작성
- [ ] `common_dag_functions.py` 작성
  - [ ] 데이터베이스 연결 함수
  - [ ] pykrx 수집 함수
  - [ ] DB 저장 함수
  - [ ] 상태 추적 함수
  - [ ] 검증 함수

### DAG 구현
- [ ] `generate_daily_collection_dag.py` (16시 실행)
- [ ] `daily_collection_dag.py` (16~23시 매시간)
- [ ] `technical_indicator_dag.py` (18~23시 매시간)
- [ ] `manual_collection_dag.py` (수동 트리거)

### 배포 및 테스트
- [ ] 4개 DAG 배포
- [ ] 정상 시나리오 테스트
- [ ] 실패 시나리오 테스트
- [ ] 수동 트리거 테스트

---

**작성일**: 2025-10-20
**상태**: 설계 문서 작성 중
**다음**: DAG 구현 시작 (내일)
