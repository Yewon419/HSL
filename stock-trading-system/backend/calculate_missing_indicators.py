"""
누락된 기술적 지표 계산 스크립트
16, 17일의 모든 티커에 대해 지표를 계산하고 저장합니다.
"""

import sys
sys.path.insert(0, '/opt/airflow/dags')

from datetime import date
import logging
import pandas as pd
from sqlalchemy import text

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Import common functions
import importlib.util
spec = importlib.util.spec_from_file_location(
    "common_functions",
    "/opt/airflow/dags/common_functions.py"
)
common_functions = importlib.util.module_from_spec(spec)
spec.loader.exec_module(common_functions)

def main():
    """메인 함수"""
    engine = common_functions.get_db_engine('postgres', 5432, 'stocktrading', 'admin', 'admin123')
    target_dates = [date(2025, 10, 16), date(2025, 10, 17)]

    total_saved = 0

    for target_date in target_dates:
        logger.info(f"{'='*60}")
        logger.info(f"Processing date: {target_date}")
        logger.info(f"{'='*60}")

        try:
            # Get all tickers for this date
            query = """
                SELECT DISTINCT ticker
                FROM stock_prices
                WHERE date = :date
                ORDER BY ticker
            """

            with engine.connect() as conn:
                result = conn.execute(text(query), {'date': target_date})
                tickers = [row[0] for row in result]

            logger.info(f"Found {len(tickers)} tickers for {target_date}")

            indicators_list = []
            success_count = 0
            error_count = 0

            for idx, ticker in enumerate(tickers):
                if (idx + 1) % 100 == 0:
                    logger.info(f"Processing ticker {idx + 1}/{len(tickers)}: {ticker}")

                try:
                    indicators = common_functions.calculate_indicators_for_ticker(
                        ticker, target_date, engine
                    )

                    if indicators:
                        indicators_list.append(indicators)
                        success_count += 1
                    else:
                        error_count += 1

                except Exception as e:
                    error_count += 1
                    if error_count <= 5:  # Log first 5 errors only
                        logger.warning(f"Error for {ticker}: {str(e)}")

            logger.info(f"Calculation complete:")
            logger.info(f"  - Success: {success_count}")
            logger.info(f"  - Errors: {error_count}")
            logger.info(f"  - Total to save: {len(indicators_list)}")

            # Save indicators
            saved_count = common_functions.save_technical_indicators(indicators_list, engine)
            logger.info(f"Saved {saved_count} indicators for {target_date}")

            total_saved += saved_count

        except Exception as e:
            logger.error(f"Failed to process {target_date}: {str(e)}")
            raise

    logger.info(f"{'='*60}")
    logger.info(f"Total saved across all dates: {total_saved}")
    logger.info(f"{'='*60}")

if __name__ == '__main__':
    main()
