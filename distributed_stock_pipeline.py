from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
import logging

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 9),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'distributed_stock_pipeline',
    default_args=default_args,
    description='Distributed stock data collection pipeline',
    schedule_interval='0 19 * * 1-5',  # 매일 오후 7시
    catchup=False,
    max_active_runs=1,
    tags=['distributed', 'stock', 'production']
)

def trigger_data_collection(**context):
    """Backend API를 통한 데이터 수집 트리거"""
    import requests

    backend_url = 'http://192.168.219.102:8080/api/data/collect'

    logging.info(f"Triggering data collection via {backend_url}")

    try:
        response = requests.post(backend_url, timeout=600)
        response.raise_for_status()

        result = response.json()
        logging.info(f"Data collection completed: {result}")

        return result
    except Exception as e:
        logging.error(f"Data collection failed: {str(e)}")
        raise

def verify_data_collection(**context):
    """데이터 수집 결과 검증"""
    import requests

    backend_url = 'http://192.168.219.102:8080/api/stocks/list'

    try:
        response = requests.get(backend_url, timeout=30)
        response.raise_for_status()

        stocks = response.json()
        logging.info(f"Verified {len(stocks)} stocks in database")

        return len(stocks)
    except Exception as e:
        logging.error(f"Verification failed: {str(e)}")
        raise

# Tasks
trigger_collection = PythonOperator(
    task_id='trigger_data_collection',
    python_callable=trigger_data_collection,
    provide_context=True,
    dag=dag,
)

verify_collection = PythonOperator(
    task_id='verify_data_collection',
    python_callable=verify_data_collection,
    provide_context=True,
    dag=dag,
)

# Task dependencies
trigger_collection >> verify_collection
