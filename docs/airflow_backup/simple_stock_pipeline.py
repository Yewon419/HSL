from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
import requests
import json

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'simple_stock_data_collection',
    default_args=default_args,
    description='Simple stock data collection without external dependencies',
    schedule_interval='0 18 * * 1-5',  # 매일 오후 6시 (평일만)
    catchup=False,
    max_active_runs=1,
    tags=['stock', 'simple', 'etl']
)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def fetch_sample_stock_data(**context):
    """샘플 주식 데이터 생성 (실제 API 호출 없이)"""
    execution_date = context['execution_date']

    logging.info("Generating sample stock data")

    # 샘플 한국 주식 데이터
    sample_stocks = [
        {'ticker': '005930', 'name': '삼성전자', 'base_price': 70000},
        {'ticker': '000660', 'name': 'SK하이닉스', 'base_price': 130000},
        {'ticker': '035420', 'name': 'NAVER', 'base_price': 180000},
        {'ticker': '051910', 'name': 'LG화학', 'base_price': 400000},
        {'ticker': '006400', 'name': '삼성SDI', 'base_price': 350000},
    ]

    all_data = []

    # 현재 시간을 기반으로 간단한 변동 생성
    import random
    random.seed(int(execution_date.timestamp()))

    for stock in sample_stocks:
        base_price = stock['base_price']

        # 랜덤한 가격 변동 (±5%)
        variation = random.uniform(-0.05, 0.05)
        close_price = base_price * (1 + variation)

        stock_data = {
            'ticker': stock['ticker'],
            'date': str(execution_date.date()),
            'open_price': close_price * random.uniform(0.98, 1.02),
            'high_price': close_price * random.uniform(1.00, 1.03),
            'low_price': close_price * random.uniform(0.97, 1.00),
            'close_price': close_price,
            'volume': random.randint(100000, 10000000),
            'created_at': str(datetime.now())
        }

        all_data.append(stock_data)

    context['task_instance'].xcom_push(key='stock_data', value=all_data)
    logging.info(f"Generated sample data for {len(all_data)} stocks")
    return len(all_data)

def save_stock_data_to_db(**context):
    """주식 데이터를 데이터베이스에 저장"""
    stock_data = context['task_instance'].xcom_pull(task_ids='fetch_sample_stock_data', key='stock_data')

    if not stock_data:
        logging.warning("No stock data to save")
        return 0

    engine = get_db_connection()

    try:
        # 먼저 stocks 테이블에 주식 정보가 있는지 확인하고 없으면 추가
        stock_info = [
            {'ticker': '005930', 'company_name': '삼성전자'},
            {'ticker': '000660', 'company_name': 'SK하이닉스'},
            {'ticker': '035420', 'company_name': 'NAVER'},
            {'ticker': '051910', 'company_name': 'LG화학'},
            {'ticker': '006400', 'company_name': '삼성SDI'},
        ]

        with engine.begin() as conn:
            # 주식 정보 삽입/업데이트
            for stock in stock_info:
                conn.execute(text("""
                    INSERT INTO stocks (ticker, company_name, market_type, is_active, currency)
                    VALUES (:ticker, :company_name, 'KOSPI', true, 'KRW')
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        is_active = EXCLUDED.is_active
                """), stock)

            # 가격 데이터 삽입/업데이트
            for row in stock_data:
                # 문자열로 변환된 날짜를 다시 date 객체로 변환
                row_data = row.copy()
                if isinstance(row_data['date'], str):
                    from datetime import datetime
                    row_data['date'] = datetime.strptime(row_data['date'], '%Y-%m-%d').date()
                if isinstance(row_data['created_at'], str):
                    row_data['created_at'] = datetime.now()

                conn.execute(text("""
                    INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                    VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                    ON CONFLICT (ticker, date)
                    DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """), row_data)

        logging.info(f"Successfully saved {len(stock_data)} stock price records")
        return len(stock_data)

    except Exception as e:
        logging.error(f"Error saving to database: {e}")
        raise

def calculate_simple_indicators(**context):
    """간단한 기술적 지표 계산"""
    engine = get_db_connection()

    try:
        with engine.begin() as conn:
            # 20일 이동평균 계산
            conn.execute(text("""
                WITH price_data AS (
                    SELECT
                        ticker,
                        date,
                        close_price,
                        AVG(close_price) OVER (
                            PARTITION BY ticker
                            ORDER BY date
                            ROWS BETWEEN 19 PRECEDING AND CURRENT ROW
                        ) as ma_20
                    FROM stock_prices
                    WHERE date >= CURRENT_DATE - INTERVAL '30 days'
                ),
                today_data AS (
                    SELECT
                        ticker,
                        date,
                        ma_20
                    FROM price_data
                    WHERE date = CURRENT_DATE
                )
                INSERT INTO technical_indicators (ticker, date, ma_20, created_at)
                SELECT ticker, date, ma_20, NOW()
                FROM today_data
                ON CONFLICT (ticker, date)
                DO UPDATE SET
                    ma_20 = EXCLUDED.ma_20
            """))

        logging.info("Successfully calculated technical indicators")
        return True

    except Exception as e:
        logging.error(f"Error calculating indicators: {e}")
        # 에러가 나도 계속 진행
        return False

def simple_data_quality_check(**context):
    """데이터 품질 검사"""
    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 오늘 수집된 데이터 개수 확인
            result = conn.execute(text("""
                SELECT COUNT(*) as count
                FROM stock_prices
                WHERE date = CURRENT_DATE
            """))
            today_count = result.fetchone()[0]

            logging.info(f"Data quality check: {today_count} records collected today")

            if today_count < 3:
                logging.warning(f"Low data count: {today_count} records")

            return today_count

    except Exception as e:
        logging.error(f"Data quality check failed: {e}")
        return 0

# Task 정의
fetch_data_task = PythonOperator(
    task_id='fetch_sample_stock_data',
    python_callable=fetch_sample_stock_data,
    dag=dag,
)

save_data_task = PythonOperator(
    task_id='save_stock_data_to_db',
    python_callable=save_stock_data_to_db,
    dag=dag,
)

calculate_indicators_task = PythonOperator(
    task_id='calculate_simple_indicators',
    python_callable=calculate_simple_indicators,
    dag=dag,
)

quality_check_task = PythonOperator(
    task_id='simple_data_quality_check',
    python_callable=simple_data_quality_check,
    dag=dag,
)

# 알림 Task (선택사항)
notify_task = BashOperator(
    task_id='notify_completion',
    bash_command='echo "Simple stock data collection completed at $(date)"',
    dag=dag,
)

# Task 의존성 설정
fetch_data_task >> save_data_task >> calculate_indicators_task >> quality_check_task >> notify_task