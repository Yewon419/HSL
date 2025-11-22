#!/usr/bin/env python3
"""
특정 날짜부터 데이터를 삭제하고 재적재 후 지표를 재계산하는 DAG
2025-09-29부터 데이터를 삭제하고 지표를 chunked로 계산합니다.

사용법:
1. Airflow UI에서 DAG를 트리거
2. Configuration에서 start_date를 지정 (예: {"start_date": "2025-09-29"})
3. 실시간 상태 모니터링 가능
"""

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.utils.dates import days_ago
from airflow.models import Variable
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np
import json
from sqlalchemy import create_engine, text

logger = logging.getLogger(__name__)

# 기본 설정
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
}

# DB 연결 설정
def get_db_connection():
    """데이터베이스 연결 생성"""
    import os
    host = os.getenv('DB_HOST', 'postgres')
    DATABASE_URL = f"postgresql://admin:admin123@{host}:5432/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
    return engine

# Task 1: 상태 체크 및 시작 로그
def check_and_log_status(**context):
    """현재 데이터 상태 체크 및 로깅"""
    start_date = context['dag_run'].conf.get('start_date', '2025-09-29')

    logger.info("="*80)
    logger.info(f"지표 재계산 작업 시작")
    logger.info(f"삭제 시작 날짜: {start_date}")
    logger.info("="*80)

    engine = get_db_connection()

    with engine.connect() as conn:
        # 현재 상태 확인
        result = conn.execute(text("""
            SELECT
                COUNT(DISTINCT ticker) as ticker_count,
                COUNT(*) as total_records,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM technical_indicators
            WHERE date >= :start_date
        """), {'start_date': start_date})

        row = result.fetchone()

        logger.info(f"삭제 대상 데이터:")
        logger.info(f"  - 종목 수: {row.ticker_count}")
        logger.info(f"  - 총 레코드: {row.total_records:,}")
        logger.info(f"  - 기간: {row.min_date} ~ {row.max_date}")

        # XCom에 저장
        context['task_instance'].xcom_push(key='start_date', value=start_date)
        context['task_instance'].xcom_push(key='total_before_delete', value=row.total_records)

    return start_date

# Task 2: 기존 지표 데이터 삭제
def delete_indicators_from_date(**context):
    """특정 날짜 이후의 지표 데이터 삭제"""
    start_date = context['task_instance'].xcom_pull(key='start_date', task_ids='check_status')

    logger.info(f"기술적 지표 삭제 시작: {start_date} 이후")

    engine = get_db_connection()

    with engine.begin() as conn:
        # technical_indicators 테이블 삭제
        result1 = conn.execute(text("""
            DELETE FROM technical_indicators
            WHERE date >= :start_date
        """), {'start_date': start_date})

        # indicator_values 테이블 삭제 (32개 지표용)
        result2 = conn.execute(text("""
            DELETE FROM indicator_values
            WHERE date >= :start_date
        """), {'start_date': start_date})

        logger.info(f"삭제 완료:")
        logger.info(f"  - technical_indicators: {result1.rowcount:,}건")
        logger.info(f"  - indicator_values: {result2.rowcount:,}건")

        context['task_instance'].xcom_push(key='deleted_count', value=result1.rowcount + result2.rowcount)

    return True

# Task 3: 대상 종목 리스트 생성
def get_ticker_list(**context):
    """지표를 계산할 종목 리스트 가져오기"""
    start_date = context['task_instance'].xcom_pull(key='start_date', task_ids='check_status')

    logger.info("대상 종목 리스트 생성 중...")

    engine = get_db_connection()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT sp.ticker, s.company_name
            FROM stock_prices sp
            JOIN stocks s ON sp.ticker = s.ticker
            WHERE s.currency = 'KRW'
              AND s.is_active = true
              AND sp.date >= :start_date
            ORDER BY sp.ticker
        """), {'start_date': start_date})

        tickers = [{'ticker': row.ticker, 'company_name': row.company_name} for row in result]

    logger.info(f"대상 종목: {len(tickers)}개")

    # XCom에 저장
    context['task_instance'].xcom_push(key='ticker_list', value=tickers)
    context['task_instance'].xcom_push(key='total_tickers', value=len(tickers))

    return len(tickers)

# Task 4: Chunk별 지표 계산 (동적 태스크)
def calculate_indicators_chunk(**context):
    """Chunk 단위로 지표 계산"""
    chunk_id = context['params']['chunk_id']
    chunk_size = context['params']['chunk_size']

    start_date = context['task_instance'].xcom_pull(key='start_date', task_ids='check_status')
    tickers = context['task_instance'].xcom_pull(key='ticker_list', task_ids='get_ticker_list')

    # Chunk 분할
    start_idx = chunk_id * chunk_size
    end_idx = min(start_idx + chunk_size, len(tickers))
    chunk_tickers = tickers[start_idx:end_idx]

    logger.info("="*80)
    logger.info(f"Chunk {chunk_id} 처리 시작")
    logger.info(f"종목: {start_idx+1}~{end_idx} / {len(tickers)}")
    logger.info(f"처리 대상: {len(chunk_tickers)}개 종목")
    logger.info("="*80)

    engine = get_db_connection()

    # 날짜 범위 생성
    date_range = pd.date_range(start=start_date, end=datetime.now().date(), freq='D')
    target_dates = [date.strftime('%Y-%m-%d') for date in date_range]

    total_saved = 0
    successful_stocks = 0
    failed_stocks = 0

    for i, stock_info in enumerate(chunk_tickers, 1):
        ticker = stock_info['ticker']
        company_name = stock_info['company_name']

        try:
            logger.info(f"[{i}/{len(chunk_tickers)}] {ticker} ({company_name}) 처리 중...")

            # 각 날짜별로 지표 계산
            for target_date in target_dates:
                saved = calculate_indicators_for_ticker_date(engine, ticker, target_date)
                total_saved += saved

            successful_stocks += 1
            logger.info(f"  ✅ {ticker} 완료 (저장: {total_saved}개)")

        except Exception as e:
            failed_stocks += 1
            logger.error(f"  ❌ {ticker} 실패: {e}")

    logger.info("="*80)
    logger.info(f"Chunk {chunk_id} 처리 완료")
    logger.info(f"성공: {successful_stocks}/{len(chunk_tickers)}")
    logger.info(f"실패: {failed_stocks}/{len(chunk_tickers)}")
    logger.info(f"저장된 지표: {total_saved:,}개")
    logger.info("="*80)

    # 결과 XCom 저장
    context['task_instance'].xcom_push(key=f'chunk_{chunk_id}_success', value=successful_stocks)
    context['task_instance'].xcom_push(key=f'chunk_{chunk_id}_saved', value=total_saved)

    return total_saved

def calculate_indicators_for_ticker_date(engine, ticker, target_date):
    """특정 종목의 특정 날짜 지표 계산"""
    try:
        with engine.connect() as conn:
            # 해당 종목의 과거 데이터 가져오기
            price_data = pd.read_sql(text("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                  AND date <= :target_date
                ORDER BY date ASC
            """), conn, params={'ticker': ticker, 'target_date': target_date})

            if len(price_data) < 20:
                return 0

            # 데이터 처리
            price_data['close'] = pd.to_numeric(price_data['close_price'])
            price_data['high'] = pd.to_numeric(price_data['high_price'])
            price_data['low'] = pd.to_numeric(price_data['low_price'])
            price_data['volume'] = pd.to_numeric(price_data['volume'])

            # 기술적 지표 계산
            price_data['ma_20'] = price_data['close'].rolling(20).mean()
            price_data['ma_50'] = price_data['close'].rolling(50).mean()
            price_data['ma_200'] = price_data['close'].rolling(200).mean()

            # RSI
            delta = price_data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            price_data['rsi'] = 100 - (100 / (1 + rs))

            # MACD
            ema12 = price_data['close'].ewm(span=12).mean()
            ema26 = price_data['close'].ewm(span=26).mean()
            price_data['macd'] = ema12 - ema26
            price_data['macd_signal'] = price_data['macd'].ewm(span=9).mean()
            price_data['macd_histogram'] = price_data['macd'] - price_data['macd_signal']

            # Bollinger Bands
            sma20 = price_data['close'].rolling(20).mean()
            std20 = price_data['close'].rolling(20).std()
            price_data['bb_upper'] = sma20 + (std20 * 2)
            price_data['bb_middle'] = sma20
            price_data['bb_lower'] = sma20 - (std20 * 2)

            # Stochastic
            lowest_low = price_data['low'].rolling(14).min()
            highest_high = price_data['high'].rolling(14).max()
            price_data['stoch_k'] = 100 * ((price_data['close'] - lowest_low) / (highest_high - lowest_low))
            price_data['stoch_d'] = price_data['stoch_k'].rolling(3).mean()

            # 대상 날짜의 데이터만 추출
            target_row = price_data[price_data['date'] == target_date]

            if len(target_row) == 0 or pd.isna(target_row.iloc[0]['ma_20']):
                return 0

            row = target_row.iloc[0]

            # Helper function
            def safe_float(val):
                if pd.isna(val) or np.isinf(val):
                    return None
                return float(val)

            # 데이터베이스에 저장
            with engine.begin() as save_conn:
                save_conn.execute(text("""
                    INSERT INTO technical_indicators (
                        ticker, date, rsi, macd, macd_signal, macd_histogram,
                        stoch_k, stoch_d, ma_20, ma_50, ma_200,
                        bollinger_upper, bollinger_middle, bollinger_lower,
                        created_at
                    ) VALUES (
                        :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                        :stoch_k, :stoch_d, :ma_20, :ma_50, :ma_200,
                        :bb_upper, :bb_middle, :bb_lower, NOW()
                    ) ON CONFLICT (ticker, date) DO UPDATE SET
                        rsi = EXCLUDED.rsi,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        macd_histogram = EXCLUDED.macd_histogram,
                        stoch_k = EXCLUDED.stoch_k,
                        stoch_d = EXCLUDED.stoch_d,
                        ma_20 = EXCLUDED.ma_20,
                        ma_50 = EXCLUDED.ma_50,
                        ma_200 = EXCLUDED.ma_200,
                        bollinger_upper = EXCLUDED.bollinger_upper,
                        bollinger_middle = EXCLUDED.bollinger_middle,
                        bollinger_lower = EXCLUDED.bollinger_lower,
                        created_at = NOW()
                """), {
                    'ticker': ticker,
                    'date': target_date,
                    'rsi': safe_float(row['rsi']),
                    'macd': safe_float(row['macd']),
                    'macd_signal': safe_float(row['macd_signal']),
                    'macd_histogram': safe_float(row['macd_histogram']),
                    'stoch_k': safe_float(row['stoch_k']),
                    'stoch_d': safe_float(row['stoch_d']),
                    'ma_20': safe_float(row['ma_20']),
                    'ma_50': safe_float(row['ma_50']),
                    'ma_200': safe_float(row['ma_200']),
                    'bb_upper': safe_float(row['bb_upper']),
                    'bb_middle': safe_float(row['bb_middle']),
                    'bb_lower': safe_float(row['bb_lower'])
                })

            return 1

    except Exception as e:
        logger.error(f"Error calculating indicators for {ticker} {target_date}: {e}")
        return 0

# Task 5: 최종 결과 리포트
def generate_final_report(**context):
    """최종 결과 리포트 생성"""
    start_date = context['task_instance'].xcom_pull(key='start_date', task_ids='check_status')
    total_tickers = context['task_instance'].xcom_pull(key='total_tickers', task_ids='get_ticker_list')
    deleted_count = context['task_instance'].xcom_pull(key='deleted_count', task_ids='delete_indicators')

    # Chunk별 결과 집계
    chunk_size = 50
    num_chunks = (total_tickers + chunk_size - 1) // chunk_size

    total_saved = 0
    for chunk_id in range(num_chunks):
        saved = context['task_instance'].xcom_pull(
            key=f'chunk_{chunk_id}_saved',
            task_ids=f'calculate_chunk_{chunk_id}'
        )
        if saved:
            total_saved += saved

    logger.info("="*80)
    logger.info("지표 재계산 작업 완료")
    logger.info("="*80)
    logger.info(f"시작 날짜: {start_date}")
    logger.info(f"대상 종목: {total_tickers}개")
    logger.info(f"삭제된 레코드: {deleted_count:,}개")
    logger.info(f"새로 저장된 지표: {total_saved:,}개")
    logger.info("="*80)

    return {
        'start_date': start_date,
        'total_tickers': total_tickers,
        'deleted_count': deleted_count,
        'saved_count': total_saved
    }

# DAG 정의
with DAG(
    'rebuild_indicators_from_date',
    default_args=default_args,
    description='특정 날짜부터 지표를 삭제하고 재계산하는 DAG (Chunked)',
    schedule_interval=None,  # 수동 실행
    start_date=days_ago(1),
    catchup=False,
    tags=['indicators', 'rebuild', 'maintenance'],
) as dag:

    # Task 1: 상태 체크
    check_status = PythonOperator(
        task_id='check_status',
        python_callable=check_and_log_status,
        provide_context=True,
    )

    # Task 2: 데이터 삭제
    delete_data = PythonOperator(
        task_id='delete_indicators',
        python_callable=delete_indicators_from_date,
        provide_context=True,
    )

    # Task 3: 종목 리스트 가져오기
    get_tickers = PythonOperator(
        task_id='get_ticker_list',
        python_callable=get_ticker_list,
        provide_context=True,
    )

    # Task 4: Chunk별 계산 (동적 생성)
    # 실제로는 총 종목 수를 알 수 없으므로, 여기서는 최대 chunk 개수를 설정
    # 실전에서는 Dynamic Task Mapping을 사용하는 것이 좋습니다
    chunk_size = 50  # 한 번에 50개 종목씩 처리
    max_chunks = 50  # 최대 50개 chunk (2500개 종목)

    calculate_tasks = []
    for chunk_id in range(max_chunks):
        task = PythonOperator(
            task_id=f'calculate_chunk_{chunk_id}',
            python_callable=calculate_indicators_chunk,
            params={'chunk_id': chunk_id, 'chunk_size': chunk_size},
            provide_context=True,
        )
        calculate_tasks.append(task)

    # Task 5: 최종 리포트
    final_report = PythonOperator(
        task_id='final_report',
        python_callable=generate_final_report,
        provide_context=True,
    )

    # Task 의존성 설정
    check_status >> delete_data >> get_tickers >> calculate_tasks >> final_report
