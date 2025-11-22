#!/usr/bin/env python3
"""
최종 누락된 날짜 데이터 수집
"""
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2

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

print("=" * 80)
print("Collecting missing data")
print("=" * 80)

total_prices = 0
total_indices = 0
success = 0

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

            # DB에 저장 (각 행별로 개별 커밋)
            conn = get_conn()
            cursor = conn.cursor()

            try:
                # 기존 데이터 삭제
                cursor.execute("DELETE FROM stock_prices WHERE date = %s", (target_date,))

                # 새로운 데이터 삽입
                for _, row in prices_df.iterrows():
                    cursor.execute("""
                        INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        row['ticker'],
                        target_date,
                        float(row['시가']),
                        float(row['고가']),
                        float(row['저가']),
                        float(row['종가']),
                        int(row['거래량'])
                    ))

                conn.commit()
                total_prices += len(prices_df)
                print(f"Prices: {len(prices_df)}", end=" ", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"Price Error: {e}", end=" ")
            finally:
                cursor.close()
                conn.close()

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

            # DB에 저장
            conn = get_conn()
            cursor = conn.cursor()

            try:
                # 기존 데이터 삭제
                cursor.execute("DELETE FROM market_indices WHERE date = %s", (target_date,))

                # 새로운 데이터 삽입
                for _, row in indices_df.iterrows():
                    cursor.execute("""
                        INSERT INTO market_indices (index_name, date, open_value, high_value, low_value, close_value, volume, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, NOW())
                    """, (
                        row['index_name'],
                        target_date,
                        float(row['시가']),
                        float(row['고가']),
                        float(row['저가']),
                        float(row['종가']),
                        int(row['거래량'])
                    ))

                conn.commit()
                total_indices += len(indices_df)
                print(f"Indices: {len(indices_df)}", end=" ", flush=True)
            except Exception as e:
                conn.rollback()
                print(f"Index Error: {e}", end=" ")
            finally:
                cursor.close()
                conn.close()

        success += 1
        print("OK")

    except Exception as e:
        print(f"ERROR: {e}")

print("\n" + "=" * 80)
print(f"Completed! Success: {success}/{len(missing_dates)}")
print(f"Prices: {total_prices:,} | Indices: {total_indices:,}")
print("=" * 80)
