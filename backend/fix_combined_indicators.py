#!/usr/bin/env python
"""
Fix Combined Indicators Script
Updates indicator_id=1 to include all basic indicators (SMA, RSI, MACD, BB)
"""

import sys
import os
import logging
from datetime import datetime, date
import socket
import pandas as pd
import talib
import json

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from models import StockPrice
from sqlalchemy import create_engine, text
from sqlalchemy import func, distinct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_db_url():
    """Get database URL based on environment"""
    try:
        socket.gethostbyname('stock-db')
        return "postgresql://admin:admin123@stock-db:5432/stocktrading"
    except socket.gaierror:
        return "postgresql://admin:admin123@192.168.219.103:5432/stocktrading"

def calculate_all_basic_indicators(df):
    """Calculate all basic technical indicators"""
    indicators = {}

    if len(df) < 50:
        return indicators

    # Moving Averages
    sma_5 = talib.SMA(df['close'], timeperiod=5)
    sma_10 = talib.SMA(df['close'], timeperiod=10)
    sma_20 = talib.SMA(df['close'], timeperiod=20)
    sma_50 = talib.SMA(df['close'], timeperiod=50)

    if len(sma_5) > 0 and pd.notna(sma_5.iloc[-1]):
        indicators['sma_5'] = sma_5.iloc[-1]
    if len(sma_10) > 0 and pd.notna(sma_10.iloc[-1]):
        indicators['sma_10'] = sma_10.iloc[-1]
    if len(sma_20) > 0 and pd.notna(sma_20.iloc[-1]):
        indicators['sma_20'] = sma_20.iloc[-1]
    if len(sma_50) > 0 and pd.notna(sma_50.iloc[-1]):
        indicators['sma_50'] = sma_50.iloc[-1]

    # RSI
    rsi = talib.RSI(df['close'], timeperiod=14)
    if len(rsi) > 0 and pd.notna(rsi.iloc[-1]):
        indicators['rsi'] = rsi.iloc[-1]

    # MACD
    macd, signal, hist = talib.MACD(df['close'])
    if len(macd) > 0 and pd.notna(macd.iloc[-1]):
        indicators['macd'] = macd.iloc[-1]
    if len(signal) > 0 and pd.notna(signal.iloc[-1]):
        indicators['macd_signal'] = signal.iloc[-1]
    if len(hist) > 0 and pd.notna(hist.iloc[-1]):
        indicators['macd_hist'] = hist.iloc[-1]

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower = talib.BBANDS(df['close'])
    if len(bb_upper) > 0 and pd.notna(bb_upper.iloc[-1]):
        indicators['bb_upper'] = bb_upper.iloc[-1]
    if len(bb_middle) > 0 and pd.notna(bb_middle.iloc[-1]):
        indicators['bb_middle'] = bb_middle.iloc[-1]
    if len(bb_lower) > 0 and pd.notna(bb_lower.iloc[-1]):
        indicators['bb_lower'] = bb_lower.iloc[-1]

    # Remove NaN values
    clean_indicators = {}
    for key, value in indicators.items():
        if pd.notna(value):
            clean_indicators[key] = float(value)

    return clean_indicators

def update_samsung_indicators(engine):
    """Update indicators for Samsung only"""
    ticker = '005930'
    try:
        # Get price data
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                ORDER BY date DESC
                LIMIT 200
            """), {"ticker": ticker})

            rows = result.fetchall()
            if len(rows) < 50:
                return False

            # Convert to DataFrame
            df = pd.DataFrame(rows, columns=['date', 'open', 'high', 'low', 'close', 'volume'])
            df = df.sort_values('date')
            df.set_index('date', inplace=True)

            # Get dates since Sept 1 that need updating
            cutoff_date = date(2025, 9, 1)
            new_dates = [idx.date() if hasattr(idx, 'date') else idx for idx in df.index if (idx.date() if hasattr(idx, 'date') else idx) >= cutoff_date]

            if not new_dates:
                return True

            # Calculate indicators for each new date
            updated_count = 0
            for target_date in new_dates:
                # Get data up to target date for calculation
                calc_df = df[df.index <= target_date]
                if len(calc_df) < 50:
                    continue

                indicators = calculate_all_basic_indicators(calc_df)
                if not indicators:
                    continue

                # Save to database (UPSERT)
                conn.execute(text("""
                    INSERT INTO indicator_values
                    (ticker, date, indicator_id, timeframe, value, parameters)
                    VALUES (:ticker, :date, 1, 'daily', :value, :parameters)
                    ON CONFLICT (ticker, date, indicator_id, timeframe)
                    DO UPDATE SET
                        value = EXCLUDED.value
                """), {
                    'ticker': ticker,
                    'date': target_date,
                    'value': json.dumps(indicators),
                    'parameters': json.dumps({"all_basic_indicators": True})
                })
                updated_count += 1

            logger.info(f"Updated {updated_count} indicator records for {ticker}")
            return True

    except Exception as e:
        logger.error(f"Error updating {ticker}: {e}")
        return False

def main():
    logger.info("=== Fix Combined Indicators ===")

    # Get database connection
    db_url = get_db_url()
    engine = create_engine(db_url)

    # Update Samsung indicators
    if update_samsung_indicators(engine):
        logger.info("Successfully updated Samsung indicators")
    else:
        logger.error("Failed to update Samsung indicators")

if __name__ == "__main__":
    main()