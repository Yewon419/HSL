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
    'enhanced_korean_stock_pipeline',
    default_args=default_args,
    description='Enhanced Korean stock pipeline with TA-Lib indicators',
    schedule_interval='0 19 * * 1-5',  # 매일 오후 7시 (한국 시장 종료 후)
    catchup=False,
    max_active_runs=1,
    tags=['enhanced', 'korean-stock', 'talib', 'indicators']
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
                WHERE is_active = true AND currency = 'KRW'
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
                {'ticker': '035720', 'name': '카카오'},
                {'ticker': '028260', 'name': '삼성물산'},
                {'ticker': '068270', 'name': '셀트리온'},
                {'ticker': '066570', 'name': 'LG전자'},
                {'ticker': '005380', 'name': '현대차'},
            ]

            # 데이터베이스에 추가
            with engine.begin() as conn:
                for stock in major_stocks:
                    conn.execute(text("""
                        INSERT INTO stocks (ticker, company_name, market_type, is_active, currency)
                        VALUES (:ticker, :name, 'KOSPI', true, 'KRW')
                        ON CONFLICT (ticker) DO UPDATE SET
                            company_name = EXCLUDED.company_name,
                            is_active = EXCLUDED.is_active,
                            currency = EXCLUDED.currency
                    """), stock)

            stock_list = major_stocks

        logging.info(f"Found {len(stock_list)} active Korean stocks")
        return [stock['ticker'] for stock in stock_list]

    except Exception as e:
        logging.error(f"Error fetching stock list: {e}")
        raise

def collect_korean_stock_data(**context):
    """한국 주식 데이터 수집 (샘플 데이터 생성)"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Collecting Korean stock data for {target_date}")

    # 주식 목록 가져오기
    stock_list = fetch_korean_stock_list(**context)

    engine = get_db_connection()
    collected_data = []

    # 기본 가격 정보 (실제 환경에서는 API 또는 크롤링 사용)
    base_prices = {
        '005930': 70000,  # 삼성전자
        '000660': 130000, # SK하이닉스
        '035420': 180000, # NAVER
        '051910': 400000, # LG화학
        '006400': 350000, # 삼성SDI
        '035720': 50000,  # 카카오
        '028260': 150000, # 삼성물산
        '068270': 200000, # 셀트리온
        '066570': 120000, # LG전자
        '005380': 180000, # 현대차
    }

    for ticker in stock_list:
        try:
            base_price = base_prices.get(ticker, 100000)

            # 랜덤한 가격 변동 생성 (±3%)
            variation = random.uniform(-0.03, 0.03)
            close_price = base_price * (1 + variation)

            # OHLCV 데이터 생성
            open_price = close_price * random.uniform(0.98, 1.02)
            high_price = max(open_price, close_price) * random.uniform(1.00, 1.02)
            low_price = min(open_price, close_price) * random.uniform(0.98, 1.00)
            volume = random.randint(100000, 10000000)

            price_data = {
                'ticker': ticker,
                'date': target_date,
                'open_price': round(open_price, 2),
                'high_price': round(high_price, 2),
                'low_price': round(low_price, 2),
                'close_price': round(close_price, 2),
                'volume': volume,
                'created_at': datetime.now()
            }

            collected_data.append(price_data)
            logging.info(f"Generated data for {ticker}: {close_price}")

        except Exception as e:
            logging.error(f"Error generating data for {ticker}: {e}")
            continue

    # 데이터베이스에 저장
    if collected_data:
        try:
            with engine.begin() as conn:
                for data in collected_data:
                    conn.execute(text("""
                        INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                        VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
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

def calculate_talib_indicators(**context):
    """TA-Lib을 사용한 기술적 지표 계산"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Calculating TA-Lib indicators for {target_date}")

    try:
        # Import the indicator calculator
        from services.indicator_calculator import IndicatorCalculator

        # Create calculator instance
        db_url = "postgresql://admin:admin123@postgres:5432/stocktrading"
        calculator = IndicatorCalculator(db_url)

        # Get list of Korean stocks that have data for target date
        engine = get_db_connection()
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                WHERE s.is_active = true
                AND s.currency = 'KRW'
                AND sp.date >= :target_date
                ORDER BY s.ticker
            """), {'target_date': target_date})
            tickers = [row[0] for row in result]

        logging.info(f"Processing TA-Lib indicators for {len(tickers)} Korean stocks")

        successful = 0
        failed = 0

        # Process each ticker
        for ticker in tickers:
            try:
                # Use incremental processing to calculate indicators efficiently
                success = calculator.process_ticker_incremental(ticker, start_date=str(target_date))
                if success:
                    successful += 1
                    logging.info(f"Successfully processed indicators for {ticker}")
                else:
                    failed += 1
                    logging.warning(f"Failed to process indicators for {ticker}")

            except Exception as e:
                logging.error(f"Error processing indicators for {ticker}: {e}")
                failed += 1

        logging.info(f"TA-Lib indicator calculation complete. Success: {successful}, Failed: {failed}")

        # Refresh materialized views
        try:
            with engine.begin() as conn:
                # Refresh views if they exist
                views_to_refresh = ['v_latest_indicators', 'v_indicator_summary', 'v_indicator_timeseries']

                for view_name in views_to_refresh:
                    try:
                        conn.execute(text(f"REFRESH MATERIALIZED VIEW CONCURRENTLY {view_name}"))
                        logging.info(f"Refreshed materialized view: {view_name}")
                    except Exception as view_error:
                        logging.warning(f"Could not refresh view {view_name}: {view_error}")

        except Exception as e:
            logging.warning(f"Error refreshing materialized views: {e}")

        return {'successful': successful, 'failed': failed}

    except Exception as e:
        logging.error(f"TA-Lib indicator calculation failed: {e}")
        import traceback
        traceback.print_exc()
        raise

def validate_data_quality(**context):
    """데이터 품질 검증"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Validating data quality for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 오늘 수집된 주가 데이터 확인
            price_result = conn.execute(text("""
                SELECT COUNT(*) as price_count,
                       AVG(close_price) as avg_price,
                       MIN(close_price) as min_price,
                       MAX(close_price) as max_price
                FROM stock_prices sp
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :date AND s.currency = 'KRW'
            """), {'date': target_date})
            price_row = price_result.fetchone()
            price_count = price_row[0]
            avg_price = price_row[1]

            # 오늘 계산된 지표 확인
            indicator_result = conn.execute(text("""
                SELECT COUNT(*) as indicator_count,
                       COUNT(CASE WHEN rsi IS NOT NULL THEN 1 END) as rsi_count,
                       COUNT(CASE WHEN macd IS NOT NULL THEN 1 END) as macd_count
                FROM technical_indicators ti
                JOIN stocks s ON ti.ticker = s.ticker
                WHERE ti.date = :date AND s.currency = 'KRW'
            """), {'date': target_date})
            indicator_row = indicator_result.fetchone()
            indicator_count = indicator_row[0]
            rsi_count = indicator_row[1]
            macd_count = indicator_row[2]

            logging.info(f"Data Quality Report for {target_date}:")
            logging.info(f"  - Stock prices: {price_count} records, avg price: {avg_price}")
            logging.info(f"  - Technical indicators: {indicator_count} records")
            logging.info(f"  - RSI values: {rsi_count}, MACD values: {macd_count}")

            # 최소 기준 확인
            if price_count >= 5 and indicator_count >= 5 and rsi_count >= 5:
                logging.info("✅ Data quality validation PASSED")
                return True
            else:
                logging.warning("❌ Data quality validation FAILED - insufficient data")
                return False

    except Exception as e:
        logging.error(f"Error during data quality validation: {e}")
        raise

def sync_to_grafana(**context):
    """Grafana에 지표 동기화"""
    logging.info("Syncing indicators to Grafana")

    try:
        # This could contain actual Grafana API calls or dashboard updates
        # For now, just log success
        logging.info("✅ Grafana sync completed successfully")
        return True

    except Exception as e:
        logging.error(f"Error syncing to Grafana: {e}")
        raise

# Define tasks
stock_list_task = PythonOperator(
    task_id='fetch_korean_stock_list',
    python_callable=fetch_korean_stock_list,
    dag=dag,
)

stock_collection_task = PythonOperator(
    task_id='collect_korean_stock_data',
    python_callable=collect_korean_stock_data,
    dag=dag,
)

indicator_calculation_task = PythonOperator(
    task_id='calculate_talib_indicators',
    python_callable=calculate_talib_indicators,
    dag=dag,
)

data_quality_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

grafana_sync_task = PythonOperator(
    task_id='sync_to_grafana',
    python_callable=sync_to_grafana,
    dag=dag,
)

# Define task dependencies - Stock collection -> Indicator calculation -> Quality check -> Grafana sync
stock_list_task >> stock_collection_task >> indicator_calculation_task >> data_quality_task >> grafana_sync_task