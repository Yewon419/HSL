"""
Generate Daily Collection DAG
매일 16:00 UTC(오전 1시)에 실행되어 collection_log 테이블에 오늘 날짜의 레코드를 생성합니다.

스케줄: 0 16 * * 1-5 (매일 16:00 UTC, 평일만)
목적: collection_log에 오늘 항목을 생성하여 daily_collection_dag이 참조할 수 있게 함
"""

from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python import PythonOperator
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
    logger
)

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 20),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # 이 DAG는 재시도 없음
}

dag = DAG(
    dag_id='generate_daily_collection_dag',
    default_args=default_args,
    description='Generate daily collection log entry at 16:00 UTC',
    schedule_interval='0 16 * * 1-5',  # 매일 16:00 UTC (평일만)
    catchup=False,
    tags=['collection', 'daily', 'generator']
)

# ========================================
# Task 정의
# ========================================

def generate_daily_collection(**context):
    """
    Task: 오늘 collection_log 엔트리 생성

    이 함수는 매일 16:00 UTC에 실행되어 collection_log 테이블에
    오늘 날짜의 레코드를 생성합니다.
    """
    target_date = date.today()
    logger.info(f"===== generate_daily_collection_dag: {target_date} =====")

    try:
        engine = get_db_engine()

        # 기존 로그 확인
        status = get_collection_status(target_date, engine)

        if status['status'] == 'found':
            logger.info(f"Collection log already exists for {target_date}")
            logger.info(f"Current status: overall={status['overall_status']}, price={status['price_status']}, indices={status['indices_status']}")
            return {
                'status': 'already_exists',
                'target_date': str(target_date),
                'overall_status': status['overall_status']
            }

        # 신규 로그 생성
        logger.info(f"Creating new collection log entry for {target_date}")
        update_collection_log_price(
            target_date=target_date,
            status='pending',
            count=None,
            error=None,
            engine=engine
        )

        logger.info(f"Successfully created collection log for {target_date}")
        return {
            'status': 'created',
            'target_date': str(target_date),
            'message': 'Collection log entry created, ready for daily_collection_dag'
        }

    except Exception as e:
        logger.error(f"Error generating daily collection: {e}", exc_info=True)
        raise

# ========================================
# DAG Task 흐름 정의
# ========================================

generate_task = PythonOperator(
    task_id='generate_daily_collection',
    python_callable=generate_daily_collection,
    provide_context=True,
    dag=dag
)

# Task 흐름
generate_task
