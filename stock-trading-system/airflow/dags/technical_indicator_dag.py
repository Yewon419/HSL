"""
Technical Indicator DAG
daily_collection_dag 완료 후에 실행되어 기술적 지표를 계산합니다.

실행 흐름:
1. daily_collection_dag (21:30 UTC / 06:30 KST) 실행 및 완료 대기
2. ExternalTaskSensor로 daily_collection_dag 완료 감지
3. 기술 지표 계산 및 저장

기능:
1. daily_collection_dag 완료 대기 (ExternalTaskSensor)
2. 수집 완료 확인 (collection_log.overall_status='success')
3. 200일 역사 데이터로 기술 지표 계산
4. 계산된 지표를 technical_indicators 테이블에 저장
5. 실패 시 자동 재시도 (최대 3회)

최신 수정: 2025-11-10 (daily_collection_dag 완료 후 실행으로 변경)
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
    get_indicator_status,
    update_indicator_log,
    get_all_tickers,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_bollinger_bands,
    save_technical_indicators,
    logger
)
import pandas as pd

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 10),  # 오늘 날짜로 설정
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 0,  # DAG 레벨에서 재시도 관리
}

dag = DAG(
    dag_id='technical_indicator_dag',
    default_args=default_args,
    description='Daily calculate technical indicators after daily_collection_dag completes',
    schedule_interval=None,  # 수동 스케줄 제거 (daily_collection_dag 완료 후 실행)
    catchup=False,
    is_paused_upon_creation=False,
    tags=['indicators', 'technical', 'daily']
)

# ========================================
# Task 정의
# ========================================

def check_and_calculate_indicators(**context):
    """
    Task: 수집 완료 확인 및 지표 계산 수행

    1. daily_collection_dag 완료 후 자동 실행 (ExternalTaskSensor 대기 완료)
    2. collection_log에서 overall_status='success' 확인
    3. 지표 계산 상태 확인
    4. 필요하면 지표 계산 수행
    """
    target_date = date.today()
    logger.info(f"===== technical_indicator_dag check: {target_date} (daily_collection_dag 완료 후) =====")

    try:

        engine = get_db_engine()

        # 수집 상태 확인
        collection_status = get_collection_status(target_date, engine)
        logger.info(f"Collection status: {collection_status}")

        # 수집이 완료되지 않았으면 대기
        if collection_status['overall_status'] != 'success':
            logger.info(f"Collection not complete for {target_date}: status={collection_status['overall_status']}")
            return {'action': 'skip', 'reason': 'collection_not_complete'}

        # 지표 계산 상태 확인
        indicator_status = get_indicator_status(target_date, engine)
        logger.info(f"Indicator status: {indicator_status}")

        # 이미 계산 완료됨
        if indicator_status['status'] == 'success':
            logger.info(f"Indicators already calculated for {target_date}")
            return {'action': 'skip', 'reason': 'already_complete'}

        # 재시도 가능 확인
        if indicator_status['status'] in ['failed', 'pending']:
            max_retries = 3
            retry_count = indicator_status.get('retry_count', 0) or 0

            if indicator_status['status'] == 'failed' and retry_count >= max_retries:
                logger.warning(f"Max retries exceeded for indicators on {target_date}")
                return {'action': 'skip', 'reason': 'max_retries_exceeded'}

            # 지표 계산 수행
            logger.info(f"Proceeding to calculate indicators for {target_date}")
            return {'action': 'calculate', 'reason': 'ready_to_calculate'}

        return {'action': 'skip', 'reason': 'unexpected_status'}

    except Exception as e:
        logger.error(f"Error checking indicator status: {e}", exc_info=True)
        raise

def calculate_and_save_indicators(**context):
    """
    Task: 모든 주식의 기술적 지표 계산 및 저장

    계산 지표:
    - RSI (14-period)
    - MACD (12, 26, 9)
    - SMA 20, 50, 200
    - Bollinger Bands (20-period, 2 std dev)

    DB 컬럼명 (자동 매핑):
    - sma_20 → ma_20
    - sma_50 → ma_50
    - sma_200 → ma_200
    - bb_upper → bollinger_upper
    - bb_lower → bollinger_lower
    """
    target_date = date.today()
    logger.info(f"===== 지표 계산 시작: {target_date} =====")

    try:
        engine = get_db_engine()

        # 200일 역사 데이터 로드
        start_date = target_date - timedelta(days=200)

        query = f"""
            SELECT ticker, date, close_price
            FROM stock_prices
            WHERE date >= '{start_date}' AND date <= '{target_date}'
            ORDER BY ticker, date
        """

        stock_data = pd.read_sql(query, engine)
        logger.info(f"Loaded {len(stock_data)} historical records")

        if stock_data.empty:
            logger.error(f"No historical data found for {target_date}")
            update_indicator_log(
                target_date=target_date,
                status='failed',
                count=0,
                error='No historical data available',
                engine=engine
            )
            raise Exception("No historical data for indicator calculation")

        tickers = stock_data['ticker'].unique()
        logger.info(f"Processing {len(tickers)} tickers")

        indicators_list = []
        skipped = 0

        # 각 주식별 지표 계산
        for ticker in tickers:
            try:
                ticker_data = stock_data[stock_data['ticker'] == ticker].copy()

                if len(ticker_data) < 20:
                    skipped += 1
                    logger.debug(f"Skipping {ticker}: insufficient data ({len(ticker_data)} records)")
                    continue

                # 종가 시리즈 준비
                prices = ticker_data.sort_values('date')['close_price'].astype(float)

                # 지표 계산
                rsi = calculate_rsi(prices, period=14)
                macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)
                sma_20 = calculate_sma(prices, period=20)
                sma_50 = calculate_sma(prices, period=50)
                sma_200 = calculate_sma(prices, period=200)
                bb_upper, bb_lower = calculate_bollinger_bands(prices, period=20, std_dev=2)

                # 가장 최신 값 추출
                indicators = {
                    'ticker': ticker,
                    'date': target_date,
                    'rsi': float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
                    'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
                    'macd_signal': float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None,
                    'sma_20': float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None,
                    'sma_50': float(sma_50.iloc[-1]) if pd.notna(sma_50.iloc[-1]) else None,
                    'sma_200': float(sma_200.iloc[-1]) if pd.notna(sma_200.iloc[-1]) else None,
                    'bb_upper': float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None,
                    'bb_lower': float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None,
                }

                indicators_list.append(indicators)

            except Exception as e:
                logger.warning(f"Error calculating indicators for {ticker}: {e}")
                skipped += 1
                continue

        logger.info(f"Calculated: {len(indicators_list)}, Skipped: {skipped}")

        if not indicators_list:
            logger.error(f"No indicators calculated for {target_date}")
            update_indicator_log(
                target_date=target_date,
                status='failed',
                count=0,
                error='No indicators calculated',
                engine=engine
            )
            raise Exception("No indicators calculated")

        # DB에 저장 (common_functions.save_technical_indicators가 컬럼명 매핑 처리)
        saved_count = save_technical_indicators(indicators_list, engine)
        logger.info(f"✅ Successfully saved {saved_count} technical indicators for {target_date}")

        # 상태 업데이트
        update_indicator_log(
            target_date=target_date,
            status='success',
            count=saved_count,
            required_prices=len(tickers),
            collected_prices=len(indicators_list),
            engine=engine
        )

        logger.info(f"✅✅✅ 지표 계산 완료: {saved_count}개 지표 저장 ({target_date}) ✅✅✅")

        return {
            'status': 'success',
            'target_date': str(target_date),
            'indicators_saved': saved_count,
            'tickers_processed': len(tickers),
            'message': f'{saved_count}개 지표 저장 완료'
        }

    except Exception as e:
        logger.error(f"Error calculating/saving indicators: {e}", exc_info=True)
        update_indicator_log(
            target_date=target_date,
            status='retrying',
            error=str(e),
            engine=engine
        )
        raise

# ========================================
# DAG Task 흐름 정의
# ========================================

# daily_collection_dag 완료 대기
check_task = PythonOperator(
    task_id='check_indicator_readiness',
    python_callable=check_and_calculate_indicators,
    provide_context=True,
    dag=dag
)

calculate_task = PythonOperator(
    task_id='calculate_indicators',
    python_callable=calculate_and_save_indicators,
    provide_context=True,
    dag=dag
)

# Task 의존성: check → calculate
check_task >> calculate_task
