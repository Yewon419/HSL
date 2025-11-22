"""
Run Technical Indicator Calculator
"""

import sys
import os
sys.path.append('/app')

from services.indicator_calculator import IndicatorCalculator
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == "__main__":
    # Database connection - detect if running in Docker or locally
    import socket
    try:
        socket.gethostbyname('stock-db')
        db_url = "postgresql://admin:admin123@stock-db:5432/stocktrading"
        logger.info("Running inside Docker, using stock-db hostname")
    except socket.gaierror:
        db_url = "postgresql://admin:admin123@localhost:5435/stocktrading"
        logger.info("Running locally, using localhost")
    
    logger.info("Starting indicator calculation...")
    
    try:
        # Create calculator
        calculator = IndicatorCalculator(db_url)
        
        # Process a few tickers first as test
        test_tickers = ['005930', '000660', '035420']  # Samsung, SK Hynix, Naver
        
        logger.info(f"Testing with {len(test_tickers)} tickers...")
        
        for ticker in test_tickers:
            success = calculator.process_ticker(ticker)
            if success:
                logger.info(f"Successfully processed {ticker}")
            else:
                logger.warning(f"Failed to process {ticker}")
        
        # If test successful, process all
        logger.info("Test successful. Processing all tickers...")
        result = calculator.process_all_tickers(batch_size=20, max_workers=4)
        
        logger.info(f"Processing complete: {result}")
        
    except Exception as e:
        logger.error(f"Error during processing: {e}")
        sys.exit(1)