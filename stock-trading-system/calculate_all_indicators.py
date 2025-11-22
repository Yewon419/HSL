#!/usr/bin/env python
"""
전체 한국 주식 기술적 지표 계산 스크립트
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
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

def calculate_technical_indicators_for_all_stocks(target_date=None):
    """전체 주식에 대해 기술적 지표 계산"""

    if target_date is None:
        target_date = datetime.now().date()

    logger.info(f"Calculating technical indicators for all Korean stocks on {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 한국 주식 중에서 해당 날짜에 데이터가 있는 종목 가져오기
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                WHERE s.currency = 'KRW'
                AND s.is_active = true
                AND sp.date = :target_date
                ORDER BY s.ticker
            """), {'target_date': target_date})

            tickers = [row[0] for row in result]
            logger.info(f"Processing {len(tickers)} Korean stocks")

            successful_count = 0
            failed_count = 0

            for i, ticker in enumerate(tickers):
                try:
                    # 최근 200일 데이터 가져오기
                    price_data = pd.read_sql(text("""
                        SELECT date, open_price, high_price, low_price, close_price, volume
                        FROM stock_prices
                        WHERE ticker = :ticker
                        AND date <= :target_date
                        ORDER BY date DESC
                        LIMIT 200
                    """), conn, params={'ticker': ticker, 'target_date': target_date})

                    # 시간순으로 다시 정렬 (지표 계산을 위해)
                    price_data = price_data.sort_values('date')

                    logger.info(f"Found {len(price_data)} records for {ticker}")

                    if len(price_data) < 20:  # 최소 20일 데이터 필요
                        logger.warning(f"Insufficient data for {ticker}: {len(price_data)} records")
                        failed_count += 1
                        continue

                    # 데이터 처리
                    price_data['close'] = pd.to_numeric(price_data['close_price'])
                    price_data['high'] = pd.to_numeric(price_data['high_price'])
                    price_data['low'] = pd.to_numeric(price_data['low_price'])
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

                    # 타겟 날짜의 지표만 저장
                    price_data['date'] = pd.to_datetime(price_data['date']).dt.date
                    target_row = price_data[price_data['date'] == target_date]

                    logger.info(f"Target row for {ticker}: {len(target_row)} rows")
                    if len(target_row) > 0:
                        logger.info(f"Target row date: {target_row.iloc[0]['date']}, target_date: {target_date}")

                    if not target_row.empty:
                        row = target_row.iloc[-1]  # 마지막 행

                        # 데이터베이스에 저장
                        with engine.begin() as save_conn:
                            save_conn.execute(text("""
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
                                    bollinger_lower = EXCLUDED.bollinger_lower,
                                    created_at = NOW()
                            """), {
                                'ticker': ticker,
                                'date': target_date,
                                'rsi': float(row['rsi']) if pd.notna(row['rsi']) else None,
                                'macd': float(row['macd']) if pd.notna(row['macd']) else None,
                                'macd_signal': float(row['macd_signal']) if pd.notna(row['macd_signal']) else None,
                                'macd_histogram': float(row['macd_histogram']) if pd.notna(row['macd_histogram']) else None,
                                'stoch_k': float(row['stoch_k']) if pd.notna(row['stoch_k']) else None,
                                'stoch_d': float(row['stoch_d']) if pd.notna(row['stoch_d']) else None,
                                'ma_20': float(row['ma_20']) if pd.notna(row['ma_20']) else None,
                                'ma_50': float(row['ma_50']) if pd.notna(row['ma_50']) else None,
                                'ma_200': float(row['ma_200']) if pd.notna(row['ma_200']) else None,
                                'bb_upper': float(row['bb_upper']) if pd.notna(row['bb_upper']) else None,
                                'bb_middle': float(row['bb_middle']) if pd.notna(row['bb_middle']) else None,
                                'bb_lower': float(row['bb_lower']) if pd.notna(row['bb_lower']) else None
                            })

                        successful_count += 1

                    # 진행상황 출력
                    if (i + 1) % 50 == 0:
                        logger.info(f"Processed {i + 1}/{len(tickers)} stocks ({successful_count} successful)")

                except Exception as e:
                    logger.warning(f"Error calculating indicators for {ticker}: {e}")
                    failed_count += 1
                    continue

            logger.info(f"Technical indicators calculation completed:")
            logger.info(f"  - Successful: {successful_count}")
            logger.info(f"  - Failed: {failed_count}")
            logger.info(f"  - Total processed: {successful_count + failed_count}")

            return successful_count

    except Exception as e:
        logger.error(f"Error in technical indicators calculation: {e}")
        raise

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='Calculate technical indicators for all Korean stocks')
    parser.add_argument('--date', type=str, help='Target date (YYYY-MM-DD format)',
                       default=datetime.now().strftime('%Y-%m-%d'))

    args = parser.parse_args()

    try:
        target_date = datetime.strptime(args.date, '%Y-%m-%d').date()
        success_count = calculate_technical_indicators_for_all_stocks(target_date)
        logger.info(f"Successfully calculated indicators for {success_count} stocks on {target_date}")
    except Exception as e:
        logger.error(f"Failed to calculate indicators: {e}")
        sys.exit(1)