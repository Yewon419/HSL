#!/usr/bin/env python3
"""
2021년 데이터가 없는 종목들의 2021년도 데이터만 수집하는 스크립트
"""

import os
import sys
import logging
from datetime import datetime, date
from sqlalchemy import create_engine, text
from pykrx import stock
import time

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('collect_missing_2021.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return engine

def get_stocks_missing_2021_data():
    """2021년 데이터가 없는 종목 조회"""
    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker, s.company_name, s.market_type
                FROM stocks s
                WHERE s.currency = 'KRW'
                  AND s.is_active = true
                  AND NOT EXISTS (
                      SELECT 1
                      FROM stock_prices sp
                      WHERE sp.ticker = s.ticker
                        AND sp.date >= '2021-01-01'
                        AND sp.date < '2022-01-01'
                  )
                ORDER BY s.market_type, s.ticker
            """))

            stocks = []
            for row in result:
                stocks.append({
                    'ticker': row[0],
                    'company_name': row[1],
                    'market_type': row[2]
                })

            return stocks

    except Exception as e:
        logger.error(f"Error getting stocks list: {e}")
        raise

def collect_2021_data_for_stock(ticker, company_name, market_type):
    """특정 종목의 2021년 데이터 수집"""
    engine = get_db_connection()

    try:
        # 2021년 전체 데이터 가져오기
        start_date = "20210101"
        end_date = "20211231"

        logger.info(f"  PyKRX에서 2021년 데이터 가져오는 중...")

        # pykrx로 데이터 가져오기
        df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)

        if df is None or len(df) == 0:
            logger.warning(f"  2021년 데이터 없음")
            return 0

        # 데이터 저장
        saved_count = 0

        with engine.begin() as conn:
            for date_idx, row in df.iterrows():
                try:
                    conn.execute(text("""
                        INSERT INTO stock_prices (
                            ticker, date, open_price, high_price, low_price,
                            close_price, volume, created_at
                        ) VALUES (
                            :ticker, :date, :open_price, :high_price, :low_price,
                            :close_price, :volume, NOW()
                        ) ON CONFLICT (ticker, date) DO UPDATE SET
                            open_price = EXCLUDED.open_price,
                            high_price = EXCLUDED.high_price,
                            low_price = EXCLUDED.low_price,
                            close_price = EXCLUDED.close_price,
                            volume = EXCLUDED.volume
                    """), {
                        'ticker': ticker,
                        'date': date_idx.date(),
                        'open_price': float(row['시가']),
                        'high_price': float(row['고가']),
                        'low_price': float(row['저가']),
                        'close_price': float(row['종가']),
                        'volume': int(row['거래량'])
                    })
                    saved_count += 1

                except Exception as e:
                    logger.warning(f"  Error saving data for {date_idx.date()}: {e}")
                    continue

        return saved_count

    except Exception as e:
        logger.error(f"  Error collecting data: {e}")
        return 0

def main():
    """메인 함수"""
    logger.info("=" * 80)
    logger.info("2021년 데이터 누락 종목 수집 시작")
    logger.info("=" * 80)

    start_time = datetime.now()

    # 2021년 데이터가 없는 종목 조회
    logger.info("2021년 데이터가 없는 종목 조회 중...")
    stocks = get_stocks_missing_2021_data()
    total_stocks = len(stocks)

    logger.info(f"\n발견된 종목 수: {total_stocks}개")

    if total_stocks == 0:
        logger.info("모든 종목에 2021년 데이터가 있습니다!")
        return

    successful_count = 0
    failed_count = 0
    total_records = 0

    # 각 종목별로 2021년 데이터 수집
    for i, stock_info in enumerate(stocks):
        ticker = stock_info['ticker']
        company_name = stock_info['company_name']
        market_type = stock_info['market_type']

        try:
            # 진척율 표시
            progress_pct = ((i + 1) / total_stocks) * 100
            logger.info(f"\n{'='*80}")
            logger.info(f"진척율: {i+1}/{total_stocks} ({progress_pct:.1f}%)")
            logger.info(f"종목: {ticker} ({company_name}) - {market_type}")
            logger.info(f"{'='*80}")

            # 데이터 수집 시작
            stock_start = datetime.now()

            saved_count = collect_2021_data_for_stock(ticker, company_name, market_type)

            # 처리 시간
            stock_duration = datetime.now() - stock_start

            if saved_count > 0:
                successful_count += 1
                total_records += saved_count
                logger.info(f"✓ 완료: {saved_count}개 레코드 저장 (소요시간: {stock_duration})")
            else:
                failed_count += 1
                logger.warning(f"✗ 실패: 데이터 없음")

            # API 호출 제한 방지 (초당 최대 1회)
            time.sleep(1)

        except Exception as e:
            failed_count += 1
            logger.error(f"✗ 에러: {ticker} - {e}")
            continue

    # 최종 결과
    end_time = datetime.now()
    duration = end_time - start_time

    logger.info("\n" + "=" * 80)
    logger.info("2021년 데이터 수집 완료")
    logger.info("=" * 80)
    logger.info(f"총 처리 종목: {total_stocks}개")
    logger.info(f"성공: {successful_count}개")
    logger.info(f"실패: {failed_count}개")
    logger.info(f"수집된 레코드: {total_records}개")
    logger.info(f"성공률: {successful_count/total_stocks*100:.1f}%")
    logger.info(f"소요 시간: {duration}")
    logger.info("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)