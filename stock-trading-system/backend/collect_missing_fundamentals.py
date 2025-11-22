#!/usr/bin/env python
"""
Collect missing fundamental data for specific date range
"""

import sys
import os
from datetime import datetime, timedelta
import logging
import time

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import SessionLocal
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def collect_fundamentals_for_date(db, date_str, stocks):
    """Collect fundamental data for a specific date"""
    from pykrx import stock as pykrx_stock
    import pandas as pd

    logger.info(f"Collecting fundamentals for {date_str}")

    success_count = 0
    error_count = 0

    for stock_info in stocks:
        ticker = stock_info['ticker']
        try:
            # Get fundamental data from pykrx
            df = pykrx_stock.get_market_fundamental(date_str, date_str, ticker)

            if not df.empty:
                info = df.iloc[-1]

                # Parse data with None for missing/invalid values
                def parse_value(val, value_type='float'):
                    try:
                        if pd.isna(val) or str(val) == 'nan' or val == 0:
                            return None
                        return float(val) if value_type == 'float' else int(val)
                    except:
                        return None

                per = parse_value(info.get('PER'), 'float')
                pbr = parse_value(info.get('PBR'), 'float')
                eps = parse_value(info.get('EPS'), 'int')
                bps = parse_value(info.get('BPS'), 'int')
                div_yield = parse_value(info.get('DIV'), 'float')

                # Only save if we have at least some data
                if any([per, pbr, eps, bps, div_yield]):
                    db.execute(text("""
                        INSERT INTO stock_fundamentals
                        (ticker, date, per, pbr, eps, bps, dividend_yield, created_at)
                        VALUES (:ticker, :date, :per, :pbr, :eps, :bps, :dividend_yield, :created_at)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            per = EXCLUDED.per,
                            pbr = EXCLUDED.pbr,
                            eps = EXCLUDED.eps,
                            bps = EXCLUDED.bps,
                            dividend_yield = EXCLUDED.dividend_yield
                    """), {
                        'ticker': ticker,
                        'date': datetime.strptime(date_str, "%Y%m%d").date(),
                        'per': per,
                        'pbr': pbr,
                        'eps': eps,
                        'bps': bps,
                        'dividend_yield': div_yield,
                        'created_at': datetime.now()
                    })

                    success_count += 1

            # Small delay to avoid API rate limiting
            time.sleep(0.05)

        except Exception as e:
            error_count += 1
            if error_count <= 5:
                logger.warning(f"Error collecting fundamentals for {ticker}: {e}")
            continue

    db.commit()
    logger.info(f"Date {date_str}: {success_count} success, {error_count} errors")
    return success_count, error_count

def collect_missing_fundamentals(start_date_str, end_date_str):
    """Collect fundamental data for missing date range"""
    try:
        logger.info("=" * 60)
        logger.info("Collecting Missing Fundamental Data")
        logger.info("=" * 60)

        # Parse dates
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

        logger.info(f"Date range: {start_date_str} to {end_date_str}")

        db = SessionLocal()

        # Get all active Korean stocks
        result = db.execute(text("""
            SELECT ticker, company_name FROM stocks
            WHERE is_active = true AND currency = 'KRW'
            ORDER BY ticker
        """))
        stocks = [{'ticker': row[0], 'name': row[1]} for row in result]
        logger.info(f"Found {len(stocks)} active stocks in database")

        # Get trading days (weekdays, excluding weekends)
        current_date = start_date
        trading_dates = []

        while current_date <= end_date:
            # Skip weekends (Saturday=5, Sunday=6)
            if current_date.weekday() < 5:
                trading_dates.append(current_date)
            current_date += timedelta(days=1)

        logger.info(f"Processing {len(trading_dates)} potential trading days")

        total_success = 0
        total_errors = 0

        for i, trade_date in enumerate(trading_dates, 1):
            date_str = trade_date.strftime("%Y%m%d")
            logger.info(f"\n{'='*60}")
            logger.info(f"[{i}/{len(trading_dates)}] Processing {trade_date.strftime('%Y-%m-%d')} ({trade_date.strftime('%A')})")
            logger.info(f"{'='*60}")

            success, errors = collect_fundamentals_for_date(db, date_str, stocks)
            total_success += success
            total_errors += errors

            # Progress indicator
            progress = (i / len(trading_dates)) * 100
            logger.info(f"Progress: {progress:.1f}% complete")

        db.close()

        logger.info("=" * 60)
        logger.info("Data collection completed!")
        logger.info(f"Total success: {total_success}")
        logger.info(f"Total errors: {total_errors}")
        logger.info("=" * 60)

        # Verify data
        db = SessionLocal()
        result = db.execute(text("""
            SELECT
                COUNT(*) as total_records,
                COUNT(DISTINCT ticker) as ticker_count,
                COUNT(DISTINCT date) as date_count,
                MIN(date) as earliest_date,
                MAX(date) as latest_date
            FROM stock_fundamentals
            WHERE date >= :start_date AND date <= :end_date
        """), {'start_date': start_date.date(), 'end_date': end_date.date()})

        row = result.fetchone()
        logger.info("\nVerification:")
        logger.info(f"  - Total records: {row[0]:,}")
        logger.info(f"  - Unique tickers: {row[1]}")
        logger.info(f"  - Unique dates: {row[2]}")
        logger.info(f"  - Date range: {row[3]} ~ {row[4]}")
        db.close()

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    # Collect from 2025-09-01 to today (2025-10-15)
    # This will fill in all missing fundamental data
    collect_missing_fundamentals("2025-09-01", "2025-10-15")
