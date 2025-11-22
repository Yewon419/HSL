#!/usr/bin/env python3
"""
볼린저밴드 하단 돌파 후 이동평균선 터치 전략 템플릿

Strategy Description:
- 주가가 볼린저밴드 하단선을 하향 돌파했다가
- 다시 상승하여 이동평균선을 터치하거나 돌파하는 패턴을 감지
- 반등 신호로 활용할 수 있는 전략

Author: AI Trading System
Created: 2025-09-25
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_screener import StockScreener, BacktestEngine
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime, timedelta

class BollingerBreakoutMATouchStrategy:
    """볼린저밴드 하단돌파 후 이평선터치 전략"""

    def __init__(self):
        self.screener = StockScreener()
        self.backtester = BacktestEngine()

    def get_strategy_conditions(self, ma_period: int = 20, lookback_days: int = 5) -> List[Dict]:
        """
        전략 조건 반환

        Args:
            ma_period: 이동평균 기간 (기본값: 20일)
            lookback_days: 패턴 확인 기간 (기본값: 5일)

        Returns:
            List[Dict]: 스크리닝 조건 리스트
        """
        return [
            {
                'indicator': 'BB',  # 볼린저밴드와 이동평균을 함께 사용하는 특수 조건
                'condition': 'bb_breakout_ma_touch',
                'ma_period': ma_period,
                'lookback_days': lookback_days
            }
        ]

    def run_screening(self, start_date: str = None, end_date: str = None,
                     ma_period: int = 20, lookback_days: int = 5) -> pd.DataFrame:
        """
        전략에 따른 종목 스크리닝 실행

        Args:
            start_date: 분석 시작일 (YYYY-MM-DD)
            end_date: 분석 종료일 (YYYY-MM-DD)
            ma_period: 이동평균 기간
            lookback_days: 패턴 확인 기간

        Returns:
            pd.DataFrame: 조건을 만족하는 종목 리스트
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        conditions = self.get_strategy_conditions(ma_period, lookback_days)
        date_range = (start_date, end_date)

        print(f"[BB Breakout MA Touch Strategy Screening]")
        print(f"Analysis Period: {start_date} ~ {end_date}")
        print(f"Moving Average Period: {ma_period} days")
        print(f"Pattern Lookback Period: {lookback_days} days")
        print("-" * 50)

        result_df = self.screener.screen_stocks(conditions, date_range)

        if not result_df.empty:
            print(f"SUCCESS: {len(result_df)} stocks found matching criteria.")
        else:
            print("NO MATCHES: No stocks found matching criteria.")

        return result_df

    def run_backtest(self, tickers: List[str], start_date: str, end_date: str,
                    initial_capital: float = 1000000, position_size: float = 0.2) -> Dict:
        """
        백테스트 실행

        Args:
            tickers: 대상 종목 리스트
            start_date: 백테스트 시작일
            end_date: 백테스트 종료일
            initial_capital: 초기 자본
            position_size: 포지션 크기 (0.0-1.0)

        Returns:
            Dict: 백테스트 결과
        """
        print(f"Backtest Execution: {len(tickers)} stocks")
        print(f"Initial Capital: {initial_capital:,.0f} KRW")
        print(f"Position Size: {position_size*100:.1f}%")
        print("-" * 30)

        result = self.backtester.run_backtest(
            tickers=tickers,
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital,
            position_size=position_size,
            transaction_cost=0.003  # 0.3% 거래비용
        )

        return result

    def display_results(self, screening_result: pd.DataFrame, backtest_result: Dict = None):
        """결과 출력"""
        print("\n" + "="*60)
        print("BB Breakout + MA Touch Strategy Results")
        print("="*60)

        if not screening_result.empty:
            print(f"\nScreening Results: {len(screening_result)} stocks")
            print("-" * 40)

            # Top 10 stocks display
            display_df = screening_result.head(10)
            for idx, row in display_df.iterrows():
                ticker = row['ticker']
                company = row.get('company_name', 'N/A')
                price = row.get('current_price', 0)
                bb_distance = row.get('bb_lower_distance_pct', 0)
                ma_distance = row.get('ma_distance_pct', 0)

                print(f"{ticker:8} | {company:15} | {price:>8.0f} KRW")
                print(f"         └ BB Lower: {bb_distance:+6.2f}% | MA: {ma_distance:+6.2f}%")

        if backtest_result and 'portfolio_results' in backtest_result:
            portfolio = backtest_result['portfolio_results']
            if 'error' not in portfolio:
                print(f"\nPortfolio Performance")
                print("-" * 30)
                print(f"Total Return: {portfolio.get('total_return_pct', 0):+.2f}%")
                print(f"Annualized Return: {portfolio.get('annualized_return_pct', 0):+.2f}%")
                print(f"Volatility: {portfolio.get('volatility_pct', 0):.2f}%")
                print(f"Sharpe Ratio: {portfolio.get('sharpe_ratio', 0):.2f}")
                print(f"Max Drawdown: {portfolio.get('max_drawdown_pct', 0):.2f}%")

        print("\n" + "="*60)


def main():
    """메인 실행 함수"""
    strategy = BollingerBreakoutMATouchStrategy()

    # 스크리닝 실행
    screening_result = strategy.run_screening(
        start_date='2025-09-01',
        end_date='2025-09-24',
        ma_period=20,  # 20일 이동평균
        lookback_days=5  # 5일 패턴 확인
    )

    # 백테스트 실행 (상위 5개 종목)
    backtest_result = None
    if not screening_result.empty:
        top_tickers = screening_result['ticker'].head(5).tolist()
        backtest_result = strategy.run_backtest(
            tickers=top_tickers,
            start_date='2025-09-01',
            end_date='2025-09-24',
            initial_capital=1000000,
            position_size=0.2  # 각 종목당 20%
        )

    # 결과 출력
    strategy.display_results(screening_result, backtest_result)


if __name__ == "__main__":
    main()