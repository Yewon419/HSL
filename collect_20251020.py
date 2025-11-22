#!/usr/bin/env python3
"""
2025-10-20 데이터 수동 수집 스크립트
"""
import sys
import os

# 환경 설정
os.environ['DATABASE_URL'] = 'postgresql://admin:admin123@stock-db:5432/stocktrading'
sys.path.insert(0, '/app')

from datetime import date
from pykrx import stock
from database import SessionLocal
from models import StockPrice, MarketIndex

target_date = date(2025, 10, 20)
date_str = '20251020'

print(f"\n{'='*60}")
print(f"2025-10-20 데이터 수동 수집 시작")
print(f"{'='*60}\n")

try:
    print("[1] 주가 데이터 수집 중...")
    tickers = stock.get_market_ticker_list(date=date_str)
    print(f"✓ 티커 조회: {len(tickers)}개")

    prices_list = []
    for i, ticker in enumerate(tickers):
        if (i+1) % 200 == 0:
            print(f"  [{i+1}/{len(tickers)}]")
        try:
            df = stock.get_market_ohlcv(date_str, date_str, ticker)
            if not df.empty:
                for idx, row in df.iterrows():
                    prices_list.append({
                        'ticker': ticker,
                        'date': target_date,
                        'open_price': float(row['시가']),
                        'high_price': float(row['고가']),
                        'low_price': float(row['저가']),
                        'close_price': float(row['종가']),
                        'volume': int(row['거래량'])
                    })
        except:
            pass

    print(f"✓ 주가 수집 완료: {len(prices_list)}개\n")

    print("[2] 시장 지수 수집 중...")
    indices_list = []
    for index_name in ['KOSPI', 'KOSDAQ']:
        try:
            df = stock.get_index_ohlcv(date_str, date_str, index_name)
            if not df.empty:
                for idx, row in df.iterrows():
                    indices_list.append({
                        'index_name': index_name,
                        'date': target_date,
                        'open_value': float(row['시가']),
                        'high_value': float(row['고가']),
                        'low_value': float(row['저가']),
                        'close_value': float(row['종가']),
                        'volume': int(row['거래량'])
                    })
        except:
            pass

    print(f"✓ 지수 수집 완료: {len(indices_list)}개\n")

    print("[3] 데이터베이스 저장 중...")
    session = SessionLocal()

    # 기존 데이터 삭제
    session.query(StockPrice).filter(StockPrice.date == target_date).delete()
    session.query(MarketIndex).filter(MarketIndex.date == target_date).delete()
    session.commit()

    # 주가 저장
    if prices_list:
        for item in prices_list:
            session.add(StockPrice(**item))
        session.commit()
        print(f"✓ 주가 저장: {len(prices_list)}개")

    # 지수 저장
    if indices_list:
        for item in indices_list:
            session.add(MarketIndex(**item))
        session.commit()
        print(f"✓ 지수 저장: {len(indices_list)}개")

    session.close()

    print(f"\n{'='*60}")
    print(f"✓ 수집 완료! (총 {len(prices_list) + len(indices_list)}개 레코드)")
    print(f"{'='*60}\n")

except Exception as e:
    print(f"✗ 오류 발생: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
