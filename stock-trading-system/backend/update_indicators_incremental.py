#!/usr/bin/env python
"""
Incremental Technical Indicator Update Script
Updates indicators only for new price data (since 2025-09-01)
"""

import sys
import os
import logging
from datetime import datetime, date
import socket

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.indicator_calculator import IndicatorCalculator
from database import SessionLocal
from models import StockPrice
from sqlalchemy import func, distinct

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'indicator_update_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def get_tickers_with_new_data():
    """Get list of tickers that have new price data since 2025-09-01"""
    db = SessionLocal()
    try:
        cutoff_date = date(2025, 9, 1)

        # Get tickers with new price data
        result = db.query(distinct(StockPrice.ticker)).filter(
            StockPrice.date >= cutoff_date
        ).all()

        tickers = [row[0] for row in result]
        logger.info(f"Found {len(tickers)} tickers with new data since {cutoff_date}")
        return tickers

    finally:
        db.close()

def main():
    try:
        logger.info("=" * 60)
        logger.info("Incremental Technical Indicator Update")
        logger.info("=" * 60)

        # Database connection - detect if running in Docker or locally
        try:
            socket.gethostbyname('stock-db')
            db_url = "postgresql://admin:admin123@stock-db:5432/stocktrading"
            logger.info("Running inside Docker, using stock-db hostname")
        except socket.gaierror:
            db_url = "postgresql://admin:admin123@localhost:5435/stocktrading"
            logger.info("Running locally, using localhost")

        # Get tickers with new data
        tickers_to_update = get_tickers_with_new_data()

        if not tickers_to_update:
            logger.info("No tickers found with new data. Exiting.")
            return

        # Create calculator
        calculator = IndicatorCalculator(db_url)

        # Process each ticker
        success_count = 0
        error_count = 0

        logger.info(f"Starting incremental update for {len(tickers_to_update)} tickers...")

        for i, ticker in enumerate(tickers_to_update, 1):
            try:
                logger.info(f"Processing {i}/{len(tickers_to_update)}: {ticker}")

                # Use update mode to only process new dates
                success = calculator.process_ticker_incremental(ticker, start_date='2025-09-01')

                if success:
                    success_count += 1
                    logger.info(f"✓ Successfully updated {ticker}")
                else:
                    error_count += 1
                    logger.warning(f"✗ Failed to update {ticker}")

            except Exception as e:
                error_count += 1
                logger.error(f"✗ Error processing {ticker}: {e}")
                continue

        logger.info("=" * 60)
        logger.info(f"Update completed!")
        logger.info(f"Success: {success_count}")
        logger.info(f"Errors: {error_count}")
        logger.info(f"Total: {len(tickers_to_update)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()