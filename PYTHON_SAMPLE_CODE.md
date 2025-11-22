# Python 샘플 코드 가이드

데이터 수집 및 처리 스크립트 실행 시 발생할 수 있는 모듈 에러를 피하기 위한 가이드입니다.

---

## 1. 필수 패키지 설치

### Python 환경 확인
```bash
python --version  # Python 3.8 이상 권장
pip --version
```

### 필수 패키지 설치
```bash
# 방법 1: 한 번에 설치
pip install pykrx psycopg2-binary sqlalchemy pandas

# 방법 2: 개별 설치 (권장 - 버전 제어)
pip install pykrx==0.2.16
pip install psycopg2-binary==2.9.9
pip install sqlalchemy==2.0.23
pip install pandas==2.1.3
```

### 설치 확인
```bash
python << 'EOF'
import pykrx
import psycopg2
import sqlalchemy
import pandas

print("✓ pykrx:", pykrx.__version__)
print("✓ psycopg2:", psycopg2.__version__)
print("✓ sqlalchemy:", sqlalchemy.__version__)
print("✓ pandas:", pandas.__version__)
EOF
```

---

## 2. 데이터베이스 연결 샘플

### 샘플 1: psycopg2 직접 연결
```python
#!/usr/bin/env python3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 운영 DB 연결 설정
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

# 사용 예시
if __name__ == '__main__':
    conn = get_db_connection()
    cursor = conn.cursor()

    # 주가 데이터 조회
    cursor.execute("""
        SELECT date, COUNT(*) as count
        FROM stock_prices
        WHERE date >= CURRENT_DATE - INTERVAL '5 days'
        GROUP BY date ORDER BY date DESC
    """)

    for row in cursor.fetchall():
        print(f"{row[0]}: {row[1]:,} records")

    cursor.close()
    conn.close()
```

### 샘플 2: SQLAlchemy 연결 (권장)
```python
#!/usr/bin/env python3
from sqlalchemy import create_engine
import pandas as pd

# 운영 DB 엔진 생성
DATABASE_URL = "postgresql://admin:admin123@192.168.219.103:5432/stocktrading"

engine = create_engine(
    DATABASE_URL,
    connect_args={"options": "-c client_encoding=utf8"}
)

# 사용 예시: SQL 쿼리 실행
def query_stock_prices(target_date):
    """특정 날짜의 주가 데이터 조회"""
    query = f"""
        SELECT ticker, date, open_price, close_price, volume
        FROM stock_prices
        WHERE date = '{target_date}'
        ORDER BY ticker
    """
    return pd.read_sql(query, engine)

# 실행
if __name__ == '__main__':
    df = query_stock_prices('2025-10-29')
    print(f"Total records: {len(df)}")
    print(df.head())
```

### 샘플 3: Docker 내부 DB 연결
```python
#!/usr/bin/env python3
import psycopg2

# Docker 내부 DB 연결 설정
DOCKER_DB_CONFIG = {
    'host': 'stock-db',  # Docker 내부 호스트명
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def get_docker_connection():
    """Docker 내부 DB 연결"""
    conn = psycopg2.connect(**DOCKER_DB_CONFIG)
    return conn

# 주의: Docker 컨테이너 내부에서만 동작
# docker exec stock-airflow-scheduler python script.py 형태로 실행
```

---

## 3. 데이터 수집 샘플

### 샘플 1: pykrx로 주가 수집
```python
#!/usr/bin/env python3
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd

def fetch_stock_prices(target_date):
    """
    pykrx에서 주가 데이터 수집

    Args:
        target_date: datetime.date 객체 (예: date(2025, 10, 29))

    Returns:
        DataFrame: ticker, 시가, 고가, 저가, 종가, 거래량
    """
    date_str = target_date.strftime("%Y%m%d")

    try:
        # 거래 가능한 종목 조회
        tickers = pykrx_stock.get_market_ticker_list(date=date_str)
        print(f"Found {len(tickers)} tickers for {target_date}")

        all_prices = []
        for ticker in tickers:
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except Exception as e:
                # 개별 종목 실패는 무시
                continue

        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            print(f"Collected {len(prices_df)} price records")
            return prices_df
        else:
            print("No price data collected")
            return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching prices: {e}")
        return pd.DataFrame()

# 실행
if __name__ == '__main__':
    target_date = date(2025, 10, 29)
    df = fetch_stock_prices(target_date)
    print(df.head())
```

### 샘플 2: pykrx로 지수 수집
```python
#!/usr/bin/env python3
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd

def fetch_market_indices(target_date):
    """
    pykrx에서 시장 지수 수집 (KOSPI, KOSDAQ)

    Args:
        target_date: datetime.date 객체

    Returns:
        DataFrame: 지수명, 시가, 고가, 저가, 종가
    """
    date_str = target_date.strftime("%Y%m%d")
    indices_data = []

    try:
        # KOSPI 지수 (ID: 1001)
        try:
            kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")
            if not kospi.empty:
                kospi['index_name'] = "KOSPI"
                indices_data.append(kospi)
                print(f"KOSPI: {kospi.iloc[0]['종가']:.2f}")
        except Exception as e:
            print(f"KOSPI error: {e}")

        # KOSDAQ 지수 (ID: 1002)
        try:
            kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "1002")
            if not kosdaq.empty:
                kosdaq['index_name'] = "KOSDAQ"
                indices_data.append(kosdaq)
                print(f"KOSDAQ: {kosdaq.iloc[0]['종가']:.2f}")
        except Exception as e:
            print(f"KOSDAQ error: {e}")

        if indices_data:
            return pd.concat(indices_data, ignore_index=True)
        else:
            return pd.DataFrame()

    except Exception as e:
        print(f"Error fetching indices: {e}")
        return pd.DataFrame()

# 실행
if __name__ == '__main__':
    target_date = date(2025, 10, 29)
    df = fetch_market_indices(target_date)
    print(df)
```

---

## 4. 데이터 저장 샘플

### 샘플 1: UPSERT 방식으로 주가 저장
```python
#!/usr/bin/env python3
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from datetime import date
import pandas as pd

DB_CONFIG = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def save_stock_prices(prices_df, target_date):
    """
    주가 데이터 저장 (UPSERT 방식)

    중복 데이터는 UPDATE, 신규는 INSERT
    """
    if prices_df.empty:
        print("No data to save")
        return 0

    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
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
        print(f"Successfully saved {saved_count} records")
        return saved_count

    except Exception as e:
        conn.rollback()
        print(f"Error saving data: {e}")
        raise

    finally:
        cursor.close()
        conn.close()

# 실행 예시
if __name__ == '__main__':
    # 주가 수집 (위의 샘플 참고)
    from datetime import date
    from pykrx import stock as pykrx_stock

    target_date = date(2025, 10, 29)
    date_str = target_date.strftime("%Y%m%d")

    # 수집
    tickers = pykrx_stock.get_market_ticker_list(date=date_str)
    all_prices = []
    for ticker in tickers[:5]:  # 테스트용 5개만
        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except:
            continue

    if all_prices:
        prices_df = pd.concat(all_prices, ignore_index=True)
        save_stock_prices(prices_df, target_date)
```

---

## 5. 전체 통합 수집 스크립트

### 완전한 예제: 단일 날짜 데이터 수집 및 저장
```python
#!/usr/bin/env python3
"""
전체 통합 수집 스크립트
실행: python collect_single_date.py <YYYY-MM-DD>
예:   python collect_single_date.py 2025-10-29
"""

import sys
from datetime import date, datetime
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 운영 DB 설정
DB_CONFIG = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def save_stock_prices(prices_df, target_date):
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

def collect_for_date(target_date):
    """특정 날짜 데이터 수집 및 저장"""
    print(f"\n{'='*60}")
    print(f"Collecting data for {target_date}")
    print(f"{'='*60}")

    # 평일 확인
    if target_date.weekday() >= 5:
        print(f"Skipped: {target_date} is weekend")
        return 0

    try:
        date_str = target_date.strftime("%Y%m%d")

        # 주가 수집
        print(f"Fetching stock prices...", end=" ", flush=True)
        tickers = pykrx_stock.get_market_ticker_list(date=date_str)
        print(f"({len(tickers)} tickers)")

        all_prices = []
        for i, ticker in enumerate(tickers):
            if (i + 1) % 100 == 0:
                print(f"  Progress: {i+1}/{len(tickers)}")
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except:
                continue

        # 저장
        prices_saved = 0
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            prices_saved = save_stock_prices(prices_df, target_date)
            print(f"✓ Saved {prices_saved:,} price records")
        else:
            print("✗ No price data collected")

        return prices_saved

    except Exception as e:
        print(f"✗ Error: {e}")
        return 0

def main():
    if len(sys.argv) < 2:
        print("Usage: python collect_single_date.py <YYYY-MM-DD>")
        print("Example: python collect_single_date.py 2025-10-29")
        sys.exit(1)

    try:
        target_date = datetime.strptime(sys.argv[1], "%Y-%m-%d").date()
    except ValueError:
        print("Invalid date format. Use YYYY-MM-DD")
        sys.exit(1)

    collect_for_date(target_date)

if __name__ == '__main__':
    main()
```

---

## 6. 에러 해결 가이드

### 에러 1: ModuleNotFoundError: No module named 'pykrx'
**해결책:**
```bash
pip install pykrx
# 또는 특정 버전
pip install pykrx==0.2.16
```

### 에러 2: psycopg2 import 실패
**해결책:**
```bash
# psycopg2-binary 설치 (권장)
pip install psycopg2-binary

# 또는 psycopg2 (컴파일 필요)
pip install psycopg2
```

### 에러 3: could not connect to server
**확인사항:**
```bash
# 1. IP 주소 확인
ping 192.168.219.103

# 2. 포트 확인 (5432가 열려있는지)
netstat -an | find "5432"

# 3. 자격증명 확인
psql -h 192.168.219.103 -U admin -d stocktrading -c "SELECT 1;"
# 비밀번호: admin123

# 4. 방화벽 확인
# Windows: netsh advfirewall set rule name="PostgreSQL" dir=in action=allow protocol=tcp localport=5432
```

### 에러 4: Isolation level error
**해결책:**
```python
# AUTOCOMMIT 모드 설정 필수
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
conn = psycopg2.connect(...)
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
```

### 에러 5: pykrx API timeout
**해결책:**
```python
import time

# 요청 사이에 delay 추가
for ticker in tickers:
    try:
        df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
        # 처리...
    except:
        continue
    time.sleep(0.1)  # 100ms 대기
```

---

## 7. 실행 방법

### 방법 1: 일반 Python 실행
```bash
# 가상환경 생성 (권장)
python -m venv venv
source venv/Scripts/activate  # Windows: venv\Scripts\activate.bat

# 패키지 설치
pip install -r requirements.txt

# 스크립트 실행
python collect_single_date.py 2025-10-29
```

### 방법 2: Docker 컨테이너 내부 실행
```bash
# Airflow 스케줄러 컨테이너에서 실행
docker exec stock-airflow-scheduler python /f/hhstock/collect_single_date.py 2025-10-29
```

### 방법 3: Airflow DAG로 실행
```python
# DAG 코드에서
from airflow.operators.python import PythonOperator

def run_collection():
    from datetime import date
    from collect_single_date import collect_for_date
    collect_for_date(date.today())

task = PythonOperator(
    task_id='collect_prices',
    python_callable=run_collection,
    dag=dag
)
```

---

## 8. requirements.txt 파일
```
pykrx==0.2.16
psycopg2-binary==2.9.9
sqlalchemy==2.0.23
pandas==2.1.3
numpy==1.24.3
```

설치:
```bash
pip install -r requirements.txt
```

---

**마지막 수정**: 2025-10-29
