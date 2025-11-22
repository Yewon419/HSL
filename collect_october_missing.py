#!/usr/bin/env python3
"""
10월 미수집 날짜 데이터 수동 수집 스크립트
"""
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 미수집 날짜 (10월만)
missing_dates = [
    date(2025, 10, 8),
    date(2025, 10, 9),
    date(2025, 10, 31),
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
    """주가 데이터 저장 (UPSERT 방식)"""
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
    """거래일 확인 (평일)"""
    return target_date.weekday() < 5

def collect_and_save(target_date):
    """데이터 수집 및 저장"""
    if not is_trading_day(target_date):
        print(f"  Skipped (not a trading day)")
        return 0

    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"Collecting {target_date}...", end=" ", flush=True)

        # 주가 수집 (KOSPI + KOSDAQ)
        kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
        kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
        tickers = list(set(kospi_tickers + kosdaq_tickers))
        print(f"Tickers: {len(tickers)} ", end="", flush=True)

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
            print(f"| Saved: {prices_saved:,} prices | OK")
        else:
            print("| No data found")

        return prices_saved

    except Exception as e:
        print(f"ERROR: {e}")
        return 0

def main():
    print("=" * 70)
    print("October Missing Data Collection")
    print("=" * 70)

    total_prices = 0
    success_count = 0

    for target_date in missing_dates:
        prices = collect_and_save(target_date)
        total_prices += prices
        if prices > 0:
            success_count += 1

    print("=" * 70)
    print(f"Collection completed!")
    print(f"  Success: {success_count}/{len(missing_dates)} dates")
    print(f"  Total prices: {total_prices:,}")
    print("=" * 70)

if __name__ == '__main__':
    main()
