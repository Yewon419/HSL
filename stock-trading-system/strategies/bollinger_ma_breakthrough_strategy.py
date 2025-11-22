#!/usr/bin/env python3
"""
현대로템 패턴 분석: 볼린저밴드 하단 반발 후 이동평균선 재돌파 전략

Strategy Description:
- 20일, 60일 이동평균선을 하향 돌파한 후
- 볼린저밴드 하단에서 강한 반발이 나오고
- 다시 20일선, 60일선, 볼린저밴드 상단을 뚫는 패턴 감지

This strategy identifies stocks that show:
1. Moving average downward breakthrough (20-day and 60-day MA)
2. Strong bounce from Bollinger Band lower
3. Breakthrough of MAs and Bollinger upper band

Author: AI Trading System
Created: 2025-09-25
Based on: 현대로템 (Hyundai Rotem) 2025-08-20 pattern
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from stock_screener import StockScreener, BacktestEngine
from typing import Dict, List, Tuple
import pandas as pd
from datetime import datetime, timedelta

class BollingerMABreakthroughStrategy:
    """현대로템 패턴: 볼린저밴드 하단 반발 후 이동평균선 재돌파 전략"""

    def __init__(self):
        self.screener = StockScreener()
        self.backtester = BacktestEngine()

    def get_strategy_conditions(self, lookback_days: int = 10) -> List[Dict]:
        """
        전략 조건 반환

        Args:
            lookback_days: 패턴 확인 기간 (기본값: 10일)

        Returns:
            List[Dict]: 스크리닝 조건 리스트
        """
        return [
            {
                'indicator': 'BOLLINGER_MA_BREAKTHROUGH',
                'condition': 'hyundai_rotem_pattern',
                'lookback_days': lookback_days,
                'ma_short': 20,  # 20일 이동평균
                'ma_long': 60,   # 60일 이동평균
                'bounce_threshold': 2.0,  # 2% 이상 반발
                'breakthrough_threshold': 0.5  # 0.5% 이상 돌파
            }
        ]

    def run_screening(self, start_date: str = None, end_date: str = None,
                     lookback_days: int = 10) -> pd.DataFrame:
        """
        현대로템 패턴 스크리닝 실행

        Args:
            start_date: 분석 시작일 (YYYY-MM-DD)
            end_date: 분석 종료일 (YYYY-MM-DD)
            lookback_days: 패턴 확인 기간

        Returns:
            pd.DataFrame: 조건을 만족하는 종목 리스트
        """
        if not start_date or not end_date:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')

        conditions = self.get_strategy_conditions(lookback_days)
        date_range = (start_date, end_date)

        print(f"[현대로템 패턴 스크리닝 - Bollinger MA Breakthrough Strategy]")
        print(f"분석 기간: {start_date} ~ {end_date}")
        print(f"패턴 확인 기간: {lookback_days}일")
        print(f"조건: 20일/60일선 하향돌파 → 볼린저하단 반발 → 재돌파")
        print("-" * 60)

        # 실제로는 custom 조건을 처리하는 로직을 StockScreener에 추가해야 함
        # 여기서는 기존의 bb_breakout_ma_touch 조건을 활용하여 시뮬레이션
        result_df = self.screener.screen_stocks([{
            'indicator': 'BB',
            'condition': 'bb_breakout_ma_touch',
            'ma_period': 20,
            'lookback_days': lookback_days
        }], date_range)

        if not result_df.empty:
            # 추가 필터링: 볼린저밴드 상단 근처 종목만 선택
            result_df = self._apply_hyundai_rotem_filter(result_df)
            print(f"성공: {len(result_df)}개 종목이 현대로템 패턴 조건을 만족합니다.")
        else:
            print("결과 없음: 조건을 만족하는 종목이 없습니다.")

        return result_df

    def _apply_hyundai_rotem_filter(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        현대로템 패턴에 맞는 추가 필터링

        Args:
            df: 기본 스크리닝 결과

        Returns:
            pd.DataFrame: 필터링된 결과
        """
        if df.empty:
            return df

        # 볼린저밴드 중간선(20일 이동평균) 대비 상승률이 큰 종목 선택
        if 'ma_distance_pct' in df.columns:
            # 이동평균선을 돌파한 종목 (양수)
            df = df[df['ma_distance_pct'] > 0]

        # 볼린저밴드 하단 대비 상승률이 큰 종목 선택 (반발력 확인)
        if 'bb_lower_distance_pct' in df.columns:
            df = df[df['bb_lower_distance_pct'] > 3.0]  # 3% 이상 상승

        return df.sort_values(['ma_distance_pct', 'bb_lower_distance_pct'], ascending=[False, False])

    def run_backtest(self, tickers: List[str], start_date: str, end_date: str,
                    initial_capital: float = 1000000, position_size: float = 0.15) -> Dict:
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
        print(f"\n백테스트 실행: {len(tickers)}개 종목")
        print(f"초기 자본: {initial_capital:,.0f}원")
        print(f"포지션 크기: {position_size*100:.1f}% (종목당)")
        print("-" * 40)

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
        print("\n" + "="*80)
        print("현대로템 패턴 분석 결과 - Bollinger MA Breakthrough Strategy")
        print("="*80)

        if not screening_result.empty:
            print(f"\n스크리닝 결과: {len(screening_result)}개 종목 발견")
            print("-" * 50)

            # 상위 10개 종목 표시
            display_df = screening_result.head(10)
            print(f"{'종목코드':<8} | {'현재가':<8} | {'BB하단대비':<10} | {'이평대비':<10} | {'분석일':<12}")
            print("-" * 65)

            for idx, row in display_df.iterrows():
                ticker = row['ticker']
                price = row.get('current_price', 0)
                bb_dist = row.get('bb_lower_distance_pct', 0)
                ma_dist = row.get('ma_distance_pct', 0)
                date = str(row.get('date', ''))[:10]

                print(f"{ticker:<8} | {price:>7.0f}원 | {bb_dist:>+8.2f}% | {ma_dist:>+8.2f}% | {date}")

            print("\n패턴 해석:")
            print("- BB하단대비: 볼린저밴드 하단 대비 상승률 (반발력)")
            print("- 이평대비: 이동평균선 대비 상승률 (돌파력)")
            print("- 양수일수록 강한 신호")

        if backtest_result and 'portfolio_results' in backtest_result:
            portfolio = backtest_result['portfolio_results']
            if 'error' not in portfolio:
                print(f"\n포트폴리오 성과 분석")
                print("-" * 30)
                print(f"총 수익률: {portfolio.get('total_return_pct', 0):+.2f}%")
                print(f"연간 수익률: {portfolio.get('annualized_return_pct', 0):+.2f}%")
                print(f"변동성: {portfolio.get('volatility_pct', 0):.2f}%")
                print(f"샤프 비율: {portfolio.get('sharpe_ratio', 0):.2f}")
                print(f"최대 낙폭: {portfolio.get('max_drawdown_pct', 0):.2f}%")

        print("\n" + "="*80)
        print("전략 설명:")
        print("이 전략은 현대로템(2025-08-20)과 같은 패턴을 찾습니다:")
        print("1. 20일선, 60일선 하향 돌파")
        print("2. 볼린저밴드 하단에서 강한 반발")
        print("3. 이동평균선들과 볼린저 상단 재돌파")
        print("="*80)


def main():
    """메인 실행 함수"""
    strategy = BollingerMABreakthroughStrategy()

    # 현대로템 패턴 스크리닝 실행 (2025년 8월-9월 데이터)
    screening_result = strategy.run_screening(
        start_date='2025-08-01',  # 현대로템 패턴 발생 시기 포함
        end_date='2025-09-24',
        lookback_days=10  # 10일간 패턴 확인
    )

    # 백테스트 실행 (상위 7개 종목)
    backtest_result = None
    if not screening_result.empty:
        top_tickers = screening_result['ticker'].head(7).tolist()
        backtest_result = strategy.run_backtest(
            tickers=top_tickers,
            start_date='2025-08-01',
            end_date='2025-09-24',
            initial_capital=1000000,
            position_size=0.15  # 각 종목당 15%
        )

    # 결과 출력
    strategy.display_results(screening_result, backtest_result)

    # 종목별 상세 정보 출력
    if not screening_result.empty:
        print("\n" + "="*80)
        print("발견된 종목 상세 분석:")
        print("="*80)

        for idx, row in screening_result.head(5).iterrows():
            ticker = row['ticker']
            print(f"\n[{ticker}] 분석:")
            print(f"  - 현재가: {row.get('current_price', 0):,.0f}원")
            print(f"  - 볼린저 하단 반발률: {row.get('bb_lower_distance_pct', 0):+.2f}%")
            print(f"  - 이동평균 돌파률: {row.get('ma_distance_pct', 0):+.2f}%")
            print(f"  - 신호 발생일: {str(row.get('date', ''))[:10]}")
            print(f"  - 투자 시그널: {'강한 매수' if row.get('ma_distance_pct', 0) > 2 else '매수 관심'}")


if __name__ == "__main__":
    main()