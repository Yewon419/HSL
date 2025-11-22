#!/usr/bin/env python
"""Test enhanced stock information collection"""

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
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def test_enhanced_stock_info():
    """Test enhanced stock information collection"""
    
    fetcher = KoreaStockFetcher()
    
    # Test with different types of companies
    test_stocks = [
        ("005930", "KOSPI"),  # 삼성전자 (반도체)
        ("000270", "KOSPI"),  # 기아 (자동차)
        ("035420", "KOSPI"),  # NAVER (IT서비스)
        ("068270", "KOSPI"),  # 셀트리온 (바이오)
    ]
    
    logger.info("=" * 60)
    logger.info("Testing enhanced stock information collection")
    logger.info("=" * 60)
    
    for ticker, market in test_stocks:
        logger.info(f"\nTesting {ticker} ({market})...")
        
        # Get enhanced stock info
        stock_info = fetcher.get_stock_info(ticker, market)
        
        if stock_info:
            logger.info(f"Company: {stock_info.get('company_name')}")
            logger.info(f"Sector: {stock_info.get('sector_name')}")
            logger.info(f"Industry: {stock_info.get('industry_name')}")
            logger.info(f"Market Cap: {stock_info.get('market_cap'):,}" if stock_info.get('market_cap') else "Market Cap: N/A")
            
            if 'fundamentals' in stock_info:
                fundamentals = stock_info['fundamentals']
                logger.info(f"PER: {fundamentals.get('per')}")
                logger.info(f"PBR: {fundamentals.get('pbr')}")
                logger.info(f"EPS: {fundamentals.get('eps')}")
                logger.info(f"BPS: {fundamentals.get('bps')}")
                logger.info(f"Dividend Yield: {fundamentals.get('dividend_yield')}")
            
            # Save to database
            success = fetcher.save_stock_to_db(stock_info)
            logger.info(f"Saved to DB: {success}")
        else:
            logger.error(f"Failed to get info for {ticker}")
        
        logger.info("-" * 40)
    
    # Clean up
    del fetcher
    
    logger.info("Enhanced stock info test completed!")

if __name__ == "__main__":
    test_enhanced_stock_info()