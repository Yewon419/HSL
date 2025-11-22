#!/usr/bin/env python3
"""
Test Script for New Airflow DAG System
새로운 Airflow DAG 시스템의 기능을 테스트합니다.

사용법:
    python test_dag_system.py [test_name]

테스트:
    - test_db_connection: 데이터베이스 연결 확인
    - test_collection_log: collection_log 테이블 확인
    - test_indicator_log: indicator_log 테이블 확인
    - test_functions: 공통 함수 확인
    - test_collection: 실제 수집 테스트 (2025-10-20)
    - all: 모든 테스트 실행
"""

import sys
import os
from datetime import date

# Setup paths
sys.path.insert(0, '/app')
sys.path.insert(0, 'F:/hhstock/stock-trading-system/airflow/dags')

print("=" * 70)
print("Airflow DAG System Test Suite")
print("=" * 70)

# Test 1: Database Connection
def test_db_connection():
    print("\n[Test 1] Database Connection Test...")
    try:
        sys.path.insert(0, 'F:/hhstock/stock-trading-system/airflow/dags')
        from common_functions import get_db_engine
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute("SELECT NOW()")
            print("OK: Database connected: {}".format(result.scalar()))
        return True
    except Exception as e:
        print("ERROR: {}".format(e))
        return False

# Test 2: Check collection_log table
def test_collection_log():
    print("\n[Test 2] collection_log 테이블 확인...")
    try:
        from stock_trading_system.airflow.dags.common_functions import get_db_engine
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'collection_log'
                ORDER BY ordinal_position
                LIMIT 5
            """)
            columns = result.fetchall()
            if columns:
                print(f"✓ collection_log 테이블 존재 ({len(columns)}개 컬럼):")
                for col_name, data_type in columns:
                    print(f"  - {col_name}: {data_type}")
                return True
            else:
                print("✗ collection_log 테이블을 찾을 수 없습니다")
                return False
    except Exception as e:
        print(f"✗ 오류: {e}")
        return False

# Test 3: Check indicator_log table
def test_indicator_log():
    print("\n[Test 3] indicator_log 테이블 확인...")
    try:
        from stock_trading_system.airflow.dags.common_functions import get_db_engine
        engine = get_db_engine()
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT column_name, data_type
                FROM information_schema.columns
                WHERE table_name = 'indicator_log'
                ORDER BY ordinal_position
                LIMIT 5
            """)
            columns = result.fetchall()
            if columns:
                print(f"✓ indicator_log 테이블 존재 ({len(columns)}개 컬럼):")
                for col_name, data_type in columns:
                    print(f"  - {col_name}: {data_type}")
                return True
            else:
                print("✗ indicator_log 테이블을 찾을 수 없습니다")
                return False
    except Exception as e:
        print(f"✗ 오류: {e}")
        return False

# Test 4: Check common functions
def test_functions():
    print("\n[Test 4] 공통 함수 확인...")
    try:
        from stock_trading_system.airflow.dags.common_functions import (
            get_db_engine,
            get_collection_status,
            update_collection_log_price,
            update_collection_log_indices,
            get_indicator_status,
            update_indicator_log,
            fetch_stock_prices_api,
            fetch_market_indices_api
        )
        print("✓ 모든 공통 함수 import 성공:")
        print("  - get_db_engine")
        print("  - get_collection_status")
        print("  - update_collection_log_price")
        print("  - update_collection_log_indices")
        print("  - get_indicator_status")
        print("  - update_indicator_log")
        print("  - fetch_stock_prices_api")
        print("  - fetch_market_indices_api")
        return True
    except Exception as e:
        print(f"✗ 오류: {e}")
        return False

# Test 5: Test actual collection
def test_collection():
    print("\n[Test 5] 실제 수집 테스트 (2025-10-20)...")
    try:
        from stock_trading_system.airflow.dags.common_functions import (
            get_db_engine,
            fetch_stock_prices_api,
            fetch_market_indices_api,
            save_stock_prices,
            save_market_indices,
            update_collection_log_price,
            update_collection_log_indices
        )

        target_date = date(2025, 10, 20)
        engine = get_db_engine()

        # Fetch stock prices
        print("  → 주가 수집 중...")
        prices_df = fetch_stock_prices_api(target_date)
        if prices_df.empty:
            print("  ✗ 주가 수집 실패")
            return False

        print(f"  ✓ {len(prices_df)}개의 주가 데이터 수집")

        # Save stock prices
        print("  → 주가 저장 중...")
        saved_count = save_stock_prices(prices_df, target_date, engine)
        print(f"  ✓ {saved_count}개의 주가 저장")

        # Update collection_log
        update_collection_log_price(target_date, 'success', saved_count, None, engine)
        print(f"  ✓ collection_log 업데이트 (주가)")

        # Fetch market indices
        print("  → 시장 지수 수집 중...")
        indices_df = fetch_market_indices_api(target_date)
        if indices_df.empty:
            print("  ✗ 시장 지수 수집 실패")
            return False

        print(f"  ✓ {len(indices_df)}개의 지수 데이터 수집")

        # Save market indices
        print("  → 시장 지수 저장 중...")
        saved_count = save_market_indices(indices_df, target_date, engine)
        print(f"  ✓ {saved_count}개의 지수 저장")

        # Update collection_log
        update_collection_log_indices(target_date, 'success', saved_count, None, engine)
        print(f"  ✓ collection_log 업데이트 (지수)")

        # Verify
        with engine.connect() as conn:
            result = conn.execute("""
                SELECT overall_status, price_count, indices_count
                FROM collection_log
                WHERE collection_date = :date
            """, {'date': target_date})
            row = result.first()
            if row:
                print(f"  ✓ collection_log 상태: {row[0]} (주가: {row[1]}, 지수: {row[2]})")
                return True

        return True

    except Exception as e:
        print(f"  ✗ 오류: {e}")
        import traceback
        traceback.print_exc()
        return False

# Run tests
def run_all_tests():
    results = {
        'DB Connection': test_db_connection(),
        'collection_log Table': test_collection_log(),
        'indicator_log Table': test_indicator_log(),
        'Common Functions': test_functions(),
        'Collection Test': test_collection(),
    }

    print("\n" + "=" * 70)
    print("테스트 결과 요약:")
    print("=" * 70)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "✓ PASS" if result else "✗ FAIL"
        print(f"{status}: {test_name}")

    print(f"\n총 {total}개 테스트 중 {passed}개 통과 ({passed*100//total}%)")

    if passed == total:
        print("\n✓ 모든 테스트 통과! 시스템이 정상입니다.")
        return True
    else:
        print("\n✗ 일부 테스트 실패. 위의 오류를 확인하세요.")
        return False

if __name__ == '__main__':
    test_name = sys.argv[1] if len(sys.argv) > 1 else 'all'

    if test_name == 'db':
        test_db_connection()
    elif test_name == 'collection_log':
        test_collection_log()
    elif test_name == 'indicator_log':
        test_indicator_log()
    elif test_name == 'functions':
        test_functions()
    elif test_name == 'collection':
        test_collection()
    elif test_name == 'all':
        run_all_tests()
    else:
        print(f"Unknown test: {test_name}")
        print("Available tests: db, collection_log, indicator_log, functions, collection, all")
        sys.exit(1)
