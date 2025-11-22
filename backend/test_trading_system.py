#!/usr/bin/env python3
"""
자동매매 시스템 테스트
현재 날짜 기준으로 실제 시그널 확인
"""

import sys
sys.path.append('/app')

from datetime import date
from trading_service.signal_detector import SignalDetector

# 데이터베이스 연결
DB_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"

def main():
    print("=" * 60)
    print("자동매매 시스템 테스트")
    print("=" * 60)

    detector = SignalDetector(DB_URL)

    # 최신 데이터 날짜 확인
    from sqlalchemy import create_engine, text
    engine = create_engine(DB_URL)

    with engine.connect() as conn:
        result = conn.execute(text("SELECT MAX(date) FROM stock_prices"))
        latest_date = result.fetchone()[0]
        print(f"\n최신 데이터 날짜: {latest_date}")

    # 해당 날짜의 시그널 감지
    print(f"\n{latest_date} 시그널 감지 중...")
    print("-" * 60)

    # 매수 시그널
    buy_signals = detector.detect_buy_signals(latest_date)
    print(f"\n📈 매수 시그널: {len(buy_signals)}개")

    if buy_signals:
        print("\n상위 5개 매수 시그널:")
        for i, signal in enumerate(buy_signals[:5], 1):
            print(f"\n{i}. {signal['ticker']} - {signal['company_name']}")
            print(f"   현재가: {signal['current_price']:,.0f}원")
            print(f"   목표가: {signal['target_price']:,.0f}원 (+10%)")
            print(f"   손절가: {signal['stop_loss_price']:,.0f}원 (-5%)")
            rsi = signal.get('rsi') or 0
            ma20 = signal.get('ma_20') or 0
            ma50 = signal.get('ma_50') or 0
            print(f"   RSI: {rsi:.2f}")
            print(f"   MA20: {ma20:,.0f} > MA50: {ma50:,.0f}")
            print(f"   이유: {signal['reason']}")

    # 매도 시그널 (보유 포지션이 있을 경우)
    sell_signals = detector.detect_sell_signals(latest_date)
    print(f"\n📉 매도 시그널: {len(sell_signals)}개")

    if sell_signals:
        print("\n매도 대상:")
        for signal in sell_signals:
            print(f"  - {signal['ticker']}: RSI {signal['rsi']:.2f}")

    # 손절 시그널
    stop_loss_signals = detector.detect_stop_loss_signals(latest_date)
    print(f"\n⚠️  손절 시그널: {len(stop_loss_signals)}개")

    if stop_loss_signals:
        print("\n손절 대상:")
        for signal in stop_loss_signals:
            print(f"  - {signal['ticker']}: 손실률 {signal['loss_rate']:.2f}%")

    print("\n" + "=" * 60)
    print("테스트 완료!")
    print("=" * 60)

if __name__ == "__main__":
    main()
