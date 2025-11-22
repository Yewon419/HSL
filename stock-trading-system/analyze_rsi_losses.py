#!/usr/bin/env python3
"""
RSI 전략 손실 종목 상세 분석
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text
import logging
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def get_stock_data_with_indicators(ticker, start_date, end_date):
    """주가 및 지표 데이터 조회"""
    engine = get_db_connection()

    query = """
        SELECT
            sp.date,
            sp.open_price,
            sp.high_price,
            sp.low_price,
            sp.close_price,
            sp.volume,
            ti.rsi,
            ti.macd,
            ti.macd_signal,
            ti.ma_20,
            ti.ma_50
        FROM stock_prices sp
        LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
        WHERE sp.ticker = :ticker
          AND sp.date >= :start_date
          AND sp.date <= :end_date
        ORDER BY sp.date
    """

    with engine.connect() as conn:
        df = pd.read_sql(
            text(query),
            conn,
            params={'ticker': ticker, 'start_date': start_date, 'end_date': end_date}
        )

    return df

def analyze_rsi_trades(ticker, company_name, start_date, end_date):
    """RSI 매매 상세 분석"""
    logger.info("=" * 80)
    logger.info(f"{company_name} ({ticker}) RSI 매매 분석")
    logger.info("=" * 80)

    df = get_stock_data_with_indicators(ticker, start_date, end_date)

    if len(df) == 0:
        logger.error("데이터 없음")
        return

    df = df.dropna(subset=['rsi'])

    logger.info(f"분석 기간: {start_date} ~ {end_date}")
    logger.info(f"데이터 개수: {len(df)}일")

    # RSI 통계
    logger.info(f"\nRSI 통계:")
    logger.info(f"  평균: {df['rsi'].mean():.2f}")
    logger.info(f"  최소: {df['rsi'].min():.2f}")
    logger.info(f"  최대: {df['rsi'].max():.2f}")
    logger.info(f"  RSI < 30 횟수: {len(df[df['rsi'] < 30])}일")
    logger.info(f"  RSI > 70 횟수: {len(df[df['rsi'] > 70])}일")

    # 가격 통계
    logger.info(f"\n주가 통계:")
    logger.info(f"  시작가: {df.iloc[0]['close_price']:,.0f}원")
    logger.info(f"  종료가: {df.iloc[-1]['close_price']:,.0f}원")
    logger.info(f"  최고가: {df['high_price'].max():,.0f}원")
    logger.info(f"  최저가: {df['low_price'].min():,.0f}원")
    logger.info(f"  변동률: {((df.iloc[-1]['close_price'] - df.iloc[0]['close_price']) / df.iloc[0]['close_price'] * 100):.2f}%")

    # RSI 매매 시뮬레이션
    capital = 10000000
    position = 0
    buy_price = 0
    trades = []

    for idx, row in df.iterrows():
        date = row['date']
        price = float(row['close_price'])
        rsi = float(row['rsi'])

        # 매수 신호
        if rsi < 30 and position == 0:
            position = capital // price
            buy_price = price
            cost = position * price
            capital -= cost

            trades.append({
                'date': date,
                'type': 'BUY',
                'price': price,
                'shares': position,
                'rsi': rsi,
                'capital': capital
            })

        # 매도 신호
        elif rsi > 70 and position > 0:
            revenue = position * price
            capital += revenue
            profit = (price - buy_price) * position
            profit_pct = ((price - buy_price) / buy_price) * 100

            trades.append({
                'date': date,
                'type': 'SELL',
                'price': price,
                'shares': position,
                'rsi': rsi,
                'profit': profit,
                'profit_pct': profit_pct,
                'capital': capital
            })

            position = 0
            buy_price = 0

    # 거래 내역 출력
    logger.info(f"\n총 거래 횟수: {len([t for t in trades if t['type'] == 'BUY'])}회")

    for i, trade in enumerate(trades):
        if trade['type'] == 'BUY':
            logger.info(f"\n거래 {i//2 + 1}:")
            logger.info(f"  매수: {trade['date'].strftime('%Y-%m-%d')} | 가격: {trade['price']:,.0f}원 | RSI: {trade['rsi']:.2f}")
        else:
            logger.info(f"  매도: {trade['date'].strftime('%Y-%m-%d')} | 가격: {trade['price']:,.0f}원 | RSI: {trade['rsi']:.2f}")
            logger.info(f"  손익: {trade['profit']:,.0f}원 ({trade['profit_pct']:.2f}%)")

    # 최종 손익
    final_value = capital
    if position > 0:
        last_price = float(df.iloc[-1]['close_price'])
        final_value += position * last_price
        logger.info(f"\n미실현 포지션: {position}주 @ {last_price:,.0f}원")

    total_return = ((final_value - 10000000) / 10000000) * 100
    logger.info(f"\n최종 손익률: {total_return:.2f}%")

    # 손실 원인 분석
    logger.info("\n" + "=" * 80)
    logger.info("손실 원인 분석")
    logger.info("=" * 80)

    # 1. 하락 추세 분석
    if df.iloc[-1]['close_price'] < df.iloc[0]['close_price']:
        logger.info("1. 전체 하락 추세:")
        logger.info(f"   - 기간 중 주가 {((df.iloc[-1]['close_price'] - df.iloc[0]['close_price']) / df.iloc[0]['close_price'] * 100):.2f}% 하락")

    # 2. RSI 매매 타이밍 분석
    buy_signals = [t for t in trades if t['type'] == 'BUY']
    sell_signals = [t for t in trades if t['type'] == 'SELL']

    if buy_signals:
        avg_buy_rsi = np.mean([t['rsi'] for t in buy_signals])
        logger.info(f"\n2. 매수 타이밍:")
        logger.info(f"   - 평균 매수 RSI: {avg_buy_rsi:.2f}")
        logger.info(f"   - 매수 후 추가 하락 여부 확인 필요")

    if sell_signals:
        avg_sell_rsi = np.mean([t['rsi'] for t in sell_signals])
        avg_profit = np.mean([t['profit_pct'] for t in sell_signals])
        logger.info(f"\n3. 매도 타이밍:")
        logger.info(f"   - 평균 매도 RSI: {avg_sell_rsi:.2f}")
        logger.info(f"   - 평균 거래당 손익: {avg_profit:.2f}%")

    # 4. 추세 분석
    if 'ma_20' in df.columns and 'ma_50' in df.columns:
        df_recent = df.tail(50).dropna(subset=['ma_20', 'ma_50'])
        if len(df_recent) > 0:
            ma_trend = "상승" if df_recent.iloc[-1]['ma_20'] > df_recent.iloc[-1]['ma_50'] else "하락"
            logger.info(f"\n4. 추세 분석:")
            logger.info(f"   - MA20/MA50 기준: {ma_trend} 추세")
            logger.info(f"   - MA20: {df_recent.iloc[-1]['ma_20']:,.0f}원")
            logger.info(f"   - MA50: {df_recent.iloc[-1]['ma_50']:,.0f}원")

    # 5. 변동성 분석
    daily_returns = df['close_price'].pct_change().dropna()
    volatility = daily_returns.std() * 100
    logger.info(f"\n5. 변동성 분석:")
    logger.info(f"   - 일일 변동성(표준편차): {volatility:.2f}%")
    logger.info(f"   - 변동성이 {'높음' if volatility > 3 else '보통' if volatility > 2 else '낮음'}")

    logger.info("=" * 80)

    return {
        'ticker': ticker,
        'company_name': company_name,
        'trades': trades,
        'total_return': total_return,
        'volatility': volatility
    }

if __name__ == "__main__":
    start_date = "2025-01-01"
    end_date = "2025-10-01"

    # 웰크론한텍 분석
    logger.info("\n\n")
    result1 = analyze_rsi_trades('112040', '웰크론한텍', start_date, end_date)

    logger.info("\n\n")
    # SK이노베이션 분석
    result2 = analyze_rsi_trades('096770', 'SK이노베이션', start_date, end_date)

    # 요약
    logger.info("\n\n")
    logger.info("=" * 80)
    logger.info("종합 분석")
    logger.info("=" * 80)
    logger.info("\n두 종목 모두 RSI 전략으로 손실을 본 공통 원인:")
    logger.info("1. RSI < 30 매수 후 추가 하락 (하락 추세 지속)")
    logger.info("2. RSI > 70 도달 전 하락하여 손절 기회 없음")
    logger.info("3. 전체적인 하락 추세에서 RSI 역추세 전략의 한계")
    logger.info("\n개선 방안:")
    logger.info("- 추세 필터 추가 (MA 기반)")
    logger.info("- 손절선 설정 (예: -5% 손절)")
    logger.info("- RSI 임계값 조정 (더 극단적인 값 사용)")
    logger.info("=" * 80)