#!/usr/bin/env python3
"""
누락된 날짜 데이터 수동 수집 스크립트
"""
import sys
from datetime import date
from pykrx import stock as pykrx_stock
import pandas as pd
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT

# 누락된 날짜들 (2025년 총 24일)
missing_dates = [
    # 1월 (신정, 방학 휴장)
    date(2025, 1, 1),      # 신정
    date(2025, 1, 27),     # 방학 휴장
    date(2025, 1, 28),     # 방학 휴장
    date(2025, 1, 29),     # 방학 휴장
    date(2025, 1, 30),     # 방학 휴장
    # 3월 (삼일절)
    date(2025, 3, 3),      # 삼일절
    # 5월 (근로자날, 부처님 오신날)
    date(2025, 5, 1),      # 근로자날
    date(2025, 5, 5),      # 부처님 오신날
    date(2025, 5, 6),      # 부처님 오신날 대체공휴일
    # 10월 (미수집 날짜만)
    date(2025, 10, 8),
    date(2025, 10, 9),
    date(2025, 10, 31),  # 노트북 미기동으로 인한 누락
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

def save_market_indices(indices_df, target_date):
    """지수 데이터 저장 (market_indices 테이블 없음 - 스킵)"""
    if indices_df.empty:
        return 0

    # market_indices 테이블이 현재 데이터베이스에 존재하지 않음
    # 주가 데이터만 저장되면 됨
    return 0

def is_trading_day(target_date):
    """거래일 확인 (평일)"""
    return target_date.weekday() < 5

def collect_and_save(target_date):
    """데이터 수집 및 저장"""
    if not is_trading_day(target_date):
        print(f"  Skipped (not a trading day)")
        return 0, 0

    try:
        date_str = target_date.strftime("%Y%m%d")
        print(f"Collecting for {target_date}...", end=" ", flush=True)

        # 주가 수집 (KOSPI + KOSDAQ 모두)
        kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
        kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
        tickers = list(set(kospi_tickers + kosdaq_tickers))
        print(f"({len(tickers)} tickers: KOSPI {len(kospi_tickers)} + KOSDAQ {len(kosdaq_tickers)})", end=" ", flush=True)

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
            print(f"Prices: {prices_saved}", end=" ", flush=True)

        # 지수 수집
        indices_data = []

        # KOSPI
        try:
            kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")
            if not kospi.empty:
                kospi['index_name'] = "KOSPI"
                indices_data.append(kospi)
        except:
            pass

        # KOSDAQ
        try:
            kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "1002")
            if not kosdaq.empty:
                kosdaq['index_name'] = "KOSDAQ"
                indices_data.append(kosdaq)
        except:
            pass

        indices_saved = 0
        if indices_data:
            indices_df = pd.concat(indices_data, ignore_index=True)
            indices_saved = save_market_indices(indices_df, target_date)
            print(f"Indices: {indices_saved}", end=" ")

        print("OK")
        return prices_saved, indices_saved

    except Exception as e:
        print(f"ERROR: {e}")
        return 0, 0

def main():
    print("=" * 80)
    print("Starting batch collection for missing dates")
    print("=" * 80)

    total_prices = 0
    total_indices = 0
    success_count = 0

    for target_date in missing_dates:
        prices, indices = collect_and_save(target_date)
        total_prices += prices
        total_indices += indices
        if prices > 0 or indices > 0:
            success_count += 1

    print("=" * 80)
    print(f"Batch collection completed!")
    print(f"  - Success: {success_count}/{len(missing_dates)} dates")
    print(f"  - Total prices: {total_prices:,}")
    print(f"  - Total indices: {total_indices:,}")
    print("=" * 80)

if __name__ == '__main__':
    main()
