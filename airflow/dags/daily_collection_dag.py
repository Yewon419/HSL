"""
Daily Collection DAG
매일 09:30 UTC (오후 6시 30분 KST)에 실행되어 주가/지수를 수집합니다.
- 정해진 시간에 한 번만 실행
- 스케줄: 30 9 * * 1-5 (매일 09:30 UTC, 평일만)
- UTC 09:30 = 한국시간 오후 6시 30분 (KST+9)
"""

from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import logging
import sys
import os

# Add DAG directory to path
sys.path.insert(0, os.path.dirname(__file__))
sys.path.append('/app')

from common_functions import (
    get_db_engine,
    get_collection_status,
    update_collection_log_price,
    update_collection_log_indices,
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices,
    logger
)

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 20),  # 과거 날짜로 설정 (현재 시간 이전 스케줄 포함)
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # 개별 task 재시도 없음 (DAG 레벨에서 관리)
}

dag = DAG(
    dag_id='daily_collection_dag',
    default_args=default_args,
    description='Daily collect stock prices and market indices at 09:30 UTC (18:30 KST)',
    schedule_interval='30 9 * * 1-5',  # 매일 09:30 UTC (한국시간 18시 30분, 평일만)
    catchup=False,
    is_paused_upon_creation=False,  # DAG 활성화
    tags=['collection', 'daily', 'prices', 'indices']
)

# ========================================
# Task 정의
# ========================================

def check_and_decide_collection(**context):
    """
    Task: 현재 시간 확인 및 수집 여부 결정

    18:30~23:59 KST - collection_log 확인 후 수집/재시도/스킵 결정
    기타 시간 - 스킵
    """
    import pytz

    target_date = date.today()

    # Get current time in KST (Asia/Seoul)
    kst_tz = pytz.timezone('Asia/Seoul')
    current_time_kst = datetime.now(kst_tz)
    current_hour = current_time_kst.hour
    current_minute = current_time_kst.minute
    logger.info(f"===== daily_collection_dag check: {target_date}, {current_hour}:{current_minute:02d} KST =====")

    try:
        # 18:30(한국시간 오후 6시 30분) 이전이면 스킵
        current_time_minutes = current_hour * 60 + current_minute
        collection_time_minutes = 18 * 60 + 30  # 18:30 KST
        if current_time_minutes < collection_time_minutes:
            logger.info(f"Skipping: current time ({current_hour}:{current_minute:02d} KST) is before 18:30 KST")
            return {'action': 'skip', 'reason': 'before_collection_time'}

        engine = get_db_engine()
        status = get_collection_status(target_date, engine)

        logger.info(f"Collection status: {status}")

        # 수집 로그 없음 - 첫 실행
        if status['status'] == 'not_found':
            logger.info(f"First run for {target_date}")
            return {'action': 'execute', 'reason': 'first_run'}

        # 완료됨 - 스킵
        if status['overall_status'] == 'success':
            logger.info(f"Collection already complete for {target_date}")
            return {'action': 'skip', 'reason': 'already_complete'}

        # 실패했지만 재시도 가능
        if status['overall_status'] in ['failed', 'partial']:
            max_retries = 3
            price_retries = status.get('price_retry_count', 0) or 0
            indices_retries = status.get('indices_retry_count', 0) or 0
            max_price_retries = max_retries if status['price_status'] == 'failed' else 0
            max_indices_retries = max_retries if status['indices_status'] == 'failed' else 0

            # 재시도 가능 확인
            price_can_retry = price_retries < max_retries if status['price_status'] == 'failed' else False
            indices_can_retry = indices_retries < max_retries if status['indices_status'] == 'failed' else False

            if price_can_retry or indices_can_retry:
                logger.info(f"Retry eligible for {target_date}: price_retries={price_retries}, indices_retries={indices_retries}")
                return {'action': 'retry', 'reason': 'retry_needed', 'price_retries': price_retries, 'indices_retries': indices_retries}
            else:
                logger.warning(f"Max retries exceeded for {target_date}. Manual intervention required.")
                return {'action': 'skip', 'reason': 'max_retries_exceeded'}

        # 기타 상태 (pending, retrying)
        logger.info(f"Collection in progress for {target_date}, status={status['overall_status']}")
        return {'action': 'execute', 'reason': 'continue_execution'}

    except Exception as e:
        logger.error(f"Error checking collection status: {e}", exc_info=True)
        raise

def fetch_and_save_stock_prices(**context):
    """
    Task Group: 주가 수집 및 저장

    1. pykrx에서 주가 데이터 수집
    2. 데이터베이스에 저장
    3. 상태 로그 업데이트
    """
    target_date = date.today()
    logger.info(f"Fetching stock prices for {target_date}...")

    try:
        engine = get_db_engine()

        # pykrx에서 수집 (KOSPI + KOSDAQ)
        prices_df = fetch_stock_prices_api(target_date, engine)

        if prices_df.empty:
            logger.warning(f"No stock prices fetched for {target_date}")
            update_collection_log_price(
                target_date=target_date,
                status='failed',
                count=0,
                error='No data returned from API',
                engine=engine
            )
            raise Exception("No stock prices data fetched")

        # DB에 저장
        saved_count = save_stock_prices(prices_df, target_date, engine)
        logger.info(f"Successfully saved {saved_count} stock prices for {target_date}")

        # 상태 업데이트 (실패해도 무시)
        try:
            update_collection_log_price(
                target_date=target_date,
                status='success',
                count=saved_count,
                error=None,
                engine=engine
            )
        except Exception as log_error:
            logger.warning(f"Failed to update collection log: {log_error}")

        return {
            'status': 'success',
            'target_date': str(target_date),
            'prices_saved': saved_count
        }

    except Exception as e:
        logger.error(f"Error fetching/saving stock prices: {e}", exc_info=True)
        try:
            update_collection_log_price(
                target_date=target_date,
                status='retrying',
                count=None,
                error=str(e),
                engine=engine
            )
        except Exception as log_error:
            logger.warning(f"Failed to update collection log: {log_error}")
        raise

def fetch_and_save_market_indices(**context):
    """
    Task Group: 지수 수집 및 저장

    1. pykrx에서 지수 데이터 수집 (KOSPI, KOSDAQ)
    2. 데이터베이스에 저장
    3. 상태 로그 업데이트
    """
    target_date = date.today()
    logger.info(f"Fetching market indices for {target_date}...")

    try:
        engine = get_db_engine()

        # pykrx에서 수집
        indices_df = fetch_market_indices_api(target_date)

        if indices_df.empty:
            logger.warning(f"No market indices fetched for {target_date}")
            update_collection_log_indices(
                target_date=target_date,
                status='failed',
                count=0,
                error='No data returned from API',
                engine=engine
            )
            raise Exception("No market indices data fetched")

        # DB에 저장
        saved_count = save_market_indices(indices_df, target_date, engine)
        logger.info(f"Successfully saved {saved_count} market indices for {target_date}")

        # 상태 업데이트 (실패해도 무시)
        try:
            update_collection_log_indices(
                target_date=target_date,
                status='success',
                count=saved_count,
                error=None,
                engine=engine
            )
        except Exception as log_error:
            logger.warning(f"Failed to update collection log: {log_error}")

        return {
            'status': 'success',
            'target_date': str(target_date),
            'indices_saved': saved_count
        }

    except Exception as e:
        logger.error(f"Error fetching/saving market indices: {e}", exc_info=True)
        try:
            update_collection_log_indices(
                target_date=target_date,
                status='retrying',
                count=None,
                error=str(e),
                engine=engine
            )
        except Exception as log_error:
            logger.warning(f"Failed to update collection log: {log_error}")
        raise

# ========================================
# DAG Task 흐름 정의
# ========================================

check_task = PythonOperator(
    task_id='check_and_decide',
    python_callable=check_and_decide_collection,
    provide_context=True,
    dag=dag
)

with TaskGroup("price_collection", dag=dag) as price_group:
    price_fetch_save = PythonOperator(
        task_id='fetch_and_save_prices',
        python_callable=fetch_and_save_stock_prices,
        provide_context=True,
        dag=dag
    )

with TaskGroup("indices_collection", dag=dag) as indices_group:
    indices_fetch_save = PythonOperator(
        task_id='fetch_and_save_indices',
        python_callable=fetch_and_save_market_indices,
        provide_context=True,
        dag=dag
    )

# Task 의존성: check_task 완료 후 병렬로 price/indices 수집
check_task >> [price_group, indices_group]
