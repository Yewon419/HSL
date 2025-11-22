#!/usr/bin/env python
"""
Calculate Technical Indicators for Oct 2, 2025 data
"""

import sys
import os
import logging
from datetime import datetime
import socket

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from services.indicator_calculator import IndicatorCalculator
from database import SessionLocal
from sqlalchemy import text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("=" * 60)
        logger.info("Calculating Technical Indicators for Oct 2, 2025")
        logger.info("=" * 60)

        # Database connection
        try:
            socket.gethostbyname('stock-db')
            db_url = "postgresql://admin:admin123@stock-db:5432/stocktrading"
            logger.info("Running inside Docker, using stock-db hostname")
        except socket.gaierror:
            db_url = "postgresql://admin:admin123@192.168.219.103:5432/stocktrading"
            logger.info("Running locally, using 192.168.219.103")

        # Get tickers that have data for Oct 2
        db = SessionLocal()
        result = db.execute(text("""
            SELECT DISTINCT ticker
            FROM stock_prices
            WHERE date = '2025-10-02'
            ORDER BY ticker
        """))
        tickers = [row[0] for row in result]
        db.close()

        logger.info(f"Found {len(tickers)} tickers with Oct 2 data")

        # Create calculator
        calculator = IndicatorCalculator(db_url)

        # Process each ticker
        success_count = 0
        error_count = 0

        for i, ticker in enumerate(tickers, 1):
            try:
                if i % 100 == 0:
                    logger.info(f"Progress: {i}/{len(tickers)} tickers")

                # Calculate indicators incrementally from Oct 2
                success = calculator.process_ticker_incremental(ticker, start_date='2025-10-02')

                if success:
                    success_count += 1
                else:
                    error_count += 1

            except Exception as e:
                error_count += 1
                if error_count <= 5:  # Only log first 5 errors
                    logger.warning(f"Error processing {ticker}: {e}")
                continue

        logger.info("=" * 60)
        logger.info(f"Indicator calculation completed!")
        logger.info(f"Success: {success_count}")
        logger.info(f"Errors: {error_count}")
        logger.info(f"Total: {len(tickers)}")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()
