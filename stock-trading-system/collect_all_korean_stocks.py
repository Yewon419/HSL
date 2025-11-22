#!/usr/bin/env python3
"""
전체 한국 주식 (코스피/코스닥) 데이터 수집 스크립트
2021년 1월 1일부터 현재까지 모든 종목 데이터를 수집합니다.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
from pykrx import stock
import time
import traceback

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('stock_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return engine

def get_all_korean_stocks():
    """전체 한국 주식 종목 리스트 가져오기"""
    logger.info("Fetching complete list of Korean stocks from KRX...")

    try:
        # 현재 날짜
        today = datetime.now().strftime('%Y%m%d')

        # 코스피 종목 가져오기
        logger.info("Getting KOSPI stocks...")
        kospi_stocks = stock.get_market_ticker_list(date=today, market="KOSPI")
        kospi_names = [stock.get_market_ticker_name(ticker) for ticker in kospi_stocks]

        # 코스닥 종목 가져오기
        logger.info("Getting KOSDAQ stocks...")
        kosdaq_stocks = stock.get_market_ticker_list(date=today, market="KOSDAQ")
        kosdaq_names = [stock.get_market_ticker_name(ticker) for ticker in kosdaq_stocks]

        # 데이터 구성
        all_stocks = []

        for ticker, name in zip(kospi_stocks, kospi_names):
            all_stocks.append({
                'ticker': ticker,
                'company_name': name,
                'market_type': 'KOSPI',
                'currency': 'KRW',
                'is_active': True
            })

        for ticker, name in zip(kosdaq_stocks, kosdaq_names):
            all_stocks.append({
                'ticker': ticker,
                'company_name': name,
                'market_type': 'KOSDAQ',
                'currency': 'KRW',
                'is_active': True
            })

        logger.info(f"Found {len(kospi_stocks)} KOSPI stocks and {len(kosdaq_stocks)} KOSDAQ stocks")
        logger.info(f"Total: {len(all_stocks)} Korean stocks")

        return all_stocks

    except Exception as e:
        logger.error(f"Error fetching stock list: {e}")
        raise

def save_stocks_to_db(stocks_data):
    """주식 종목 정보를 데이터베이스에 저장"""
    logger.info("Saving stock information to database...")

    engine = get_db_connection()

    try:
        with engine.begin() as conn:
            for stock_info in stocks_data:
                conn.execute(text("""
                    INSERT INTO stocks (ticker, company_name, market_type, is_active, currency)
                    VALUES (:ticker, :company_name, :market_type, :is_active, :currency)
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        market_type = EXCLUDED.market_type,
                        is_active = EXCLUDED.is_active,
                        currency = EXCLUDED.currency,
                        updated_at = CURRENT_TIMESTAMP
                """), stock_info)

        logger.info(f"Successfully saved {len(stocks_data)} stock information records")
        return True

    except Exception as e:
        logger.error(f"Error saving stock information: {e}")
        raise

def collect_stock_data(ticker, start_date, end_date):
    """특정 종목의 주가 데이터 수집"""
    try:
        # pykrx로 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)

        if df.empty:
            logger.warning(f"No data found for {ticker}")
            return []

        # 데이터 정리 - 인덱스가 날짜인 경우 컬럼으로 변환
        df = df.reset_index()

        # 컬럼명 확인 및 매핑 (reset_index 후에는 보통 7개 컬럼)
        if len(df.columns) == 7:  # date + 6개 데이터 컬럼
            df.columns = ['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume', 'change_rate']
        else:
            logger.warning(f"Unexpected column count for {ticker}: {len(df.columns)}, columns: {df.columns.tolist()}")
            return []

        # 데이터 변환
        stock_data = []
        for _, row in df.iterrows():
            stock_data.append({
                'ticker': ticker,
                'date': row['date'],
                'open_price': float(row['open_price']),
                'high_price': float(row['high_price']),
                'low_price': float(row['low_price']),
                'close_price': float(row['close_price']),
                'volume': int(row['volume']),
                'created_at': datetime.now()
            })

        return stock_data

    except Exception as e:
        logger.error(f"Error collecting data for {ticker}: {e}")
        return []

def save_stock_data_to_db(stock_data):
    """주가 데이터를 데이터베이스에 저장"""
    if not stock_data:
        return 0

    engine = get_db_connection()

    try:
        with engine.begin() as conn:
            for data in stock_data:
                conn.execute(text("""
                    INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                    VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume,
                        updated_at = CURRENT_TIMESTAMP
                """), data)

        return len(stock_data)

    except Exception as e:
        logger.error(f"Error saving stock data: {e}")
        raise

def collect_all_historical_data():
    """전체 종목의 히스토리 데이터 수집"""
    logger.info("Starting comprehensive historical data collection...")

    # 기간 설정
    start_date = "20210101"
    end_date = datetime.now().strftime('%Y%m%d')

    logger.info(f"Collection period: {start_date} to {end_date}")

    # 전체 종목 리스트 가져오기
    try:
        all_stocks = get_all_korean_stocks()
        save_stocks_to_db(all_stocks)

        total_stocks = len(all_stocks)
        logger.info(f"Starting data collection for {total_stocks} stocks...")

        successful_count = 0
        failed_count = 0
        total_records = 0

        # 각 종목별로 데이터 수집
        for i, stock_info in enumerate(all_stocks):
            ticker = stock_info['ticker']
            company_name = stock_info['company_name']
            market_type = stock_info['market_type']

            try:
                logger.info(f"[{i+1}/{total_stocks}] Collecting {ticker} ({company_name}) - {market_type}")

                # 데이터 수집
                stock_data = collect_stock_data(ticker, start_date, end_date)

                if stock_data:
                    # 데이터베이스에 저장
                    saved_count = save_stock_data_to_db(stock_data)
                    total_records += saved_count
                    successful_count += 1

                    logger.info(f"  -> Saved {saved_count} records for {ticker}")
                else:
                    failed_count += 1
                    logger.warning(f"  -> No data collected for {ticker}")

                # 너무 빠른 요청 방지 (API 제한)
                time.sleep(0.1)

                # 진행 상황 출력
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i+1}/{total_stocks} ({(i+1)/total_stocks*100:.1f}%)")
                    logger.info(f"  Success: {successful_count}, Failed: {failed_count}")
                    logger.info(f"  Total records collected: {total_records}")

            except Exception as e:
                failed_count += 1
                logger.error(f"Error processing {ticker}: {e}")
                continue

        # 최종 결과
        logger.info("=" * 60)
        logger.info("COLLECTION COMPLETED")
        logger.info(f"Total stocks processed: {total_stocks}")
        logger.info(f"Successful: {successful_count}")
        logger.info(f"Failed: {failed_count}")
        logger.info(f"Total records collected: {total_records}")
        logger.info(f"Success rate: {successful_count/total_stocks*100:.1f}%")
        logger.info("=" * 60)

        return {
            'total_stocks': total_stocks,
            'successful': successful_count,
            'failed': failed_count,
            'total_records': total_records
        }

    except Exception as e:
        logger.error(f"Critical error in data collection: {e}")
        traceback.print_exc()
        raise

if __name__ == "__main__":
    try:
        start_time = datetime.now()
        logger.info(f"Starting Korean stock data collection at {start_time}")

        result = collect_all_historical_data()

        end_time = datetime.now()
        duration = end_time - start_time

        logger.info(f"Collection completed in {duration}")
        logger.info(f"Final result: {result}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)