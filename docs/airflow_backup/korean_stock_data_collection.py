#!/usr/bin/env python3
"""
한국 주식 데이터 수집 DAG (날짜별 실행)

역할:
1. target_date 파라미터로 특정 날짜의 데이터 수집
2. 주가, 지수, 기술적 지표 계산
3. generate_collection_dates DAG에 의해 트리거됨

실행 방법:
- 자동: generate_collection_dates DAG가 누락된 날짜별로 트리거
- 수동: Airflow UI에서 target_date 지정하여 실행
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import os
import logging

logger = logging.getLogger(__name__)

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 25),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

def get_db_connection():
    """데이터베이스 연결 생성"""
    from sqlalchemy import create_engine
    host = os.getenv('DB_HOST', 'postgres')
    DATABASE_URL = f"postgresql://admin:admin123@{host}:5432/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
    return engine

def get_target_date(**context):
    """
    수집할 대상 날짜 결정
    1. DAG 실행 시 target_date 파라미터가 있으면 사용
    2. 없으면 execution_date 사용
    """
    dag_run = context.get('dag_run')

    if dag_run and dag_run.conf:
        target_date_str = dag_run.conf.get('target_date')
        if target_date_str:
            target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
            logger.info(f"Using target_date from conf: {target_date_str}")
            context['task_instance'].xcom_push(key='target_date', value=target_date_str)
            return target_date_str

    # 기본값: execution_date
    execution_date = context['execution_date']
    target_date_str = execution_date.strftime('%Y-%m-%d')
    logger.info(f"Using execution_date as target: {target_date_str}")
    context['task_instance'].xcom_push(key='target_date', value=target_date_str)
    return target_date_str

def collect_stock_prices(**context):
    """주가 데이터 수집 (target_date 기준)"""
    from pykrx import stock
    from sqlalchemy import text
    import pandas as pd
    import time

    target_date_str = context['task_instance'].xcom_pull(key='target_date', task_ids='determine_target_date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    target_date_pykrx = target_date.strftime("%Y%m%d")

    logger.info(f"Collecting stock prices for {target_date_str}")

    engine = get_db_connection()

    # KOSPI와 KOSDAQ 종목 리스트 가져오기
    kospi_tickers = stock.get_market_ticker_list(target_date_pykrx, market="KOSPI")
    kosdaq_tickers = stock.get_market_ticker_list(target_date_pykrx, market="KOSDAQ")
    all_tickers = kospi_tickers + kosdaq_tickers

    logger.info(f"Found {len(all_tickers)} tickers (KOSPI: {len(kospi_tickers)}, KOSDAQ: {len(kosdaq_tickers)})")

    successful = 0
    failed = 0

    for ticker in all_tickers:
        try:
            # 종목명 가져오기
            company_name = stock.get_market_ticker_name(ticker)
            market_type = "KOSPI" if ticker in kospi_tickers else "KOSDAQ"

            # 종목 정보 저장
            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO stocks (ticker, company_name, market_type, is_active, currency)
                    VALUES (:ticker, :name, :market, true, 'KRW')
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        market_type = EXCLUDED.market_type,
                        is_active = EXCLUDED.is_active
                """), {
                    'ticker': ticker,
                    'name': company_name,
                    'market': market_type
                })

            # 주가 데이터 가져오기 (해당 날짜만)
            price_df = stock.get_market_ohlcv_by_date(target_date_pykrx, target_date_pykrx, ticker)

            if not price_df.empty:
                price_df = price_df.reset_index()

                with engine.begin() as conn:
                    for _, row in price_df.iterrows():
                        conn.execute(text("""
                            INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                            VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, NOW())
                            ON CONFLICT (ticker, date)
                            DO UPDATE SET
                                open_price = EXCLUDED.open_price,
                                high_price = EXCLUDED.high_price,
                                low_price = EXCLUDED.low_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume
                        """), {
                            'ticker': ticker,
                            'date': row['날짜'],
                            'open_price': row['시가'],
                            'high_price': row['고가'],
                            'low_price': row['저가'],
                            'close_price': row['종가'],
                            'volume': row['거래량']
                        })

                successful += 1
                if successful % 100 == 0:
                    logger.info(f"Progress: {successful} stocks collected")

            # API 속도 제한
            time.sleep(0.2)

        except Exception as e:
            logger.warning(f"Failed to collect {ticker}: {e}")
            failed += 1
            continue

    logger.info(f"Stock price collection completed: {successful} successful, {failed} failed")
    context['task_instance'].xcom_push(key='stocks_collected', value=successful)
    return successful

def collect_market_indices(**context):
    """시장 지수 수집 (target_date 기준)"""
    from pykrx import stock
    from sqlalchemy import text

    target_date_str = context['task_instance'].xcom_pull(key='target_date', task_ids='determine_target_date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')
    target_date_pykrx = target_date.strftime("%Y%m%d")

    logger.info(f"Collecting market indices for {target_date_str}")

    engine = get_db_connection()

    indices = {
        'KOSPI': '0001',
        'KOSDAQ': '1001',
        'KOSPI200': '2001'
    }

    collected = 0

    for index_name, index_code in indices.items():
        try:
            # 지수 데이터 가져오기
            df = stock.get_index_ohlcv_by_date(target_date_pykrx, target_date_pykrx, index_code)

            if not df.empty:
                df = df.reset_index()

                with engine.begin() as conn:
                    for _, row in df.iterrows():
                        conn.execute(text("""
                            INSERT INTO market_indices (index_name, date, open_value, high_value, low_value, close_value, volume)
                            VALUES (:name, :date, :open, :high, :low, :close, :volume)
                            ON CONFLICT (index_name, date)
                            DO UPDATE SET
                                open_value = EXCLUDED.open_value,
                                high_value = EXCLUDED.high_value,
                                low_value = EXCLUDED.low_value,
                                close_value = EXCLUDED.close_value,
                                volume = EXCLUDED.volume
                        """), {
                            'name': index_name,
                            'date': row['날짜'],
                            'open': row['시가'],
                            'high': row['고가'],
                            'low': row['저가'],
                            'close': row['종가'],
                            'volume': row['거래대금']
                        })

                collected += 1
                logger.info(f"Collected {index_name} index data")

        except Exception as e:
            logger.warning(f"Failed to collect {index_name}: {e}")
            continue

    logger.info(f"Market indices collection completed: {collected}/{len(indices)} indices")
    return collected

def calculate_technical_indicators(**context):
    """기술적 지표 계산 (target_date 기준)"""
    from sqlalchemy import text
    import pandas as pd
    import numpy as np

    target_date_str = context['task_instance'].xcom_pull(key='target_date', task_ids='determine_target_date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')

    logger.info(f"Calculating technical indicators for {target_date_str}")

    engine = get_db_connection()

    # 해당 날짜에 수집된 종목 조회
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT ticker FROM stock_prices WHERE date = :target_date
        """), {'target_date': target_date.date()})
        tickers = [row[0] for row in result]

    logger.info(f"Calculating indicators for {len(tickers)} tickers")

    successful = 0
    failed = 0

    # 지표 계산을 위해 충분한 과거 데이터 조회 (최대 200일)
    lookback_date = target_date - timedelta(days=250)

    for ticker in tickers:
        try:
            # 과거 데이터 조회
            with engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT date, close_price, high_price, low_price, volume
                    FROM stock_prices
                    WHERE ticker = :ticker AND date BETWEEN :start_date AND :end_date
                    ORDER BY date
                """), {
                    'ticker': ticker,
                    'start_date': lookback_date.date(),
                    'end_date': target_date.date()
                })

                data = pd.DataFrame(result.fetchall(), columns=['date', 'close', 'high', 'low', 'volume'])

            if len(data) < 20:  # 최소 20일 데이터 필요
                continue

            # RSI 계산 (14일)
            delta = data['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))

            # MACD 계산
            ema_12 = data['close'].ewm(span=12, adjust=False).mean()
            ema_26 = data['close'].ewm(span=26, adjust=False).mean()
            macd = ema_12 - ema_26
            macd_signal = macd.ewm(span=9, adjust=False).mean()
            macd_hist = macd - macd_signal

            # Bollinger Bands (20일, 2σ)
            sma_20 = data['close'].rolling(window=20).mean()
            std_20 = data['close'].rolling(window=20).std()
            bb_upper = sma_20 + (std_20 * 2)
            bb_lower = sma_20 - (std_20 * 2)

            # 이동평균선
            sma_50 = data['close'].rolling(window=50).mean()
            sma_200 = data['close'].rolling(window=200).mean()

            # Stochastic Oscillator (14일)
            low_14 = data['low'].rolling(window=14).min()
            high_14 = data['high'].rolling(window=14).max()
            stoch_k = 100 * ((data['close'] - low_14) / (high_14 - low_14))
            stoch_d = stoch_k.rolling(window=3).mean()

            # target_date의 지표값만 저장
            idx = data[data['date'] == target_date.date()].index
            if len(idx) == 0:
                continue

            i = idx[0]

            with engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO technical_indicators (
                        ticker, date, rsi, macd, macd_signal, macd_hist,
                        stoch_k, stoch_d, sma_20, sma_50, sma_200,
                        bb_upper, bb_middle, bb_lower
                    )
                    VALUES (
                        :ticker, :date, :rsi, :macd, :macd_signal, :macd_hist,
                        :stoch_k, :stoch_d, :sma_20, :sma_50, :sma_200,
                        :bb_upper, :bb_middle, :bb_lower
                    )
                    ON CONFLICT (ticker, date)
                    DO UPDATE SET
                        rsi = EXCLUDED.rsi,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        macd_hist = EXCLUDED.macd_hist,
                        stoch_k = EXCLUDED.stoch_k,
                        stoch_d = EXCLUDED.stoch_d,
                        sma_20 = EXCLUDED.sma_20,
                        sma_50 = EXCLUDED.sma_50,
                        sma_200 = EXCLUDED.sma_200,
                        bb_upper = EXCLUDED.bb_upper,
                        bb_middle = EXCLUDED.bb_middle,
                        bb_lower = EXCLUDED.bb_lower
                """), {
                    'ticker': ticker,
                    'date': target_date.date(),
                    'rsi': float(rsi.iloc[i]) if pd.notna(rsi.iloc[i]) else None,
                    'macd': float(macd.iloc[i]) if pd.notna(macd.iloc[i]) else None,
                    'macd_signal': float(macd_signal.iloc[i]) if pd.notna(macd_signal.iloc[i]) else None,
                    'macd_hist': float(macd_hist.iloc[i]) if pd.notna(macd_hist.iloc[i]) else None,
                    'stoch_k': float(stoch_k.iloc[i]) if pd.notna(stoch_k.iloc[i]) else None,
                    'stoch_d': float(stoch_d.iloc[i]) if pd.notna(stoch_d.iloc[i]) else None,
                    'sma_20': float(sma_20.iloc[i]) if pd.notna(sma_20.iloc[i]) else None,
                    'sma_50': float(sma_50.iloc[i]) if pd.notna(sma_50.iloc[i]) else None,
                    'sma_200': float(sma_200.iloc[i]) if pd.notna(sma_200.iloc[i]) else None,
                    'bb_upper': float(bb_upper.iloc[i]) if pd.notna(bb_upper.iloc[i]) else None,
                    'bb_middle': float(sma_20.iloc[i]) if pd.notna(sma_20.iloc[i]) else None,
                    'bb_lower': float(bb_lower.iloc[i]) if pd.notna(bb_lower.iloc[i]) else None,
                })

            successful += 1
            if successful % 100 == 0:
                logger.info(f"Progress: {successful} indicators calculated")

        except Exception as e:
            logger.warning(f"Failed to calculate indicators for {ticker}: {e}")
            failed += 1
            continue

    logger.info(f"Technical indicators calculation completed: {successful} successful, {failed} failed")
    return successful

def verify_data_quality(**context):
    """데이터 품질 검증"""
    from sqlalchemy import text

    target_date_str = context['task_instance'].xcom_pull(key='target_date', task_ids='determine_target_date')
    target_date = datetime.strptime(target_date_str, '%Y-%m-%d')

    logger.info(f"Verifying data quality for {target_date_str}")

    engine = get_db_connection()

    with engine.connect() as conn:
        # 주가 데이터 개수
        result = conn.execute(text("""
            SELECT COUNT(*) FROM stock_prices WHERE date = :date
        """), {'date': target_date.date()})
        price_count = result.scalar()

        # 지표 데이터 개수
        result = conn.execute(text("""
            SELECT COUNT(*) FROM technical_indicators WHERE date = :date
        """), {'date': target_date.date()})
        indicator_count = result.scalar()

        # 지수 데이터 개수
        result = conn.execute(text("""
            SELECT COUNT(*) FROM market_indices WHERE date = :date
        """), {'date': target_date.date()})
        index_count = result.scalar()

    logger.info("="*80)
    logger.info(f"Data Quality Report for {target_date_str}")
    logger.info(f"  Stock Prices: {price_count} records")
    logger.info(f"  Technical Indicators: {indicator_count} records")
    logger.info(f"  Market Indices: {index_count} records")
    logger.info("="*80)

    # 최소 기준 검증
    if price_count < 100:
        logger.warning(f"Low stock price count: {price_count} < 100")

    return {
        'price_count': price_count,
        'indicator_count': indicator_count,
        'index_count': index_count
    }

# DAG 정의
with DAG(
    'korean_stock_data_collection',
    default_args=default_args,
    description='한국 주식 데이터 수집 (날짜별)',
    schedule_interval=None,  # 수동 실행 또는 트리거에 의해 실행
    start_date=datetime(2025, 9, 25),
    catchup=False,
    max_active_runs=3,  # 동시에 3개 날짜까지 처리 가능
    tags=['korean-stock', 'data-collection', 'production'],
) as dag:

    # Task 1: 대상 날짜 결정
    determine_date = PythonOperator(
        task_id='determine_target_date',
        python_callable=get_target_date,
    )

    # Task 2: 주가 데이터 수집
    collect_prices = PythonOperator(
        task_id='collect_stock_prices',
        python_callable=collect_stock_prices,
        execution_timeout=timedelta(hours=2),
        retries=1,
        retry_delay=timedelta(minutes=10),
    )

    # Task 3: 시장 지수 수집
    collect_indices = PythonOperator(
        task_id='collect_market_indices',
        python_callable=collect_market_indices,
        execution_timeout=timedelta(minutes=30),
    )

    # Task 4: 기술적 지표 계산
    calculate_indicators = PythonOperator(
        task_id='calculate_technical_indicators',
        python_callable=calculate_technical_indicators,
        execution_timeout=timedelta(hours=1),
        retries=1,
        retry_delay=timedelta(minutes=5),
    )

    # Task 5: 데이터 품질 검증
    verify_quality = PythonOperator(
        task_id='verify_data_quality',
        python_callable=verify_data_quality,
    )

    # 태스크 의존성
    determine_date >> [collect_prices, collect_indices]
    collect_prices >> calculate_indicators
    [collect_indices, calculate_indicators] >> verify_quality
