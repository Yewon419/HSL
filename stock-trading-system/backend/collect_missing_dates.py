#!/usr/bin/env python
"""
Collect missing fundamental data day by day
This script processes one date at a time with delays to avoid API rate limiting
"""

import sys
import os
from datetime import datetime, timedelta
import logging
import time
import subprocess

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def get_trading_dates(start_date_str, end_date_str):
    """Get list of potential trading dates (weekdays only)"""
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d")

    trading_dates = []
    current_date = start_date

    while current_date <= end_date:
        # Skip weekends (Saturday=5, Sunday=6)
        if current_date.weekday() < 5:
            trading_dates.append(current_date)
        current_date += timedelta(days=1)

    return trading_dates

def main():
    start_date = "2025-09-01"
    end_date = "2025-10-15"
    delay_between_dates = 10  # seconds between dates

    logger.info("=" * 80)
    logger.info("Day-by-Day Fundamental Data Collection")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Delay between dates: {delay_between_dates} seconds")
    logger.info("=" * 80)

    # Get trading dates
    trading_dates = get_trading_dates(start_date, end_date)
    logger.info(f"\nProcessing {len(trading_dates)} potential trading days:")
    for i, date in enumerate(trading_dates, 1):
        logger.info(f"  {i}. {date.strftime('%Y-%m-%d')} ({date.strftime('%A')})")

    logger.info("\n" + "=" * 80)
    logger.info("Starting collection...")
    logger.info("=" * 80)

    total_success = 0
    total_errors = 0
    start_time = datetime.now()

    for i, trade_date in enumerate(trading_dates, 1):
        date_str = trade_date.strftime("%Y-%m-%d")

        logger.info(f"\n{'='*80}")
        logger.info(f"[{i}/{len(trading_dates)}] Processing {date_str} ({trade_date.strftime('%A')})")
        logger.info(f"{'='*80}")

        try:
            # Run the single date collection script
            script_path = os.path.join(os.path.dirname(__file__), "collect_fundamentals_single_date.py")
            result = subprocess.run(
                [sys.executable, script_path, date_str],
                capture_output=True,
                text=True
            )

            # Log output
            if result.stdout:
                logger.info(result.stdout)
            if result.stderr:
                logger.error(result.stderr)

            if result.returncode == 0:
                logger.info(f"✅ Successfully collected data for {date_str}")
            else:
                logger.error(f"❌ Failed to collect data for {date_str}")

            # Progress indicator
            progress = (i / len(trading_dates)) * 100
            elapsed = (datetime.now() - start_time).total_seconds()
            avg_time_per_date = elapsed / i
            remaining_dates = len(trading_dates) - i
            eta_seconds = avg_time_per_date * remaining_dates
            eta = timedelta(seconds=int(eta_seconds))

            logger.info(f"\nProgress: {progress:.1f}% complete ({i}/{len(trading_dates)})")
            logger.info(f"Estimated time remaining: {eta}")

            # Wait before next date (except for last date)
            if i < len(trading_dates):
                logger.info(f"Waiting {delay_between_dates} seconds before next date...")
                time.sleep(delay_between_dates)

        except Exception as e:
            logger.error(f"Error processing {date_str}: {e}")
            continue

    # Final summary
    end_time = datetime.now()
    total_time = end_time - start_time

    logger.info("\n" + "=" * 80)
    logger.info("Day-by-Day Collection Completed!")
    logger.info("=" * 80)
    logger.info(f"Date range: {start_date} to {end_date}")
    logger.info(f"Total dates processed: {len(trading_dates)}")
    logger.info(f"Total time: {total_time}")
    logger.info("=" * 80)

    # Verify data
    logger.info("\nVerifying collected data...")
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from database import SessionLocal
    from sqlalchemy import text

    db = SessionLocal()
    result = db.execute(text("""
        SELECT
            COUNT(*) as total_records,
            COUNT(DISTINCT ticker) as ticker_count,
            COUNT(DISTINCT date) as date_count,
            MIN(date) as earliest_date,
            MAX(date) as latest_date,
            COUNT(CASE WHEN per IS NOT NULL THEN 1 END) as per_count,
            COUNT(CASE WHEN pbr IS NOT NULL THEN 1 END) as pbr_count
        FROM stock_fundamentals
        WHERE date >= :start_date AND date <= :end_date
    """), {
        'start_date': datetime.strptime(start_date, "%Y-%m-%d").date(),
        'end_date': datetime.strptime(end_date, "%Y-%m-%d").date()
    })

    row = result.fetchone()
    logger.info("\nFinal Verification:")
    logger.info(f"  - Total records: {row[0]:,}")
    logger.info(f"  - Unique tickers: {row[1]}")
    logger.info(f"  - Unique dates: {row[2]}")
    logger.info(f"  - Date range: {row[3]} ~ {row[4]}")
    logger.info(f"  - PER values: {row[5]:,}")
    logger.info(f"  - PBR values: {row[6]:,}")
    db.close()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n\nCollection interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
