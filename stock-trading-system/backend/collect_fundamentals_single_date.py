#!/usr/bin/env python
"""
Collect fundamental data for a single date
Usage: python collect_fundamentals_single_date.py YYYY-MM-DD
"""

import sys
import os
from datetime import datetime
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

def collect_fundamentals_for_date(target_date_str):
    """Collect fundamental data for a specific date"""
    from pykrx import stock as pykrx_stock
    import pandas as pd

    try:
        logger.info("=" * 60)
        logger.info(f"Collecting Fundamentals for {target_date_str}")
        logger.info("=" * 60)

        # Parse date
        target_date = datetime.strptime(target_date_str, "%Y-%m-%d")
        date_str = target_date.strftime("%Y%m%d")

        db = SessionLocal()

        # Get all active Korean stocks
        result = db.execute(text("""
            SELECT ticker, company_name FROM stocks
            WHERE is_active = true AND currency = 'KRW'
            ORDER BY ticker
        """))
        stocks = [{'ticker': row[0], 'name': row[1]} for row in result]
        logger.info(f"Found {len(stocks)} active stocks in database")

        success_count = 0
        error_count = 0

        for i, stock_info in enumerate(stocks, 1):
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
                            'date': target_date.date(),
                            'per': per,
                            'pbr': pbr,
                            'eps': eps,
                            'bps': bps,
                            'dividend_yield': div_yield,
                            'created_at': datetime.now()
                        })

                        success_count += 1

                # Delay to avoid API rate limiting
                time.sleep(0.05)

                # Progress indicator every 100 stocks
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(stocks)} stocks processed ({success_count} saved)")

            except Exception as e:
                error_count += 1
                if error_count <= 10:
                    logger.warning(f"Error collecting fundamentals for {ticker}: {e}")
                continue

        db.commit()
        db.close()

        logger.info("=" * 60)
        logger.info(f"Date {target_date_str} completed!")
        logger.info(f"Success: {success_count}")
        logger.info(f"Errors: {error_count}")
        logger.info("=" * 60)

        # Verify data
        db = SessionLocal()
        result = db.execute(text("""
            SELECT
                COUNT(*) as total_records,
                COUNT(CASE WHEN per IS NOT NULL THEN 1 END) as per_count,
                COUNT(CASE WHEN pbr IS NOT NULL THEN 1 END) as pbr_count,
                COUNT(CASE WHEN eps IS NOT NULL THEN 1 END) as eps_count
            FROM stock_fundamentals
            WHERE date = :date
        """), {'date': target_date.date()})

        row = result.fetchone()
        logger.info("\nVerification:")
        logger.info(f"  - Total records: {row[0]}")
        logger.info(f"  - PER count: {row[1]}")
        logger.info(f"  - PBR count: {row[2]}")
        logger.info(f"  - EPS count: {row[3]}")
        db.close()

        return success_count, error_count

    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python collect_fundamentals_single_date.py YYYY-MM-DD")
        print("Example: python collect_fundamentals_single_date.py 2025-10-15")
        sys.exit(1)

    target_date = sys.argv[1]
    collect_fundamentals_for_date(target_date)
