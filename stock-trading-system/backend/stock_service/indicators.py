import pandas as pd
import numpy as np
from typing import Dict, Optional

class TechnicalIndicators:
    @staticmethod
    def calculate_stochastic(df: pd.DataFrame, k_period: int = 14, d_period: int = 3) -> Dict[str, pd.Series]:
        """Calculate Stochastic Oscillator without pandas_ta"""
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()

        stoch_k = 100 * (df['Close'] - low_min) / (high_max - low_min)
        stoch_d = stoch_k.rolling(window=d_period).mean()

        return {'stoch_k': stoch_k, 'stoch_d': stoch_d}

    @staticmethod
    def calculate_macd(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal: int = 9) -> Dict[str, pd.Series]:
        """Calculate MACD without pandas_ta"""
        exp1 = df['Close'].ewm(span=fast, adjust=False).mean()
        exp2 = df['Close'].ewm(span=slow, adjust=False).mean()

        macd = exp1 - exp2
        macd_signal = macd.ewm(span=signal, adjust=False).mean()
        macd_histogram = macd - macd_signal

        return {
            'macd': macd,
            'macd_signal': macd_signal,
            'macd_histogram': macd_histogram
        }

    @staticmethod
    def calculate_rsi(df: pd.DataFrame, period: int = 14) -> pd.Series:
        """Calculate RSI without pandas_ta"""
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()

        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))

        return rsi

    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame) -> Dict[str, pd.Series]:
        """Calculate Simple Moving Averages without pandas_ta"""
        ma_20 = df['Close'].rolling(window=20).mean()
        ma_50 = df['Close'].rolling(window=50).mean()
        ma_200 = df['Close'].rolling(window=200).mean()

        return {
            'ma_20': ma_20,
            'ma_50': ma_50,
            'ma_200': ma_200
        }

    @staticmethod
    def calculate_bollinger_bands(df: pd.DataFrame, period: int = 20, std_dev: int = 2) -> Dict[str, pd.Series]:
        """Calculate Bollinger Bands without pandas_ta"""
        ma = df['Close'].rolling(window=period).mean()
        std = df['Close'].rolling(window=period).std()

        upper = ma + (std * std_dev)
        lower = ma - (std * std_dev)

        return {
            'bollinger_upper': upper,
            'bollinger_middle': ma,
            'bollinger_lower': lower
        }
    
    @staticmethod
    def calculate_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        indicators = TechnicalIndicators()
        
        result_df = df.copy()
        
        stoch = indicators.calculate_stochastic(df)
        result_df['stoch_k'] = stoch['stoch_k']
        result_df['stoch_d'] = stoch['stoch_d']
        
        macd = indicators.calculate_macd(df)
        result_df['macd'] = macd['macd']
        result_df['macd_signal'] = macd['macd_signal']
        result_df['macd_histogram'] = macd['macd_histogram']
        
        result_df['rsi'] = indicators.calculate_rsi(df)
        
        ma = indicators.calculate_moving_averages(df)
        result_df['ma_20'] = ma['ma_20']
        result_df['ma_50'] = ma['ma_50']
        result_df['ma_200'] = ma['ma_200']
        
        bb = indicators.calculate_bollinger_bands(df)
        result_df['bollinger_upper'] = bb['bollinger_upper']
        result_df['bollinger_middle'] = bb['bollinger_middle']
        result_df['bollinger_lower'] = bb['bollinger_lower']
        
        return result_df

class SignalGenerator:
    @staticmethod
    def generate_stochastic_signals(df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(index=df.index, dtype=str)
        signals[:] = 'HOLD'
        
        oversold = (df['stoch_k'] < 20) & (df['stoch_d'] < 20)
        overbought = (df['stoch_k'] > 80) & (df['stoch_d'] > 80)
        
        bullish_cross = (df['stoch_k'] > df['stoch_d']) & (df['stoch_k'].shift(1) <= df['stoch_d'].shift(1))
        bearish_cross = (df['stoch_k'] < df['stoch_d']) & (df['stoch_k'].shift(1) >= df['stoch_d'].shift(1))
        
        signals[oversold & bullish_cross] = 'BUY'
        signals[overbought & bearish_cross] = 'SELL'
        
        return signals
    
    @staticmethod
    def generate_macd_signals(df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(index=df.index, dtype=str)
        signals[:] = 'HOLD'
        
        bullish_cross = (df['macd'] > df['macd_signal']) & (df['macd'].shift(1) <= df['macd_signal'].shift(1))
        bearish_cross = (df['macd'] < df['macd_signal']) & (df['macd'].shift(1) >= df['macd_signal'].shift(1))
        
        signals[bullish_cross & (df['macd'] < 0)] = 'BUY'
        signals[bearish_cross & (df['macd'] > 0)] = 'SELL'
        
        return signals
    
    @staticmethod
    def generate_rsi_signals(df: pd.DataFrame) -> pd.Series:
        signals = pd.Series(index=df.index, dtype=str)
        signals[:] = 'HOLD'
        
        oversold = df['rsi'] < 30
        overbought = df['rsi'] > 70
        
        recovering = oversold & (df['rsi'] > df['rsi'].shift(1))
        declining = overbought & (df['rsi'] < df['rsi'].shift(1))
        
        signals[recovering] = 'BUY'
        signals[declining] = 'SELL'
        
        return signals
    
    @staticmethod
    def generate_combined_signals(df: pd.DataFrame) -> pd.Series:
        stoch_signals = SignalGenerator.generate_stochastic_signals(df)
        macd_signals = SignalGenerator.generate_macd_signals(df)
        rsi_signals = SignalGenerator.generate_rsi_signals(df)
        
        signal_counts = pd.DataFrame({
            'stoch': stoch_signals,
            'macd': macd_signals,
            'rsi': rsi_signals
        })
        
        def combine_signals(row):
            buy_count = (row == 'BUY').sum()
            sell_count = (row == 'SELL').sum()
            
            if buy_count >= 2:
                return 'STRONG_BUY'
            elif buy_count == 1:
                return 'BUY'
            elif sell_count >= 2:
                return 'STRONG_SELL'
            elif sell_count == 1:
                return 'SELL'
            else:
                return 'HOLD'
        
        return signal_counts.apply(combine_signals, axis=1)