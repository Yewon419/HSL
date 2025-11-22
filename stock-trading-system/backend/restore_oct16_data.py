#!/usr/bin/env python
"""
Restore Oct 16 stock data using pykrx
"""

import sys
from datetime import datetime
import logging
from pykrx import stock as pykrx_stock
from sqlalchemy import create_engine, text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Database connection
DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
engine = create_engine(DATABASE_URL)

def restore_oct16_data():
    """Restore Oct 17, 2025 stock data"""
    target_date = "20251017"
    target_date_obj = datetime(2025, 10, 17).date()

    logger.info("=" * 60)
    logger.info(f"Restoring data for October 17, 2025")
    logger.info("=" * 60)

    with engine.begin() as conn:
        # Get all active Korean stock tickers
        result = conn.execute(text("""
            SELECT ticker, company_name
            FROM stocks
            WHERE is_active = true AND currency = 'KRW'
            ORDER BY ticker
        """))
        stocks = [{'ticker': row[0], 'name': row[1]} for row in result]

        logger.info(f"Found {len(stocks)} active stocks")

        success_count = 0
        error_count = 0

        for idx, stock_info in enumerate(stocks, 1):
            ticker = stock_info['ticker']

            try:
                # Fetch OHLCV data for Oct 16
                df = pykrx_stock.get_market_ohlcv(target_date, target_date, ticker)

                if not df.empty:
                    row = df.iloc[0]

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
                        'date': target_date_obj,
                        'open_price': float(row['시가']),
                        'high_price': float(row['고가']),
                        'low_price': float(row['저가']),
                        'close_price': float(row['종가']),
                        'volume': int(row['거래량']),
                        'created_at': datetime.now()
                    })

                    success_count += 1

                    if idx % 100 == 0:
                        logger.info(f"Progress: {idx}/{len(stocks)} - Success: {success_count}, Errors: {error_count}")

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    logger.warning(f"Error fetching {ticker}: {e}")
                continue

        # Get market indices
        try:
            # KOSPI
            kospi = pykrx_stock.get_index_ohlcv(target_date, target_date, "1001")
            if not kospi.empty:
                conn.execute(text("""
                    INSERT INTO market_indices
                    (index_name, date, index_value, total_volume, created_at)
                    VALUES (:index_name, :date, :index_value, :total_volume, :created_at)
                    ON CONFLICT (index_name, date) DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        total_volume = EXCLUDED.total_volume
                """), {
                    'index_name': 'KOSPI',
                    'date': target_date_obj,
                    'index_value': float(kospi.iloc[0]['종가']),
                    'total_volume': int(kospi.iloc[0]['거래량']),
                    'created_at': datetime.now()
                })

            # KOSDAQ
            kosdaq = pykrx_stock.get_index_ohlcv(target_date, target_date, "2001")
            if not kosdaq.empty:
                conn.execute(text("""
                    INSERT INTO market_indices
                    (index_name, date, index_value, total_volume, created_at)
                    VALUES (:index_name, :date, :index_value, :total_volume, :created_at)
                    ON CONFLICT (index_name, date) DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        total_volume = EXCLUDED.total_volume
                """), {
                    'index_name': 'KOSDAQ',
                    'date': target_date_obj,
                    'index_value': float(kosdaq.iloc[0]['종가']),
                    'total_volume': int(kosdaq.iloc[0]['거래량']),
                    'created_at': datetime.now()
                })

            logger.info("Market indices collected")

        except Exception as e:
            logger.warning(f"Error collecting market indices: {e}")

    logger.info("=" * 60)
    logger.info(f"Completed! Success: {success_count}, Errors: {error_count}")
    logger.info("=" * 60)

if __name__ == "__main__":
    try:
        restore_oct16_data()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
