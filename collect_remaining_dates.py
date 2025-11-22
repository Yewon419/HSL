#!/usr/bin/env python3
"""
2025-10-16 이후 누락된 데이터 수집 스크립트
(이전 스크립트가 2025-10-15에서 멈춘 부분부터 수집)
"""
import sys
import time
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 2025-10-16 이후 남은 날짜들
remaining_dates = [
    date(2025, 10, 16),
    date(2025, 10, 17),
    date(2025, 10, 20),
    date(2025, 10, 21),
    date(2025, 10, 22),
    date(2025, 10, 23),
    date(2025, 10, 24),
    date(2025, 10, 27),
    date(2025, 10, 28),
]

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

def save_stock_prices(prices_df, target_date):
    """주가 데이터 저장 (UPSERT 방식 - TimescaleDB 메타데이터 충돌 방지)"""
    if prices_df.empty:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0

    try:
        # UPSERT 방식으로 저장 (DELETE 대신 ON CONFLICT 사용)
        for _, row in prices_df.iterrows():
            cursor.execute("""
                INSERT INTO stock_prices
                (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    created_at = NOW()
            """, (
                row['ticker'],
                target_date,
                float(row['시가']),
                float(row['고가']),
                float(row['저가']),
                float(row['종가']),
                int(row['거래량'])
            ))
            saved_count += 1

        conn.commit()
    except Exception as e:
        conn.rollback()
        print(f"Error saving prices: {e}")
        raise
    finally:
        cursor.close()
        conn.close()

    return saved_count

def is_trading_day(target_date):
    """거래일 확인 (평일)"""
    return target_date.weekday() < 5

def collect_and_save(target_date):
    """데이터 수집 및 저장"""
    if not is_trading_day(target_date):
        print(f"  Skipped (not a trading day)")
        return 0

    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"Collecting for {target_date}...", end=" ", flush=True)

        # 주가 수집
        tickers = pykrx_stock.get_market_ticker_list(date=date_str)
        print(f"({len(tickers)} tickers)", end=" ", flush=True)

        all_prices = []
        for ticker in tickers:
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except:
                continue

        prices_saved = 0
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            prices_saved = save_stock_prices(prices_df, target_date)
            print(f"Prices: {prices_saved}", end=" ")

        print("OK")
        return prices_saved

    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def main():
    print("=" * 80)
    print("Collecting remaining dates (2025-10-16 onwards)")
    print("=" * 80)

    total_prices = 0
    success_count = 0

    for target_date in remaining_dates:
        prices = collect_and_save(target_date)
        total_prices += prices
        if prices > 0:
            success_count += 1

        # Add a small delay between collections to avoid API throttling
        time.sleep(1)

    print("=" * 80)
    print(f"Collection completed!")
    print(f"  - Success: {success_count}/{len(remaining_dates)} dates")
    print(f"  - Total prices: {total_prices:,}")
    print("=" * 80)

if __name__ == '__main__':
    main()
