"""
Manual Collection DAG
수동으로 특정 날짜의 주가 데이터와 시장 지수를 수집하는 DAG

스케줄: 수동 트리거 전용 (자동 스케줄 없음)
특징:
- 원하는 날짜의 데이터를 수동으로 수집
- execution_date 변수로 처리 대상 날짜 관리
- 실패 시 3회 자동 재시도
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import logging
import sys
import os

# Add DAG directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from common_functions import (
    get_db_engine,
    get_execution_date,
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices
)

logger = logging.getLogger(__name__)

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 1),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 3,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='manual_collection_dag',
    default_args=default_args,
    description='수동으로 특정 날짜의 주가 데이터와 시장 지수를 수집',
    schedule_interval=None,  # 수동 트리거 전용 (자동 스케줄 없음)
    catchup=False,
    max_active_runs=1,  # 동시 실행 최대 1개
    tags=['manual', 'collection', 'stock-prices', 'market-indices']
)

# ========================================
# Task 정의
# ========================================

def task_fetch_stock_prices(**context):
    """
    Task: 주가 데이터 수집

    pykrx API를 사용하여 모든 활성 한국 주식의 주가 데이터를 수집합니다.
    """
    target_date = get_execution_date(context)

    logger.info(f"[manual_collection_dag] Fetching stock prices for {target_date}")

    try:
        prices_df = fetch_stock_prices_api(target_date)

        if prices_df.empty:
            logger.warning(f"No stock prices fetched for {target_date}")
            return {'status': 'no_data', 'count': 0}

        # XCom을 통해 다음 Task로 전달
        context['task_instance'].xcom_push(
            key='stock_prices_df',
            value=prices_df.to_json()
        )

        logger.info(f"Successfully fetched {len(prices_df)} stock prices for {target_date}")
        return {'status': 'success', 'count': len(prices_df)}

    except Exception as e:
        logger.error(f"Failed to fetch stock prices for {target_date}: {str(e)}")
        raise

def task_fetch_market_indices(**context):
    """
    Task: 시장 지수 데이터 수집

    KOSPI, KOSDAQ 등의 시장 지수 데이터를 수집합니다.
    """
    target_date = get_execution_date(context)

    logger.info(f"[manual_collection_dag] Fetching market indices for {target_date}")

    try:
        indices_df = fetch_market_indices_api(target_date)

        if indices_df.empty:
            logger.warning(f"No market indices fetched for {target_date}")
            return {'status': 'no_data', 'count': 0}

        # XCom을 통해 다음 Task로 전달
        context['task_instance'].xcom_push(
            key='market_indices_df',
            value=indices_df.to_json()
        )

        logger.info(f"Successfully fetched {len(indices_df)} market indices for {target_date}")
        return {'status': 'success', 'count': len(indices_df)}

    except Exception as e:
        logger.error(f"Failed to fetch market indices for {target_date}: {str(e)}")
        raise

def task_save_to_database(**context):
    """
    Task: 데이터베이스에 저장

    수집한 주가 데이터와 시장 지수를 데이터베이스에 저장합니다.
    """
    target_date = get_execution_date(context)

    logger.info(f"[manual_collection_dag] Saving data to database for {target_date}")

    try:
        engine = get_db_engine()
        task_instance = context['task_instance']

        # XCom에서 데이터 조회
        prices_json = task_instance.xcom_pull(
            task_ids='fetch_stock_prices',
            key='stock_prices_df'
        )
        indices_json = task_instance.xcom_pull(
            task_ids='fetch_market_indices',
            key='market_indices_df'
        )

        saved_count = 0

        # 주가 데이터 저장
        if prices_json:
            import pandas as pd
            prices_df = pd.read_json(prices_json)
            price_count = save_stock_prices(prices_df, target_date, engine)
            saved_count += price_count

        # 시장 지수 저장
        if indices_json:
            import pandas as pd
            indices_df = pd.read_json(indices_json)
            indices_count = save_market_indices(indices_df, target_date, engine)
            saved_count += indices_count

        logger.info(f"Successfully saved {saved_count} records to database for {target_date}")
        return {'status': 'success', 'count': saved_count}

    except Exception as e:
        logger.error(f"Failed to save data to database for {target_date}: {str(e)}")
        raise

# ========================================
# DAG Task 흐름 정의
# ========================================

# Task 생성
fetch_prices = PythonOperator(
    task_id='fetch_stock_prices',
    python_callable=task_fetch_stock_prices,
    provide_context=True,
    dag=dag
)

fetch_indices = PythonOperator(
    task_id='fetch_market_indices',
    python_callable=task_fetch_market_indices,
    provide_context=True,
    dag=dag
)

save_db = PythonOperator(
    task_id='save_to_database',
    python_callable=task_save_to_database,
    provide_context=True,
    dag=dag
)

# Task 의존성 설정
# fetch_prices와 fetch_indices는 병렬 실행, 두 작업 완료 후 save_db 실행
[fetch_prices, fetch_indices] >> save_db
