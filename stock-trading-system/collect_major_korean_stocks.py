#!/usr/bin/env python3
"""
주요 한국 주식 데이터 수집 스크립트 (테스트용)
2021년 1월 1일부터 현재까지 주요 종목 데이터를 먼저 수집합니다.
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
        logging.FileHandler('major_stock_collection.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return engine

def get_major_korean_stocks():
    """주요 한국 주식 종목 리스트"""
    # 시가총액 상위 주요 종목들
    major_stocks = [
        # 대형주 (시가총액 상위)
        {'ticker': '005930', 'name': '삼성전자', 'market': 'KOSPI'},
        {'ticker': '000660', 'name': 'SK하이닉스', 'market': 'KOSPI'},
        {'ticker': '207940', 'name': '삼성바이오로직스', 'market': 'KOSPI'},
        {'ticker': '005935', 'name': '삼성전자우', 'market': 'KOSPI'},
        {'ticker': '051910', 'name': 'LG화학', 'market': 'KOSPI'},
        {'ticker': '006400', 'name': '삼성SDI', 'market': 'KOSPI'},
        {'ticker': '035420', 'name': 'NAVER', 'market': 'KOSPI'},
        {'ticker': '012330', 'name': '현대모비스', 'market': 'KOSPI'},
        {'ticker': '028260', 'name': '삼성물산', 'market': 'KOSPI'},
        {'ticker': '066570', 'name': 'LG전자', 'market': 'KOSPI'},
        {'ticker': '105560', 'name': 'KB금융', 'market': 'KOSPI'},
        {'ticker': '055550', 'name': '신한지주', 'market': 'KOSPI'},
        {'ticker': '035720', 'name': '카카오', 'market': 'KOSPI'},
        {'ticker': '005380', 'name': '현대차', 'market': 'KOSPI'},
        {'ticker': '005490', 'name': 'POSCO홀딩스', 'market': 'KOSPI'},
        {'ticker': '068270', 'name': '셀트리온', 'market': 'KOSPI'},
        {'ticker': '015760', 'name': '한국전력', 'market': 'KOSPI'},
        {'ticker': '003550', 'name': 'LG', 'market': 'KOSPI'},
        {'ticker': '096770', 'name': 'SK이노베이션', 'market': 'KOSPI'},
        {'ticker': '017670', 'name': 'SK텔레콤', 'market': 'KOSPI'},

        # 주요 코스닥 종목
        {'ticker': '091990', 'name': '셀트리온헬스케어', 'market': 'KOSDAQ'},
        {'ticker': '196170', 'name': '알테오젠', 'market': 'KOSDAQ'},
        {'ticker': '068760', 'name': '셀트리온제약', 'market': 'KOSDAQ'},
        {'ticker': '403870', 'name': 'HPSP', 'market': 'KOSDAQ'},
        {'ticker': '039030', 'name': '이오테크닉스', 'market': 'KOSDAQ'},
        {'ticker': '247540', 'name': '에코프로비엠', 'market': 'KOSDAQ'},
        {'ticker': '322000', 'name': 'HD현대에너지솔루션', 'market': 'KOSDAQ'},
        {'ticker': '095340', 'name': 'ISC', 'market': 'KOSDAQ'},
        {'ticker': '112040', 'name': '위메이드', 'market': 'KOSDAQ'},
        {'ticker': '058470', 'name': '리노공업', 'market': 'KOSDAQ'},
    ]

    return major_stocks

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
                """), {
                    'ticker': stock_info['ticker'],
                    'company_name': stock_info['name'],
                    'market_type': stock_info['market'],
                    'is_active': True,
                    'currency': 'KRW'
                })

        logger.info(f"Successfully saved {len(stocks_data)} stock information records")
        return True

    except Exception as e:
        logger.error(f"Error saving stock information: {e}")
        raise

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
                        volume = EXCLUDED.volume
                """), data)

        return len(stock_data)

    except Exception as e:
        logger.error(f"Error saving stock data: {e}")
        raise

def collect_major_stocks_data():
    """주요 종목의 히스토리 데이터 수집"""
    logger.info("Starting major Korean stocks data collection...")

    # 기간 설정
    start_date = "20210101"
    end_date = datetime.now().strftime('%Y%m%d')

    logger.info(f"Collection period: {start_date} to {end_date}")

    # 주요 종목 리스트 가져오기
    major_stocks = get_major_korean_stocks()
    save_stocks_to_db(major_stocks)

    total_stocks = len(major_stocks)
    logger.info(f"Starting data collection for {total_stocks} major stocks...")

    successful_count = 0
    failed_count = 0
    total_records = 0

    # 각 종목별로 데이터 수집
    for i, stock_info in enumerate(major_stocks):
        ticker = stock_info['ticker']
        company_name = stock_info['name']
        market_type = stock_info['market']

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

            # API 제한 방지
            time.sleep(0.1)

        except Exception as e:
            failed_count += 1
            logger.error(f"Error processing {ticker}: {e}")
            continue

    # 최종 결과
    logger.info("=" * 60)
    logger.info("MAJOR STOCKS COLLECTION COMPLETED")
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

if __name__ == "__main__":
    try:
        start_time = datetime.now()
        logger.info(f"Starting major Korean stock data collection at {start_time}")

        result = collect_major_stocks_data()

        end_time = datetime.now()
        duration = end_time - start_time

        logger.info(f"Collection completed in {duration}")
        logger.info(f"Final result: {result}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)