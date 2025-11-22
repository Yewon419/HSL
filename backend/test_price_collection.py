#!/usr/bin/env python
"""Test price data collection with enhanced stock info"""

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

def test_price_collection():
    """Test complete stock info and price collection"""
    
    fetcher = KoreaStockFetcher()
    
    # Test with Samsung Electronics
    ticker = "005930"
    market = "KOSPI"
    
    logger.info("=" * 60)
    logger.info("Testing complete stock and price data collection")
    logger.info("=" * 60)
    
    # 1. Get and save detailed stock info
    logger.info(f"Getting detailed info for {ticker}...")
    detailed_info = fetcher.get_stock_info(ticker, market)
    
    if detailed_info:
        logger.info(f"Company: {detailed_info.get('company_name')}")
        logger.info(f"Sector: {detailed_info.get('sector_name')}")
        logger.info(f"Industry: {detailed_info.get('industry_name')}")
        
        # Save to DB
        success = fetcher.save_stock_to_db(detailed_info)
        logger.info(f"Stock info saved: {success}")
    else:
        logger.error("Failed to get detailed stock info")
        return
    
    # 2. Get and save price data
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * 5)  # 5 years
    start_str = start_date.strftime("%Y%m%d")
    end_str = end_date.strftime("%Y%m%d")
    
    logger.info(f"Fetching price data from {start_str} to {end_str}...")
    prices_df = fetcher.fetch_historical_prices(ticker, start_str, end_str)
    
    if not prices_df.empty:
        logger.info(f"Fetched {len(prices_df)} price records")
        logger.info(f"Date range: {prices_df['date'].min()} to {prices_df['date'].max()}")
        
        # Save price data
        saved_count = fetcher.save_prices_to_db(prices_df)
        logger.info(f"Saved {saved_count} price records to database")
        
        if saved_count > 0:
            logger.info("✅ Price data collection test PASSED")
        else:
            logger.error("❌ Price data collection test FAILED - No records saved")
    else:
        logger.error("❌ Price data collection test FAILED - No data fetched")
    
    # Clean up
    del fetcher
    
    logger.info("=" * 60)
    logger.info("Test completed!")

if __name__ == "__main__":
    test_price_collection()