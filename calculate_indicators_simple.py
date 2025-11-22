#!/usr/bin/env python3
"""
기술 지표 계산 (간단한 버전 - numpy 사용)
"""
from datetime import datetime, date
import pandas as pd
import numpy as np
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# DB 연결 설정
DB_CONFIG = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def get_db_connection():
    """DB 연결"""
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def sma(prices, period):
    """Simple Moving Average"""
    if len(prices) < period:
        return None
    return np.mean(prices[-period:])

def bollinger_bands(prices, period=20, std_dev=2):
    """Bollinger Bands"""
    if len(prices) < period:
        return None, None, None

    ma = np.mean(prices[-period:])
    std = np.std(prices[-period:])

    upper = ma + (std * std_dev)
    lower = ma - (std * std_dev)

    return upper, ma, lower

def rsi(prices, period=14):
    """Relative Strength Index"""
    if len(prices) < period + 1:
        return None

    deltas = np.diff(prices[-period-1:])
    seed = deltas[:period]

    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period

    rs = up / down if down != 0 else 0
    rsi_val = 100 - (100 / (1 + rs))

    return rsi_val

def macd(prices, fast=12, slow=26, signal=9):
    """MACD"""
    if len(prices) < slow:
        return None, None, None

    fast_ema = ema(prices, fast)
    slow_ema = ema(prices, slow)

    if fast_ema is None or slow_ema is None:
        return None, None, None

    macd_line = fast_ema - slow_ema
    signal_line = ema_from_series(np.array([macd_line]), signal) if macd_line else None
    histogram = macd_line - signal_line if signal_line else None

    return macd_line, signal_line, histogram

def ema(prices, period):
    """Exponential Moving Average"""
    if len(prices) < period:
        return None

    prices = np.array(prices)
    ema_val = prices[-period:].mean()
    multiplier = 2 / (period + 1)

    for price in prices[-period:]:
        ema_val = price * multiplier + ema_val * (1 - multiplier)

    return ema_val

def ema_from_series(values, period):
    """EMA from a series"""
    if len(values) < period:
        return None
    return values[-1] if len(values) > 0 else None

def stochastic(high_prices, low_prices, close_prices, period=14):
    """Stochastic K%D"""
    if len(close_prices) < period:
        return None, None

    lowest_low = np.min(low_prices[-period:])
    highest_high = np.max(high_prices[-period:])

    k_percent = 100 * (close_prices[-1] - lowest_low) / (highest_high - lowest_low) if (highest_high - lowest_low) > 0 else 0
    d_percent = k_percent  # Simplified

    return k_percent, d_percent

def load_historical_data(ticker, target_date, days=200):
    """과거 데이터 로드"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT close_price, open_price, high_price, low_price, volume
            FROM stock_prices
            WHERE ticker = %s AND date <= %s
            ORDER BY date ASC
            LIMIT %s
        """, (ticker, target_date, days))

        rows = cursor.fetchall()
        if not rows:
            return None, None, None, None, None

        closes = np.array([r[0] for r in rows], dtype=float)
        opens = np.array([r[1] for r in rows], dtype=float)
        highs = np.array([r[2] for r in rows], dtype=float)
        lows = np.array([r[3] for r in rows], dtype=float)
        volumes = np.array([r[4] for r in rows], dtype=float)

        return closes, opens, highs, lows, volumes

    finally:
        cursor.close()
        conn.close()

def calculate_indicators(ticker, closes, opens, highs, lows, volumes):
    """지표 계산"""
    if closes is None or len(closes) < 20:
        return None

    indicators = {}

    try:
        # Moving Averages
        indicators['ma_20'] = sma(closes, 20)
        indicators['ma_50'] = sma(closes, 50) if len(closes) >= 50 else None
        indicators['ma_200'] = sma(closes, 200) if len(closes) >= 200 else None

        # Bollinger Bands
        bb_upper, bb_middle, bb_lower = bollinger_bands(closes, 20, 2)
        indicators['bollinger_upper'] = bb_upper
        indicators['bollinger_middle'] = bb_middle
        indicators['bollinger_lower'] = bb_lower

        # RSI
        indicators['rsi'] = rsi(closes, 14)

        # MACD
        macd_line, macd_signal, macd_hist = macd(closes)
        indicators['macd'] = macd_line
        indicators['macd_signal'] = macd_signal
        indicators['macd_histogram'] = macd_hist

        # Stochastic
        k, d = stochastic(highs, lows, closes, 14)
        indicators['stoch_k'] = k
        indicators['stoch_d'] = d

        # Ichimoku (간단 버전)
        indicators['ichimoku_tenkan'] = None
        indicators['ichimoku_kijun'] = None
        indicators['ichimoku_senkou_a'] = None
        indicators['ichimoku_senkou_b'] = None
        indicators['ichimoku_chikou'] = None

        return indicators

    except Exception as e:
        print(f"Error calculating for {ticker}: {e}")
        return None

def save_indicators(ticker, target_date, indicators):
    """지표 저장"""
    if indicators is None:
        return False

    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            INSERT INTO technical_indicators
            (ticker, date, ma_20, ma_50, ma_200, bollinger_upper, bollinger_middle,
             bollinger_lower, rsi, macd, macd_signal, macd_histogram, stoch_k, stoch_d,
             ichimoku_tenkan, ichimoku_kijun, ichimoku_senkou_a, ichimoku_senkou_b,
             ichimoku_chikou, created_at)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, NOW())
            ON CONFLICT (ticker, date) DO UPDATE SET
                ma_20 = EXCLUDED.ma_20,
                ma_50 = EXCLUDED.ma_50,
                ma_200 = EXCLUDED.ma_200,
                bollinger_upper = EXCLUDED.bollinger_upper,
                bollinger_middle = EXCLUDED.bollinger_middle,
                bollinger_lower = EXCLUDED.bollinger_lower,
                rsi = EXCLUDED.rsi,
                macd = EXCLUDED.macd,
                macd_signal = EXCLUDED.macd_signal,
                macd_histogram = EXCLUDED.macd_histogram,
                stoch_k = EXCLUDED.stoch_k,
                stoch_d = EXCLUDED.stoch_d,
                ichimoku_tenkan = EXCLUDED.ichimoku_tenkan,
                ichimoku_kijun = EXCLUDED.ichimoku_kijun,
                ichimoku_senkou_a = EXCLUDED.ichimoku_senkou_a,
                ichimoku_senkou_b = EXCLUDED.ichimoku_senkou_b,
                ichimoku_chikou = EXCLUDED.ichimoku_chikou
        """, (
            ticker, target_date,
            indicators['ma_20'], indicators['ma_50'], indicators['ma_200'],
            indicators['bollinger_upper'], indicators['bollinger_middle'], indicators['bollinger_lower'],
            indicators['rsi'],
            indicators['macd'], indicators['macd_signal'], indicators['macd_histogram'],
            indicators['stoch_k'], indicators['stoch_d'],
            indicators['ichimoku_tenkan'], indicators['ichimoku_kijun'],
            indicators['ichimoku_senkou_a'], indicators['ichimoku_senkou_b'],
            indicators['ichimoku_chikou']
        ))

        conn.commit()
        return True

    except Exception as e:
        conn.rollback()
        return False

    finally:
        cursor.close()
        conn.close()

def get_tickers_for_date(target_date):
    """특정 날짜의 모든 티커 조회"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT DISTINCT ticker
            FROM stock_prices
            WHERE date = %s
            ORDER BY ticker
        """, (target_date,))

        tickers = [row[0] for row in cursor.fetchall()]
        return tickers

    finally:
        cursor.close()
        conn.close()

def main():
    target_date = date(2025, 10, 31)

    print("=" * 70)
    print(f"Calculating technical indicators for {target_date}")
    print("=" * 70)

    tickers = get_tickers_for_date(target_date)
    print(f"Found {len(tickers)} tickers\n")

    success = 0
    failed = 0

    for i, ticker in enumerate(tickers, 1):
        if i % 100 == 0:
            print(f"Processing {i}/{len(tickers)}...", end="\r", flush=True)

        closes, opens, highs, lows, volumes = load_historical_data(ticker, target_date, 200)

        if closes is None:
            failed += 1
            continue

        indicators = calculate_indicators(ticker, closes, opens, highs, lows, volumes)

        if indicators is None:
            failed += 1
            continue

        if save_indicators(ticker, target_date, indicators):
            success += 1
        else:
            failed += 1

    print(f"\nProcessing 100/{len(tickers)}...Done!")
    print("\n" + "=" * 70)
    print(f"Calculation completed!")
    print(f"  Success: {success}/{len(tickers)}")
    print(f"  Failed: {failed}/{len(tickers)}")
    print("=" * 70)

if __name__ == '__main__':
    main()
