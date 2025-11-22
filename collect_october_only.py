#!/usr/bin/env python3
"""
October 10-28 데이터만 재수집 (KOSDAQ 포함)
"""
import sys
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# October 10-28 거래일만
missing_dates = [
    date(2025, 10, 10),
    date(2025, 10, 13),
    date(2025, 10, 14),
    date(2025, 10, 15),
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

DB_CONFIG = {
    'host': '192.168.219.103',
    'port': 5432,
    'database': 'stocktrading',
    'user': 'admin',
    'password': 'admin123'
}

def get_db_connection():
    conn = psycopg2.connect(**DB_CONFIG)
    conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
    return conn

def save_stock_prices(prices_df, target_date):
    if prices_df.empty:
        return 0

    conn = get_db_connection()
    cursor = conn.cursor()
    saved_count = 0

    try:
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
    return target_date.weekday() < 5

def collect_and_save(target_date):
    if not is_trading_day(target_date):
        print(f"  Skipped (not a trading day)")
        return 0, 0

    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"Collecting for {target_date}...", end=" ", flush=True)

        # KOSPI + KOSDAQ 모두 수집
        kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
        kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
        tickers = list(set(kospi_tickers + kosdaq_tickers))
        print(f"({len(tickers)} tickers: KOSPI {len(kospi_tickers)} + KOSDAQ {len(kosdaq_tickers)})", end=" ", flush=True)

        all_prices = []
        failed_count = 0
        for ticker in tickers:
            try:
                df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                if not df.empty:
                    df['ticker'] = ticker
                    all_prices.append(df)
            except:
                failed_count += 1
                continue

        prices_saved = 0
        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)
            prices_saved = save_stock_prices(prices_df, target_date)
            print(f"Prices: {prices_saved}", end=" ")

        print(f"OK")
        return prices_saved, 0

    except Exception as e:
        print(f"ERROR: {e}")
        return 0, 0

def main():
    print("=" * 80)
    print("OCTOBER 10-28 RAPID COLLECTION (KOSDAQ INCLUDED)")
    print("=" * 80)

    total_prices = 0
    success_count = 0

    for target_date in missing_dates:
        prices, _ = collect_and_save(target_date)
        total_prices += prices
        if prices > 0:
            success_count += 1

    print("=" * 80)
    print(f"Collection completed!")
    print(f"  - Success: {success_count}/{len(missing_dates)} dates")
    print(f"  - Total prices: {total_prices:,}")
    print("=" * 80)

if __name__ == '__main__':
    main()
