#!/usr/bin/env python
"""
Collect missing stock data for specific dates
"""

import sys
import os
from datetime import datetime, timedelta
import logging

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_service.korea_stock_fetcher import KoreaStockFetcher
from database import SessionLocal
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def collect_data_for_dates(start_date_str, end_date_str):
    """Collect stock data for specific date range"""
    try:
        logger.info("=" * 60)
        logger.info("Collecting Missing Stock Data")
        logger.info("=" * 60)

        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        logger.info(f"Date range: {start_date_str} to {end_date_str}")

        # Initialize fetcher
        fetcher = KoreaStockFetcher()
        db = SessionLocal()

        # Get all active tickers from database
        result = db.execute(text("""
            SELECT ticker, company_name, market_type
            FROM stocks
            WHERE is_active = true AND currency = 'KRW'
            ORDER BY ticker
        """))
        stocks = [{'ticker': row[0], 'name': row[1], 'market': row[2]} for row in result]
        logger.info(f"Found {len(stocks)} active stocks in database")

        # Collect data for each date
        current_date = start_date
        while current_date <= end_date:
            date_str = current_date.strftime("%Y-%m-%d")
            logger.info(f"\n{'='*60}")
            logger.info(f"Collecting data for {date_str}")
            logger.info(f"{'='*60}")

            # Fetch price data for this date
            success_count = 0
            error_count = 0

            for stock_info in stocks:
                ticker = stock_info['ticker']
                try:
                    # Fetch historical price data for just this date
                    from_date = current_date.strftime("%Y%m%d")
                    to_date = current_date.strftime("%Y%m%d")

                    from pykrx import stock as pykrx_stock
                    df = pykrx_stock.get_market_ohlcv(from_date, to_date, ticker)

                    if not df.empty:
                        for date_index, row in df.iterrows():
                            # Insert into database
                            db.execute(text("""
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

                        db.commit()
                        success_count += 1

                        if success_count % 50 == 0:
                            logger.info(f"Progress: {success_count}/{len(stocks)} stocks processed")

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Only log first 5 errors
                        logger.warning(f"Error fetching {ticker}: {e}")
                    continue

            logger.info(f"Completed {date_str}: {success_count} stocks, {error_count} errors")

            # Also collect market indices for this date
            try:
                from pykrx import stock as pykrx_stock
                date_fmt = current_date.strftime("%Y%m%d")

                # KOSPI
                kospi_value = pykrx_stock.get_index_ohlcv(date_fmt, date_fmt, "1001")
                if not kospi_value.empty:
                    close_val = float(kospi_value.iloc[0]['종가'])
                    volume_val = int(kospi_value.iloc[0]['거래량'])

                    db.execute(text("""
                        INSERT INTO market_indices
                        (index_name, date, index_value, total_volume, created_at)
                        VALUES (:index_name, :date, :index_value, :total_volume, :created_at)
                        ON CONFLICT (index_name, date) DO UPDATE SET
                            index_value = EXCLUDED.index_value,
                            total_volume = EXCLUDED.total_volume
                    """), {
                        'index_name': 'KOSPI',
                        'date': current_date.date(),
                        'index_value': close_val,
                        'total_volume': volume_val,
                        'created_at': datetime.now()
                    })

                # KOSDAQ
                kosdaq_value = pykrx_stock.get_index_ohlcv(date_fmt, date_fmt, "2001")
                if not kosdaq_value.empty:
                    close_val = float(kosdaq_value.iloc[0]['종가'])
                    volume_val = int(kosdaq_value.iloc[0]['거래량'])

                    db.execute(text("""
                        INSERT INTO market_indices
                        (index_name, date, index_value, total_volume, created_at)
                        VALUES (:index_name, :date, :index_value, :total_volume, :created_at)
                        ON CONFLICT (index_name, date) DO UPDATE SET
                            index_value = EXCLUDED.index_value,
                            total_volume = EXCLUDED.total_volume
                    """), {
                        'index_name': 'KOSDAQ',
                        'date': current_date.date(),
                        'index_value': close_val,
                        'total_volume': volume_val,
                        'created_at': datetime.now()
                    })

                db.commit()
                logger.info(f"Market indices collected for {date_str}")

            except Exception as e:
                logger.warning(f"Error collecting market indices for {date_str}: {e}")

            # Move to next date
            current_date += timedelta(days=1)

        db.close()
        logger.info("=" * 60)
        logger.info("Data collection completed successfully!")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Collect data for Oct 16, 2025 (restore deleted data)
    collect_data_for_dates("2025-10-16", "2025-10-16")
