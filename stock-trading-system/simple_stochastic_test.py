#!/usr/bin/env python3
"""
Simple test script to verify Stochastic %K and %D lines
"""

import pandas as pd
from sqlalchemy import create_engine, text

def get_db_connection():
    """Get database connection"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def test_stochastic_data(ticker='005930'):
    """Test Stochastic %K and %D data for a specific ticker"""
    engine = get_db_connection()

    print(f"Testing Stochastic data for {ticker}")

    # Get Stochastic data from indicator_values table
    query = text("""
        SELECT
            iv.date,
            (iv.value->>'stoch_k')::numeric as stoch_k,
            (iv.value->>'stoch_d')::numeric as stoch_d
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        WHERE iv.ticker = :ticker
          AND id.code = 'STOCH'
          AND iv.date >= CURRENT_DATE - INTERVAL '30 days'
          AND (iv.value->>'stoch_k') IS NOT NULL
          AND (iv.value->>'stoch_d') IS NOT NULL
        ORDER BY iv.date DESC
        LIMIT 10
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'ticker': ticker}, parse_dates=['date'])

    if df.empty:
        print("No Stochastic data found!")
        return False

    print(f"Found {len(df)} Stochastic records")
    print(f"Date range: {df['date'].min()} to {df['date'].max()}")

    # Display recent data
    print("\nRecent Stochastic Values:")
    print("Date       | %K     | %D     | Signal")
    print("-" * 40)

    for _, row in df.iterrows():
        k_val = row['stoch_k']
        d_val = row['stoch_d']
        signal = "K>D" if k_val > d_val else "K<D"
        print(f"{row['date'].date()} | {k_val:6.2f} | {d_val:6.2f} | {signal}")

    # Latest values
    latest = df.iloc[0]  # Most recent (DESC order)
    print(f"\nLatest Values ({latest['date'].date()}):")
    print(f"   %K (Fast Line): {latest['stoch_k']:.2f}")
    print(f"   %D (Slow Line): {latest['stoch_d']:.2f}")

    # Check if both lines are different (indicating both are calculated)
    if latest['stoch_k'] != latest['stoch_d']:
        print("SUCCESS: Both %K and %D lines have different values - both are being calculated!")
    else:
        print("WARNING: %K and %D have the same value - possible calculation issue")

    return True

def check_data_consistency():
    """Check consistency between technical_indicators and indicator_values tables"""
    engine = get_db_connection()

    print("Checking data consistency between tables")

    with engine.connect() as conn:
        # Count from technical_indicators
        ti_count = conn.execute(text("""
            SELECT COUNT(*) FROM technical_indicators
            WHERE stoch_k IS NOT NULL AND stoch_d IS NOT NULL
        """)).fetchone()[0]

        # Count from indicator_values
        iv_count = conn.execute(text("""
            SELECT COUNT(*) FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'STOCH'
              AND (iv.value->>'stoch_k') IS NOT NULL
              AND (iv.value->>'stoch_d') IS NOT NULL
        """)).fetchone()[0]

        print(f"Record counts:")
        print(f"   technical_indicators: {ti_count:,}")
        print(f"   indicator_values: {iv_count:,}")

        if iv_count >= ti_count:
            print("SUCCESS: indicator_values has comprehensive data")
        else:
            print("WARNING: technical_indicators has more data than indicator_values")

if __name__ == "__main__":
    print("Stochastic Indicator Test Suite")
    print("=" * 50)

    try:
        # Test data consistency
        check_data_consistency()
        print()

        # Test Samsung (005930)
        test_stochastic_data('005930')
        print()

        # Test SK Hynix (000660)
        test_stochastic_data('000660')

        print("\nStochastic test completed successfully!")

    except Exception as e:
        print(f"Test failed: {e}")
        import traceback
        traceback.print_exc()