#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Advanced Portfolio Optimization and Stock Selection System
포트폴리오 최적화 및 자동 종목 선택 시스템
"""

import sqlite3
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import yfinance as yf
from scipy.optimize import minimize
import warnings
warnings.filterwarnings('ignore')

class PortfolioOptimizer:
    def __init__(self, db_path='stock_demo.db'):
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)

        # 투자 가능한 종목 풀 (확장 가능)
        self.stock_universe = {
            # 한국 주식
            '005930.KS': 'Samsung Electronics',
            '000660.KS': 'SK Hynix',
            '035420.KS': 'NAVER',
            '207940.KS': 'Samsung Bio',
            '006400.KS': 'Samsung SDI',
            '051910.KS': 'LG Chem',
            '035720.KS': 'Kakao',
            '028260.KS': 'Samsung C&T',

            # 미국 주식
            'AAPL': 'Apple Inc.',
            'MSFT': 'Microsoft Corp.',
            'GOOGL': 'Alphabet Inc.',
            'AMZN': 'Amazon.com Inc.',
            'NVDA': 'NVIDIA Corp.',
            'TSLA': 'Tesla Inc.',
            'META': 'Meta Platforms',
            'NFLX': 'Netflix Inc.',
            'AMD': 'Advanced Micro Devices',
            'CRM': 'Salesforce Inc.'
        }

        self.risk_free_rate = 0.03  # 3% 무위험 수익률

    def get_stock_returns(self, lookback_days=252) -> pd.DataFrame:
        """주식 수익률 데이터 계산"""
        query = """
        SELECT ticker, date, close_price
        FROM stock_prices
        WHERE date >= date('now', '-{} days')
        ORDER BY ticker, date
        """.format(lookback_days + 50)  # 여유분 추가

        df = pd.read_sql_query(query, self.conn)

        if df.empty:
            print("No price data found. Fetching fresh data...")
            return self._fetch_fresh_data()

        # 피벗 테이블로 변환
        price_matrix = df.pivot(index='date', columns='ticker', values='close_price')

        # 일별 수익률 계산
        returns = price_matrix.pct_change().dropna()

        return returns

    def _fetch_fresh_data(self, days=252) -> pd.DataFrame:
        """새로운 데이터 수집 (DB에 데이터가 없을 경우)"""
        print("Fetching fresh market data...")

        end_date = datetime.now()
        start_date = end_date - timedelta(days=days + 50)

        price_data = {}

        for ticker in self.stock_universe.keys():
            try:
                stock = yf.Ticker(ticker)
                hist = stock.history(start=start_date, end=end_date)

                if not hist.empty:
                    price_data[ticker] = hist['Close']
                    print(f"✓ {ticker}: {len(hist)} days")

            except Exception as e:
                print(f"✗ {ticker}: Failed - {e}")
                continue

        if not price_data:
            print("No data fetched. Using dummy data for demo.")
            return self._generate_dummy_returns()

        # DataFrame으로 결합
        price_df = pd.DataFrame(price_data)
        price_df = price_df.dropna()

        # 수익률 계산
        returns = price_df.pct_change().dropna()

        return returns

    def _generate_dummy_returns(self) -> pd.DataFrame:
        """데모용 더미 데이터 생성"""
        np.random.seed(42)

        dates = pd.date_range(start='2023-01-01', end='2024-12-31', freq='D')
        tickers = list(self.stock_universe.keys())[:8]  # 상위 8개만

        # 시뮬레이션 수익률 생성
        returns_data = {}
        for ticker in tickers:
            # 각 주식마다 다른 특성 부여
            if ticker.endswith('.KS'):  # 한국 주식
                mean_return = np.random.uniform(-0.001, 0.002)
                volatility = np.random.uniform(0.015, 0.035)
            else:  # 미국 주식
                mean_return = np.random.uniform(-0.0005, 0.003)
                volatility = np.random.uniform(0.020, 0.045)

            returns_data[ticker] = np.random.normal(mean_return, volatility, len(dates))

        return pd.DataFrame(returns_data, index=dates)

    def calculate_portfolio_metrics(self, weights: np.array, returns: pd.DataFrame) -> Dict:
        """포트폴리오 메트릭 계산"""
        portfolio_returns = (returns * weights).sum(axis=1)

        annual_return = portfolio_returns.mean() * 252
        annual_volatility = portfolio_returns.std() * np.sqrt(252)
        sharpe_ratio = (annual_return - self.risk_free_rate) / annual_volatility

        # 최대 손실 (Maximum Drawdown)
        cumulative = (1 + portfolio_returns).cumprod()
        rolling_max = cumulative.expanding().max()
        drawdown = (cumulative / rolling_max) - 1
        max_drawdown = drawdown.min()

        return {
            'annual_return': annual_return,
            'annual_volatility': annual_volatility,
            'sharpe_ratio': sharpe_ratio,
            'max_drawdown': max_drawdown
        }

    def stock_selection_score(self, returns: pd.DataFrame) -> pd.Series:
        """종목 선택 점수 계산 (다중 지표 융합)"""
        scores = pd.Series(index=returns.columns, dtype=float)

        for ticker in returns.columns:
            stock_returns = returns[ticker].dropna()

            if len(stock_returns) < 30:  # 최소 데이터 요구
                scores[ticker] = 0
                continue

            # 1. 수익률 점수 (연율화)
            annual_return = stock_returns.mean() * 252
            return_score = min(annual_return * 10, 5)  # 최대 5점

            # 2. 샤프 비율 점수
            volatility = stock_returns.std() * np.sqrt(252)
            if volatility > 0:
                sharpe = (annual_return - self.risk_free_rate) / volatility
                sharpe_score = min(sharpe * 2, 3)  # 최대 3점
            else:
                sharpe_score = 0

            # 3. 모멘텀 점수 (최근 성과)
            recent_returns = stock_returns.tail(20)
            momentum = recent_returns.mean() * 252
            momentum_score = min(momentum * 5, 2)  # 최대 2점

            # 4. 안정성 점수 (변동성의 역수)
            stability_score = max(0, 2 - volatility * 5)  # 최대 2점

            # 5. 기술적 지표 점수 (RSI 기반)
            technical_score = self._get_technical_score(ticker)

            # 총점 계산 (가중평균)
            total_score = (
                return_score * 0.3 +
                sharpe_score * 0.25 +
                momentum_score * 0.2 +
                stability_score * 0.15 +
                technical_score * 0.1
            )

            scores[ticker] = max(0, total_score)

        return scores.sort_values(ascending=False)

    def _get_technical_score(self, ticker: str) -> float:
        """기술적 지표 점수 계산"""
        try:
            query = """
            SELECT rsi, macd, macd_signal
            FROM technical_indicators
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """
            cursor = self.conn.cursor()
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()

            if not result:
                return 1.0  # 중립 점수

            rsi, macd, macd_signal = result
            score = 1.0

            # RSI 점수
            if rsi and 30 <= rsi <= 70:  # 적정 구간
                score += 0.5
            elif rsi and rsi < 30:  # 과매도 (매수 기회)
                score += 1.0

            # MACD 점수
            if macd and macd_signal and macd > macd_signal:  # 상승 모멘텀
                score += 0.5

            return min(score, 2.0)

        except Exception:
            return 1.0

    def optimize_portfolio(self, selected_stocks: List[str], target_return: Optional[float] = None) -> Dict:
        """포트폴리오 최적화 (평균-분산 최적화)"""
        returns = self.get_stock_returns()

        # 선택된 종목만 필터링
        available_stocks = [s for s in selected_stocks if s in returns.columns]

        if len(available_stocks) < 2:
            print("Not enough stocks for optimization")
            return self._create_equal_weight_portfolio(available_stocks, returns)

        returns = returns[available_stocks]
        n_assets = len(available_stocks)

        # 기대수익률과 공분산 행렬
        mu = returns.mean() * 252
        sigma = returns.cov() * 252

        # 제약 조건
        constraints = [
            {'type': 'eq', 'fun': lambda x: np.sum(x) - 1}  # 합이 1
        ]

        # 목표 수익률이 있으면 추가 제약
        if target_return:
            constraints.append({
                'type': 'eq',
                'fun': lambda x: np.dot(x, mu) - target_return
            })

        # 경계 조건 (각 자산 0~50%)
        bounds = tuple((0, 0.5) for _ in range(n_assets))

        # 초기 추정치 (동일 비중)
        x0 = np.array([1/n_assets] * n_assets)

        # 최적화 목적함수 (샤프 비율 최대화)
        def objective(x):
            portfolio_return = np.dot(x, mu)
            portfolio_vol = np.sqrt(np.dot(x, np.dot(sigma, x)))
            if portfolio_vol == 0:
                return -np.inf
            sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
            return -sharpe  # 최소화 문제로 변환

        # 최적화 실행
        try:
            result = minimize(
                objective, x0,
                method='SLSQP',
                bounds=bounds,
                constraints=constraints,
                options={'ftol': 1e-9, 'maxiter': 1000}
            )

            if result.success:
                optimal_weights = result.x
            else:
                print("Optimization failed. Using equal weights.")
                optimal_weights = x0

        except Exception as e:
            print(f"Optimization error: {e}. Using equal weights.")
            optimal_weights = x0

        # 결과 정리
        portfolio_data = {}
        for i, stock in enumerate(available_stocks):
            if optimal_weights[i] > 0.01:  # 1% 이상만 포함
                portfolio_data[stock] = {
                    'weight': float(optimal_weights[i]),
                    'name': self.stock_universe.get(stock, stock)
                }

        # 포트폴리오 성과 계산
        metrics = self.calculate_portfolio_metrics(optimal_weights, returns)

        return {
            'portfolio': portfolio_data,
            'metrics': metrics,
            'total_stocks': len(portfolio_data),
            'optimization_success': result.success if 'result' in locals() else False
        }

    def _create_equal_weight_portfolio(self, stocks: List[str], returns: pd.DataFrame) -> Dict:
        """동일 비중 포트폴리오 생성 (최적화 실패시 대안)"""
        if not stocks:
            return {'portfolio': {}, 'metrics': {}, 'total_stocks': 0}

        weight = 1.0 / len(stocks)
        portfolio_data = {}

        for stock in stocks:
            portfolio_data[stock] = {
                'weight': weight,
                'name': self.stock_universe.get(stock, stock)
            }

        weights = np.array([weight] * len(stocks))
        metrics = self.calculate_portfolio_metrics(weights, returns[stocks])

        return {
            'portfolio': portfolio_data,
            'metrics': metrics,
            'total_stocks': len(stocks),
            'optimization_success': False
        }

    def generate_optimal_portfolio(self,
                                  investment_amount: float = 10000000,  # 1천만원
                                  max_stocks: int = 8,
                                  target_return: Optional[float] = None) -> Dict:
        """최적 포트폴리오 생성 (전체 프로세스)"""

        print("Analyzing stock universe...")

        # 1. 주식 수익률 데이터 수집
        returns = self.get_stock_returns()

        if returns.empty:
            return {'error': 'No market data available'}

        # 2. 종목 선택 (점수 기반)
        print("Scoring and selecting stocks...")
        stock_scores = self.stock_selection_score(returns)

        # 상위 종목 선택
        top_stocks = stock_scores.head(max_stocks).index.tolist()

        print(f"Selected stocks: {top_stocks}")

        # 3. 포트폴리오 최적화
        print("Optimizing portfolio allocation...")
        optimization_result = self.optimize_portfolio(top_stocks, target_return)

        # 4. 투자 금액 할당
        allocation_result = self._calculate_allocation(
            optimization_result['portfolio'],
            investment_amount
        )

        # 5. 최종 결과 생성
        final_result = {
            'timestamp': datetime.now().isoformat(),
            'investment_amount': investment_amount,
            'selected_stocks': len(top_stocks),
            'final_portfolio_size': optimization_result['total_stocks'],
            'stock_scores': stock_scores.head(max_stocks).to_dict(),
            'portfolio_weights': optimization_result['portfolio'],
            'share_allocation': allocation_result,
            'expected_metrics': optimization_result['metrics'],
            'optimization_success': optimization_result['optimization_success']
        }

        return final_result

    def _calculate_allocation(self, portfolio: Dict, total_amount: float) -> Dict:
        """투자 금액을 주식별로 할당"""
        allocation = {}

        # 현재 주가 가져오기
        current_prices = self._get_current_prices(list(portfolio.keys()))

        for ticker, data in portfolio.items():
            if ticker in current_prices:
                allocation_amount = total_amount * data['weight']
                current_price = current_prices[ticker]
                shares = int(allocation_amount / current_price)
                actual_amount = shares * current_price

                allocation[ticker] = {
                    'weight': data['weight'],
                    'target_amount': allocation_amount,
                    'shares': shares,
                    'actual_amount': actual_amount,
                    'current_price': current_price,
                    'name': data['name']
                }

        return allocation

    def _get_current_prices(self, tickers: List[str]) -> Dict:
        """현재 주가 조회"""
        prices = {}

        # DB에서 최신 가격 조회
        for ticker in tickers:
            query = """
            SELECT close_price FROM stock_prices
            WHERE ticker = ?
            ORDER BY date DESC
            LIMIT 1
            """
            cursor = self.conn.cursor()
            cursor.execute(query, (ticker,))
            result = cursor.fetchone()

            if result:
                prices[ticker] = result[0]
            else:
                # DB에 없으면 야후 파이낸스에서 실시간 조회
                try:
                    stock = yf.Ticker(ticker)
                    info = stock.history(period='1d')
                    if not info.empty:
                        prices[ticker] = info['Close'].iloc[-1]
                except Exception:
                    prices[ticker] = 100  # 기본값

        return prices

    def save_optimized_portfolio(self, portfolio_result: Dict):
        """최적화된 포트폴리오를 DB에 저장"""
        try:
            cursor = self.conn.cursor()

            # 기존 최적화 결과 삭제
            cursor.execute("DELETE FROM optimized_portfolios WHERE created_at < date('now', '-7 days')")

            # 새 결과 저장
            cursor.execute("""
                INSERT OR REPLACE INTO optimized_portfolios
                (portfolio_data, created_at, expected_return, expected_risk, sharpe_ratio)
                VALUES (?, ?, ?, ?, ?)
            """, (
                json.dumps(portfolio_result),
                datetime.now().isoformat(),
                portfolio_result.get('expected_metrics', {}).get('annual_return', 0),
                portfolio_result.get('expected_metrics', {}).get('annual_volatility', 0),
                portfolio_result.get('expected_metrics', {}).get('sharpe_ratio', 0)
            ))

            self.conn.commit()
            print("Portfolio optimization results saved to database")

        except Exception as e:
            print(f"Error saving portfolio: {e}")

    def close(self):
        """DB 연결 종료"""
        self.conn.close()


def main():
    """메인 실행 함수"""
    optimizer = PortfolioOptimizer()

    print("Advanced Portfolio Optimization System")
    print("=" * 50)

    # 최적 포트폴리오 생성
    result = optimizer.generate_optimal_portfolio(
        investment_amount=10000000,  # 1천만원
        max_stocks=6,
        target_return=0.12  # 12% 목표 수익률
    )

    if 'error' in result:
        print(f"Error: {result['error']}")
        return

    print("\nOPTIMIZATION RESULTS")
    print("=" * 50)

    print(f"Investment Amount: {result['investment_amount']:,} KRW")
    print(f"Selected Stocks: {result['selected_stocks']} -> Final: {result['final_portfolio_size']}")
    print(f"Optimization Success: {'YES' if result['optimization_success'] else 'NO - Equal Weight Used'}")

    print(f"\nTOP STOCK SCORES:")
    for ticker, score in result['stock_scores'].items():
        name = optimizer.stock_universe.get(ticker, ticker)
        print(f"  {ticker} ({name}): {score:.2f}")

    print(f"\nOPTIMAL PORTFOLIO ALLOCATION:")
    total_allocated = 0
    for ticker, allocation in result['share_allocation'].items():
        print(f"  {ticker} ({allocation['name']})")
        print(f"    Weight: {allocation['weight']:.1%}")
        print(f"    Shares: {allocation['shares']:,}")
        print(f"    Amount: {allocation['actual_amount']:,.0f} KRW")
        total_allocated += allocation['actual_amount']

    print(f"\nTotal Allocated: {total_allocated:,.0f} KRW ({total_allocated/result['investment_amount']:.1%})")

    print(f"\nEXPECTED PERFORMANCE:")
    metrics = result['expected_metrics']
    print(f"  Expected Annual Return: {metrics['annual_return']:.1%}")
    print(f"  Expected Volatility: {metrics['annual_volatility']:.1%}")
    print(f"  Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
    print(f"  Maximum Drawdown: {metrics['max_drawdown']:.1%}")

    # 결과를 JSON 파일로 저장
    import json
    with open('optimized_portfolio.json', 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nResults saved to: optimized_portfolio.json")

    optimizer.close()


if __name__ == "__main__":
    main()