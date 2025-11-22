#!/usr/bin/env python3
"""
수동으로 기술적 지표 생성
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def generate_technical_indicators():
    """기술적 지표 생성"""
    logger.info("Starting technical indicators generation")

    try:
        engine = get_db_connection()

        with engine.connect() as conn:
            # 24일 데이터가 있는 한국 주식 목록 가져오기
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                WHERE s.currency = 'KRW'
                AND sp.date = '2025-09-24'
                ORDER BY s.ticker
            """))
            tickers = [row[0] for row in result]

        logger.info(f"Generating indicators for {len(tickers)} Korean stocks: {tickers}")

        success_count = 0
        for ticker in tickers:
            try:
                logger.info(f"Processing {ticker}...")

                # 주가 데이터 조회 (최근 200일)
                df = pd.read_sql_query(text("""
                    SELECT date, close_price, high_price, low_price, volume
                    FROM stock_prices
                    WHERE ticker = :ticker
                    ORDER BY date DESC
                    LIMIT 200
                """), engine, params={'ticker': ticker})

                if len(df) < 20:
                    logger.warning(f"Insufficient data for {ticker}: {len(df)} records")
                    continue

                logger.info(f"{ticker}: Found {len(df)} records, date range: {df['date'].min()} to {df['date'].max()}")

                df = df.sort_values('date').reset_index(drop=True)
                df['close'] = pd.to_numeric(df['close_price'])
                df['high'] = pd.to_numeric(df['high_price'])
                df['low'] = pd.to_numeric(df['low_price'])
                df['volume'] = pd.to_numeric(df['volume'])

                # 기술적 지표 계산
                # RSI 계산
                def calculate_rsi(prices, window=14):
                    delta = prices.diff()
                    gain = delta.where(delta > 0, 0)
                    loss = -delta.where(delta < 0, 0)
                    avg_gain = gain.rolling(window=window).mean()
                    avg_loss = loss.rolling(window=window).mean()
                    rs = avg_gain / avg_loss
                    return 100 - (100 / (1 + rs))

                # MACD 계산
                def calculate_macd(prices, fast=12, slow=26, signal=9):
                    ema_fast = prices.ewm(span=fast).mean()
                    ema_slow = prices.ewm(span=slow).mean()
                    macd_line = ema_fast - ema_slow
                    signal_line = macd_line.ewm(span=signal).mean()
                    histogram = macd_line - signal_line
                    return macd_line, signal_line, histogram

                # 이동평균 계산
                df['ma_20'] = df['close'].rolling(20).mean()
                df['ma_50'] = df['close'].rolling(50).mean()
                df['ma_200'] = df['close'].rolling(200).mean()

                # RSI
                df['rsi'] = calculate_rsi(df['close'])

                # MACD
                df['macd'], df['macd_signal'], df['macd_histogram'] = calculate_macd(df['close'])

                # 스토캐스틱
                df['lowest_low'] = df['low'].rolling(14).min()
                df['highest_high'] = df['high'].rolling(14).max()
                df['stoch_k'] = 100 * (df['close'] - df['lowest_low']) / (df['highest_high'] - df['lowest_low'])
                df['stoch_d'] = df['stoch_k'].rolling(3).mean()

                # 볼린저 밴드
                df['bb_middle'] = df['close'].rolling(20).mean()
                bb_std = df['close'].rolling(20).std()
                df['bb_upper'] = df['bb_middle'] + (bb_std * 2)
                df['bb_lower'] = df['bb_middle'] - (bb_std * 2)

                # 최근 5일 데이터만 저장
                recent_data = df.tail(5)
                logger.info(f"{ticker}: Processing {len(recent_data)} recent records")

                # 데이터베이스에 저장
                saved_count = 0
                with engine.begin() as conn:
                    for _, row in recent_data.iterrows():
                        if pd.notna(row['rsi']) and pd.notna(row['macd']):
                            conn.execute(text("""
                                INSERT INTO technical_indicators (
                                    ticker, date, rsi, macd, macd_signal, macd_histogram,
                                    stoch_k, stoch_d, ma_20, ma_50, ma_200,
                                    bollinger_upper, bollinger_middle, bollinger_lower
                                ) VALUES (
                                    :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                                    :stoch_k, :stoch_d, :ma_20, :ma_50, :ma_200,
                                    :bb_upper, :bb_middle, :bb_lower
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
                            saved_count += 1

                success_count += 1
                logger.info(f"Generated indicators for {ticker}: {saved_count} records saved")

            except Exception as e:
                logger.error(f"Error generating indicators for {ticker}: {e}")
                import traceback
                traceback.print_exc()
                continue

        logger.info(f"Technical indicators generation completed: {success_count}/{len(tickers)} successful")
        return success_count

    except Exception as e:
        logger.error(f"Technical indicators generation failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    generate_technical_indicators()