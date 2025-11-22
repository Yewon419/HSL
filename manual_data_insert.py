#!/usr/bin/env python3
"""
수동으로 누락된 날짜의 주식 데이터를 생성하는 스크립트
"""

import os
import sys
from datetime import datetime, date
from sqlalchemy import create_engine, text
import random

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def generate_stock_data_for_date(target_date):
    """특정 날짜의 주식 데이터 생성"""
    # 샘플 한국 주식 데이터
    sample_stocks = [
        {'ticker': '005930', 'name': '삼성전자', 'base_price': 70000},
        {'ticker': '000660', 'name': 'SK하이닉스', 'base_price': 130000},
        {'ticker': '035420', 'name': 'NAVER', 'base_price': 180000},
        {'ticker': '051910', 'name': 'LG화학', 'base_price': 400000},
        {'ticker': '006400', 'name': '삼성SDI', 'base_price': 350000},
        {'ticker': '035720', 'name': '카카오', 'base_price': 50000},
        {'ticker': '028260', 'name': '삼성물산', 'base_price': 120000},
        {'ticker': '068270', 'name': '셀트리온', 'base_price': 150000},
        {'ticker': '207940', 'name': '삼성바이오로직스', 'base_price': 800000},
        {'ticker': '066570', 'name': 'LG전자', 'base_price': 90000},
    ]

    all_data = []

    # 날짜를 시드로 사용해서 일관된 데이터 생성
    if isinstance(target_date, str):
        date_obj = datetime.strptime(target_date, '%Y-%m-%d').date()
    else:
        date_obj = target_date

    random.seed(int(date_obj.strftime('%Y%m%d')))

    for stock in sample_stocks:
        base_price = stock['base_price']

        # 랜덤한 가격 변동 (±5%)
        variation = random.uniform(-0.05, 0.05)
        close_price = base_price * (1 + variation)

        stock_data = {
            'ticker': stock['ticker'],
            'date': date_obj,
            'open_price': close_price * random.uniform(0.98, 1.02),
            'high_price': close_price * random.uniform(1.00, 1.03),
            'low_price': close_price * random.uniform(0.97, 1.00),
            'close_price': close_price,
            'volume': random.randint(100000, 10000000),
            'created_at': datetime.now()
        }

        all_data.append(stock_data)

    return all_data

def insert_stock_data(stock_data):
    """주식 데이터를 데이터베이스에 삽입"""
    engine = get_db_connection()

    try:
        # 먼저 stocks 테이블에 주식 정보가 있는지 확인하고 없으면 추가
        stock_info = [
            {'ticker': '005930', 'company_name': '삼성전자'},
            {'ticker': '000660', 'company_name': 'SK하이닉스'},
            {'ticker': '035420', 'company_name': 'NAVER'},
            {'ticker': '051910', 'company_name': 'LG화학'},
            {'ticker': '006400', 'company_name': '삼성SDI'},
            {'ticker': '035720', 'company_name': '카카오'},
            {'ticker': '028260', 'company_name': '삼성물산'},
            {'ticker': '068270', 'company_name': '셀트리온'},
            {'ticker': '207940', 'company_name': '삼성바이오로직스'},
            {'ticker': '066570', 'company_name': 'LG전자'},
        ]

        with engine.begin() as conn:
            # 주식 정보 삽입/업데이트
            for stock in stock_info:
                conn.execute(text("""
                    INSERT INTO stocks (ticker, company_name, market_type, is_active, currency)
                    VALUES (:ticker, :company_name, 'KOSPI', true, 'KRW')
                    ON CONFLICT (ticker) DO UPDATE SET
                        company_name = EXCLUDED.company_name,
                        is_active = EXCLUDED.is_active
                """), stock)

            # 가격 데이터 삽입/업데이트
            for row in stock_data:
                conn.execute(text("""
                    INSERT INTO stock_prices (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                    VALUES (:ticker, :date, :open_price, :high_price, :low_price, :close_price, :volume, :created_at)
                    ON CONFLICT (ticker, date)
                    DO UPDATE SET
                        open_price = EXCLUDED.open_price,
                        high_price = EXCLUDED.high_price,
                        low_price = EXCLUDED.low_price,
                        close_price = EXCLUDED.close_price,
                        volume = EXCLUDED.volume
                """), row)

        print(f"Successfully inserted {len(stock_data)} stock price records")
        return len(stock_data)

    except Exception as e:
        print(f"Error inserting data: {e}")
        raise

if __name__ == "__main__":
    # 지난 60일 동안의 데이터 생성 (기술적 지표 계산을 위해)
    from datetime import date, timedelta

    end_date = date(2025, 9, 30)
    start_date = end_date - timedelta(days=60)

    current_date = start_date
    while current_date <= end_date:
        # 주말 건너뛰기 (월-금만)
        if current_date.weekday() < 5:
            target_date = current_date.strftime('%Y-%m-%d')
            print(f"Generating stock data for {target_date}")
            stock_data = generate_stock_data_for_date(target_date)

            print(f"Inserting {len(stock_data)} records into database")
            result = insert_stock_data(stock_data)

            print(f"Successfully processed {result} records for {target_date}")

        current_date += timedelta(days=1)

    print("=" * 50)
    print("Historical data generation completed!")