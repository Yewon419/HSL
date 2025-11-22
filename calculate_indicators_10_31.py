#!/usr/bin/env python3
"""
10월 31일 기술 지표 계산 스크립트
"""
from datetime import datetime, date, timedelta
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import pandas_ta

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

def load_historical_prices(ticker, target_date, days=200):
    """과거 데이터 로드 (200일)"""
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT date, close_price, open_price, high_price, low_price, volume
            FROM stock_prices
            WHERE ticker = %s AND date <= %s
            ORDER BY date DESC
            LIMIT %s
        """, (ticker, target_date, days))

        rows = cursor.fetchall()
        if not rows:
            return None

        df = pd.DataFrame(rows, columns=['date', 'close', 'open', 'high', 'low', 'volume'])
        df = df.iloc[::-1]  # 오름차순으로 정렬
        df['date'] = pd.to_datetime(df['date'])

        return df

    finally:
        cursor.close()
        conn.close()

def calculate_indicators(ticker, prices_df):
    """기술 지표 계산"""
    if prices_df is None or len(prices_df) < 20:
        return None

    try:
        # 필요한 최소 데이터 확인
        if len(prices_df) < 20:
            return None

        # Moving Averages
        ma_20 = prices_df['close'].ta.sma(20)
        ma_50 = prices_df['close'].ta.sma(50) if len(prices_df) >= 50 else None
        ma_200 = prices_df['close'].ta.sma(200) if len(prices_df) >= 200 else None

        # Bollinger Bands
        bbands = prices_df['close'].ta.bbands(length=20)
        if bbands is not None and len(bbands.columns) >= 3:
            bb_upper = bbands.iloc[:, 2]  # BBU
            bb_middle = bbands.iloc[:, 1]  # BBM
            bb_lower = bbands.iloc[:, 0]  # BBL
        else:
            bb_upper = bb_middle = bb_lower = None

        # RSI
        rsi = prices_df['close'].ta.rsi(14)

        # MACD
        macd = prices_df['close'].ta.macd()
        if macd is not None:
            macd_line = macd.iloc[:, 0]
            macd_signal = macd.iloc[:, 1]
            macd_histogram = macd.iloc[:, 2]
        else:
            macd_line = macd_signal = macd_histogram = None

        # Stochastic
        stoch = prices_df[['high', 'low', 'close']].ta.stoch()
        if stoch is not None:
            stoch_k = stoch.iloc[:, 0]
            stoch_d = stoch.iloc[:, 1]
        else:
            stoch_k = stoch_d = None

        # Ichimoku
        ichimoku = prices_df[['high', 'low', 'close']].ta.ichimoku()
        if ichimoku is not None and len(ichimoku.columns) >= 5:
            tenkan = ichimoku.iloc[:, 0]
            kijun = ichimoku.iloc[:, 1]
            senkou_a = ichimoku.iloc[:, 2]
            senkou_b = ichimoku.iloc[:, 3]
            chikou = ichimoku.iloc[:, 4]
        else:
            tenkan = kijun = senkou_a = senkou_b = chikou = None

        # 마지막 행의 값들 추출
        latest_idx = len(prices_df) - 1

        indicators = {
            'ma_20': ma_20.iloc[latest_idx] if ma_20 is not None else None,
            'ma_50': ma_50.iloc[latest_idx] if ma_50 is not None else None,
            'ma_200': ma_200.iloc[latest_idx] if ma_200 is not None else None,
            'bb_upper': bb_upper.iloc[latest_idx] if bb_upper is not None else None,
            'bb_middle': bb_middle.iloc[latest_idx] if bb_middle is not None else None,
            'bb_lower': bb_lower.iloc[latest_idx] if bb_lower is not None else None,
            'rsi': rsi.iloc[latest_idx] if rsi is not None else None,
            'macd': macd_line.iloc[latest_idx] if macd_line is not None else None,
            'macd_signal': macd_signal.iloc[latest_idx] if macd_signal is not None else None,
            'macd_histogram': macd_histogram.iloc[latest_idx] if macd_histogram is not None else None,
            'stoch_k': stoch_k.iloc[latest_idx] if stoch_k is not None else None,
            'stoch_d': stoch_d.iloc[latest_idx] if stoch_d is not None else None,
            'ichimoku_tenkan': tenkan.iloc[latest_idx] if tenkan is not None else None,
            'ichimoku_kijun': kijun.iloc[latest_idx] if kijun is not None else None,
            'ichimoku_senkou_a': senkou_a.iloc[latest_idx] if senkou_a is not None else None,
            'ichimoku_senkou_b': senkou_b.iloc[latest_idx] if senkou_b is not None else None,
            'ichimoku_chikou': chikou.iloc[latest_idx] if chikou is not None else None,
        }

        return indicators

    except Exception as e:
        print(f"Error calculating indicators for {ticker}: {e}")
        return None

def save_indicators(ticker, target_date, indicators):
    """기술 지표 저장"""
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
            indicators['bb_upper'], indicators['bb_middle'], indicators['bb_lower'],
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
        print(f"Error saving indicators for {ticker}: {e}")
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

    # 해당 날짜의 모든 티커 조회
    tickers = get_tickers_for_date(target_date)
    print(f"\nFound {len(tickers)} tickers")

    success_count = 0
    failed_count = 0

    for i, ticker in enumerate(tickers, 1):
        if i % 100 == 0:
            print(f"Processing {i}/{len(tickers)}...", end="\r")

        # 과거 데이터 로드
        prices_df = load_historical_prices(ticker, target_date, days=200)

        if prices_df is None:
            failed_count += 1
            continue

        # 지표 계산
        indicators = calculate_indicators(ticker, prices_df)

        if indicators is None:
            failed_count += 1
            continue

        # 저장
        if save_indicators(ticker, target_date, indicators):
            success_count += 1
        else:
            failed_count += 1

    print("\n" + "=" * 70)
    print(f"Calculation completed!")
    print(f"  Success: {success_count}/{len(tickers)}")
    print(f"  Failed: {failed_count}/{len(tickers)}")
    print("=" * 70)

if __name__ == '__main__':
    main()
