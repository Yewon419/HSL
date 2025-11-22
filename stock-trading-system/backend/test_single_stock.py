#!/usr/bin/env python
"""Test single stock data collection - Samsung Electronics"""

import sys
import os
import logging
from datetime import datetime, timedelta

# Add the backend directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from stock_service.korea_stock_fetcher import KoreaStockFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_single_stock():
    """Test fetching and saving data for Samsung Electronics"""
    
    fetcher = KoreaStockFetcher()
    
    # Test with Samsung Electronics
    ticker = "005930"
    name = "삼성전자"
    market = "KOSPI"
    
    logger.info("=" * 60)
    logger.info(f"Testing single stock: {name} ({ticker})")
    logger.info("=" * 60)
    
    # 1. Save stock info
    stock_info = {
        'ticker': ticker,
        'name': name,
        'market_type': market
    }
    
    logger.info(f"Saving stock info for {ticker}...")
    success = fetcher.save_stock_to_db(stock_info)
    logger.info(f"Stock info saved: {success}")
    
    # 2. Fetch 5 years of price data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 5)
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    logger.info(f"Fetching price data from {start_str} to {end_str}...")
    prices_df = fetcher.fetch_historical_prices(ticker, start_str, end_str)
    
    if not prices_df.empty:
        logger.info(f"Fetched {len(prices_df)} price records")
        logger.info(f"Date range: {prices_df['date'].min()} to {prices_df['date'].max()}")
        logger.info(f"Sample data (first 5 rows):")
        print(prices_df.head())
        
        # 3. Save price data to database
        logger.info("Saving price data to database...")
        saved_count = fetcher.save_prices_to_db(prices_df)
        logger.info(f"Saved {saved_count} price records to database")
    else:
        logger.error("No price data fetched!")
    
    logger.info("=" * 60)
    logger.info("Test completed!")
    logger.info("=" * 60)
    
    # Clean up
    del fetcher

if __name__ == "__main__":
    test_single_stock()