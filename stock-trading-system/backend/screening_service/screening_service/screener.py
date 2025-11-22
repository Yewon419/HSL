#!/usr/bin/env python3
"""
주식 스크리닝 및 백테스팅 시스템
다중 지표 조건을 통한 종목 필터링 및 성과 분석
"""

import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Tuple, Any, Optional
import json

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockScreener:
    """주식 스크리닝 클래스"""

    def __init__(self):
        self.engine = self._get_db_connection()

    def _get_db_connection(self):
        """데이터베이스 연결 생성"""
        import os
        # 환경에 따른 데이터베이스 URL 설정
        if os.path.exists('/app'):  # Docker 컨테이너 환경
            DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
        else:  # 로컬 개발 환경
            DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
        engine = create_engine(DATABASE_URL)
        return engine

    def get_available_indicators(self) -> List[Dict]:
        """사용 가능한 지표 목록 조회"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT id, name, code, description
                    FROM indicator_definitions
                    ORDER BY id
                """))
                indicators = []
                for row in result:
                    indicators.append({
                        'id': row[0],
                        'name': row[1],
                        'code': row[2],
                        'description': row[3] if len(row) > 3 else ''
                    })
                return indicators
        except Exception as e:
            logger.error(f"Error fetching indicators: {e}")
            return []

    def screen_stocks(self, conditions: List[Dict], date_range: Tuple[str, str] = None) -> pd.DataFrame:
        """
        다중 조건으로 주식 스크리닝

        Args:
            conditions: 스크리닝 조건 리스트
                예: [
                    {
                        'indicator': 'RSI',
                        'condition': 'golden_cross',  # golden_cross, death_cross, above, below, between
                        'value': 30,  # 기준값 (선택적)
                        'value2': 70,  # 범위의 경우 두 번째 값 (선택적)
                        'lookback_days': 5  # 골든크로스 확인할 기간 (선택적)
                    },
                    {
                        'indicator': 'MACD',
                        'condition': 'golden_cross',
                        'lookback_days': 3
                    }
                ]
            date_range: 분석 기간 (start_date, end_date)

        Returns:
            pd.DataFrame: 조건을 만족하는 종목 및 날짜
        """
        try:
            if not date_range:
                # 기본적으로 최근 30일 분석
                end_date = datetime.now().strftime('%Y-%m-%d')
                start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
                date_range = (start_date, end_date)

            logger.info(f"Screening stocks with {len(conditions)} conditions from {date_range[0]} to {date_range[1]}")

            # 조건별 결과를 저장할 리스트
            condition_results = []

            for i, condition in enumerate(conditions):
                logger.info(f"Processing condition {i+1}: {condition}")
                result_df = self._apply_single_condition(condition, date_range)
                if result_df is not None and not result_df.empty:
                    condition_results.append(result_df)
                else:
                    logger.warning(f"No results for condition {i+1}")

            if not condition_results:
                logger.warning("No results from any conditions")
                return pd.DataFrame()

            # 모든 조건을 만족하는 종목 찾기 (교집합)
            final_result = condition_results[0]
            for result_df in condition_results[1:]:
                final_result = pd.merge(
                    final_result, result_df,
                    on=['ticker', 'date'],
                    how='inner'
                )

            # 추가 정보 조회 (회사명, 현재가 등)
            if not final_result.empty:
                final_result = self._enrich_screening_results(final_result)

            logger.info(f"Screening completed: {len(final_result)} matches found")
            return final_result.sort_values(['date', 'ticker']).reset_index(drop=True)

        except Exception as e:
            logger.error(f"Error in stock screening: {e}")
            import traceback
            traceback.print_exc()
            return pd.DataFrame()

    def _apply_single_condition(self, condition: Dict, date_range: Tuple[str, str]) -> pd.DataFrame:
        """단일 조건 적용"""
        indicator = condition['indicator'].upper()
        condition_type = condition['condition'].lower()

        if condition_type == 'golden_cross':
            return self._find_golden_cross(indicator, date_range, condition.get('lookback_days', 5))
        elif condition_type == 'death_cross':
            return self._find_death_cross(indicator, date_range, condition.get('lookback_days', 5))
        elif condition_type == 'above':
            return self._find_above_threshold(indicator, date_range, condition['value'])
        elif condition_type == 'below':
            return self._find_below_threshold(indicator, date_range, condition['value'])
        elif condition_type == 'between':
            return self._find_between_values(indicator, date_range, condition['value'], condition['value2'])
        else:
            logger.warning(f"Unknown condition type: {condition_type}")
            return pd.DataFrame()

    def _find_golden_cross(self, indicator: str, date_range: Tuple[str, str], lookback_days: int = 5) -> pd.DataFrame:
        """골든크로스 패턴 찾기"""
        try:
            # 지표별 골든크로스 로직
            if indicator == 'RSI':
                return self._find_rsi_golden_cross(date_range, lookback_days)
            elif indicator == 'MACD':
                return self._find_macd_golden_cross(date_range, lookback_days)
            elif indicator.startswith('SMA') or indicator == 'SMA':
                return self._find_sma_golden_cross(date_range, lookback_days)
            elif indicator == 'EMA':
                return self._find_ema_golden_cross(date_range, lookback_days)
            elif indicator == 'STOCH':
                return self._find_stoch_golden_cross(date_range, lookback_days)
            elif indicator == 'STOCHRSI':
                return self._find_stochrsi_golden_cross(date_range, lookback_days)
            else:
                logger.warning(f"Golden cross not implemented for {indicator}")
                return pd.DataFrame()

        except Exception as e:
            logger.error(f"Error finding golden cross for {indicator}: {e}")
            return pd.DataFrame()

    def _find_rsi_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """RSI 골든크로스: RSI가 30 이하에서 50 이상으로 상승"""
        query = """
        WITH rsi_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'rsi')::float as rsi_value,
                LAG((iv.value::json->>'rsi')::float, 1) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_rsi,
                LAG((iv.value::json->>'rsi')::float, 2) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_rsi2
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'RSI'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'rsi') IS NOT NULL
        )
        SELECT ticker, date, rsi_value as current_rsi, prev_rsi, prev_rsi2
        FROM rsi_data
        WHERE rsi_value > 50  -- 현재 RSI > 50
        AND prev_rsi <= 30    -- 이전 RSI <= 30 (과매도 상태에서)
        AND prev_rsi2 IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'current_rsi', 'prev_rsi', 'prev_rsi2'])
            return df

    def _find_macd_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """MACD 골든크로스: MACD 라인이 시그널 라인을 상향돌파"""
        query = """
        WITH macd_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'macd')::float as macd_value,
                (iv.value::json->>'macd_signal')::float as signal_value,
                LAG((iv.value::json->>'macd')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_macd,
                LAG((iv.value::json->>'macd_signal')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_signal
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'MACD'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'macd') IS NOT NULL
            AND (iv.value::json->>'macd_signal') IS NOT NULL
        )
        SELECT ticker, date, macd_value, signal_value, prev_macd, prev_signal
        FROM macd_data
        WHERE macd_value > signal_value    -- 현재 MACD > Signal
        AND prev_macd <= prev_signal       -- 이전 MACD <= Signal
        AND prev_macd IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'macd_value', 'signal_value', 'prev_macd', 'prev_signal'])
            return df

    def _find_sma_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """SMA 골든크로스: SMA20이 SMA50을 상향돌파"""
        query = """
        WITH sma_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'sma_20')::float as sma_20,
                (iv.value::json->>'sma_50')::float as sma_50,
                LAG((iv.value::json->>'sma_20')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_sma_20,
                LAG((iv.value::json->>'sma_50')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_sma_50
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'SMA'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'sma_20') IS NOT NULL
            AND (iv.value::json->>'sma_50') IS NOT NULL
        )
        SELECT ticker, date, sma_20, sma_50, prev_sma_20, prev_sma_50
        FROM sma_data
        WHERE sma_20 > sma_50              -- 현재 SMA20 > SMA50
        AND prev_sma_20 <= prev_sma_50     -- 이전 SMA20 <= SMA50
        AND prev_sma_20 IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'sma_20', 'sma_50', 'prev_sma_20', 'prev_sma_50'])
            return df

    def _find_ema_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """EMA 골든크로스: EMA12가 EMA26을 상향돌파"""
        query = """
        WITH ema_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'ema_12')::float as ema_12,
                (iv.value::json->>'ema_26')::float as ema_26,
                LAG((iv.value::json->>'ema_12')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_ema_12,
                LAG((iv.value::json->>'ema_26')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_ema_26
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'EMA'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'ema_12') IS NOT NULL
            AND (iv.value::json->>'ema_26') IS NOT NULL
        )
        SELECT ticker, date, ema_12, ema_26, prev_ema_12, prev_ema_26
        FROM ema_data
        WHERE ema_12 > ema_26              -- 현재 EMA12 > EMA26
        AND prev_ema_12 <= prev_ema_26     -- 이전 EMA12 <= EMA26
        AND prev_ema_12 IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'ema_12', 'ema_26', 'prev_ema_12', 'prev_ema_26'])
            return df

    def _find_stoch_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """Stochastic 골든크로스: %K가 %D를 상향돌파"""
        query = """
        WITH stoch_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'stoch_k')::float as stoch_k,
                (iv.value::json->>'stoch_d')::float as stoch_d,
                LAG((iv.value::json->>'stoch_k')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_stoch_k,
                LAG((iv.value::json->>'stoch_d')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_stoch_d
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'STOCH'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'stoch_k') IS NOT NULL
            AND (iv.value::json->>'stoch_d') IS NOT NULL
        )
        SELECT ticker, date, stoch_k, stoch_d, prev_stoch_k, prev_stoch_d
        FROM stoch_data
        WHERE stoch_k > stoch_d              -- 현재 %K > %D
        AND prev_stoch_k <= prev_stoch_d     -- 이전 %K <= %D
        AND prev_stoch_k IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'stoch_k', 'stoch_d', 'prev_stoch_k', 'prev_stoch_d'])
            return df

    def _find_stochrsi_golden_cross(self, date_range: Tuple[str, str], lookback_days: int) -> pd.DataFrame:
        """StochRSI 골든크로스: StochRSI %K가 %D를 상향돌파"""
        query = """
        WITH stochrsi_data AS (
            SELECT
                iv.ticker,
                iv.date,
                (iv.value::json->>'stochrsi_k')::float as stochrsi_k,
                (iv.value::json->>'stochrsi_d')::float as stochrsi_d,
                LAG((iv.value::json->>'stochrsi_k')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_stochrsi_k,
                LAG((iv.value::json->>'stochrsi_d')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_stochrsi_d
            FROM indicator_values iv
            JOIN indicator_definitions id ON iv.indicator_id = id.id
            WHERE id.code = 'STOCHRSI'
            AND iv.date BETWEEN :start_date AND :end_date
            AND (iv.value::json->>'stochrsi_k') IS NOT NULL
            AND (iv.value::json->>'stochrsi_d') IS NOT NULL
        )
        SELECT ticker, date, stochrsi_k, stochrsi_d, prev_stochrsi_k, prev_stochrsi_d
        FROM stochrsi_data
        WHERE stochrsi_k > stochrsi_d              -- 현재 StochRSI %K > %D
        AND prev_stochrsi_k <= prev_stochrsi_d     -- 이전 StochRSI %K <= %D
        AND prev_stochrsi_k IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'start_date': date_range[0],
                'end_date': date_range[1]
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'stochrsi_k', 'stochrsi_d', 'prev_stochrsi_k', 'prev_stochrsi_d'])
            return df

    def _find_death_cross(self, indicator: str, date_range: Tuple[str, str], lookback_days: int = 5) -> pd.DataFrame:
        """데드크로스 패턴 찾기"""
        # 골든크로스와 반대 로직
        if indicator == 'MACD':
            query = """
            WITH macd_data AS (
                SELECT
                    iv.ticker,
                    iv.date,
                    (iv.value::json->>'macd')::float as macd_value,
                    (iv.value::json->>'macd_signal')::float as signal_value,
                    LAG((iv.value::json->>'macd')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_macd,
                    LAG((iv.value::json->>'macd_signal')::float) OVER (PARTITION BY iv.ticker ORDER BY iv.date) as prev_signal
                FROM indicator_values iv
                JOIN indicator_definitions id ON iv.indicator_id = id.id
                WHERE id.code = 'MACD'
                AND iv.date BETWEEN :start_date AND :end_date
                AND (iv.value::json->>'macd') IS NOT NULL
                AND (iv.value::json->>'macd_signal') IS NOT NULL
            )
            SELECT ticker, date, macd_value, signal_value, prev_macd, prev_signal
            FROM macd_data
            WHERE macd_value < signal_value    -- 현재 MACD < Signal
            AND prev_macd >= prev_signal       -- 이전 MACD >= Signal
            AND prev_macd IS NOT NULL
            ORDER BY date DESC, ticker
            """

            with self.engine.connect() as conn:
                result = conn.execute(text(query), {
                    'start_date': date_range[0],
                    'end_date': date_range[1]
                })
                df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'macd_value', 'signal_value', 'prev_macd', 'prev_signal'])
                return df

        return pd.DataFrame()

    def _find_above_threshold(self, indicator: str, date_range: Tuple[str, str], threshold: float) -> pd.DataFrame:
        """임계값 이상 조건"""
        indicator_map = {
            'RSI': 'rsi',
            'MACD': 'macd',
            'ADX': 'adx',
            'CCI': 'cci',
            'MFI': 'mfi',
            'STOCH': 'stoch_k',
            'STOCHRSI': 'stochrsi_k',
            'WILLR': 'willr',
            'MOM': 'momentum',
            'ROC': 'roc',
            'ATR': 'atr',
            'OBV': 'obv',
            'VWAP': 'vwap',
            'TRIX': 'trix'
        }

        if indicator not in indicator_map:
            logger.warning(f"Above threshold not implemented for {indicator}")
            return pd.DataFrame()

        field_name = indicator_map[indicator]

        query = f"""
        SELECT
            iv.ticker,
            iv.date,
            (iv.value::json->>'{field_name}')::float as indicator_value
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        WHERE id.code = :indicator_code
        AND iv.date BETWEEN :start_date AND :end_date
        AND (iv.value::json->>'{field_name}')::float > :threshold
        AND (iv.value::json->>'{field_name}') IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'indicator_code': indicator,
                'start_date': date_range[0],
                'end_date': date_range[1],
                'threshold': threshold
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'indicator_value'])
            return df

    def _find_below_threshold(self, indicator: str, date_range: Tuple[str, str], threshold: float) -> pd.DataFrame:
        """임계값 이하 조건"""
        indicator_map = {
            'RSI': 'rsi',
            'MACD': 'macd',
            'ADX': 'adx',
            'CCI': 'cci',
            'MFI': 'mfi',
            'STOCH': 'stoch_k',
            'STOCHRSI': 'stochrsi_k',
            'WILLR': 'willr',
            'MOM': 'momentum',
            'ROC': 'roc',
            'ATR': 'atr',
            'OBV': 'obv',
            'VWAP': 'vwap',
            'TRIX': 'trix'
        }

        if indicator not in indicator_map:
            logger.warning(f"Below threshold not implemented for {indicator}")
            return pd.DataFrame()

        field_name = indicator_map[indicator]

        query = f"""
        SELECT
            iv.ticker,
            iv.date,
            (iv.value::json->>'{field_name}')::float as indicator_value
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        WHERE id.code = :indicator_code
        AND iv.date BETWEEN :start_date AND :end_date
        AND (iv.value::json->>'{field_name}')::float < :threshold
        AND (iv.value::json->>'{field_name}') IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'indicator_code': indicator,
                'start_date': date_range[0],
                'end_date': date_range[1],
                'threshold': threshold
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'indicator_value'])
            return df

    def _find_between_values(self, indicator: str, date_range: Tuple[str, str], value1: float, value2: float) -> pd.DataFrame:
        """값 범위 조건"""
        min_val, max_val = min(value1, value2), max(value1, value2)

        indicator_map = {
            'RSI': 'rsi',
            'MACD': 'macd',
            'ADX': 'adx',
            'CCI': 'cci',
            'MFI': 'mfi',
            'STOCH': 'stoch_k',
            'STOCHRSI': 'stochrsi_k',
            'WILLR': 'willr',
            'MOM': 'momentum',
            'ROC': 'roc',
            'ATR': 'atr',
            'OBV': 'obv',
            'VWAP': 'vwap',
            'TRIX': 'trix'
        }

        if indicator not in indicator_map:
            logger.warning(f"Between values not implemented for {indicator}")
            return pd.DataFrame()

        field_name = indicator_map[indicator]

        query = f"""
        SELECT
            iv.ticker,
            iv.date,
            (iv.value::json->>'{field_name}')::float as indicator_value
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        WHERE id.code = :indicator_code
        AND iv.date BETWEEN :start_date AND :end_date
        AND (iv.value::json->>'{field_name}')::float BETWEEN :min_val AND :max_val
        AND (iv.value::json->>'{field_name}') IS NOT NULL
        ORDER BY date DESC, ticker
        """

        with self.engine.connect() as conn:
            result = conn.execute(text(query), {
                'indicator_code': indicator,
                'start_date': date_range[0],
                'end_date': date_range[1],
                'min_val': min_val,
                'max_val': max_val
            })
            df = pd.DataFrame(result.fetchall(), columns=['ticker', 'date', 'indicator_value'])
            return df

    def _enrich_screening_results(self, df: pd.DataFrame) -> pd.DataFrame:
        """스크리닝 결과에 추가 정보 첨부"""
        try:
            # 종목 정보 조회
            tickers = df['ticker'].unique()
            ticker_list = "','".join(tickers)

            with self.engine.connect() as conn:
                # 회사 정보
                company_query = f"""
                SELECT ticker, company_name, market_type
                FROM stocks
                WHERE ticker IN ('{ticker_list}')
                """
                company_result = conn.execute(text(company_query))
                company_df = pd.DataFrame(company_result.fetchall(), columns=['ticker', 'company_name', 'market_type'])

                # 현재가 정보 (최신 날짜)
                price_query = f"""
                SELECT sp.ticker, sp.close_price, sp.date
                FROM stock_prices sp
                JOIN (
                    SELECT ticker, MAX(date) as max_date
                    FROM stock_prices
                    WHERE ticker IN ('{ticker_list}')
                    GROUP BY ticker
                ) latest ON sp.ticker = latest.ticker AND sp.date = latest.max_date
                """
                price_result = conn.execute(text(price_query))
                price_df = pd.DataFrame(price_result.fetchall(), columns=['ticker', 'current_price', 'price_date'])

            # 데이터 결합
            df = pd.merge(df, company_df, on='ticker', how='left')
            df = pd.merge(df, price_df, on='ticker', how='left')

            return df

        except Exception as e:
            logger.error(f"Error enriching screening results: {e}")
            return df


class BacktestEngine:
    """백테스팅 엔진 클래스"""

    def __init__(self):
        self.engine = self._get_db_connection()

    def _get_db_connection(self):
        """데이터베이스 연결 생성"""
        import os
        # 환경에 따른 데이터베이스 URL 설정
        if os.path.exists('/app'):  # Docker 컨테이너 환경
            DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
        else:  # 로컬 개발 환경
            DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
        engine = create_engine(DATABASE_URL)
        return engine

    def run_backtest(self,
                     tickers: List[str],
                     start_date: str,
                     end_date: str,
                     initial_capital: float = 1000000,  # 초기 자본 100만원
                     position_size: float = 0.1,       # 포지션 크기 (10%)
                     transaction_cost: float = 0.003   # 거래 비용 (0.3%)
                     ) -> Dict:
        """
        백테스팅 실행

        Args:
            tickers: 백테스트할 종목 리스트
            start_date: 시작 날짜
            end_date: 종료 날짜
            initial_capital: 초기 자본
            position_size: 포지션 크기 (전체 자본 대비 비율)
            transaction_cost: 거래 비용 (매수/매도 시 수수료)

        Returns:
            Dict: 백테스트 결과
        """
        try:
            logger.info(f"Starting backtest for {len(tickers)} tickers from {start_date} to {end_date}")

            results = {
                'tickers': tickers,
                'period': {'start': start_date, 'end': end_date},
                'initial_capital': initial_capital,
                'settings': {
                    'position_size': position_size,
                    'transaction_cost': transaction_cost
                },
                'individual_results': {},
                'portfolio_results': {},
                'summary': {}
            }

            # 개별 종목 백테스트
            individual_returns = []
            for ticker in tickers:
                ticker_result = self._backtest_single_stock(ticker, start_date, end_date,
                                                          initial_capital * position_size,
                                                          transaction_cost)
                results['individual_results'][ticker] = ticker_result
                individual_returns.append(ticker_result)

            # 포트폴리오 백테스트 (균등 분산)
            portfolio_result = self._backtest_portfolio(tickers, start_date, end_date,
                                                      initial_capital, position_size,
                                                      transaction_cost)
            results['portfolio_results'] = portfolio_result

            # 요약 통계
            results['summary'] = self._calculate_summary_stats(individual_returns, portfolio_result)

            logger.info("Backtest completed successfully")
            return results

        except Exception as e:
            logger.error(f"Error in backtesting: {e}")
            import traceback
            traceback.print_exc()
            return {}

    def _backtest_single_stock(self, ticker: str, start_date: str, end_date: str,
                              capital: float, transaction_cost: float) -> Dict:
        """단일 종목 백테스트"""
        try:
            # 주가 데이터 조회
            with self.engine.connect() as conn:
                price_query = """
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                AND date BETWEEN :start_date AND :end_date
                ORDER BY date
                """
                result = conn.execute(text(price_query), {
                    'ticker': ticker,
                    'start_date': start_date,
                    'end_date': end_date
                })
                price_data = pd.DataFrame(result.fetchall(),
                                        columns=['date', 'open_price', 'high_price', 'low_price', 'close_price', 'volume'])

            if price_data.empty:
                return {'error': f'No price data for {ticker}'}

            # 모든 가격 데이터를 float로 변환
            numeric_columns = ['open_price', 'high_price', 'low_price', 'close_price', 'volume']
            for col in numeric_columns:
                price_data[col] = pd.to_numeric(price_data[col], errors='coerce')

            # 수익률 계산
            price_data['daily_return'] = price_data['close_price'].pct_change()
            price_data['cumulative_return'] = (1 + price_data['daily_return']).cumprod()

            # 매수/매도 시뮬레이션 (단순 매수 후 보유)
            buy_price = float(price_data['close_price'].iloc[0]) * (1 + transaction_cost)  # 매수가 + 수수료
            sell_price = float(price_data['close_price'].iloc[-1]) * (1 - transaction_cost)  # 매도가 - 수수료

            shares = capital / buy_price
            final_value = shares * sell_price
            total_return = (final_value - capital) / capital

            # 추가 통계 (NaN 방지)
            volatility = price_data['daily_return'].std() * np.sqrt(252)  # 연간화
            if pd.isna(volatility):
                volatility = 0.0

            max_price = float(price_data['close_price'].max())
            min_price = float(price_data['close_price'].min())
            max_drawdown = self._calculate_max_drawdown(price_data['close_price'])

            if pd.isna(max_drawdown):
                max_drawdown = 0.0

            return {
                'ticker': ticker,
                'period_days': len(price_data),
                'buy_price': round(buy_price, 2) if not pd.isna(buy_price) else 0.0,
                'sell_price': round(sell_price, 2) if not pd.isna(sell_price) else 0.0,
                'total_return_pct': round(total_return * 100, 2) if not pd.isna(total_return) else 0.0,
                'annualized_return_pct': round(total_return * 365 / len(price_data) * 100, 2) if not pd.isna(total_return) else 0.0,
                'volatility_pct': round(volatility * 100, 2),
                'max_drawdown_pct': round(max_drawdown * 100, 2),
                'max_price': round(max_price, 2) if not pd.isna(max_price) else 0.0,
                'min_price': round(min_price, 2) if not pd.isna(min_price) else 0.0,
                'final_value': round(final_value, 2) if not pd.isna(final_value) else 0.0,
                'profit_loss': round(final_value - capital, 2) if not pd.isna(final_value - capital) else 0.0
            }

        except Exception as e:
            logger.error(f"Error in single stock backtest for {ticker}: {e}")
            return {'error': f'Backtest failed for {ticker}: {str(e)}'}

    def _backtest_portfolio(self, tickers: List[str], start_date: str, end_date: str,
                           total_capital: float, position_size: float, transaction_cost: float) -> Dict:
        """포트폴리오 백테스트 (균등 분산)"""
        try:
            capital_per_stock = total_capital * position_size / len(tickers)
            portfolio_value = []
            portfolio_returns = []

            # 각 종목의 수익률 데이터 수집
            stock_returns = {}
            for ticker in tickers:
                with self.engine.connect() as conn:
                    price_query = """
                    SELECT date, close_price
                    FROM stock_prices
                    WHERE ticker = :ticker
                    AND date BETWEEN :start_date AND :end_date
                    ORDER BY date
                    """
                    result = conn.execute(text(price_query), {
                        'ticker': ticker,
                        'start_date': start_date,
                        'end_date': end_date
                    })
                    price_data = pd.DataFrame(result.fetchall(), columns=['date', 'close_price'])

                    if not price_data.empty:
                        # 가격 데이터를 float로 변환
                        price_data['close_price'] = pd.to_numeric(price_data['close_price'], errors='coerce')
                        price_data['daily_return'] = price_data['close_price'].pct_change()
                        stock_returns[ticker] = price_data.set_index('date')['daily_return']

            if not stock_returns:
                return {'error': 'No valid stock data for portfolio'}

            # 포트폴리오 수익률 계산 (균등 가중)
            returns_df = pd.DataFrame(stock_returns).fillna(0)
            portfolio_daily_returns = returns_df.mean(axis=1)  # 균등 가중 평균
            portfolio_cumulative_returns = (1 + portfolio_daily_returns).cumprod()

            # 포트폴리오 성과 지표 (NaN 방지)
            total_return = portfolio_cumulative_returns.iloc[-1] - 1
            if pd.isna(total_return):
                total_return = 0.0

            annualized_return = total_return * 365 / len(portfolio_daily_returns)
            if pd.isna(annualized_return):
                annualized_return = 0.0

            volatility = portfolio_daily_returns.std() * np.sqrt(252)
            if pd.isna(volatility):
                volatility = 0.0

            sharpe_ratio = annualized_return / volatility if volatility > 0 else 0
            if pd.isna(sharpe_ratio):
                sharpe_ratio = 0.0

            max_drawdown = self._calculate_max_drawdown(portfolio_cumulative_returns)
            if pd.isna(max_drawdown):
                max_drawdown = 0.0

            final_portfolio_value = total_capital * (1 + total_return)
            if pd.isna(final_portfolio_value):
                final_portfolio_value = total_capital

            return {
                'total_return_pct': round(total_return * 100, 2),
                'annualized_return_pct': round(annualized_return * 100, 2),
                'volatility_pct': round(volatility * 100, 2),
                'sharpe_ratio': round(sharpe_ratio, 3),
                'max_drawdown_pct': round(max_drawdown * 100, 2),
                'final_value': round(final_portfolio_value, 2),
                'profit_loss': round(final_portfolio_value - total_capital, 2),
                'period_days': len(portfolio_daily_returns)
            }

        except Exception as e:
            logger.error(f"Error in portfolio backtest: {e}")
            return {'error': f'Portfolio backtest failed: {str(e)}'}

    def _calculate_max_drawdown(self, price_series: pd.Series) -> float:
        """최대 손실폭(Maximum Drawdown) 계산"""
        try:
            if isinstance(price_series.iloc[0], (int, float)):
                cumulative = price_series / price_series.iloc[0]
            else:
                cumulative = price_series

            running_max = cumulative.expanding().max()
            drawdown = (cumulative - running_max) / running_max
            return abs(drawdown.min())

        except Exception as e:
            logger.error(f"Error calculating max drawdown: {e}")
            return 0.0

    def _calculate_summary_stats(self, individual_results: List[Dict], portfolio_result: Dict) -> Dict:
        """요약 통계 계산"""
        try:
            valid_results = [r for r in individual_results if 'error' not in r]

            if not valid_results:
                return {'error': 'No valid individual results'}

            # 개별 종목 통계
            returns = [r['total_return_pct'] for r in valid_results]
            volatilities = [r['volatility_pct'] for r in valid_results]

            summary = {
                'individual_stats': {
                    'best_performer': max(valid_results, key=lambda x: x['total_return_pct']),
                    'worst_performer': min(valid_results, key=lambda x: x['total_return_pct']),
                    'avg_return_pct': round(np.mean(returns), 2),
                    'median_return_pct': round(np.median(returns), 2),
                    'avg_volatility_pct': round(np.mean(volatilities), 2),
                    'success_rate': len([r for r in returns if r > 0]) / len(returns) * 100
                },
                'portfolio_vs_individual': {},
                'risk_metrics': {}
            }

            # 포트폴리오 vs 개별 종목 비교
            if 'error' not in portfolio_result:
                summary['portfolio_vs_individual'] = {
                    'portfolio_return_pct': portfolio_result['total_return_pct'],
                    'avg_individual_return_pct': summary['individual_stats']['avg_return_pct'],
                    'diversification_benefit': round(portfolio_result['volatility_pct'] - summary['individual_stats']['avg_volatility_pct'], 2)
                }

            return summary

        except Exception as e:
            logger.error(f"Error calculating summary stats: {e}")
            return {'error': f'Summary calculation failed: {str(e)}'}


def main():
    """메인 실행 함수 - 예제"""
    # 스크리너 초기화
    screener = StockScreener()

    # 사용 가능한 지표 확인
    indicators = screener.get_available_indicators()
    print("Available Indicators:")
    for ind in indicators[:10]:  # 처음 10개만 표시
        print(f"  - {ind['code']}: {ind['name']}")

    # 스크리닝 조건 설정
    conditions = [
        {
            'indicator': 'RSI',
            'condition': 'golden_cross',
            'lookback_days': 5
        },
        {
            'indicator': 'MACD',
            'condition': 'golden_cross',
            'lookback_days': 3
        }
    ]

    # 스크리닝 실행
    print("\nRunning screening...")
    date_range = ('2025-09-01', '2025-09-24')
    screening_result = screener.screen_stocks(conditions, date_range)

    print(f"\nScreening completed: {len(screening_result)} matches found")
    if not screening_result.empty:
        print(screening_result[['ticker', 'company_name', 'date', 'current_price']].head())

        # 백테스트 실행
        if len(screening_result) > 0:
            tickers = screening_result['ticker'].unique().tolist()[:3]  # 최대 3개 종목
            print(f"\nRunning backtest for: {tickers}")

            backtester = BacktestEngine()
            backtest_result = backtester.run_backtest(
                tickers=tickers,
                start_date='2025-09-01',
                end_date='2025-09-24',
                initial_capital=1000000
            )

            if 'error' not in backtest_result:
                print("\nBacktest Results:")
                if 'portfolio_results' in backtest_result and 'total_return_pct' in backtest_result['portfolio_results']:
                    print(f"Portfolio Return: {backtest_result['portfolio_results']['total_return_pct']}%")

                if ('summary' in backtest_result and
                    'individual_stats' in backtest_result['summary'] and
                    'best_performer' in backtest_result['summary']['individual_stats']):
                    best = backtest_result['summary']['individual_stats']['best_performer']
                    print(f"Best Performer: {best['ticker']} ({best['total_return_pct']}%)")

                # 개별 종목 결과 출력
                print("\nIndividual Stock Results:")
                for ticker, result in backtest_result.get('individual_results', {}).items():
                    if 'error' not in result:
                        print(f"  {ticker}: {result['total_return_pct']}%")
                    else:
                        print(f"  {ticker}: Error - {result['error']}")
            else:
                print(f"Backtest failed: {backtest_result.get('error', 'Unknown error')}")


if __name__ == "__main__":
    main()