#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
import os
sys.path.insert(0, '/app')
sys.path.insert(0, 'F:/hhstock/stock-trading-system/airflow/dags')

from datetime import date

print("=" * 70)
print("Quick DAG System Test")
print("=" * 70)

try:
    print("\n1. Testing database connection...")
    from common_functions import get_db_engine
    engine = get_db_engine()
    with engine.connect() as conn:
        result = conn.execute("SELECT NOW()")
        print("   OK: {}".format(result.scalar()))

    print("\n2. Testing collection_log table exists...")
    with engine.connect() as conn:
        result = conn.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'collection_log'
            )
        """)
        exists = result.scalar()
        print("   OK: collection_log exists = {}".format(exists))

    print("\n3. Testing indicator_log table exists...")
    with engine.connect() as conn:
        result = conn.execute("""
            SELECT EXISTS(
                SELECT 1 FROM information_schema.tables
                WHERE table_name = 'indicator_log'
            )
        """)
        exists = result.scalar()
        print("   OK: indicator_log exists = {}".format(exists))

    print("\n4. Testing common functions import...")
    from common_functions import (
        get_collection_status,
        update_collection_log_price,
        update_collection_log_indices,
        get_indicator_status,
        fetch_stock_prices_api,
        save_stock_prices
    )
    print("   OK: All functions imported")

    print("\n5. Testing fetch_stock_prices_api...")
    target_date = date(2025, 10, 20)
    prices_df = fetch_stock_prices_api(target_date)
    print("   OK: Fetched {} stock prices".format(len(prices_df)))

    if not prices_df.empty:
        print("\n6. Testing save_stock_prices...")
        saved_count = save_stock_prices(prices_df, target_date, engine)
        print("   OK: Saved {} records".format(saved_count))

        print("\n7. Testing update_collection_log_price...")
        update_collection_log_price(target_date, 'success', saved_count, None, engine)
        print("   OK: Updated collection_log")

        print("\n8. Verifying collection_log...")
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT overall_status, price_count, price_status
                FROM collection_log
                WHERE collection_date = :date
            """, {'date': target_date})
            row = result.first()
            if row:
                print("   OK: Status={}, Price Count={}, Price Status={}".format(row[0], row[1], row[2]))

    print("\n" + "=" * 70)
    print("All tests PASSED!")
    print("=" * 70)

except Exception as e:
    print("\nERROR: {}".format(e))
    import traceback
    traceback.print_exc()
    sys.exit(1)
