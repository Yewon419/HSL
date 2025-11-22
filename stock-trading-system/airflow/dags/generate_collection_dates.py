#!/usr/bin/env python3
"""
누락된 거래일 감지 및 수집 날짜 생성 DAG

역할:
1. DB에서 수집되지 않은 거래일(평일) 찾기
2. 각 누락된 날짜별로 korean_stock_data_collection DAG 트리거
3. Airflow 기동 시 자동 실행되어 누락 데이터 보완

스케줄: 매일 오후 7시 (장 마감 후)
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator
from airflow.utils.dates import days_ago
from datetime import datetime, timedelta
import logging
import pandas as pd
from sqlalchemy import create_engine, text
import os

# 스케줄 설정 (config/schedules.py 참조)
SCHEDULE_MISSING_DATE_DETECTION = '0 19 * * *'  # 매일 오후 7시

logger = logging.getLogger(__name__)

# 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def get_db_connection():
    """데이터베이스 연결 생성"""
    import os
    host = os.getenv('DB_HOST', 'postgres')
    DATABASE_URL = f"postgresql://admin:admin123@{host}:5432/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
    return engine

def get_missing_trading_dates(**context):
    """
    수집되지 않은 거래일 찾기
    - 최근 30일 이내의 평일(월-금) 중
    - stock_prices에 데이터가 없는 날짜
    """
    engine = get_db_connection()

    # 30일 전부터 어제까지의 날짜 범위
    end_date = datetime.now().date() - timedelta(days=1)  # 어제까지
    start_date = end_date - timedelta(days=30)  # 30일 전부터

    logger.info(f"검색 기간: {start_date} ~ {end_date}")

    with engine.connect() as conn:
        # 이미 수집된 날짜 조회
        result = conn.execute(text("""
            SELECT DISTINCT date
            FROM stock_prices
            WHERE date >= :start_date AND date <= :end_date
            ORDER BY date
        """), {'start_date': start_date, 'end_date': end_date})

        collected_dates = {row.date for row in result}
        logger.info(f"이미 수집된 날짜: {len(collected_dates)}개")

    # 전체 날짜 범위 생성 (평일만)
    all_dates = pd.date_range(start=start_date, end=end_date, freq='B')  # B = Business days (평일)
    all_dates_set = {date.date() for date in all_dates}

    # 누락된 날짜 = 전체 평일 - 수집된 날짜
    missing_dates = sorted(all_dates_set - collected_dates)

    logger.info("="*80)
    logger.info(f"전체 거래일(평일): {len(all_dates_set)}개")
    logger.info(f"수집 완료: {len(collected_dates)}개")
    logger.info(f"누락된 날짜: {len(missing_dates)}개")

    if missing_dates:
        logger.info("누락된 날짜 목록:")
        for date in missing_dates:
            logger.info(f"  - {date}")
    else:
        logger.info("누락된 날짜 없음!")
    logger.info("="*80)

    # XCom에 저장
    missing_dates_str = [date.strftime('%Y-%m-%d') for date in missing_dates]
    context['task_instance'].xcom_push(key='missing_dates', value=missing_dates_str)
    context['task_instance'].xcom_push(key='missing_count', value=len(missing_dates))

    return missing_dates_str

def trigger_collection_for_dates(**context):
    """
    누락된 각 날짜별로 korean_stock_data_collection DAG 트리거
    """
    from airflow.api.common.trigger_dag import trigger_dag

    missing_dates = context['task_instance'].xcom_pull(key='missing_dates', task_ids='detect_missing_dates')

    if not missing_dates:
        logger.info("수집할 날짜가 없습니다.")
        return 0

    logger.info(f"총 {len(missing_dates)}개 날짜에 대해 수집 DAG 트리거 시작")

    triggered_count = 0

    for date_str in missing_dates:
        try:
            # korean_stock_data_collection DAG 트리거
            dag_run_id = f"collect_{date_str.replace('-', '')}"

            trigger_dag(
                dag_id='korean_stock_data_collection',
                run_id=dag_run_id,
                conf={'target_date': date_str},
                execution_date=None,
                replace_microseconds=False,
            )

            triggered_count += 1
            logger.info(f"Triggered collection for {date_str} (run_id: {dag_run_id})")

        except Exception as e:
            logger.error(f"Failed to trigger collection for {date_str}: {e}")
            continue

    logger.info(f"Collection trigger completed: {triggered_count}/{len(missing_dates)} DAGs triggered")
    return triggered_count

# DAG 정의
with DAG(
    'generate_collection_dates',
    default_args=default_args,
    description='누락된 거래일 감지 및 수집 DAG 트리거',
    schedule_interval=SCHEDULE_MISSING_DATE_DETECTION,  # 매일 오후 7시
    start_date=datetime(2025, 10, 1),
    catchup=False,
    tags=['data-collection', 'scheduler'],
) as dag:

    # Task 1: 누락된 날짜 감지
    detect_missing_dates = PythonOperator(
        task_id='detect_missing_dates',
        python_callable=get_missing_trading_dates,
    )

    # Task 2: 누락된 날짜별로 수집 DAG 트리거
    trigger_tasks = PythonOperator(
        task_id='trigger_collection_tasks',
        python_callable=trigger_collection_for_dates,
    )

    # 의존성 설정
    detect_missing_dates >> trigger_tasks
