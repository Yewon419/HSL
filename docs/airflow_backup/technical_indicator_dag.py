"""
Technical Indicator DAG
매일 기술적 지표를 자동으로 연산하는 DAG

스케줄: 매일 09:00 UTC (한국 시간 18:00 - 오후 6시)
특징:
- daily_collection_dag 완료 후 자동 트리거
- 모든 활성 티커에 대해 지표 연산
- 실패 시 2회 자동 재시도
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.utils.task_group import TaskGroup
import logging
import sys
import os
from sqlalchemy import text

# Add DAG directory to path for imports
sys.path.insert(0, os.path.dirname(__file__))

from common_functions import (
    get_db_engine,
    get_execution_date,
    get_all_tickers,
    calculate_indicators_for_ticker
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
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    dag_id='technical_indicator_dag',
    default_args=default_args,
    description='매일 기술적 지표(RSI, MACD, SMA, Bollinger Band)를 자동으로 연산',
    schedule_interval='0 9 * * 1-5',  # 평일(월~금) 09:00 UTC (한국 시간 18:00 - 오후 6시) - 주말/공휴일 제외
    catchup=False,  # 과거 날짜는 수동으로 generate_task_dag 사용
    max_active_runs=1,  # 동시 실행 최대 1개
    tags=['production', 'daily', 'indicators', 'technical-analysis']
)

# ========================================
# Task 정의
# ========================================

def task_calculate_indicators(**context):
    """
    Task: 기술적 지표 연산

    모든 활성 티커에 대해 RSI, MACD, SMA, Bollinger Bands 등을 계산합니다.
    배치 처리로 성능 최적화
    """
    target_date = get_execution_date(context)

    logger.info(f"[technical_indicator_dag] Calculating indicators for {target_date}")

    try:
        engine = get_db_engine()

        # 해당 날짜의 모든 주가 데이터 티커 조회
        query = text("""
            SELECT DISTINCT ticker
            FROM stock_prices
            WHERE date = :target_date
            ORDER BY ticker
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {'target_date': target_date})
            tickers = [row[0] for row in result.fetchall()]

        logger.info(f"Found {len(tickers)} tickers with price data for {target_date}")

        if not tickers:
            logger.warning(f"No price data found for {target_date}")
            return {'status': 'no_data', 'calculated': 0, 'saved': 0}

        # 배치 처리로 성능 최적화 (배치 크기: 100)
        batch_size = 100
        success_count = 0
        total_batches = (len(tickers) + batch_size - 1) // batch_size

        for batch_idx in range(0, len(tickers), batch_size):
            batch_tickers = tickers[batch_idx:batch_idx + batch_size]
            current_batch = (batch_idx // batch_size) + 1

            logger.info(f"Processing batch {current_batch}/{total_batches} ({len(batch_tickers)} tickers)")

            # 배치의 모든 지표 계산
            batch_indicators = []
            for ticker in batch_tickers:
                try:
                    indicators = calculate_indicators_for_ticker(ticker, target_date, engine)
                    if indicators:
                        batch_indicators.append(indicators)
                except Exception as e:
                    logger.warning(f"Failed to calculate indicators for {ticker}: {str(e)}")
                    continue

            # 배치를 한 번에 저장
            if batch_indicators:
                try:
                    with engine.begin() as conn:
                        for indicators in batch_indicators:
                            conn.execute(text("""
                                INSERT INTO technical_indicators
                                (ticker, date, rsi, macd, macd_signal, ma_20, bollinger_upper, bollinger_lower, created_at)
                                VALUES (:ticker, :date, :rsi, :macd, :macd_signal, :ma_20, :bollinger_upper, :bollinger_lower, :created_at)
                                ON CONFLICT (ticker, date) DO UPDATE SET
                                    rsi = EXCLUDED.rsi,
                                    macd = EXCLUDED.macd,
                                    macd_signal = EXCLUDED.macd_signal,
                                    ma_20 = EXCLUDED.ma_20,
                                    bollinger_upper = EXCLUDED.bollinger_upper,
                                    bollinger_lower = EXCLUDED.bollinger_lower
                            """), {
                                'ticker': indicators['ticker'],
                                'date': indicators['date'],
                                'rsi': indicators.get('rsi'),
                                'macd': indicators.get('macd'),
                                'macd_signal': indicators.get('macd_signal'),
                                'ma_20': indicators.get('sma_20'),  # 이름 매핑
                                'bollinger_upper': indicators.get('bb_upper'),  # 이름 매핑
                                'bollinger_lower': indicators.get('bb_lower'),  # 이름 매핑
                                'created_at': datetime.now()
                            })
                    success_count += len(batch_indicators)
                    logger.info(f"✓ Batch {current_batch} saved: {len(batch_indicators)} indicators")
                except Exception as e:
                    logger.error(f"Failed to save batch {current_batch}: {str(e)}")

        logger.info(f"✓ Successfully calculated and saved {success_count} indicators for {target_date}")

        return {
            'status': 'success',
            'calculated': success_count,
            'saved': success_count
        }

    except Exception as e:
        logger.error(f"Failed to calculate indicators for {target_date}: {str(e)}")
        raise

def task_verify_results(**context):
    """
    Task: 계산 결과 검증

    계산된 지표가 정상적으로 저장되었는지 확인합니다.
    """
    target_date = get_execution_date(context)

    logger.info(f"[technical_indicator_dag] Verifying indicators for {target_date}")

    try:
        engine = get_db_engine()

        # 해당 날짜의 저장된 지표 개수 확인
        query = text("""
            SELECT COUNT(*) as count
            FROM technical_indicators
            WHERE date = :target_date
        """)

        with engine.connect() as conn:
            result = conn.execute(query, {'target_date': target_date})
            count = result.scalar()

        logger.info(f"✓ Verification complete: {count} indicators saved for {target_date}")

        return {'status': 'success', 'count': count}

    except Exception as e:
        logger.error(f"Failed to verify indicators for {target_date}: {str(e)}")
        raise

# ========================================
# DAG Task 흐름 정의
# ========================================

# Task 생성
calc_ind = PythonOperator(
    task_id='calculate_indicators',
    python_callable=task_calculate_indicators,
    provide_context=True,
    dag=dag
)

verify = PythonOperator(
    task_id='verify_results',
    python_callable=task_verify_results,
    provide_context=True,
    dag=dag
)

# Task 의존성 설정
# 직렬 실행: calculate_indicators -> verify_results
calc_ind >> verify
