#!/usr/bin/env python
"""
2025-10-22 누락된 티커의 기술적 지표 계산
새로 수집된 1,802개 티커의 지표 계산
"""

import sys
sys.path.insert(0, '/app')

from datetime import date
from database import SessionLocal
from sqlalchemy import text
import pandas as pd
import numpy as np
import logging

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

TARGET_DATE = date(2025, 10, 22)

def calculate_rsi(prices, period=14):
    """RSI 계산"""
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
    """MACD 계산"""
    exp1 = pd.Series(prices).ewm(span=fast).mean().values
    exp2 = pd.Series(prices).ewm(span=slow).mean().values
    macd = exp1 - exp2
    macd_signal = pd.Series(macd).ewm(span=signal).mean().values
    return macd, macd_signal

def calculate_sma(prices, period):
    """SMA 계산"""
    return pd.Series(prices).rolling(window=period).mean().values

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """Bollinger Bands 계산"""
    sma = pd.Series(prices).rolling(window=period).mean().values
    std = pd.Series(prices).rolling(window=period).std().values
    bb_upper = sma + (std * std_dev)
    bb_lower = sma - (std * std_dev)
    return bb_upper, bb_lower

def get_missing_tickers_for_indicators():
    """지표가 없는 티커 조회"""
    db = SessionLocal()
    try:
        query = text("""
            SELECT sp.ticker
            FROM (SELECT DISTINCT ticker FROM stock_prices WHERE date = :target_date) sp
            LEFT JOIN (SELECT DISTINCT ticker FROM technical_indicators WHERE date = :target_date) ti
            ON sp.ticker = ti.ticker
            WHERE ti.ticker IS NULL
            ORDER BY sp.ticker
        """)
        result = db.execute(query, {'target_date': TARGET_DATE})
        missing_tickers = [row[0] for row in result.fetchall()]
        return missing_tickers
    finally:
        db.close()

def calculate_missing_indicators(missing_tickers):
    """지표가 없는 티커의 지표 계산"""
    logger.info("=" * 80)
    logger.info(f"누락된 {len(missing_tickers)} 개 티커 지표 계산 시작: {TARGET_DATE}")
    logger.info("=" * 80)

    db = SessionLocal()
    try:
        # 모든 주가 데이터 로드
        query = text("""
            SELECT ticker, date, close_price
            FROM stock_prices
            WHERE date <= :target_date
            ORDER BY ticker, date
        """)
        df = pd.read_sql(query, db.bind, params={'target_date': TARGET_DATE})
        logger.info(f"로드된 주가 데이터: {len(df)} 행")

        if df.empty:
            logger.warning("로드된 주가 데이터가 없습니다")
            return 0

        indicators_list = []
        processed_count = 0

        for i, ticker in enumerate(missing_tickers):
            try:
                ticker_data = df[df['ticker'] == ticker].copy()
                ticker_data = ticker_data.sort_values('date')

                if len(ticker_data) < 20:
                    continue

                # 종가 시리즈
                prices = ticker_data['close_price'].astype(float).values

                # RSI 계산
                rsi = calculate_rsi(prices, period=14)

                # MACD 계산
                macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)

                # SMA 계산
                sma_20 = calculate_sma(prices, period=20)
                sma_50 = calculate_sma(prices, period=50)
                sma_200 = calculate_sma(prices, period=200)

                # Bollinger Bands 계산
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
                logger.info(f"  [{i+1}/{len(missing_tickers)}] 진행 중... (처리: {processed_count})")

        # DB에 저장
        if indicators_list:
            saved_count = save_indicators_to_db(db, indicators_list)
            logger.info(f"✅ 누락된 티커 지표 계산 완료: {saved_count} 종목 저장됨")
            return saved_count
        else:
            logger.warning("계산된 지표가 없습니다")
            return 0

    except Exception as e:
        logger.error(f"지표 계산 중 오류: {e}", exc_info=True)
        raise
    finally:
        db.close()

def save_indicators_to_db(db, indicators_list):
    """지표를 DB에 저장"""
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

if __name__ == '__main__':
    try:
        logger.info(f"\n{'='*80}")
        logger.info(f"2025-10-22 누락된 티커 지표 계산")
        logger.info(f"{'='*80}\n")

        # 1. 지표가 없는 티커 조회
        missing_tickers = get_missing_tickers_for_indicators()
        logger.info(f"지표 계산 필요한 티커: {len(missing_tickers)} 개\n")

        # 2. 지표 계산
        if missing_tickers:
            saved_count = calculate_missing_indicators(missing_tickers)
        else:
            saved_count = 0
            logger.info("지표가 이미 계산되었습니다")

        logger.info(f"\n{'='*80}")
        logger.info(f"작업 완료!")
        logger.info(f"  - 계산된 지표: {saved_count} 종목")
        logger.info(f"{'='*80}\n")

    except Exception as e:
        logger.error(f"작업 실패: {e}", exc_info=True)
        sys.exit(1)
