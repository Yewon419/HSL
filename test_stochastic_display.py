#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test script to verify Stochastic %K and %D lines are properly calculated and displayed
"""

import pandas as pd
import matplotlib.pyplot as plt
from sqlalchemy import create_engine, text
import matplotlib.dates as mdates
from datetime import datetime, timedelta
import numpy as np

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
          AND iv.date >= CURRENT_DATE - INTERVAL '3 months'
          AND (iv.value->>'stoch_k') IS NOT NULL
          AND (iv.value->>'stoch_d') IS NOT NULL
        ORDER BY iv.date DESC
        LIMIT 30
    """)

    with engine.connect() as conn:
        df = pd.read_sql(query, conn, params={'ticker': ticker}, parse_dates=['date'])

    if df.empty:
        print("❌ No Stochastic data found!")
        return False

    # Sort by date for plotting
    df = df.sort_values('date').reset_index(drop=True)

    print(f"✅ Found {len(df)} Stochastic records")
    print(f"📅 Date range: {df['date'].min()} to {df['date'].max()}")

    # Display statistics
    print(f"\n📊 Stochastic Statistics:")
    print(f"   %K Range: {df['stoch_k'].min():.2f} - {df['stoch_k'].max():.2f}")
    print(f"   %D Range: {df['stoch_d'].min():.2f} - {df['stoch_d'].max():.2f}")

    # Latest values
    latest = df.iloc[-1]
    print(f"\n🔢 Latest Values ({latest['date'].date()}):")
    print(f"   %K (빠른선): {latest['stoch_k']:.2f}")
    print(f"   %D (느린선): {latest['stoch_d']:.2f}")

    # Check for crossovers
    df['k_above_d'] = df['stoch_k'] > df['stoch_d']
    df['crossover'] = df['k_above_d'].diff().fillna(False)

    crossovers = df[df['crossover'] != 0]
    if not crossovers.empty:
        print(f"\n🔄 Recent Crossovers:")
        for _, row in crossovers.tail(3).iterrows():
            signal = "상승" if row['k_above_d'] else "하락"
            print(f"   {row['date'].date()}: %K crossed {signal} (K={row['stoch_k']:.2f}, D={row['stoch_d']:.2f})")

    # Create visualization
    plt.figure(figsize=(12, 8))

    # Main plot
    plt.subplot(2, 1, 1)
    plt.plot(df['date'], df['stoch_k'], label='%K (빠른선)', color='blue', linewidth=2)
    plt.plot(df['date'], df['stoch_d'], label='%D (느린선)', color='red', linewidth=2)

    # Add horizontal lines
    plt.axhline(y=80, color='orange', linestyle='--', alpha=0.7, label='과매수 (80)')
    plt.axhline(y=20, color='green', linestyle='--', alpha=0.7, label='과매도 (20)')

    plt.title(f'Stochastic Oscillator - {ticker}', fontsize=14, fontweight='bold')
    plt.ylabel('Stochastic (%)')
    plt.ylim(0, 100)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)

    # Signal strength plot
    plt.subplot(2, 1, 2)
    signal_strength = df['stoch_k'] - df['stoch_d']
    colors = ['green' if x > 0 else 'red' for x in signal_strength]
    plt.bar(df['date'], signal_strength, color=colors, alpha=0.6, width=1)
    plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    plt.title('Signal Strength (%K - %D)', fontsize=12)
    plt.ylabel('Difference')
    plt.xlabel('Date')
    plt.grid(True, alpha=0.3)
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
    plt.gca().xaxis.set_major_locator(mdates.WeekdayLocator(interval=1))
    plt.xticks(rotation=45)

    plt.tight_layout()

    # Save plot
    plot_filename = f'stochastic_test_{ticker}_{datetime.now().strftime("%Y%m%d_%H%M%S")}.png'
    plt.savefig(plot_filename, dpi=300, bbox_inches='tight')
    print(f"\n📈 Chart saved as: {plot_filename}")

    plt.show()

    return True

def test_multiple_tickers():
    """Test Stochastic data for multiple tickers"""
    tickers = ['005930', '000660', '035420']  # Samsung, SK Hynix, Naver

    print("🧪 Testing Stochastic data for multiple tickers\n")

    for ticker in tickers:
        print(f"{'='*50}")
        success = test_stochastic_data(ticker)
        if not success:
            print(f"❌ Failed to get data for {ticker}")
        print()

def check_data_consistency():
    """Check consistency between technical_indicators and indicator_values tables"""
    engine = get_db_connection()

    print("🔍 Checking data consistency between tables")

    # Compare record counts
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

        print(f"📊 Record counts:")
        print(f"   technical_indicators: {ti_count:,}")
        print(f"   indicator_values: {iv_count:,}")

        if iv_count > ti_count:
            print("✅ indicator_values has more comprehensive data")
        elif ti_count == iv_count:
            print("✅ Both tables have the same amount of data")
        else:
            print("⚠️ technical_indicators has more data than indicator_values")

if __name__ == "__main__":
    print("🚀 Stochastic Indicator Test Suite")
    print("="*50)

    try:
        # Test data consistency
        check_data_consistency()
        print()

        # Test single ticker
        test_stochastic_data('005930')

        # Optional: Test multiple tickers
        # test_multiple_tickers()

        print("✅ Stochastic test completed successfully!")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()