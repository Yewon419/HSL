#!/usr/bin/env python3
"""
주요 수집된 주식의 기술적 지표를 계산하는 스크립트
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, date, timedelta
from sqlalchemy import create_engine, text
import time
import traceback

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('major_indicators_calculation.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@192.168.219.103:5432/stocktrading"
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    return engine

def calculate_rsi(prices, period=14):
    """RSI (Relative Strength Index) 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD 계산"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal).mean()
    macd_histogram = macd_line - macd_signal
    return macd_line, macd_signal, macd_histogram

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, sma, lower_band

def calculate_stochastic(high, low, close, period=14):
    """스토캐스틱 오실레이터 계산"""
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(3).mean()
    return k_percent, d_percent

def get_major_stocks():
    """주요 종목 리스트 가져오기"""
    major_tickers = [
        '005930', '000660', '207940', '005935', '051910', '006400',
        '035420', '012330', '028260', '066570', '105560', '055550',
        '035720', '005380', '005490', '068270', '015760', '003550',
        '096770', '017670', '091990', '196170', '068760', '403870',
        '039030', '247540', '322000', '095340', '112040', '058470'
    ]

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            stocks = []
            for ticker in major_tickers:
                result = conn.execute(text("""
                    SELECT s.ticker, s.company_name, s.market_type, COUNT(sp.date) as data_count
                    FROM stocks s
                    JOIN stock_prices sp ON s.ticker = sp.ticker
                    WHERE s.ticker = :ticker AND s.currency = 'KRW' AND s.is_active = true
                    GROUP BY s.ticker, s.company_name, s.market_type
                """), {'ticker': ticker})

                row = result.fetchone()
                if row and row[3] >= 50:  # 최소 50일 데이터가 있는 종목만
                    stocks.append({
                        'ticker': row[0],
                        'company_name': row[1],
                        'market_type': row[2],
                        'data_count': row[3]
                    })

            return stocks

    except Exception as e:
        logger.error(f"Error getting major stocks list: {e}")
        raise

def calculate_indicators_for_stock(ticker):
    """특정 종목의 기술적 지표 계산"""
    engine = get_db_connection()

    try:
        # 주가 데이터 가져오기
        with engine.connect() as conn:
            price_data = pd.read_sql(text("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                ORDER BY date ASC
            """), conn, params={'ticker': ticker})

        if len(price_data) < 50:  # 최소 50일 데이터 필요
            logger.warning(f"Insufficient data for {ticker}: {len(price_data)} records")
            return 0

        # 데이터 처리
        price_data['close'] = pd.to_numeric(price_data['close_price'])
        price_data['high'] = pd.to_numeric(price_data['high_price'])
        price_data['low'] = pd.to_numeric(price_data['low_price'])
        price_data['open'] = pd.to_numeric(price_data['open_price'])
        price_data['volume'] = pd.to_numeric(price_data['volume'])

        # 기술적 지표 계산
        # 이동평균
        price_data['ma_20'] = price_data['close'].rolling(20).mean()
        price_data['ma_50'] = price_data['close'].rolling(50).mean()
        price_data['ma_200'] = price_data['close'].rolling(200).mean()

        # RSI
        price_data['rsi'] = calculate_rsi(price_data['close'])

        # MACD
        price_data['macd'], price_data['macd_signal'], price_data['macd_histogram'] = calculate_macd(price_data['close'])

        # 볼린저 밴드
        price_data['bb_upper'], price_data['bb_middle'], price_data['bb_lower'] = calculate_bollinger_bands(price_data['close'])

        # 스토캐스틱
        price_data['stoch_k'], price_data['stoch_d'] = calculate_stochastic(
            price_data['high'], price_data['low'], price_data['close']
        )

        # 데이터베이스에 저장
        saved_count = 0

        with engine.begin() as conn:
            for _, row in price_data.iterrows():
                # NaN 값 체크
                def safe_float(val):
                    return float(val) if pd.notna(val) else None

                try:
                    conn.execute(text("""
                        INSERT INTO technical_indicators (
                            ticker, date, rsi, macd, macd_signal, macd_histogram,
                            stoch_k, stoch_d, ma_20, ma_50, ma_200,
                            bollinger_upper, bollinger_middle, bollinger_lower,
                            created_at
                        ) VALUES (
                            :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                            :stoch_k, :stoch_d, :ma_20, :ma_50, :ma_200,
                            :bb_upper, :bb_middle, :bb_lower, NOW()
                        ) ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            macd_histogram = EXCLUDED.macd_histogram,
                            stoch_k = EXCLUDED.stoch_k,
                            stoch_d = EXCLUDED.stoch_d,
                            ma_20 = EXCLUDED.ma_20,
                            ma_50 = EXCLUDED.ma_50,
                            ma_200 = EXCLUDED.ma_200,
                            bollinger_upper = EXCLUDED.bollinger_upper,
                            bollinger_middle = EXCLUDED.bollinger_middle,
                            bollinger_lower = EXCLUDED.bollinger_lower
                    """), {
                        'ticker': ticker,
                        'date': row['date'],
                        'rsi': safe_float(row['rsi']),
                        'macd': safe_float(row['macd']),
                        'macd_signal': safe_float(row['macd_signal']),
                        'macd_histogram': safe_float(row['macd_histogram']),
                        'stoch_k': safe_float(row['stoch_k']),
                        'stoch_d': safe_float(row['stoch_d']),
                        'ma_20': safe_float(row['ma_20']),
                        'ma_50': safe_float(row['ma_50']),
                        'ma_200': safe_float(row['ma_200']),
                        'bb_upper': safe_float(row['bb_upper']),
                        'bb_middle': safe_float(row['bb_middle']),
                        'bb_lower': safe_float(row['bb_lower'])
                    })
                    saved_count += 1

                except Exception as e:
                    logger.warning(f"Error saving indicator for {ticker} on {row['date']}: {e}")
                    continue

        return saved_count

    except Exception as e:
        logger.error(f"Error calculating indicators for {ticker}: {e}")
        return 0

def calculate_major_indicators():
    """주요 주식의 기술적 지표 계산"""
    logger.info("Starting technical indicators calculation for major stocks...")

    start_time = datetime.now()

    # 주요 주식 목록 가져오기
    stocks = get_major_stocks()
    total_stocks = len(stocks)

    logger.info(f"Found {total_stocks} major stocks with sufficient data")

    successful_count = 0
    failed_count = 0
    total_indicators = 0

    # 각 종목별로 지표 계산
    for i, stock in enumerate(stocks):
        ticker = stock['ticker']
        company_name = stock['company_name']
        market_type = stock['market_type']
        data_count = stock['data_count']

        try:
            # 진척율 표시
            progress_pct = ((i + 1) / total_stocks) * 100
            logger.info(f"\n{'='*60}")
            logger.info(f"진척율: {i+1}/{total_stocks} ({progress_pct:.1f}%)")
            logger.info(f"처리 중: {ticker} ({company_name}) - {market_type}")
            logger.info(f"데이터: {data_count}개 레코드")
            logger.info(f"{'='*60}")

            # 지표 계산 시작 시간
            stock_start = datetime.now()

            # 지표 계산
            saved_count = calculate_indicators_for_stock(ticker)

            # 처리 시간 계산
            stock_duration = datetime.now() - stock_start

            if saved_count > 0:
                successful_count += 1
                total_indicators += saved_count
                logger.info(f"✓ 완료: {ticker} - {saved_count}개 지표 계산됨 (소요시간: {stock_duration})")
            else:
                failed_count += 1
                logger.warning(f"✗ 실패: {ticker} - 지표 계산 실패")

        except Exception as e:
            failed_count += 1
            logger.error(f"✗ 에러: {ticker} - {e}")
            continue

    end_time = datetime.now()
    duration = end_time - start_time

    # 최종 결과
    logger.info("=" * 60)
    logger.info("MAJOR STOCKS TECHNICAL INDICATORS CALCULATION COMPLETED")
    logger.info(f"Total stocks processed: {total_stocks}")
    logger.info(f"Successful: {successful_count}")
    logger.info(f"Failed: {failed_count}")
    logger.info(f"Total indicators calculated: {total_indicators}")
    logger.info(f"Success rate: {successful_count/total_stocks*100:.1f}%")
    logger.info(f"Processing time: {duration}")
    logger.info("=" * 60)

    return {
        'total_stocks': total_stocks,
        'successful': successful_count,
        'failed': failed_count,
        'total_indicators': total_indicators,
        'duration': duration
    }

if __name__ == "__main__":
    try:
        logger.info("Starting major stocks technical indicators calculation...")
        result = calculate_major_indicators()
        logger.info(f"Final result: {result}")

    except Exception as e:
        logger.error(f"Fatal error: {e}")
        traceback.print_exc()
        sys.exit(1)