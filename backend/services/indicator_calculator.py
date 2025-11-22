"""
Technical Indicator Calculator Service
Comprehensive indicator calculation for all categories
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import talib
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
import warnings

warnings.filterwarnings('ignore')

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class IndicatorCalculator:
    """Calculate technical indicators for stocks"""
    
    def __init__(self, db_url: str):
        """Initialize calculator with database connection"""
        self.engine = create_engine(db_url)
        self.indicators_config = self._load_indicator_definitions()
        
    def _load_indicator_definitions(self) -> Dict:
        """Load indicator definitions from database"""
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    id.id,
                    id.code,
                    id.name,
                    id.parameters,
                    id.output_columns,
                    ic.name as category
                FROM indicator_definitions id
                JOIN indicator_categories ic ON id.category_id = ic.id
                WHERE id.is_active = true
                ORDER BY ic.display_order, id.display_order
            """))
            
            indicators = {}
            for row in result:
                # Handle parameters - might already be dict from database
                params = row.parameters
                if params and isinstance(params, str):
                    params = json.loads(params)
                elif not params:
                    params = {}
                    
                # Handle output_columns - might already be list from database
                output_cols = row.output_columns
                if output_cols and isinstance(output_cols, str):
                    output_cols = json.loads(output_cols)
                elif not output_cols:
                    output_cols = []
                    
                indicators[row.code] = {
                    'id': row.id,
                    'name': row.name,
                    'category': row.category,
                    'parameters': params,
                    'output_columns': output_cols
                }
            return indicators
    
    def get_price_data(self, ticker: str, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> pd.DataFrame:
        """Get price data for a ticker"""
        query = """
            SELECT 
                date,
                open_price as open,
                high_price as high,
                low_price as low,
                close_price as close,
                volume,
                close_price as adjusted_close
            FROM stock_prices
            WHERE ticker = %(ticker)s
        """
        
        params = {'ticker': ticker}
        
        if start_date:
            query += " AND date >= %(start_date)s"
            params['start_date'] = start_date
            
        if end_date:
            query += " AND date <= %(end_date)s"
            params['end_date'] = end_date
            
        query += " ORDER BY date"
        
        with self.engine.connect() as conn:
            df = pd.read_sql(query, conn, params=params, parse_dates=['date'])
            df.set_index('date', inplace=True)
            
        return df
    
    def calculate_moving_averages(self, df: pd.DataFrame) -> Dict:
        """Calculate various moving averages"""
        results = {}
        close = df['close'].values
        
        # Simple Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            if len(close) >= period:
                results[f'sma_{period}'] = talib.SMA(close, timeperiod=period)
        
        # Exponential Moving Averages
        for period in [5, 10, 20, 50, 100, 200]:
            if len(close) >= period:
                results[f'ema_{period}'] = talib.EMA(close, timeperiod=period)
        
        # Weighted Moving Average
        for period in [10, 20, 50]:
            if len(close) >= period:
                results[f'wma_{period}'] = talib.WMA(close, timeperiod=period)
        
        # Triple Exponential Moving Average
        for period in [10, 20, 50]:
            if len(close) >= period * 3:  # TEMA needs more data
                results[f'tema_{period}'] = talib.TEMA(close, timeperiod=period)
        
        # Hull Moving Average (custom implementation)
        for period in [9, 16, 25]:
            if len(close) >= period * 2:
                wma_half = talib.WMA(close, timeperiod=period//2)
                wma_full = talib.WMA(close, timeperiod=period)
                raw_hma = 2 * wma_half - wma_full
                hma_period = int(np.sqrt(period))
                results[f'hma_{period}'] = talib.WMA(raw_hma, timeperiod=hma_period)
        
        return results
    
    def calculate_trend_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate trend confirmation indicators"""
        results = {}
        high = df['high'].values.astype(np.float64)
        low = df['low'].values.astype(np.float64)
        close = df['close'].values.astype(np.float64)
        
        # MACD
        if len(close) >= 26:
            macd, macd_signal, macd_hist = talib.MACD(close, 
                                                       fastperiod=12, 
                                                       slowperiod=26, 
                                                       signalperiod=9)
            results['macd'] = macd
            results['macd_signal'] = macd_signal
            results['macd_histogram'] = macd_hist
        
        # ADX
        if len(close) >= 14:
            results['adx'] = talib.ADX(high, low, close, timeperiod=14)
            results['plus_di'] = talib.PLUS_DI(high, low, close, timeperiod=14)
            results['minus_di'] = talib.MINUS_DI(high, low, close, timeperiod=14)
        
        # Parabolic SAR
        if len(close) >= 2:
            results['psar'] = talib.SAR(high, low, acceleration=0.02, maximum=0.2)
            # Calculate trend direction
            psar_trend = np.where(close > results['psar'], 1, -1)
            results['psar_trend'] = psar_trend
        
        # Aroon
        if len(close) >= 25:
            aroon_down, aroon_up = talib.AROON(high, low, timeperiod=25)
            results['aroon_up'] = aroon_up
            results['aroon_down'] = aroon_down
            results['aroon_oscillator'] = aroon_up - aroon_down
        
        return results
    
    def calculate_oscillators(self, df: pd.DataFrame) -> Dict:
        """Calculate momentum oscillators"""
        results = {}
        high = df['high'].values.astype(np.float64)
        low = df['low'].values.astype(np.float64)
        close = df['close'].values.astype(np.float64)
        volume = df['volume'].values.astype(np.float64)
        
        # RSI
        if len(close) >= 14:
            results['rsi'] = talib.RSI(close, timeperiod=14)
        
        # Stochastic
        if len(close) >= 14:
            slowk, slowd = talib.STOCH(high, low, close,
                                       fastk_period=14,
                                       slowk_period=3,
                                       slowk_matype=0,
                                       slowd_period=3,
                                       slowd_matype=0)
            results['stoch_k'] = slowk
            results['stoch_d'] = slowd
        
        # Stochastic RSI
        if len(close) >= 14:
            rsi = talib.RSI(close, timeperiod=14)
            if len(rsi[~np.isnan(rsi)]) >= 14:
                fastk, fastd = talib.STOCHF(rsi, rsi, rsi,
                                           fastk_period=14,
                                           fastd_period=3,
                                           fastd_matype=0)
                results['stochrsi_k'] = fastk
                results['stochrsi_d'] = fastd
        
        # Williams %R
        if len(close) >= 14:
            results['williams_r'] = talib.WILLR(high, low, close, timeperiod=14)
        
        # CCI
        if len(close) >= 20:
            results['cci'] = talib.CCI(high, low, close, timeperiod=20)
        
        # Momentum
        if len(close) >= 10:
            results['momentum'] = talib.MOM(close, timeperiod=10)
        
        # Rate of Change
        if len(close) >= 10:
            results['roc'] = talib.ROC(close, timeperiod=10)
        
        # Ultimate Oscillator
        if len(close) >= 28:
            results['ultimate_oscillator'] = talib.ULTOSC(high, low, close,
                                                         timeperiod1=7,
                                                         timeperiod2=14,
                                                         timeperiod3=28)
        
        # Money Flow Index
        if len(close) >= 14 and volume is not None:
            results['mfi'] = talib.MFI(high, low, close, volume, timeperiod=14)
        
        return results
    
    def calculate_volatility_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate volatility indicators"""
        results = {}
        high = df['high'].values.astype(np.float64)
        low = df['low'].values.astype(np.float64)
        close = df['close'].values.astype(np.float64)
        
        # Bollinger Bands
        if len(close) >= 20:
            upper, middle, lower = talib.BBANDS(close,
                                               timeperiod=20,
                                               nbdevup=2,
                                               nbdevdn=2,
                                               matype=0)
            results['bb_upper'] = upper
            results['bb_middle'] = middle
            results['bb_lower'] = lower
            results['bb_width'] = upper - lower
            results['bb_percent'] = (close - lower) / (upper - lower)
        
        # Average True Range
        if len(close) >= 14:
            results['atr'] = talib.ATR(high, low, close, timeperiod=14)
        
        # Keltner Channels
        if len(close) >= 20:
            ema = talib.EMA(close, timeperiod=20)
            atr = talib.ATR(high, low, close, timeperiod=10)
            if atr is not None:
                results['kc_upper'] = ema + (2 * atr)
                results['kc_middle'] = ema
                results['kc_lower'] = ema - (2 * atr)
        
        # Donchian Channels
        if len(close) >= 20:
            results['dc_upper'] = pd.Series(high).rolling(20).max().values
            results['dc_lower'] = pd.Series(low).rolling(20).min().values
            results['dc_middle'] = (results['dc_upper'] + results['dc_lower']) / 2
        
        return results
    
    def calculate_volume_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate volume-based indicators"""
        results = {}
        high = df['high'].values.astype(np.float64)
        low = df['low'].values.astype(np.float64)
        close = df['close'].values.astype(np.float64)
        volume = df['volume'].values.astype(np.float64)
        
        if volume is None or len(volume) == 0:
            return results
        
        # On Balance Volume
        results['obv'] = talib.OBV(close, volume)
        
        # Accumulation/Distribution
        results['ad_line'] = talib.AD(high, low, close, volume)
        
        # Chaikin Money Flow
        if len(close) >= 20:
            adl = talib.AD(high, low, close, volume)
            if adl is not None:
                cmf = pd.Series(adl).rolling(20).sum() / pd.Series(volume).rolling(20).sum()
                results['cmf'] = cmf.values
        
        # Volume Weighted Average Price
        typical_price = (high + low + close) / 3
        results['vwap'] = np.cumsum(typical_price * volume) / np.cumsum(volume)
        
        # Price Volume Trend
        price_change = pd.Series(close).pct_change()
        pvt = (price_change * volume).cumsum()
        results['pvt'] = pvt.values
        
        return results
    
    def calculate_support_resistance(self, df: pd.DataFrame) -> Dict:
        """Calculate support and resistance levels"""
        results = {}
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Pivot Points (Standard)
        if len(close) >= 1:
            # Use previous day's data for pivot calculation
            prev_high = high[-2] if len(high) > 1 else high[-1]
            prev_low = low[-2] if len(low) > 1 else low[-1]
            prev_close = close[-2] if len(close) > 1 else close[-1]
            
            pivot = (prev_high + prev_low + prev_close) / 3
            r1 = 2 * pivot - prev_low
            r2 = pivot + (prev_high - prev_low)
            r3 = prev_high + 2 * (pivot - prev_low)
            s1 = 2 * pivot - prev_high
            s2 = pivot - (prev_high - prev_low)
            s3 = prev_low - 2 * (prev_high - pivot)
            
            # Create arrays with same length as input
            results['pivot'] = np.full(len(close), pivot)
            results['r1'] = np.full(len(close), r1)
            results['r2'] = np.full(len(close), r2)
            results['r3'] = np.full(len(close), r3)
            results['s1'] = np.full(len(close), s1)
            results['s2'] = np.full(len(close), s2)
            results['s3'] = np.full(len(close), s3)
        
        # Fibonacci Retracement
        if len(close) >= 20:
            recent_high = np.max(high[-20:])
            recent_low = np.min(low[-20:])
            diff = recent_high - recent_low
            
            fib_levels = {
                'fib_0': recent_low,
                'fib_236': recent_low + 0.236 * diff,
                'fib_382': recent_low + 0.382 * diff,
                'fib_500': recent_low + 0.500 * diff,
                'fib_618': recent_low + 0.618 * diff,
                'fib_786': recent_low + 0.786 * diff,
                'fib_1000': recent_high
            }
            
            for key, value in fib_levels.items():
                results[key] = np.full(len(close), value)
        
        return results
    
    def calculate_advanced_indicators(self, df: pd.DataFrame) -> Dict:
        """Calculate advanced indicators"""
        results = {}
        high = df['high'].values
        low = df['low'].values
        close = df['close'].values
        
        # Ichimoku Cloud
        if len(close) >= 52:
            # Tenkan-sen (Conversion Line)
            period9_high = pd.Series(high).rolling(9).max()
            period9_low = pd.Series(low).rolling(9).min()
            tenkan_sen = (period9_high + period9_low) / 2
            
            # Kijun-sen (Base Line)
            period26_high = pd.Series(high).rolling(26).max()
            period26_low = pd.Series(low).rolling(26).min()
            kijun_sen = (period26_high + period26_low) / 2
            
            # Senkou Span A (Leading Span A)
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)
            
            # Senkou Span B (Leading Span B)
            period52_high = pd.Series(high).rolling(52).max()
            period52_low = pd.Series(low).rolling(52).min()
            senkou_span_b = ((period52_high + period52_low) / 2).shift(26)
            
            # Chikou Span (Lagging Span)
            chikou_span = pd.Series(close).shift(-26)
            
            results['tenkan_sen'] = tenkan_sen.values
            results['kijun_sen'] = kijun_sen.values
            results['senkou_span_a'] = senkou_span_a.values
            results['senkou_span_b'] = senkou_span_b.values
            results['chikou_span'] = chikou_span.values
        
        # TRIX
        if len(close) >= 14:
            trix = talib.TRIX(close, timeperiod=14)
            results['trix'] = trix
            if trix is not None:
                trix_signal = talib.EMA(trix, timeperiod=9)
                results['trix_signal'] = trix_signal
        
        # ZigZag (simplified version)
        if len(close) >= 10:
            deviation = 5  # 5% deviation
            zigzag = self._calculate_zigzag(high, low, deviation)
            results['zigzag_value'] = zigzag['values']
            results['zigzag_peak_trough'] = zigzag['peaks_troughs']
        
        return results
    
    def _calculate_zigzag(self, high: np.ndarray, low: np.ndarray, 
                         deviation: float) -> Dict:
        """Calculate ZigZag indicator"""
        zigzag_values = np.full(len(high), np.nan)
        peaks_troughs = np.zeros(len(high))
        
        # Find initial point
        zigzag_values[0] = (high[0] + low[0]) / 2
        last_peak_trough = 0
        last_peak_trough_type = 0  # 1 for peak, -1 for trough
        
        for i in range(1, len(high)):
            # Calculate percentage change
            if last_peak_trough_type == 0:
                # No previous peak/trough, look for first significant move
                change_up = (high[i] - zigzag_values[last_peak_trough]) / zigzag_values[last_peak_trough] * 100
                change_down = (zigzag_values[last_peak_trough] - low[i]) / zigzag_values[last_peak_trough] * 100
                
                if change_up >= deviation:
                    last_peak_trough = i
                    last_peak_trough_type = 1
                    zigzag_values[i] = high[i]
                    peaks_troughs[i] = 1
                elif change_down >= deviation:
                    last_peak_trough = i
                    last_peak_trough_type = -1
                    zigzag_values[i] = low[i]
                    peaks_troughs[i] = -1
            elif last_peak_trough_type == 1:
                # Last was peak, look for trough
                change = (high[last_peak_trough] - low[i]) / high[last_peak_trough] * 100
                if change >= deviation:
                    last_peak_trough = i
                    last_peak_trough_type = -1
                    zigzag_values[i] = low[i]
                    peaks_troughs[i] = -1
                elif high[i] > high[last_peak_trough]:
                    # New higher peak
                    zigzag_values[last_peak_trough] = np.nan
                    peaks_troughs[last_peak_trough] = 0
                    last_peak_trough = i
                    zigzag_values[i] = high[i]
                    peaks_troughs[i] = 1
            else:
                # Last was trough, look for peak
                change = (high[i] - low[last_peak_trough]) / low[last_peak_trough] * 100
                if change >= deviation:
                    last_peak_trough = i
                    last_peak_trough_type = 1
                    zigzag_values[i] = high[i]
                    peaks_troughs[i] = 1
                elif low[i] < low[last_peak_trough]:
                    # New lower trough
                    zigzag_values[last_peak_trough] = np.nan
                    peaks_troughs[last_peak_trough] = 0
                    last_peak_trough = i
                    zigzag_values[i] = low[i]
                    peaks_troughs[i] = -1
        
        return {'values': zigzag_values, 'peaks_troughs': peaks_troughs}
    
    def calculate_all_indicators(self, ticker: str, df: pd.DataFrame) -> Dict[str, Dict]:
        """Calculate all indicators for a ticker"""
        all_results = {}
        
        # Calculate each category
        try:
            all_results['moving_averages'] = self.calculate_moving_averages(df)
        except Exception as e:
            logger.error(f"Error calculating moving averages for {ticker}: {e}")
            all_results['moving_averages'] = {}
        
        try:
            all_results['trend'] = self.calculate_trend_indicators(df)
        except Exception as e:
            logger.error(f"Error calculating trend indicators for {ticker}: {e}")
            all_results['trend'] = {}
        
        try:
            all_results['oscillators'] = self.calculate_oscillators(df)
        except Exception as e:
            logger.error(f"Error calculating oscillators for {ticker}: {e}")
            all_results['oscillators'] = {}
        
        try:
            all_results['volatility'] = self.calculate_volatility_indicators(df)
        except Exception as e:
            logger.error(f"Error calculating volatility indicators for {ticker}: {e}")
            all_results['volatility'] = {}
        
        try:
            all_results['volume'] = self.calculate_volume_indicators(df)
        except Exception as e:
            logger.error(f"Error calculating volume indicators for {ticker}: {e}")
            all_results['volume'] = {}
        
        try:
            all_results['support_resistance'] = self.calculate_support_resistance(df)
        except Exception as e:
            logger.error(f"Error calculating support/resistance for {ticker}: {e}")
            all_results['support_resistance'] = {}
        
        try:
            all_results['advanced'] = self.calculate_advanced_indicators(df)
        except Exception as e:
            logger.error(f"Error calculating advanced indicators for {ticker}: {e}")
            all_results['advanced'] = {}
        
        return all_results
    
    def save_indicators(self, ticker: str, indicators: Dict[str, Dict], 
                       dates: pd.DatetimeIndex) -> None:
        """Save calculated indicators to database"""
        records = []
        
        indicator_map = {
            'SMA': ['sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_100', 'sma_200'],
            'EMA': ['ema_5', 'ema_10', 'ema_20', 'ema_50', 'ema_100', 'ema_200'],
            'WMA': ['wma_10', 'wma_20', 'wma_50'],
            'TEMA': ['tema_10', 'tema_20', 'tema_50'],
            'HMA': ['hma_9', 'hma_16', 'hma_25'],
            'MACD': ['macd', 'macd_signal', 'macd_histogram'],
            'ADX': ['adx', 'plus_di', 'minus_di'],
            'PSAR': ['psar', 'psar_trend'],
            'AROON': ['aroon_up', 'aroon_down', 'aroon_oscillator'],
            'RSI': ['rsi'],
            'STOCH': ['stoch_k', 'stoch_d'],
            'STOCHRSI': ['stochrsi_k', 'stochrsi_d'],
            'WILLR': ['williams_r'],
            'CCI': ['cci'],
            'MOM': ['momentum'],
            'ROC': ['roc'],
            'UO': ['ultimate_oscillator'],
            'MFI': ['mfi'],
            'BB': ['bb_upper', 'bb_middle', 'bb_lower', 'bb_width', 'bb_percent'],
            'ATR': ['atr'],
            'KC': ['kc_upper', 'kc_middle', 'kc_lower'],
            'DC': ['dc_upper', 'dc_middle', 'dc_lower'],
            'OBV': ['obv'],
            'AD': ['ad_line'],
            'CMF': ['cmf'],
            'VWAP': ['vwap'],
            'PVT': ['pvt'],
            'PIVOT': ['pivot', 'r1', 'r2', 'r3', 's1', 's2', 's3'],
            'FIB': ['fib_0', 'fib_236', 'fib_382', 'fib_500', 'fib_618', 'fib_786', 'fib_1000'],
            'ICHIMOKU': ['tenkan_sen', 'kijun_sen', 'senkou_span_a', 'senkou_span_b', 'chikou_span'],
            'TRIX': ['trix', 'trix_signal'],
            'ZIGZAG': ['zigzag_value', 'zigzag_peak_trough']
        }
        
        # Flatten all indicators
        flat_indicators = {}
        for category, category_indicators in indicators.items():
            flat_indicators.update(category_indicators)
        
        # Process each indicator
        for indicator_code, output_columns in indicator_map.items():
            if indicator_code not in self.indicators_config:
                continue
                
            indicator_id = self.indicators_config[indicator_code]['id']
            
            # Collect values for this indicator
            indicator_values = {}
            all_found = True
            for col in output_columns:
                if col in flat_indicators:
                    indicator_values[col] = flat_indicators[col]
                else:
                    all_found = False
                    break
            
            if not all_found or not indicator_values:
                continue
            
            # Create records for each date
            for i, date in enumerate(dates):
                # Skip if all values are NaN for this date
                values_at_date = {}
                has_valid_value = False
                
                for col, values in indicator_values.items():
                    if isinstance(values, (list, np.ndarray)) and i < len(values):
                        value = values[i]
                        if not pd.isna(value):
                            values_at_date[col] = float(value)
                            has_valid_value = True
                
                if has_valid_value:
                    records.append({
                        'ticker': ticker,
                        'date': date,
                        'indicator_id': indicator_id,
                        'timeframe': 'daily',
                        'value': json.dumps(values_at_date),
                        'parameters': json.dumps(self.indicators_config[indicator_code]['parameters'])
                    })
        
        # Batch insert records
        if records:
            with self.engine.begin() as conn:
                # Delete existing records for this ticker
                conn.execute(text("""
                    DELETE FROM indicator_values 
                    WHERE ticker = :ticker 
                    AND timeframe = 'daily'
                """), {'ticker': ticker})
                
                # Insert new records
                for batch in [records[i:i+1000] for i in range(0, len(records), 1000)]:
                    for record in batch:
                        conn.execute(text("""
                            INSERT INTO indicator_values 
                            (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, :indicator_id, :timeframe, :value, :parameters)
                        """), record)
            
            logger.info(f"Saved {len(records)} indicator records for {ticker}")

    def save_indicators_incremental(self, ticker: str, indicators: Dict, dates: List):
        """Save indicators using UPSERT for incremental updates"""
        records = []

        for category, category_indicators in indicators.items():
            indicator_id = self.indicators_config[category]['id']

            for date in dates:
                if date in category_indicators['dates']:
                    date_idx = list(category_indicators['dates']).index(date)

                    # Build indicator values for this date
                    values = {}
                    for col_name in category_indicators['columns']:
                        if date_idx < len(category_indicators['data'][col_name]):
                            value = category_indicators['data'][col_name][date_idx]
                            if pd.notna(value) and value != np.inf and value != -np.inf:
                                values[col_name] = float(value)

                    if values:  # Only save if we have valid values
                        records.append({
                            'ticker': ticker,
                            'date': date.date(),
                            'indicator_id': indicator_id,
                            'timeframe': 'daily',
                            'value': json.dumps(values),
                            'parameters': json.dumps(category_indicators['parameters'])
                        })

        if records:
            with self.engine.begin() as conn:
                # Use ON CONFLICT DO UPDATE for PostgreSQL UPSERT
                for record in records:
                    conn.execute(text("""
                        INSERT INTO indicator_values
                        (ticker, date, indicator_id, timeframe, value, parameters)
                        VALUES (:ticker, :date, :indicator_id, :timeframe, :value, :parameters)
                        ON CONFLICT (ticker, date, indicator_id, timeframe)
                        DO UPDATE SET
                            value = EXCLUDED.value,
                            parameters = EXCLUDED.parameters,
                            updated_at = CURRENT_TIMESTAMP
                    """), record)

        logger.info(f"Saved {len(records)} incremental indicator records for {ticker}")
    
    def process_ticker(self, ticker: str, start_date: Optional[datetime] = None) -> bool:
        """Process all indicators for a single ticker"""
        try:
            # Get price data
            df = self.get_price_data(ticker, start_date)

            if df.empty or len(df) < 20:
                logger.warning(f"Insufficient data for {ticker}: {len(df)} records")
                return False

            # Calculate all indicators
            indicators = self.calculate_all_indicators(ticker, df)

            # Save to database
            self.save_indicators(ticker, indicators, df.index)

            return True

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            return False

    def process_ticker_incremental(self, ticker: str, start_date: str = '2025-09-01') -> bool:
        """Process indicators for a ticker only for new data (incremental update)"""
        try:
            from datetime import datetime

            # Convert string to datetime
            cutoff_date = datetime.strptime(start_date, '%Y-%m-%d').date()

            # Get the latest indicator date for this ticker
            with self.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT MAX(date) as max_date
                    FROM indicator_values
                    WHERE ticker = :ticker
                """), {"ticker": ticker})

                row = result.fetchone()
                last_indicator_date = row[0] if row and row[0] else None

            # Get all price data (need full history for proper indicator calculation)
            df = self.get_price_data(ticker)

            if df.empty or len(df) < 20:
                logger.warning(f"Insufficient data for {ticker}: {len(df)} records")
                return False

            # Calculate all indicators for full dataset
            indicators = self.calculate_all_indicators(ticker, df)

            # Filter to only save new indicators (after cutoff_date or last_indicator_date)
            if last_indicator_date:
                filter_date = max(cutoff_date, last_indicator_date)
            else:
                filter_date = cutoff_date

            # Filter indicators to only new dates
            new_dates = [date for date in df.index if date.date() > filter_date]

            if not new_dates:
                logger.info(f"No new data to process for {ticker}")
                return True

            # Save only new indicators using UPSERT
            self.save_indicators_incremental(ticker, indicators, new_dates)

            logger.info(f"Saved {len(new_dates)} new indicator records for {ticker}")
            return True

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            return False
    
    def process_all_tickers(self, batch_size: int = 10, max_workers: int = 4):
        """Process all active tickers in batches"""
        # Get all active tickers
        with self.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT ticker 
                FROM stocks 
                WHERE is_active = true
                ORDER BY ticker
            """))
            tickers = [row[0] for row in result]
        
        logger.info(f"Processing {len(tickers)} tickers")
        
        successful = 0
        failed = 0
        
        # Process in parallel batches
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for ticker in tickers:
                future = executor.submit(self.process_ticker, ticker)
                futures.append((ticker, future))
                
                # Process batch when full
                if len(futures) >= batch_size:
                    for ticker, future in futures:
                        try:
                            if future.result(timeout=60):
                                successful += 1
                            else:
                                failed += 1
                        except Exception as e:
                            logger.error(f"Failed to process {ticker}: {e}")
                            failed += 1
                    
                    logger.info(f"Progress: {successful + failed}/{len(tickers)} "
                              f"(Success: {successful}, Failed: {failed})")
                    futures = []
            
            # Process remaining futures
            for ticker, future in futures:
                try:
                    if future.result(timeout=60):
                        successful += 1
                    else:
                        failed += 1
                except Exception as e:
                    logger.error(f"Failed to process {ticker}: {e}")
                    failed += 1
        
        logger.info(f"Completed processing. Success: {successful}, Failed: {failed}")
        
        # Refresh materialized view
        with self.engine.begin() as conn:
            conn.execute(text("REFRESH MATERIALIZED VIEW indicator_summary"))
        
        return {'successful': successful, 'failed': failed}


if __name__ == "__main__":
    # Database connection
    db_url = "postgresql://admin:stockadmin123!@localhost:5435/stocktrading"
    
    # Create calculator
    calculator = IndicatorCalculator(db_url)
    
    # Process all tickers
    result = calculator.process_all_tickers(batch_size=20, max_workers=4)
    
    print(f"Processing complete: {result}")