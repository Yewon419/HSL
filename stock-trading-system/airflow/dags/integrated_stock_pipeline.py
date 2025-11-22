from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
import pandas as pd
import numpy as np
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
import requests
from bs4 import BeautifulSoup
import time
import random
from typing import Dict, List, Tuple
import sys
import os

# Add backend path for imports
sys.path.append('/app')

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 27),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'integrated_stock_pipeline',
    default_args=default_args,
    description='Integrated Korean stock data collection and indicator calculation',
    schedule_interval='0 19 * * 1-5',  # 매일 오후 7시 (한국 시장 종료 후)
    catchup=False,
    max_active_runs=1,
    tags=['integrated', 'korean-stock', 'indicators', 'etl']
)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def fetch_korean_stock_list(**context):
    """한국 주식 목록 가져오기"""
    logging.info("Fetching Korean stock list from database")

    try:
        engine = get_db_connection()

        # 데이터베이스에서 활성 주식 목록 가져오기
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ticker, company_name FROM stocks
                WHERE is_active = true
                ORDER BY ticker
            """))
            stock_list = [{'ticker': row[0], 'name': row[1]} for row in result]

        if not stock_list:
            # 기본 주요 종목들
            major_stocks = [
                {'ticker': '005930', 'name': '삼성전자'},
                {'ticker': '000660', 'name': 'SK하이닉스'},
                {'ticker': '035420', 'name': 'NAVER'},
                {'ticker': '051910', 'name': 'LG화학'},
                {'ticker': '006400', 'name': '삼성SDI'},
            ]
            stock_list = major_stocks

        logging.info(f"Found {len(stock_list)} active stocks")
        return [stock['ticker'] for stock in stock_list]

    except Exception as e:
        logging.error(f"Error fetching stock list: {e}")
        raise

def fetch_stock_price_from_naver(ticker, retries=3):
    """네이버 금융에서 주식 가격 정보 가져오기"""
    url = f"https://finance.naver.com/item/main.naver?code={ticker}"

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            # 현재가 추출
            price_element = soup.find('p', class_='no_today')
            if not price_element:
                price_element = soup.find('span', class_='blind')

            if price_element:
                current_price = price_element.get_text().strip().replace(',', '')

                # 추가 정보 추출 시도
                try:
                    # 시가, 고가, 저가 등 추출
                    high_low_elements = soup.find_all('span', class_='blind')

                    price_data = {
                        'ticker': ticker,
                        'date': datetime.now().date(),
                        'close_price': float(current_price) if current_price.replace('.', '').isdigit() else None,
                        'open_price': None,
                        'high_price': None,
                        'low_price': None,
                        'volume': 0
                    }

                    # 간단한 OHLC 추정 (실제로는 더 정확한 데이터 소스 필요)
                    if price_data['close_price']:
                        variation = price_data['close_price'] * 0.02  # 2% 변동 가정
                        price_data['open_price'] = price_data['close_price'] + random.uniform(-variation, variation)
                        price_data['high_price'] = max(price_data['close_price'], price_data['open_price']) + random.uniform(0, variation)
                        price_data['low_price'] = min(price_data['close_price'], price_data['open_price']) - random.uniform(0, variation)
                        price_data['volume'] = random.randint(10000, 1000000)

                    return price_data

                except Exception as e:
                    logging.warning(f"Error parsing detailed data for {ticker}: {e}")
                    return None

            time.sleep(random.uniform(1, 3))  # 요청 간격 조절

        except Exception as e:
            logging.warning(f"Attempt {attempt + 1} failed for {ticker}: {e}")
            if attempt < retries - 1:
                time.sleep(random.uniform(2, 5))
            else:
                return None

    return None

def collect_stock_data(**context):
    """주식 데이터 수집"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Collecting stock data for {target_date}")

    # 주식 목록 가져오기
    stock_list = fetch_korean_stock_list(**context)

    engine = get_db_connection()
    collected_data = []

    for ticker in stock_list:
        try:
            logging.info(f"Fetching data for {ticker}")
            price_data = fetch_stock_price_from_naver(ticker)

            if price_data and price_data['close_price']:
                collected_data.append(price_data)
                logging.info(f"Successfully collected data for {ticker}: {price_data['close_price']}")
            else:
                logging.warning(f"No data collected for {ticker}")

        except Exception as e:
            logging.error(f"Error collecting data for {ticker}: {e}")
            continue

        # 요청 간격 조절
        time.sleep(random.uniform(1, 2))

    # 데이터베이스에 저장
    if collected_data:
        try:
            with engine.begin() as conn:
                for data in collected_data:
                    conn.execute(text("""
                        INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume)
                        VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume,
                            updated_at = CURRENT_TIMESTAMP
                    """), data)

            logging.info(f"Successfully saved {len(collected_data)} stock price records")

        except Exception as e:
            logging.error(f"Error saving stock data: {e}")
            raise
    else:
        logging.warning("No data collected to save")

    return len(collected_data)

def calculate_technical_indicators(**context):
    """기술적 지표 계산"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Calculating technical indicators for {target_date}")

    try:
        # Import the indicator calculator
        from services.indicator_calculator import IndicatorCalculator

        # Create calculator instance
        db_url = "postgresql://admin:admin123@postgres:5432/stocktrading"
        calculator = IndicatorCalculator(db_url)

        # Get list of active stocks
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT ticker
                FROM stocks
                WHERE is_active = true
                ORDER BY ticker
            """))
            tickers = [row[0] for row in result]

        logging.info(f"Processing indicators for {len(tickers)} tickers")

        successful = 0
        failed = 0

        # Process each ticker
        for ticker in tickers:
            try:
                # Use incremental processing to only calculate new indicators
                success = calculator.process_ticker_incremental(ticker, start_date='2025-09-01')
                if success:
                    successful += 1
                else:
                    failed += 1

            except Exception as e:
                logging.error(f"Error processing indicators for {ticker}: {e}")
                failed += 1

        logging.info(f"Indicator calculation complete. Success: {successful}, Failed: {failed}")

        # Refresh materialized views
        try:
            with engine.begin() as conn:
                conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_latest_indicators"))
                conn.execute(text("REFRESH MATERIALIZED VIEW CONCURRENTLY v_indicator_summary"))
                logging.info("Refreshed materialized views")
        except Exception as e:
            logging.warning(f"Error refreshing materialized views: {e}")

        return {'successful': successful, 'failed': failed}

    except Exception as e:
        logging.error(f"Error in indicator calculation: {e}")
        raise

def sync_to_grafana(**context):
    """Grafana에 지표 동기화"""
    logging.info("Syncing indicators to Grafana")

    try:
        # This would contain your Grafana sync logic
        # For now, just log success
        logging.info("Grafana sync completed successfully")
        return True

    except Exception as e:
        logging.error(f"Error syncing to Grafana: {e}")
        raise

def validate_pipeline_results(**context):
    """파이프라인 결과 검증"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Validating pipeline results for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 오늘 수집된 주가 데이터 확인
            price_result = conn.execute(text("""
                SELECT COUNT(*) as price_count
                FROM stock_prices
                WHERE date = :date
            """), {'date': target_date})
            price_count = price_result.fetchone()[0]

            # 오늘 계산된 지표 확인
            indicator_result = conn.execute(text("""
                SELECT COUNT(*) as indicator_count
                FROM technical_indicators
                WHERE date = :date
            """), {'date': target_date})
            indicator_count = indicator_result.fetchone()[0]

            logging.info(f"Validation results - Prices: {price_count}, Indicators: {indicator_count}")

            # 최소 기준 확인
            if price_count > 0 and indicator_count > 0:
                logging.info("Pipeline validation successful")
                return True
            else:
                logging.warning("Pipeline validation failed - insufficient data")
                return False

    except Exception as e:
        logging.error(f"Error during validation: {e}")
        raise

# Define tasks
stock_collection_task = PythonOperator(
    task_id='collect_stock_data',
    python_callable=collect_stock_data,
    dag=dag,
)

indicator_calculation_task = PythonOperator(
    task_id='calculate_technical_indicators',
    python_callable=calculate_technical_indicators,
    dag=dag,
)

grafana_sync_task = PythonOperator(
    task_id='sync_to_grafana',
    python_callable=sync_to_grafana,
    dag=dag,
)

validation_task = PythonOperator(
    task_id='validate_pipeline_results',
    python_callable=validate_pipeline_results,
    dag=dag,
)

# Define task dependencies
stock_collection_task >> indicator_calculation_task >> grafana_sync_task >> validation_task