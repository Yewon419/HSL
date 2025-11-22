#!/usr/bin/env python3
import sys
sys.path.insert(0, '/opt/airflow/dags')
from datetime import date
from common_functions import (
    get_db_engine,
    fetch_stock_prices_api,
    fetch_market_indices_api,
    save_stock_prices,
    save_market_indices,
    logger
)

# Numlock of dates
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

engine = get_db_engine()
total_prices = 0
total_indices = 0
success_count = 0

print("=" * 80)
print("Starting batch data collection for missing dates")
print("=" * 80)

for target_date in missing_dates:
    try:
        print(f"\nCollecting for {target_date}...")

        # Collect stock prices
        prices_df = fetch_stock_prices_api(target_date)
        if not prices_df.empty:
            saved_prices = save_stock_prices(prices_df, target_date, engine)
            print(f"  Prices: {saved_prices} saved")
            total_prices += saved_prices
        else:
            print(f"  Prices: No data from API")

        # Collect market indices
        indices_df = fetch_market_indices_api(target_date)
        if not indices_df.empty:
            saved_indices = save_market_indices(indices_df, target_date, engine)
            print(f"  Indices: {saved_indices} saved")
            total_indices += saved_indices
        else:
            print(f"  Indices: No data from API")

        success_count += 1

    except Exception as e:
        print(f"  ERROR: {e}")

print("\n" + "=" * 80)
print("Batch collection completed!")
print("  - Success: {}/{} dates".format(success_count, len(missing_dates)))
print("  - Total prices collected: {:,}".format(total_prices))
print("  - Total indices collected: {:,}".format(total_indices))
print("=" * 80)
