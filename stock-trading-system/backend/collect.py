#!/usr/bin/env python
"""
한국 주식 데이터 수동 수집 - 재사용 가능 템플릿
사용법: python collect_stock_data.py [YYYY-MM-DD] 또는 python collect_stock_data.py (오늘 날짜 자동)

예시:
  python collect_stock_data.py 2025-10-22
  python collect_stock_data.py
"""

import sys
import os
sys.path.insert(0, '/app')

from datetime import date, datetime, timedelta
from pykrx import stock as pykrx_stock
from database import SessionLocal
from sqlalchemy import text
import pandas as pd
import numpy as np
import logging
import argparse

# ============================================================================
# 🎯 변수 설정 - 이 부분을 수정하여 날짜를 변경하세요
# ============================================================================

# 명령줄 인자 파싱
parser = argparse.ArgumentParser(description='한국 주식 데이터 수집')
parser.add_argument('--date', '-d', help='수집 대상 날짜 (YYYY-MM-DD 형식)', default=None)
parser.add_argument('--skip-indicators', action='store_true', help='지표 계산 스킵')
parser.add_argument('--skip-prices', action='store_true', help='주가 수집 스킵')
args = parser.parse_args()

# 대상 날짜 결정
if args.date:
    try:
        TARGET_DATE = datetime.strptime(args.date, '%Y-%m-%d').date()
    except ValueError:
        print(f"❌ 날짜 형식이 잘못되었습니다: {args.date}")
        print("올바른 형식: YYYY-MM-DD (예: 2025-10-22)")
        sys.exit(1)
else:
    TARGET_DATE = date.today()

DATE_STR = TARGET_DATE.strftime('%Y%m%d')

# ============================================================================
# 로깅 설정
# ============================================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================================================
# 기술지표 계산 함수
# ============================================================================

def calculate_rsi(prices, period=14):
    """RSI (상대강도지수) 계산 - 기본값 14기간"""
    if len(prices) < period + 1:
        return np.full_like(prices, np.nan)

    deltas = np.diff(prices)
    seed = deltas[:period+1]
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period
    rs = up / down if down != 0 else 0
    rsi = np.zeros_like(prices)
    rsi[:period] = 100. - 100. / (1. + rs) if rs != 0 else 0

    for i in range(period, len(prices)):
        delta = deltas[i-1]
        if delta > 0:
            upval = delta
            downval = 0.
        else:
            upval = 0.
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period

        rs = up / down if down != 0 else 0
        rsi[i] = 100. - 100. / (1. + rs) if rs != 0 else 0

    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD (이동평균수렴산산) 계산"""
    exp1 = pd.Series(prices).ewm(span=fast).mean().values
    exp2 = pd.Series(prices).ewm(span=slow).mean().values
    macd = exp1 - exp2
    macd_signal = pd.Series(macd).ewm(span=signal).mean().values
    return macd, macd_signal

def calculate_sma(prices, period):
    """SMA (단순이동평균) 계산"""
    return pd.Series(prices).rolling(window=period).mean().values

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Bollinger Bands (볼린저 밴드) 계산 - 변동성 지표"""
    sma = pd.Series(prices).rolling(window=period).mean().values
    std = pd.Series(prices).rolling(window=period).std().values
    bb_upper = sma + (std * std_dev)
    bb_lower = sma - (std * std_dev)
    return bb_upper, bb_lower

# ============================================================================
# 데이터 수집 함수
# ============================================================================

def check_market_status():
    """시장 운영 상태 확인"""
    logger.info("=" * 80)
    logger.info(f"시장 상태 확인: {TARGET_DATE}")
    logger.info("=" * 80)

    # 요일 확인
    weekday = TARGET_DATE.weekday()  # 0=월, 5=토, 6=일
    day_names = ['월', '화', '수', '목', '금', '토', '일']

    if weekday >= 5:  # 토요일 또는 일요일
        logger.warning(f"⚠️  {day_names[weekday]}요일입니다. 한국 주식시장은 휴장입니다.")
        return False

    logger.info(f"✅ {day_names[weekday]}요일 - 거래일입니다.")

    # 공휴일 확인 (2025년 기준)
    holidays_2025 = [
        date(2025, 1, 1),   # 신정
        date(2025, 2, 10),  # 설 연휴
        date(2025, 3, 1),   # 삼일절
        date(2025, 4, 10),  # 국회의원선거일
        date(2025, 5, 5),   # 어린이날
        date(2025, 5, 15),  # 부처님오신날
        date(2025, 6, 6),   # 현충일
        date(2025, 8, 15),  # 광복절
        date(2025, 9, 16),  # 추석 연휴
        date(2025, 10, 3),  # 개천절
        date(2025, 10, 9),  # 한글날
        date(2025, 12, 25), # 크리스마스
    ]

    if TARGET_DATE in holidays_2025:
        logger.warning(f"⚠️  {TARGET_DATE}는 공휴일입니다. 한국 주식시장은 휴장입니다.")
        return False

    logger.info("✅ 공휴일이 아닙니다.")
    return True

def collect_stock_prices():
    """주가 데이터 수집"""
    logger.info("=" * 80)
    logger.info(f"주가 데이터 수집 시작: {TARGET_DATE}")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        # 거래소 전체 티커 조회
        tickers = pykrx_stock.get_market_ticker_list(date=DATE_STR)
        logger.info(f"거래소에서 {len(tickers)} 개의 티커 조회")

        saved_count = 0
        error_count = 0

        for i, ticker in enumerate(tickers):
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
            except Exception as e:
                error_count += 1
                if (i + 1) % 200 == 0:
                    logger.warning(f"  [{i+1}/{len(tickers)}] {ticker} 오류: {str(e)[:50]}")
                continue

            if (i + 1) % 200 == 0:
                db.commit()
                logger.info(f"  [{i+1}/{len(tickers)}] 진행 중... (성공: {saved_count}, 오류: {error_count})")

        db.commit()
        logger.info(f"✅ 주가 수집 완료: {saved_count} 종목 저장됨")

        # 검증
        result = db.execute(text("SELECT COUNT(*) FROM stock_prices WHERE date = :date"), {'date': TARGET_DATE})
        count = result.fetchone()[0]
        logger.info(f"데이터베이스 확인: {count} 개의 주가 레코드")

        return saved_count

    except Exception as e:
        logger.error(f"주가 수집 중 오류: {e}", exc_info=True)
        raise
    finally:
        db.close()

def calculate_indicators():
    """기술적 지표 계산"""
    logger.info("=" * 80)
    logger.info(f"기술적 지표 계산 시작: {TARGET_DATE}")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        # 모든 주가 데이터 로드
        query = text("""
            SELECT ticker, date, open_price, high_price, low_price, close_price, volume
            FROM stock_prices
            WHERE date <= :target_date
            ORDER BY ticker, date
        """)
        df = pd.read_sql(query, db.bind, params={'target_date': TARGET_DATE})
        logger.info(f"로드된 주가 데이터: {len(df)} 행")

        if df.empty:
            logger.warning("로드된 주가 데이터가 없습니다")
            return 0

        tickers = df['ticker'].unique()
        logger.info(f"처리할 티커: {len(tickers)} 개")

        indicators_list = []
        processed_count = 0

        for i, ticker in enumerate(tickers):
            try:
                ticker_data = df[df['ticker'] == ticker].copy()
                ticker_data = ticker_data.sort_values('date')

                # 최소 20개 데이터 필요 (SMA 200기간 때문에 필요)
                if len(ticker_data) < 20:
                    continue

                # 종가 시리즈
                prices = ticker_data['close_price'].astype(float).values

                # 지표 계산
                rsi = calculate_rsi(prices, period=14)
                macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)
                sma_20 = calculate_sma(prices, period=20)
                sma_50 = calculate_sma(prices, period=50)
                sma_200 = calculate_sma(prices, period=200)
                bb_upper, bb_lower = calculate_bollinger_bands(prices, period=20, std_dev=2)

                # 가장 최신 값 추출
                indicators = {
                    'ticker': ticker,
                    'date': TARGET_DATE,
                    'rsi': float(rsi[-1]) if not np.isnan(rsi[-1]) else None,
                    'macd': float(macd[-1]) if not np.isnan(macd[-1]) else None,
                    'macd_signal': float(macd_signal[-1]) if not np.isnan(macd_signal[-1]) else None,
                    'ma_20': float(sma_20[-1]) if not np.isnan(sma_20[-1]) else None,
                    'ma_50': float(sma_50[-1]) if not np.isnan(sma_50[-1]) else None,
                    'ma_200': float(sma_200[-1]) if not np.isnan(sma_200[-1]) else None,
                    'bollinger_upper': float(bb_upper[-1]) if not np.isnan(bb_upper[-1]) else None,
                    'bollinger_lower': float(bb_lower[-1]) if not np.isnan(bb_lower[-1]) else None,
                }

                indicators_list.append(indicators)
                processed_count += 1

            except Exception as e:
                logger.warning(f"  {ticker} 지표 계산 오류: {str(e)[:50]}")
                continue

            if (i + 1) % 200 == 0:
                logger.info(f"  [{i+1}/{len(tickers)}] 진행 중... (처리: {processed_count})")

        # DB에 저장
        if indicators_list:
            saved_count = save_indicators_to_db(db, indicators_list)
            logger.info(f"✅ 기술적 지표 계산 완료: {saved_count} 종목 저장됨")
            return saved_count
        else:
            logger.warning("계산된 지표가 없습니다")
            return 0

    except Exception as e:
        logger.error(f"기술적 지표 계산 중 오류: {e}", exc_info=True)
        raise
    finally:
        db.close()

def save_indicators_to_db(db, indicators_list):
    """지표를 DB에 저장 - ⚠️ 컬럼명 주의: ma_20, bollinger_upper 등"""
    saved_count = 0

    for i, indicators in enumerate(indicators_list):
        try:
            db.execute(text("""
                INSERT INTO technical_indicators
                (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, ma_200, bollinger_upper, bollinger_lower, created_at)
                VALUES (:ticker, :date, :rsi, :macd, :macd_signal, :ma_20, :ma_50, :ma_200, :bollinger_upper, :bollinger_lower, :created_at)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    rsi = EXCLUDED.rsi,
                    macd = EXCLUDED.macd,
                    macd_signal = EXCLUDED.macd_signal,
                    ma_20 = EXCLUDED.ma_20,
                    ma_50 = EXCLUDED.ma_50,
                    ma_200 = EXCLUDED.ma_200,
                    bollinger_upper = EXCLUDED.bollinger_upper,
                    bollinger_lower = EXCLUDED.bollinger_lower
            """), {
                'ticker': indicators['ticker'],
                'date': indicators['date'],
                'rsi': indicators['rsi'],
                'macd': indicators['macd'],
                'macd_signal': indicators['macd_signal'],
                'ma_20': indicators['ma_20'],
                'ma_50': indicators['ma_50'],
                'ma_200': indicators['ma_200'],
                'bollinger_upper': indicators['bollinger_upper'],
                'bollinger_lower': indicators['bollinger_lower'],
                'created_at': pd.Timestamp.now().to_pydatetime()
            })
            saved_count += 1
        except Exception as e:
            logger.warning(f"  {indicators['ticker']} 저장 오류: {str(e)[:50]}")
            continue

        if (i + 1) % 200 == 0:
            db.commit()
            logger.info(f"  [{i+1}/{len(indicators_list)}] 저장 중...")

    db.commit()
    return saved_count

# ============================================================================
# Main 실행
# ============================================================================

if __name__ == '__main__':
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"한국 주식 데이터 수동 수집")
        logger.info(f"대상 날짜: {TARGET_DATE}")
        logger.info(f"{'='*80}\n")

        # 시장 상태 확인
        if not check_market_status():
            logger.warning("시장이 휴장 중입니다. 계속 진행하시겠습니까? (y/n)")
            response = input().strip().lower()
            if response != 'y':
                logger.info("작업을 취소했습니다.")
                sys.exit(0)

        # 1. 주가 수집
        if not args.skip_prices:
            price_count = collect_stock_prices()
            logger.info("")
        else:
            price_count = 0
            logger.info("주가 수집을 스킵했습니다.\n")

        # 2. 기술지표 계산
        if not args.skip_indicators:
            indicator_count = calculate_indicators()
        else:
            indicator_count = 0
            logger.info("기술지표 계산을 스킵했습니다.\n")

        logger.info(f"\n{'='*80}")
        logger.info(f"작업 완료!")
        logger.info(f"  - 주가: {price_count} 종목 저장")
        logger.info(f"  - 지표: {indicator_count} 종목 계산")
        logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"작업 실패: {e}", exc_info=True)
        sys.exit(1)
