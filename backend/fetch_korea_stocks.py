#!/usr/bin/env python
"""
Korean Stock Market Data Fetcher
Fetches all KOSPI and KOSDAQ stock data for the last 5 years
"""

import sys
import os
import logging
from datetime import datetime
import argparse

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
    parser = argparse.ArgumentParser(description='Fetch Korean stock market data')
    parser.add_argument('--years', type=int, default=5, 
                       help='Number of years of historical data to fetch (default: 5)')
    parser.add_argument('--update-only', action='store_true',
                       help='Only update recent prices (last 30 days)')
    parser.add_argument('--days', type=int, default=30,
                       help='Number of days to update when using --update-only (default: 30)')
    
    args = parser.parse_args()
    
    try:
        logger.info("=" * 60)
        logger.info("Korean Stock Market Data Fetcher")
        logger.info("=" * 60)
        
        # Initialize fetcher
        fetcher = KoreaStockFetcher()
        
        if args.update_only:
            logger.info(f"Updating recent prices for the last {args.days} days...")
            fetcher.update_recent_prices(days=args.days)
        else:
            logger.info(f"Fetching {args.years} years of historical data for all Korean stocks...")
            logger.info("This process may take several hours depending on the number of stocks.")
            logger.info("Please ensure you have a stable internet connection.")
            
            # Confirm before proceeding
            response = input("\nDo you want to continue? (yes/no): ").strip().lower()
            if response not in ['yes', 'y']:
                logger.info("Operation cancelled by user")
                return
            
            # Start fetching
            start_time = datetime.now()
            fetcher.fetch_and_save_all_stocks(years=args.years)
            end_time = datetime.now()
            
            duration = end_time - start_time
            logger.info(f"Total time taken: {duration}")
        
        logger.info("=" * 60)
        logger.info("Data fetching completed successfully!")
        logger.info("=" * 60)
        
    except KeyboardInterrupt:
        logger.warning("\nProcess interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"An error occurred: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()