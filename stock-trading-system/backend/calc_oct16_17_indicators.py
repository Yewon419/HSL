#!/usr/bin/env python
"""
10월 16, 17일 기술적 지표 재계산 스크립트
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    if os.path.exists('/.dockerenv'):
        db_url = f"postgresql://admin:admin123@postgres:5432/stocktrading"
    else:
        db_url = f"postgresql://admin:admin123@localhost:5435/stocktrading"

    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return engine

def calculate_rsi(prices, period=14):
    """RSI 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD 계산"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal).mean()
    macd_histogram = macd_line - macd_signal
    return macd_line, macd_signal, macd_histogram

def calculate_sma(prices, period=20):
    """SMA 계산"""
    return prices.rolling(window=period).mean()

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, sma, lower_band

def recalculate_indicators_for_date(engine, target_date_str):
    """특정 날짜의 모든 티커에 대해 지표 재계산"""
    logger.info(f"Recalculating indicators for {target_date_str}")

    try:
        # 해당 날짜의 모든 티커 조회
        query = """
            SELECT DISTINCT ticker
            FROM stock_prices
            WHERE date = %s
            ORDER BY ticker
        """

        tickers_df = pd.read_sql(query, engine, params=[target_date_str])
        tickers = tickers_df['ticker'].tolist()

        logger.info(f"Found {len(tickers)} tickers for {target_date_str}")

        total_count = 0
        error_count = 0

        for idx, ticker in enumerate(tickers):
            if (idx + 1) % 500 == 0:
                logger.info(f"Processing {idx + 1}/{len(tickers)}")

            try:
                # 해당 티커의 최근 60일 데이터 조회
                price_query = """
                    SELECT date, open_price, high_price, low_price, close_price, volume
                    FROM stock_prices
                    WHERE ticker = %s AND date <= %s
                    ORDER BY date DESC
                    LIMIT 60
                """

                df = pd.read_sql(price_query, engine, params=[ticker, target_date_str])

                if len(df) < 20:
                    error_count += 1
                    continue

                # 날짜 역순으로 정렬
                df = df.sort_values('date').reset_index(drop=True)

                # 지표 계산
                close_prices = df['close_price']
                high_prices = df['high_price']
                low_prices = df['low_price']

                # 각 지표 계산
                rsi = calculate_rsi(close_prices)
                macd, macd_signal, macd_histogram = calculate_macd(close_prices)
                sma_20 = calculate_sma(close_prices, 20)
                bb_upper, bb_middle, bb_lower = calculate_bollinger_bands(close_prices)

                # 최종 값만 추출
                rsi_val = float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None
                macd_val = float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None
                macd_signal_val = float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None
                macd_histogram_val = float(macd_histogram.iloc[-1]) if pd.notna(macd_histogram.iloc[-1]) else None
                sma_20_val = float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None
                bb_upper_val = float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None
                bb_lower_val = float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None

                # 데이터베이스에 저장 (upsert)
                with engine.begin() as conn:
                    conn.execute(text("""
                        INSERT INTO technical_indicators
                        (ticker, date, rsi, macd, macd_signal, sma_20, bb_upper, bb_lower, created_at)
                        VALUES (:ticker, :date, :rsi, :macd, :macd_signal, :sma_20, :bb_upper, :bb_lower, NOW())
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            sma_20 = EXCLUDED.sma_20,
                            bb_upper = EXCLUDED.bb_upper,
                            bb_lower = EXCLUDED.bb_lower,
                            updated_at = NOW()
                    """), {
                        'ticker': ticker,
                        'date': target_date_str,
                        'rsi': rsi_val,
                        'macd': macd_val,
                        'macd_signal': macd_signal_val,
                        'sma_20': sma_20_val,
                        'bb_upper': bb_upper_val,
                        'bb_lower': bb_lower_val,
                    })

                total_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:
                    logger.warning(f"Error calculating indicators for {ticker}: {str(e)}")

        logger.info(f"Completed for {target_date_str}")
        logger.info(f"  - Saved: {total_count}")
        logger.info(f"  - Errors: {error_count}")

        return total_count

    except Exception as e:
        logger.error(f"Error recalculating indicators: {str(e)}")
        raise

def main():
    engine = get_db_connection()

    target_dates = ['2025-10-16', '2025-10-17']
    total_saved = 0

    for target_date in target_dates:
        logger.info(f"{'='*60}")
        saved = recalculate_indicators_for_date(engine, target_date)
        total_saved += saved
        logger.info(f"{'='*60}")

    logger.info(f"\nFinal Summary")
    logger.info(f"Total indicators saved: {total_saved}")

if __name__ == '__main__':
    main()
