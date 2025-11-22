#!/usr/bin/env python3
"""
운영 DB에 직접 수집 데이터 저장
"""
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2 import sql

# DB 연결
def get_conn():
    return psycopg2.connect(
        host='192.168.219.103',
        port=5432,
        database='stocktrading',
        user='admin',
        password='admin123'
    )

# 누락된 날짜들
missing_dates = [
    date(2025, 10, 8),
    date(2025, 10, 9),
]

print("=" * 80)
print("Direct collection to operating DB")
print("=" * 80)

for target_date in missing_dates:
    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"\n{target_date}...", end=" ", flush=True)

        # 주가 데이터 수집
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
                pass

        if not all_prices:
            print("No data")
            continue

        prices_df = pd.concat(all_prices, ignore_index=True)
        print(f"Prices: {len(prices_df)}", end=" ", flush=True)

        # DB에 직접 저장
        conn = get_conn()
        cursor = conn.cursor()

        # 기존 데이터 삭제
        cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))

        # 데이터 삽입 (bulk insert)
        insert_values = []
        for _, row in prices_df.iterrows():
            insert_values.append((
                row['ticker'],
                target_date,
                float(row['시가']),
                float(row['고가']),
                float(row['저가']),
                float(row['종가']),
                int(row['거래량'])
            ))

        # bulk insert
        if insert_values:
            cursor.executemany("""
                INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
            """, insert_values)

        conn.commit()
        cursor.close()
        conn.close()

        # collection_log 업데이트
        conn = get_conn()
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO collection_log (collection_date, overall_status, price_count, price_status)
            VALUES (%s, 'success', %s, 'success')
            ON CONFLICT (collection_date) DO UPDATE SET
                overall_status = 'success',
                price_count = %s,
                price_status = 'success',
                updated_at = CURRENT_TIMESTAMP
        """, (target_date, len(insert_values), len(insert_values)))
        conn.commit()
        cursor.close()
        conn.close()

        print("OK")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 80)
print("Completed")
print("=" * 80)
