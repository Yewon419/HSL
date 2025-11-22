#!/usr/bin/env python3
"""
간단한 누락된 날짜 데이터 수집
"""
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from sqlalchemy import create_engine, text

# DB 엔진 생성
engine = create_engine("postgresql://admin:admin123@192.168.219.103:5432/stocktrading")

# 누락된 날짜들
missing_dates = [
    date(2025, 10, 8),
    date(2025, 10, 9),
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
]

total_prices = 0
total_indices = 0
success = 0

print("=" * 80)
print("Collecting missing data")
print("=" * 80)

for target_date in missing_dates:
    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"\n{target_date}...", end=" ", flush=True)

        # 주가 데이터
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

        if all_prices:
            prices_df = pd.concat(all_prices, ignore_index=True)

            # 준비된 가격 데이터
            insert_data = []
            for _, row in prices_df.iterrows():
                insert_data.append({
                    'ticker': row['ticker'],
                    'date': target_date,
                    'open_price': float(row['시가']),
                    'high_price': float(row['고가']),
                    'low_price': float(row['저가']),
                    'close_price': float(row['종가']),
                    'volume': int(row['거래량'])
                })

            # bulk insert
            if insert_data:
                with engine.begin() as conn:
                    # 먼저 기존 데이터 삭제
                    conn.execute(text("DELETE FROM stock_prices WHERE date = :date"), {"date": target_date})
                    # 새로운 데이터 삽입
                    for data in insert_data:
                        conn.execute(text("""
                            INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                            VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, NOW())
                        """), data)

            total_prices += len(insert_data)
            print(f"Prices: {len(insert_data)}", end=" ", flush=True)

        # 지수 데이터
        indices_list = []

        for idx_code, idx_name in [("1001", "KOSPI"), ("1002", "KOSDAQ")]:
            try:
                df = pykrx_stock.get_index_ohlcv(date_str, date_str, idx_code)
                if not df.empty:
                    df['index_name'] = idx_name
                    indices_list.append(df)
            except:
                pass

        if indices_list:
            indices_df = pd.concat(indices_list, ignore_index=True)

            # 준비된 지수 데이터
            insert_data = []
            for _, row in indices_df.iterrows():
                insert_data.append({
                    'index_name': row['index_name'],
                    'date': target_date,
                    'open_value': float(row['시가']),
                    'high_value': float(row['고가']),
                    'low_value': float(row['저가']),
                    'close_value': float(row['종가']),
                    'volume': int(row['거래량'])
                })

            # bulk insert
            if insert_data:
                with engine.begin() as conn:
                    # 먼저 기존 데이터 삭제
                    conn.execute(text("DELETE FROM market_indices WHERE date = :date"), {"date": target_date})
                    # 새로운 데이터 삽입
                    for data in insert_data:
                        conn.execute(text("""
                            INSERT INTO market_indices (index_name, date, open_value, high_value, low_value, close_value, volume, created_at)
                            VALUES (:index_name, :date, :open_value, :high_value, :low_value, :close_value, :volume, NOW())
                        """), data)

            total_indices += len(insert_data)
            print(f"Indices: {len(insert_data)}", end=" ", flush=True)

        success += 1
        print("OK")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 80)
print(f"Completed! Success: {success}/{len(missing_dates)}")
print(f"Prices: {total_prices:,} | Indices: {total_indices:,}")
print("=" * 80)

engine.dispose()
