#!/usr/bin/env python
"""
2025-10-22 누락된 티커 데이터 수집
어제(2025-10-21)와 비교해서 누락된 1,802개 티커 수집
"""

import sys
sys.path.insert(0, '/app')

from datetime import date
from pykrx import stock as pykrx_stock
from database import SessionLocal
from sqlalchemy import text
import pandas as pd
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TARGET_DATE = date(2025, 10, 22)
DATE_STR = TARGET_DATE.strftime('%Y%m%d')

def get_missing_tickers():
    """어제 수집된 것 중 오늘 누락된 티커 조회"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT t1.ticker
            FROM (SELECT DISTINCT ticker FROM stock_prices WHERE date = '2025-10-21') t1
            LEFT JOIN (SELECT DISTINCT ticker FROM stock_prices WHERE date = '2025-10-22') t2
            ON t1.ticker = t2.ticker
            WHERE t2.ticker IS NULL
            ORDER BY t1.ticker
        """)
        result = db.execute(query)
        missing_tickers = [row[0] for row in result.fetchall()]
        return missing_tickers
    finally:
        db.close()

def collect_missing_tickers(missing_tickers):
    """누락된 티커 데이터 수집"""
    logger.info("=" * 80)
    logger.info(f"누락된 {len(missing_tickers)} 개 티커 수집 시작: {TARGET_DATE}")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        saved_count = 0
        error_count = 0

        for i, ticker in enumerate(missing_tickers):
            try:
                df = pykrx_stock.get_market_ohlcv(DATE_STR, DATE_STR, ticker)
                if not df.empty:
                    for date_index, row in df.iterrows():
                        db.execute(text("""
                            INSERT INTO stock_prices
                            (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                            VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                            ON CONFLICT (ticker, date) DO UPDATE SET
                                open_price = EXCLUDED.open_price,
                                high_price = EXCLUDED.high_price,
                                low_price = EXCLUDED.low_price,
                                close_price = EXCLUDED.close_price,
                                volume = EXCLUDED.volume
                        """), {
                            'ticker': ticker,
                            'date': date_index.date(),
                            'open_price': float(row['시가']),
                            'high_price': float(row['고가']),
                            'low_price': float(row['저가']),
                            'close_price': float(row['종가']),
                            'volume': int(row['거래량']),
                            'created_at': pd.Timestamp.now().to_pydatetime()
                        })
                    saved_count += 1
                else:
                    # 데이터 없음 (휴장일, 폐지 종목 등)
                    error_count += 1
            except Exception as e:
                error_count += 1
                if (i + 1) % 200 == 0:
                    logger.warning(f"  [{i+1}/{len(missing_tickers)}] {ticker} 오류: {str(e)[:50]}")
                continue

            if (i + 1) % 200 == 0:
                db.commit()
                logger.info(f"  [{i+1}/{len(missing_tickers)}] 진행 중... (성공: {saved_count}, 오류: {error_count})")

        db.commit()
        logger.info(f"✅ 누락된 티커 수집 완료: {saved_count} 종목 저장됨 (오류/없음: {error_count})")

        # 검증
        result = db.execute(text("SELECT COUNT(*) FROM stock_prices WHERE date = :date"), {'date': TARGET_DATE})
        count = result.fetchone()[0]
        logger.info(f"데이터베이스 확인: {count} 개의 주가 레코드 (누적)")

        return saved_count

    except Exception as e:
        logger.error(f"누락된 티커 수집 중 오류: {e}", exc_info=True)
        raise
    finally:
        db.close()

if __name__ == '__main__':
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"2025-10-22 누락된 티커 수집")
        logger.info(f"{'='*80}\n")

        # 1. 누락된 티커 조회
        missing_tickers = get_missing_tickers()
        logger.info(f"누락된 티커 총 {len(missing_tickers)} 개 발견\n")

        # 2. 누락된 티커 수집
        if missing_tickers:
            saved_count = collect_missing_tickers(missing_tickers)
        else:
            saved_count = 0
            logger.info("누락된 티커가 없습니다")

        logger.info(f"\n{'='*80}")
        logger.info(f"작업 완료!")
        logger.info(f"  - 추가 수집: {saved_count} 종목")
        logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"작업 실패: {e}", exc_info=True)
        sys.exit(1)
