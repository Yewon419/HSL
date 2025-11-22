"""
Daily Stock Data Collection and Indicator Calculation Pipeline
Collects Korean stock market data and calculates technical indicators daily
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import pandas as pd
import numpy as np
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
import sys
import os

# Add backend path for imports
sys.path.append('/app')

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
    'daily_stock_data_pipeline',
    default_args=default_args,
    description='Daily Korean stock data collection and indicator calculation',
    schedule_interval='0 19 * * 1-5',  # 매일 오후 7시 (한국 시장 종료 후, 월-금)
    catchup=False,
    max_active_runs=1,
    tags=['production', 'korean-stock', 'daily', 'indicators']
)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def collect_stock_prices(**context):
    """한국 주식 가격 데이터 수집"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Collecting stock prices for {target_date}")

    try:
        from pykrx import stock as pykrx_stock

        engine = get_db_connection()

        # Get all active Korean stocks
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ticker, company_name FROM stocks
                WHERE is_active = true AND currency = 'KRW'
                ORDER BY ticker
            """))
            stocks = [{'ticker': row[0], 'name': row[1]} for row in result]

        logging.info(f"Found {len(stocks)} active stocks")

        date_str = target_date.strftime("%Y%m%d")
        success_count = 0
        error_count = 0

        for stock in stocks:
            ticker = stock['ticker']
            try:
                # Fetch OHLCV data
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)

                if not df.empty:
                    for date_index, row in df.iterrows():
                        with engine.begin() as conn:
                            conn.execute(text("""
                                INSERT INTO stock_prices
                                (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                                VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                                ON CONFLICT (ticker, date) DO UPDATE SET
                                    open_price = EXCLUDED.open_price,
                                    high_price = EXCLUDED.high_price,
                                    low_price = EXCLUDED.low_price,
                                    close_price = EXCLUDED.close_price,
                                    volume = EXCLUDED.volume
                            """), {
                                'ticker': ticker,
                                'date': date_index.date(),
                                'open_price': float(row['시가']),
                                'high_price': float(row['고가']),
                                'low_price': float(row['저가']),
                                'close_price': float(row['종가']),
                                'volume': int(row['거래량']),
                                'created_at': datetime.now()
                            })
                    success_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    logging.warning(f"Error fetching {ticker}: {e}")
                continue

        logging.info(f"Stock prices collected: {success_count} success, {error_count} errors")
        return {'success': success_count, 'errors': error_count}

    except Exception as e:
        logging.error(f"Fatal error in stock price collection: {e}")
        raise

def collect_market_indices(**context):
    """시장 지수 데이터 수집"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Collecting market indices for {target_date}")

    try:
        from pykrx import stock as pykrx_stock

        engine = get_db_connection()
        date_str = target_date.strftime("%Y%m%d")

        indices = {
            'KOSPI': '1001',
            'KOSDAQ': '2001'
        }

        for index_name, index_code in indices.items():
            try:
                df = pykrx_stock.get_index_ohlcv(date_str, date_str, index_code)

                if not df.empty:
                    close_val = float(df.iloc[0]['종가'])
                    volume_val = int(df.iloc[0]['거래량'])

                    with engine.begin() as conn:
                        conn.execute(text("""
                            INSERT INTO market_indices
                            (index_name, date, index_value, total_volume, created_at)
                            VALUES (:index_name, :date, :index_value, :total_volume, :created_at)
                            ON CONFLICT (index_name, date) DO UPDATE SET
                                index_value = EXCLUDED.index_value,
                                total_volume = EXCLUDED.total_volume
                        """), {
                            'index_name': index_name,
                            'date': target_date,
                            'index_value': close_val,
                            'total_volume': volume_val,
                            'created_at': datetime.now()
                        })

                    logging.info(f"Collected {index_name}: {close_val}")

            except Exception as e:
                logging.warning(f"Error collecting {index_name}: {e}")

        logging.info("Market indices collection completed")
        return True

    except Exception as e:
        logging.error(f"Fatal error in market indices collection: {e}")
        raise

def calculate_technical_indicators(**context):
    """기술적 지표 계산"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Calculating technical indicators for {target_date}")

    try:
        engine = get_db_connection()

        # Get tickers with data for target date
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT ticker FROM stock_prices
                WHERE date = :date
                ORDER BY ticker
            """), {'date': target_date})
            tickers = [row[0] for row in result]

        logging.info(f"Processing {len(tickers)} tickers")

        success_count = 0
        error_count = 0

        for ticker in tickers:
            try:
                # Get recent 200 days of data for MA200
                with engine.connect() as conn:
                    df = pd.read_sql(text("""
                        SELECT date, close_price, high_price, low_price
                        FROM stock_prices
                        WHERE ticker = :ticker
                        AND date <= :target_date
                        AND date >= :start_date
                        ORDER BY date ASC
                    """), conn, params={
                        'ticker': ticker,
                        'target_date': target_date,
                        'start_date': target_date - timedelta(days=300)
                    })

                if len(df) < 20:
                    continue

                # Convert data types
                df['close'] = pd.to_numeric(df['close_price'], errors='coerce')
                df['high'] = pd.to_numeric(df['high_price'], errors='coerce')
                df['low'] = pd.to_numeric(df['low_price'], errors='coerce')

                # Calculate RSI
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

                # Calculate MACD
                ema12 = df['close'].ewm(span=12).mean()
                ema26 = df['close'].ewm(span=26).mean()
                macd_line = ema12 - ema26
                macd_signal = macd_line.ewm(span=9).mean()
                macd_hist = macd_line - macd_signal

                # Calculate Moving Averages
                ma20 = df['close'].rolling(20).mean()
                ma50 = df['close'].rolling(50).mean()
                ma200 = df['close'].rolling(200).mean()

                # Calculate Bollinger Bands
                bb_middle = df['close'].rolling(20).mean()
                bb_std = df['close'].rolling(20).std()
                bb_upper = bb_middle + (2 * bb_std)
                bb_lower = bb_middle - (2 * bb_std)

                # Calculate Stochastic
                lowest_low = df['low'].rolling(14).min()
                highest_high = df['high'].rolling(14).max()
                stoch_k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
                stoch_d = stoch_k.rolling(3).mean()

                # Extract latest values
                latest_idx = -1

                # Handle infinite values
                def safe_float(val):
                    if pd.isna(val) or np.isinf(val):
                        return None
                    return float(val)

                indicators = {
                    'ticker': ticker,
                    'date': target_date,
                    'rsi': safe_float(rsi.iloc[latest_idx]),
                    'macd': safe_float(macd_line.iloc[latest_idx]),
                    'macd_signal': safe_float(macd_signal.iloc[latest_idx]),
                    'macd_histogram': safe_float(macd_hist.iloc[latest_idx]),
                    'ma_20': safe_float(ma20.iloc[latest_idx]),
                    'ma_50': safe_float(ma50.iloc[latest_idx]),
                    'ma_200': safe_float(ma200.iloc[latest_idx]),
                    'bollinger_upper': safe_float(bb_upper.iloc[latest_idx]),
                    'bollinger_middle': safe_float(bb_middle.iloc[latest_idx]),
                    'bollinger_lower': safe_float(bb_lower.iloc[latest_idx]),
                    'stoch_k': safe_float(stoch_k.iloc[latest_idx]),
                    'stoch_d': safe_float(stoch_d.iloc[latest_idx])
                }

                # Save to database
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO technical_indicators (
                            ticker, date, rsi, macd, macd_signal, macd_histogram,
                            ma_20, ma_50, ma_200,
                            bollinger_upper, bollinger_middle, bollinger_lower,
                            stoch_k, stoch_d
                        ) VALUES (
                            :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                            :ma_20, :ma_50, :ma_200,
                            :bollinger_upper, :bollinger_middle, :bollinger_lower,
                            :stoch_k, :stoch_d
                        )
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            macd_histogram = EXCLUDED.macd_histogram,
                            ma_20 = EXCLUDED.ma_20,
                            ma_50 = EXCLUDED.ma_50,
                            ma_200 = EXCLUDED.ma_200,
                            bollinger_upper = EXCLUDED.bollinger_upper,
                            bollinger_middle = EXCLUDED.bollinger_middle,
                            bollinger_lower = EXCLUDED.bollinger_lower,
                            stoch_k = EXCLUDED.stoch_k,
                            stoch_d = EXCLUDED.stoch_d
                    """), indicators)

                success_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    logging.warning(f"Error processing {ticker}: {e}")
                continue

        logging.info(f"Indicators calculated: {success_count} success, {error_count} errors")
        return {'success': success_count, 'errors': error_count}

    except Exception as e:
        logging.error(f"Fatal error in indicator calculation: {e}")
        raise

def validate_data_quality(**context):
    """데이터 품질 검증"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Validating data quality for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # Check stock prices
            price_result = conn.execute(text("""
                SELECT COUNT(*) as count FROM stock_prices
                WHERE date = :date
            """), {'date': target_date})
            price_count = price_result.fetchone()[0]

            # Check market indices
            index_result = conn.execute(text("""
                SELECT COUNT(*) as count FROM market_indices
                WHERE date = :date
            """), {'date': target_date})
            index_count = index_result.fetchone()[0]

            # Check indicators
            indicator_result = conn.execute(text("""
                SELECT COUNT(*) as count,
                       COUNT(CASE WHEN rsi IS NOT NULL THEN 1 END) as rsi_count
                FROM technical_indicators
                WHERE date = :date
            """), {'date': target_date})
            ind_row = indicator_result.fetchone()
            indicator_count = ind_row[0]
            rsi_count = ind_row[1]

            logging.info(f"Quality Report for {target_date}:")
            logging.info(f"  - Stock prices: {price_count}")
            logging.info(f"  - Market indices: {index_count}")
            logging.info(f"  - Technical indicators: {indicator_count} (RSI: {rsi_count})")

            if price_count >= 100 and indicator_count >= 100:
                logging.info("✅ Data quality validation PASSED")
                return True
            else:
                logging.warning("⚠️ Data quality validation WARNING - lower than expected")
                return False

    except Exception as e:
        logging.error(f"Error during validation: {e}")
        raise

# Define tasks
collect_prices_task = PythonOperator(
    task_id='collect_stock_prices',
    python_callable=collect_stock_prices,
    dag=dag,
)

collect_indices_task = PythonOperator(
    task_id='collect_market_indices',
    python_callable=collect_market_indices,
    dag=dag,
)

calculate_indicators_task = PythonOperator(
    task_id='calculate_technical_indicators',
    python_callable=calculate_technical_indicators,
    dag=dag,
)

validate_task = PythonOperator(
    task_id='validate_data_quality',
    python_callable=validate_data_quality,
    dag=dag,
)

# Define task dependencies
[collect_prices_task, collect_indices_task] >> calculate_indicators_task >> validate_task
