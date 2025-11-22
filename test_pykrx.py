#!/usr/bin/env python
"""Test pykrx data format"""

from pykrx import stock
from datetime import datetime, timedelta
import pandas as pd

# Test parameters
ticker = "005930"  # Samsung Electronics
end_date = datetime.now()
start_date = end_date - timedelta(days=30)  # Just 30 days for testing
start_str = start_date.strftime("%Y%m%d")
end_str = end_date.strftime("%Y%m%d")

print(f"Testing ticker: {ticker}")
print(f"Date range: {start_str} to {end_str}")
print("-" * 50)

# Get OHLCV data
df = stock.get_market_ohlcv_by_date(start_str, end_str, ticker)

print(f"DataFrame shape: {df.shape}")
print(f"DataFrame columns: {df.columns.tolist()}")
print(f"Number of columns: {len(df.columns)}")
print("-" * 50)

print("First 5 rows:")
print(df.head())
print("-" * 50)

print("Data types:")
print(df.dtypes)
print("-" * 50)

# Reset index and check again
df_reset = df.reset_index()
print(f"After reset_index - columns: {df_reset.columns.tolist()}")
print(f"After reset_index - shape: {df_reset.shape}")
print("First row after reset:")
print(df_reset.iloc[0])