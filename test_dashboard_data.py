#!/usr/bin/env python3
"""
Test script to verify dashboard data availability
"""

import pandas as pd
from sqlalchemy import create_engine, text

def get_db_connection():
    """Get database connection"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def test_dashboard_queries():
    """Test all dashboard queries for different tickers"""
    engine = get_db_connection()

    # Test tickers
    test_tickers = ['005930', '000660', '035420', '051910', '006400']

    print("Testing Dashboard Data Availability")
    print("=" * 50)

    for ticker in test_tickers:
        print(f"\nTesting ticker: {ticker}")

        with engine.connect() as conn:
            # Get company name
            company_result = conn.execute(text("""
                SELECT company_name FROM stocks WHERE ticker = :ticker
            """), {'ticker': ticker})
            company_name = company_result.fetchone()
            if company_name:
                print(f"Company: {company_name[0]}")

            # Test price data
            price_result = conn.execute(text("""
                SELECT COUNT(*) as count, MAX(date) as latest_date, AVG(volume) as avg_volume
                FROM stock_prices
                WHERE ticker = :ticker
                AND date >= CURRENT_DATE - INTERVAL '3 months'
            """), {'ticker': ticker})
            price_data = price_result.fetchone()
            print(f"Price records (3M): {price_data[0]}, Latest: {price_data[1]}, Avg Volume: {price_data[2]:,.0f}")

            # Test MACD data
            macd_result = conn.execute(text("""
                SELECT COUNT(*) as count,
                       AVG((value->>'macd')::numeric) as avg_macd
                FROM indicator_values iv
                JOIN indicator_definitions id ON iv.indicator_id = id.id
                WHERE iv.ticker = :ticker
                AND id.code = 'MACD'
                AND date >= CURRENT_DATE - INTERVAL '3 months'
                AND (value->>'macd') IS NOT NULL
            """), {'ticker': ticker})
            macd_data = macd_result.fetchone()
            print(f"MACD records (3M): {macd_data[0]}, Avg MACD: {macd_data[1]:.2f}" if macd_data[1] else f"MACD records (3M): {macd_data[0]}")

            # Test Stochastic data
            stoch_result = conn.execute(text("""
                SELECT COUNT(*) as count,
                       AVG((value->>'stoch_k')::numeric) as avg_k,
                       AVG((value->>'stoch_d')::numeric) as avg_d
                FROM indicator_values iv
                JOIN indicator_definitions id ON iv.indicator_id = id.id
                WHERE iv.ticker = :ticker
                AND id.code = 'STOCH'
                AND date >= CURRENT_DATE - INTERVAL '3 months'
                AND (value->>'stoch_k') IS NOT NULL
                AND (value->>'stoch_d') IS NOT NULL
            """), {'ticker': ticker})
            stoch_data = stoch_result.fetchone()
            if stoch_data[1] and stoch_data[2]:
                print(f"Stochastic records (3M): {stoch_data[0]}, Avg %K: {stoch_data[1]:.2f}, Avg %D: {stoch_data[2]:.2f}")
            else:
                print(f"Stochastic records (3M): {stoch_data[0]}")

            # Test latest values
            latest_result = conn.execute(text("""
                SELECT
                    sp.close_price,
                    (macd_iv.value->>'macd')::numeric as macd,
                    (stoch_iv.value->>'stoch_k')::numeric as stoch_k,
                    (stoch_iv.value->>'stoch_d')::numeric as stoch_d
                FROM stock_prices sp
                LEFT JOIN indicator_values macd_iv ON sp.ticker = macd_iv.ticker AND sp.date = macd_iv.date
                LEFT JOIN indicator_definitions macd_id ON macd_iv.indicator_id = macd_id.id AND macd_id.code = 'MACD'
                LEFT JOIN indicator_values stoch_iv ON sp.ticker = stoch_iv.ticker AND sp.date = stoch_iv.date
                LEFT JOIN indicator_definitions stoch_id ON stoch_iv.indicator_id = stoch_id.id AND stoch_id.code = 'STOCH'
                WHERE sp.ticker = :ticker
                ORDER BY sp.date DESC
                LIMIT 1
            """), {'ticker': ticker})
            latest_data = latest_result.fetchone()
            if latest_data:
                macd_val = f"{latest_data[1]:.2f}" if latest_data[1] is not None else "N/A"
                stoch_k_val = f"{latest_data[2]:.2f}" if latest_data[2] is not None else "N/A"
                stoch_d_val = f"{latest_data[3]:.2f}" if latest_data[3] is not None else "N/A"
                print(f"Latest - Price: {latest_data[0]:,.0f}, MACD: {macd_val}, Stoch K: {stoch_k_val}, Stoch D: {stoch_d_val}")

def test_ticker_dropdown():
    """Test ticker dropdown query"""
    engine = get_db_connection()

    print("\n" + "=" * 50)
    print("Testing Ticker Dropdown Query")
    print("=" * 50)

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT ticker, ticker || ' - ' || company_name as display_name
            FROM stocks
            WHERE is_active = true
            AND currency = 'KRW'
            AND ticker IN (
                SELECT DISTINCT ticker
                FROM stock_prices
                WHERE date >= CURRENT_DATE - INTERVAL '30 days'
            )
            ORDER BY CASE
                WHEN ticker = '005930' THEN 1
                WHEN ticker = '000660' THEN 2
                WHEN ticker = '035420' THEN 3
                WHEN ticker = '051910' THEN 4
                WHEN ticker = '006400' THEN 5
                WHEN ticker = '035720' THEN 6
                WHEN ticker = '028260' THEN 7
                WHEN ticker = '068270' THEN 8
                WHEN ticker = '066570' THEN 9
                WHEN ticker = '005380' THEN 10
                ELSE 99
            END, company_name
            LIMIT 15
        """))

        tickers = result.fetchall()
        print(f"Available tickers: {len(tickers)}")
        print("\nTop 15 tickers in dropdown:")
        for ticker, display_name in tickers:
            print(f"  {ticker}: {display_name}")

if __name__ == "__main__":
    try:
        test_dashboard_queries()
        test_ticker_dropdown()
        print("\n" + "=" * 50)
        print("Dashboard data test completed successfully!")
        print("All queries are working properly.")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()