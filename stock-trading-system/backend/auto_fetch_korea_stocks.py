#!/usr/bin/env python
"""
Korean Stock Market Data Fetcher - Auto Version
Fetches all KOSPI and KOSDAQ stock data automatically without user confirmation
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_service.korea_stock_fetcher import KoreaStockFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(f'korea_stock_fetch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)

def main():
    try:
        logger.info("=" * 60)
        logger.info("Korean Stock Market Data Fetcher - AUTO MODE")
        logger.info("=" * 60)
        
        # Initialize fetcher
        fetcher = KoreaStockFetcher()
        
        logger.info("Starting automatic data collection for 2 years of Korean stock data...")
        logger.info("This will collect KOSPI and KOSDAQ stocks without confirmation.")
        
        # Start fetching automatically
        start_time = datetime.now()
        fetcher.fetch_and_save_all_stocks(years=2)
        end_time = datetime.now()
        
        duration = end_time - start_time
        logger.info(f"Total time taken: {duration}")
        
        logger.info("=" * 60)
        logger.info("Data fetching completed successfully!")
        logger.info("=" * 60)
        
        # Show final stats
        logger.info("Final statistics:")
        logger.info("Check database for collected stocks and price data")
        
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()