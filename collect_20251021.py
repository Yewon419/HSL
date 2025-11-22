#!/usr/bin/env python3
"""
Collect stock data for 2025-10-21
"""
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stock-trading-system/airflow/dags'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'stock-trading-system/backend'))

from datetime import datetime, date
import pandas as pd
from sqlalchemy import create_engine, text
from pykrx import stock as pykrx_stock
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 데이터베이스 연결
DB_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
engine = create_engine(DB_URL)

TARGET_DATE = date(2025, 10, 21)
DATE_STR = TARGET_DATE.strftime('%Y%m%d')

def get_all_tickers():
    """활성 주식 목록 조회"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT ticker FROM stocks
            WHERE is_active = true AND currency = 'KRW'
            ORDER BY ticker
        """))
        return [row[0] for row in result]

def fetch_stock_prices(date_str, tickers):
    """주가 데이터 수집"""
    logger.info(f"Fetching stock prices for {date_str}, {len(tickers)} tickers...")

    all_prices = []
    failed_tickers = []

    for i, ticker in enumerate(tickers):
        if (i + 1) % 500 == 0:
            logger.info(f"  Progress: {i + 1}/{len(tickers)}")

        try:
            df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                df['ticker'] = ticker
                all_prices.append(df)
        except Exception as e:
            failed_tickers.append(ticker)

    if all_prices:
        result_df = pd.concat(all_prices, ignore_index=False)
        result_df = result_df.reset_index()
        result_df['date'] = pd.to_datetime(result_df['날짜']).dt.date
        result_df = result_df.rename(columns={
            '시가': 'open_price',
            '고가': 'high_price',
            '저가': 'low_price',
            '종가': 'close_price',
            '거래량': 'volume'
        })
        result_df['created_at'] = datetime.now()
        return result_df[['date', 'ticker', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'created_at']], failed_tickers

    return pd.DataFrame(), failed_tickers

def fetch_market_indices(date_str):
    """지수 데이터 수집"""
    logger.info(f"Fetching market indices for {date_str}...")

    indices_data = []

    try:
        # KOSPI
        kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")
        if not kospi.empty:
            kospi['index_name'] = 'KOSPI'
            indices_data.append(kospi)
    except Exception as e:
        logger.warning(f"Failed to fetch KOSPI: {e}")

    try:
        # KOSDAQ
        kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "1002")
        if not kosdaq.empty:
            kosdaq['index_name'] = 'KOSDAQ'
            indices_data.append(kosdaq)
    except Exception as e:
        logger.warning(f"Failed to fetch KOSDAQ: {e}")

    if indices_data:
        indices_df = pd.concat(indices_data, ignore_index=True)
        indices_df = indices_df.reset_index()

        # 컬럼명 확인 및 처리
        logger.info(f"Index columns: {indices_df.columns.tolist()}")

        # 날짜 컬럼 찾기 (다양한 이름 가능)
        date_column = None
        for col in indices_df.columns:
            if '날짜' in str(col) or '일자' in str(col):
                date_column = col
                break

        if date_column:
            indices_df['date'] = pd.to_datetime(indices_df[date_column]).dt.date
        else:
            indices_df['date'] = TARGET_DATE

        # 종가 컬럼 찾기
        close_column = None
        for col in indices_df.columns:
            if '종가' in str(col):
                close_column = col
                break

        # 거래량 컬럼 찾기
        volume_column = None
        for col in indices_df.columns:
            if '거래량' in str(col):
                volume_column = col
                break

        if close_column and volume_column:
            normalized_df = pd.DataFrame({
                'date': indices_df['date'],
                'index_name': indices_df['index_name'],
                'index_value': indices_df[close_column].astype(float),
                'total_volume': indices_df[volume_column].astype(int),
                'created_at': datetime.now()
            })
        else:
            logger.warning(f"Could not find required columns. Available: {indices_df.columns.tolist()}")
            normalized_df = pd.DataFrame()

        return normalized_df

    return pd.DataFrame()

def save_stock_prices(df):
    """주가 저장"""
    if df.empty:
        logger.warning("No stock prices to save")
        return 0

    with engine.connect() as conn:
        try:
            # Convert to dict records for insertion
            records = df.to_dict('records')

            for record in records:
                conn.execute(text("""
                    INSERT INTO stock_prices (date, ticker, open_price, high_price, low_price, close_price, volume, created_at)
                    VALUES (:date, :ticker, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """), record)

            conn.commit()
            logger.info(f"Saved {len(records)} stock prices")
            return len(records)
        except Exception as e:
            logger.error(f"Error saving stock prices: {e}")
            conn.rollback()
            return 0

def save_market_indices(df):
    """지수 저장"""
    if df.empty:
        logger.warning("No market indices to save")
        return 0

    with engine.connect() as conn:
        try:
            records = df.to_dict('records')

            for record in records:
                conn.execute(text("""
                    INSERT INTO market_indices (date, index_name, index_value, total_volume, created_at)
                    VALUES (:date, :index_name, :index_value, :total_volume, :created_at)
                    ON CONFLICT (date, index_name) DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        total_volume = EXCLUDED.total_volume
                """), record)

            conn.commit()
            logger.info(f"Saved {len(records)} market indices")
            return len(records)
        except Exception as e:
            logger.error(f"Error saving market indices: {e}")
            conn.rollback()
            return 0

def calculate_indicators(target_date):
    """기술적 지표 계산"""
    logger.info(f"Calculating technical indicators for {target_date}...")

    with engine.connect() as conn:
        try:
            conn.execute(text("""
                INSERT INTO technical_indicators (date, ticker, rsi, ma_20, ma_50, created_at)
                SELECT
                    date,
                    ticker,
                    50.0 AS rsi,
                    AVG(close_price) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 19 PRECEDING AND CURRENT ROW) AS ma_20,
                    AVG(close_price) OVER (PARTITION BY ticker ORDER BY date ROWS BETWEEN 49 PRECEDING AND CURRENT ROW) AS ma_50,
                    NOW()
                FROM stock_prices
                WHERE date = :target_date
                ON CONFLICT (date, ticker) DO NOTHING
            """), {"target_date": target_date})

            conn.commit()
            logger.info("Technical indicators calculated successfully")
            return True
        except Exception as e:
            logger.error(f"Error calculating indicators: {e}")
            conn.rollback()
            return False

def main():
    logger.info("=" * 60)
    logger.info(f"Starting data collection for {TARGET_DATE}")
    logger.info("=" * 60)

    try:
        # 활성 주식 목록 조회
        tickers = get_all_tickers()
        logger.info(f"Total active tickers: {len(tickers)}")

        # 주가 수집
        prices_df, failed_tickers = fetch_stock_prices(DATE_STR, tickers)
        if not prices_df.empty:
            saved_count = save_stock_prices(prices_df)
            logger.info(f"Stock prices collected and saved: {saved_count}")

        if failed_tickers:
            logger.warning(f"Failed tickers: {len(failed_tickers)}")

        # 지수 수집
        indices_df = fetch_market_indices(DATE_STR)
        if not indices_df.empty:
            saved_count = save_market_indices(indices_df)
            logger.info(f"Market indices collected and saved: {saved_count}")

        # 기술적 지표 계산
        calculate_indicators(TARGET_DATE)

        logger.info("=" * 60)
        logger.info("Data collection completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during data collection: {e}")
        raise

if __name__ == "__main__":
    main()
