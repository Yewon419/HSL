#!/usr/bin/env python
import sys
sys.path.insert(0, '/app')

from datetime import date
import os

os.environ['DATABASE_URL'] = 'postgresql://admin:admin123@stock-db:5432/stocktrading'

from common_functions import (
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices,
    update_collection_log_price,
    update_collection_log_indices,
    get_db_engine
)

target_date = date(2025, 10, 20)
engine = get_db_engine()

print("\n" + "="*70)
print("2025-10-20 stock price and index collection")
print("="*70 + "\n")

try:
    print("[1] Fetching stock prices...")
    prices_df = fetch_stock_prices_api(target_date)
    print("Collected: {}".format(len(prices_df)))
    
    if not prices_df.empty:
        price_count = save_stock_prices(prices_df, target_date, engine)
        print("Saved: {}".format(price_count))
        update_collection_log_price(target_date, 'success', price_count, None, engine)
        print("Updated collection_log (prices)\n")
    
    print("[2] Fetching market indices...")
    indices_df = fetch_market_indices_api(target_date)
    print("Collected: {}".format(len(indices_df)))
    
    if not indices_df.empty:
        indices_count = save_market_indices(indices_df, target_date, engine)
        print("Saved: {}".format(indices_count))
        update_collection_log_indices(target_date, 'success', indices_count, None, engine)
        print("Updated collection_log (indices)\n")
    
    print("="*70)
    print("Collection complete! (prices: {}, indices: {})".format(len(prices_df), len(indices_df)))
    print("="*70 + "\n")
    
except Exception as e:
    print("Error: {}".format(e))
    import traceback
    traceback.print_exc()

