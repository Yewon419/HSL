#!/usr/bin/env python3
"""
RSI 매매 전략 백테스팅
- 매수: RSI < 30
- 매도: RSI > 70
"""

import pandas as pd
import numpy as np
from datetime import datetime
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('backtest_rsi.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    return create_engine(DATABASE_URL, pool_pre_ping=True)

def get_stock_data_with_rsi(ticker, start_date, end_date):
    """특정 종목의 가격 및 RSI 데이터 조회"""
    engine = get_db_connection()

    query = """
        SELECT sp.date, sp.close_price, ti.rsi
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

def backtest_rsi_strategy(ticker, company_name, start_date, end_date, initial_capital=10000000):
    """RSI 전략 백테스팅"""
    try:
        df = get_stock_data_with_rsi(ticker, start_date, end_date)

        if len(df) < 20:
            return None

        # RSI가 없는 경우 스킵
        df = df.dropna(subset=['rsi'])
        if len(df) < 20:
            return None

        capital = initial_capital
        position = 0  # 보유 주식 수
        buy_price = 0
        trades = []

        for idx, row in df.iterrows():
            date = row['date']
            price = float(row['close_price'])
            rsi = float(row['rsi'])

            # 매수 신호: RSI < 30, 포지션 없을 때
            if rsi < 30 and position == 0:
                # 전액 매수
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

            # 매도 신호: RSI > 70, 포지션 있을 때
            elif rsi > 70 and position > 0:
                # 전량 매도
                revenue = position * price
                capital += revenue
                profit = (price - buy_price) * position

                trades.append({
                    'date': date,
                    'type': 'SELL',
                    'price': price,
                    'shares': position,
                    'rsi': rsi,
                    'profit': profit,
                    'capital': capital
                })

                position = 0
                buy_price = 0

        # 마지막 날 포지션이 남아있으면 정리
        final_value = capital
        if position > 0:
            last_price = float(df.iloc[-1]['close_price'])
            final_value += position * last_price

        total_return = ((final_value - initial_capital) / initial_capital) * 100

        return {
            'ticker': ticker,
            'company_name': company_name,
            'trades': trades,
            'total_trades': len([t for t in trades if t['type'] == 'BUY']),
            'initial_capital': initial_capital,
            'final_value': final_value,
            'return_pct': total_return
        }

    except Exception as e:
        logger.error(f"Error backtesting {ticker}: {e}")
        return None

def get_all_stocks_with_indicators(year):
    """지표가 있는 모든 종목 조회"""
    engine = get_db_connection()

    query = """
        SELECT DISTINCT s.ticker, s.company_name
        FROM stocks s
        JOIN technical_indicators ti ON s.ticker = ti.ticker
        WHERE s.currency = 'KRW'
          AND s.is_active = true
          AND ti.date >= :start_date
          AND ti.date < :end_date
          AND ti.rsi IS NOT NULL
        ORDER BY s.ticker
    """

    with engine.connect() as conn:
        result = conn.execute(
            text(query),
            {'start_date': f'{year}-01-01', 'end_date': f'{year+1}-01-01'}
        )

        stocks = [{'ticker': row[0], 'company_name': row[1]} for row in result]

    return stocks

def run_backtest_for_year(year):
    """특정 연도 전체 백테스팅"""
    logger.info("=" * 80)
    logger.info(f"{year}년 RSI 매매 전략 백테스팅")
    logger.info("매수 신호: RSI < 30")
    logger.info("매도 신호: RSI > 70")
    logger.info("=" * 80)

    start_date = f"{year}-01-01"
    end_date = f"{year}-12-31"

    # 현재 날짜가 연도 중간이면 현재까지만
    if year == 2025:
        end_date = datetime.now().strftime("%Y-%m-%d")

    logger.info(f"기간: {start_date} ~ {end_date}")
    logger.info("종목 조회 중...")

    stocks = get_all_stocks_with_indicators(year)
    total_stocks = len(stocks)

    logger.info(f"총 {total_stocks}개 종목 발견\n")

    results = []
    successful = 0
    failed = 0

    for i, stock in enumerate(stocks):
        ticker = stock['ticker']
        company_name = stock['company_name']

        if (i + 1) % 50 == 0:
            logger.info(f"진행중: {i+1}/{total_stocks} ({(i+1)/total_stocks*100:.1f}%)")

        result = backtest_rsi_strategy(ticker, company_name, start_date, end_date)

        if result and result['total_trades'] > 0:
            results.append(result)
            successful += 1
        else:
            failed += 1

    logger.info(f"\n처리 완료: {successful}개 성공, {failed}개 스킵")

    # 결과 분석
    if results:
        df_results = pd.DataFrame(results)

        # 통계
        total_return = df_results['return_pct'].sum()
        avg_return = df_results['return_pct'].mean()
        positive_trades = len(df_results[df_results['return_pct'] > 0])
        negative_trades = len(df_results[df_results['return_pct'] < 0])
        win_rate = (positive_trades / len(df_results)) * 100

        logger.info("\n" + "=" * 80)
        logger.info(f"{year}년 RSI 전략 백테스팅 결과")
        logger.info("=" * 80)
        logger.info(f"백테스팅 종목 수: {len(results)}개")
        logger.info(f"평균 수익률: {avg_return:.2f}%")
        logger.info(f"승률: {win_rate:.2f}% ({positive_trades}/{len(df_results)})")
        logger.info(f"수익 종목: {positive_trades}개")
        logger.info(f"손실 종목: {negative_trades}개")
        logger.info(f"\n상위 10개 수익 종목:")

        top_10 = df_results.nlargest(10, 'return_pct')
        for idx, row in top_10.iterrows():
            logger.info(f"  {row['ticker']} ({row['company_name']}): {row['return_pct']:.2f}% (거래 {row['total_trades']}회)")

        logger.info(f"\n하위 10개 손실 종목:")
        bottom_10 = df_results.nsmallest(10, 'return_pct')
        for idx, row in bottom_10.iterrows():
            logger.info(f"  {row['ticker']} ({row['company_name']}): {row['return_pct']:.2f}% (거래 {row['total_trades']}회)")

        logger.info("=" * 80)

        # 결과를 CSV로 저장
        df_results[['ticker', 'company_name', 'total_trades', 'return_pct']].to_csv(
            f'backtest_rsi_{year}.csv', index=False, encoding='utf-8-sig'
        )
        logger.info(f"결과 저장: backtest_rsi_{year}.csv")

        return {
            'year': year,
            'total_stocks': len(results),
            'avg_return': avg_return,
            'win_rate': win_rate,
            'positive_trades': positive_trades,
            'negative_trades': negative_trades
        }
    else:
        logger.info("백테스팅 결과가 없습니다.")
        return None

if __name__ == "__main__":
    # 2024년 백테스팅
    result_2024 = run_backtest_for_year(2024)

    # 2025년 백테스팅
    result_2025 = run_backtest_for_year(2025)

    # 최종 요약
    logger.info("\n" + "=" * 80)
    logger.info("전체 백테스팅 요약")
    logger.info("=" * 80)

    if result_2024:
        logger.info(f"\n2024년:")
        logger.info(f"  평균 수익률: {result_2024['avg_return']:.2f}%")
        logger.info(f"  승률: {result_2024['win_rate']:.2f}%")
        logger.info(f"  백테스팅 종목: {result_2024['total_stocks']}개")

    if result_2025:
        logger.info(f"\n2025년:")
        logger.info(f"  평균 수익률: {result_2025['avg_return']:.2f}%")
        logger.info(f"  승률: {result_2025['win_rate']:.2f}%")
        logger.info(f"  백테스팅 종목: {result_2025['total_stocks']}개")

    logger.info("=" * 80)