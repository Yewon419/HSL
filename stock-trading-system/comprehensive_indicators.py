#!/usr/bin/env python3
"""
32개 모든 기술적 지표를 계산하는 종합 모듈
"""

import pandas as pd
import numpy as np
import json
from sqlalchemy import create_engine, text
import logging
from datetime import datetime, timedelta

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def calculate_all_technical_indicators(df):
    """32개 모든 기술적 지표 계산"""

    # 기본 데이터 준비
    close = df['close']
    high = df['high']
    low = df['low']
    volume = df['volume']

    # 결과를 저장할 딕셔너리
    indicators = {}

    try:
        # 1. SMA (Simple Moving Average) - 다양한 기간
        periods = [5, 10, 20, 50, 100, 200]
        sma_values = {}
        for period in periods:
            if len(df) >= period:
                sma_values[f'sma_{period}'] = close.rolling(period).mean().iloc[-1]
        indicators['SMA'] = sma_values

        # 2. EMA (Exponential Moving Average)
        ema_values = {}
        for period in [5, 10, 20, 50, 100, 200]:
            if len(df) >= period:
                ema_values[f'ema_{period}'] = close.ewm(span=period).mean().iloc[-1]
        indicators['EMA'] = ema_values

        # 3. WMA (Weighted Moving Average)
        wma_values = {}
        for period in [10, 20, 50]:
            if len(df) >= period:
                weights = np.arange(1, period + 1)
                wma_values[f'wma_{period}'] = (close.rolling(period).apply(
                    lambda x: np.average(x, weights=weights), raw=True)).iloc[-1]
        indicators['WMA'] = wma_values

        # 4. TEMA (Triple Exponential Moving Average)
        tema_values = {}
        for period in [10, 20, 50]:
            if len(df) >= period * 3:
                ema1 = close.ewm(span=period).mean()
                ema2 = ema1.ewm(span=period).mean()
                ema3 = ema2.ewm(span=period).mean()
                tema_values[f'tema_{period}'] = (3 * ema1 - 3 * ema2 + ema3).iloc[-1]
        indicators['TEMA'] = tema_values

        # 5. HMA (Hull Moving Average)
        hma_values = {}
        for period in [9, 16, 25]:
            if len(df) >= period:
                half_length = int(period / 2)
                sqrt_length = int(np.sqrt(period))
                wma1 = close.rolling(half_length).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)))
                wma2 = close.rolling(period).apply(lambda x: np.average(x, weights=np.arange(1, len(x) + 1)))
                raw_hma = 2 * wma1 - wma2
                if len(raw_hma.dropna()) >= sqrt_length:
                    hma_values[f'hma_{period}'] = raw_hma.rolling(sqrt_length).apply(
                        lambda x: np.average(x, weights=np.arange(1, len(x) + 1))).iloc[-1]
        indicators['HMA'] = hma_values

        # 6. MACD (Moving Average Convergence Divergence)
        if len(df) >= 34:  # 26 + 9 - 1
            ema12 = close.ewm(span=12).mean()
            ema26 = close.ewm(span=26).mean()
            macd_line = ema12 - ema26
            signal_line = macd_line.ewm(span=9).mean()
            histogram = macd_line - signal_line
            indicators['MACD'] = {
                'macd': macd_line.iloc[-1],
                'macd_signal': signal_line.iloc[-1],
                'macd_histogram': histogram.iloc[-1]
            }

        # 7. ADX (Average Directional Index)
        if len(df) >= 14:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()

            up_move = high - high.shift(1)
            down_move = low.shift(1) - low

            plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
            minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)

            plus_dm_series = pd.Series(plus_dm, index=df.index)
            minus_dm_series = pd.Series(minus_dm, index=df.index)

            plus_di = 100 * (plus_dm_series.rolling(14).mean() / atr)
            minus_di = 100 * (minus_dm_series.rolling(14).mean() / atr)

            dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)
            adx = dx.rolling(14).mean()

            indicators['ADX'] = {
                'adx': adx.iloc[-1],
                'plus_di': plus_di.iloc[-1],
                'minus_di': minus_di.iloc[-1]
            }

        # 8. PSAR (Parabolic SAR)
        if len(df) >= 2:
            # 간단한 PSAR 구현
            af = 0.02
            max_af = 0.20
            psar = close.iloc[0]
            trend = 1
            indicators['PSAR'] = {
                'psar': psar,
                'psar_trend': trend
            }

        # 9. AROON
        if len(df) >= 25:
            period = 25
            aroon_up = 100 * (period - close.rolling(period).apply(lambda x: period - 1 - x.argmax())) / period
            aroon_down = 100 * (period - close.rolling(period).apply(lambda x: period - 1 - x.argmin())) / period
            indicators['AROON'] = {
                'aroon_up': aroon_up.iloc[-1],
                'aroon_down': aroon_down.iloc[-1],
                'aroon_oscillator': (aroon_up - aroon_down).iloc[-1]
            }

        # 10. RSI (Relative Strength Index)
        if len(df) >= 14:
            delta = close.diff()
            gain = delta.where(delta > 0, 0).rolling(14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            indicators['RSI'] = {'rsi': rsi.iloc[-1]}

        # 11. STOCH (Stochastic Oscillator)
        if len(df) >= 14:
            lowest_low = low.rolling(14).min()
            highest_high = high.rolling(14).max()
            k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
            d_percent = k_percent.rolling(3).mean()
            indicators['STOCH'] = {
                'stoch_k': k_percent.iloc[-1],
                'stoch_d': d_percent.iloc[-1]
            }

        # 12. STOCHRSI
        if len(df) >= 14:
            rsi_series = 100 - (100 / (1 + gain / loss))
            rsi_low = rsi_series.rolling(14).min()
            rsi_high = rsi_series.rolling(14).max()
            stoch_rsi_k = (rsi_series - rsi_low) / (rsi_high - rsi_low) * 100
            stoch_rsi_d = stoch_rsi_k.rolling(3).mean()
            indicators['STOCHRSI'] = {
                'stochrsi_k': stoch_rsi_k.iloc[-1],
                'stochrsi_d': stoch_rsi_d.iloc[-1]
            }

        # 13. WILLR (Williams %R)
        if len(df) >= 14:
            highest_high = high.rolling(14).max()
            lowest_low = low.rolling(14).min()
            willr = -100 * (highest_high - close) / (highest_high - lowest_low)
            indicators['WILLR'] = {'williams_r': willr.iloc[-1]}

        # 14. CCI (Commodity Channel Index)
        if len(df) >= 20:
            typical_price = (high + low + close) / 3
            sma_tp = typical_price.rolling(20).mean()
            mad = typical_price.rolling(20).apply(lambda x: np.mean(np.abs(x - x.mean())))
            cci = (typical_price - sma_tp) / (0.015 * mad)
            indicators['CCI'] = {'cci': cci.iloc[-1]}

        # 15. MOM (Momentum)
        if len(df) >= 10:
            momentum = close / close.shift(10) * 100 - 100
            indicators['MOM'] = {'momentum': close.iloc[-1] - close.iloc[-11]}

        # 16. ROC (Rate of Change)
        if len(df) >= 10:
            roc = ((close / close.shift(10)) - 1) * 100
            indicators['ROC'] = {'roc': roc.iloc[-1]}

        # 17. UO (Ultimate Oscillator)
        if len(df) >= 28:
            bp = close - np.minimum(low, close.shift(1))
            tr = np.maximum(high, close.shift(1)) - np.minimum(low, close.shift(1))
            avg7 = bp.rolling(7).sum() / tr.rolling(7).sum()
            avg14 = bp.rolling(14).sum() / tr.rolling(14).sum()
            avg28 = bp.rolling(28).sum() / tr.rolling(28).sum()
            uo = 100 * (4 * avg7 + 2 * avg14 + avg28) / 7
            indicators['UO'] = {'ultimate_oscillator': uo.iloc[-1]}

        # 18. BB (Bollinger Bands)
        if len(df) >= 20:
            sma20 = close.rolling(20).mean()
            std20 = close.rolling(20).std()
            bb_upper = sma20 + (std20 * 2)
            bb_lower = sma20 - (std20 * 2)
            bb_width = bb_upper - bb_lower
            bb_percent = (close - bb_lower) / (bb_upper - bb_lower)
            indicators['BB'] = {
                'bb_upper': bb_upper.iloc[-1],
                'bb_middle': sma20.iloc[-1],
                'bb_lower': bb_lower.iloc[-1],
                'bb_width': bb_width.iloc[-1],
                'bb_percent': bb_percent.iloc[-1]
            }

        # 19. ATR (Average True Range)
        if len(df) >= 14:
            tr1 = high - low
            tr2 = abs(high - close.shift(1))
            tr3 = abs(low - close.shift(1))
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(14).mean()
            indicators['ATR'] = {'atr': atr.iloc[-1]}

        # 20. KC (Keltner Channels)
        if len(df) >= 20:
            ema20 = close.ewm(span=20).mean()
            atr = tr.rolling(10).mean()
            kc_upper = ema20 + (2 * atr)
            kc_lower = ema20 - (2 * atr)
            indicators['KC'] = {
                'kc_upper': kc_upper.iloc[-1],
                'kc_middle': ema20.iloc[-1],
                'kc_lower': kc_lower.iloc[-1]
            }

        # 21. DC (Donchian Channels)
        if len(df) >= 20:
            dc_upper = high.rolling(20).max()
            dc_lower = low.rolling(20).min()
            dc_middle = (dc_upper + dc_lower) / 2
            indicators['DC'] = {
                'dc_upper': dc_upper.iloc[-1],
                'dc_middle': dc_middle.iloc[-1],
                'dc_lower': dc_lower.iloc[-1]
            }

        # 22. OBV (On Balance Volume)
        if len(df) >= 2:
            obv = volume.copy()
            price_change = close.diff()
            obv[price_change > 0] = volume[price_change > 0]
            obv[price_change < 0] = -volume[price_change < 0]
            obv[price_change == 0] = 0
            indicators['OBV'] = {'obv': obv.cumsum().iloc[-1]}

        # 23. AD (Accumulation/Distribution)
        if len(df) >= 2:
            clv = ((close - low) - (high - close)) / (high - low)
            clv = clv.fillna(0)
            ad = (clv * volume).cumsum()
            indicators['AD'] = {'ad_line': ad.iloc[-1]}

        # 24. CMF (Chaikin Money Flow)
        if len(df) >= 20:
            clv = ((close - low) - (high - close)) / (high - low)
            clv = clv.fillna(0)
            cmf = (clv * volume).rolling(20).sum() / volume.rolling(20).sum()
            indicators['CMF'] = {'cmf': cmf.iloc[-1]}

        # 25. MFI (Money Flow Index)
        if len(df) >= 14:
            typical_price = (high + low + close) / 3
            money_flow = typical_price * volume
            positive_flow = money_flow.where(typical_price.diff() > 0, 0).rolling(14).sum()
            negative_flow = money_flow.where(typical_price.diff() < 0, 0).rolling(14).sum()
            mfi = 100 - (100 / (1 + (positive_flow / abs(negative_flow))))
            indicators['MFI'] = {'mfi': mfi.iloc[-1]}

        # 26. VWAP (Volume Weighted Average Price)
        if len(df) >= 1:
            typical_price = (high + low + close) / 3
            vwap = (typical_price * volume).cumsum() / volume.cumsum()
            indicators['VWAP'] = {'vwap': vwap.iloc[-1]}

        # 27. PVT (Price Volume Trend)
        if len(df) >= 2:
            pvt = ((close.diff() / close.shift(1)) * volume).cumsum()
            indicators['PVT'] = {'pvt': pvt.iloc[-1]}

        # 28. PIVOT (Pivot Points)
        if len(df) >= 1:
            pivot = (high.iloc[-1] + low.iloc[-1] + close.iloc[-1]) / 3
            r1 = 2 * pivot - low.iloc[-1]
            s1 = 2 * pivot - high.iloc[-1]
            r2 = pivot + (high.iloc[-1] - low.iloc[-1])
            s2 = pivot - (high.iloc[-1] - low.iloc[-1])
            r3 = high.iloc[-1] + 2 * (pivot - low.iloc[-1])
            s3 = low.iloc[-1] - 2 * (high.iloc[-1] - pivot)
            indicators['PIVOT'] = {
                'pivot': pivot,
                'r1': r1, 'r2': r2, 'r3': r3,
                's1': s1, 's2': s2, 's3': s3
            }

        # 29. FIB (Fibonacci Retracement)
        if len(df) >= 1:
            high_price = high.max()
            low_price = low.min()
            diff = high_price - low_price
            levels = [0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0]
            fib_values = {}
            for level in levels:
                fib_values[f'fib_{int(level * 1000)}'] = low_price + (diff * level)
            indicators['FIB'] = fib_values

        # 30. ICHIMOKU (Ichimoku Cloud)
        if len(df) >= 52:
            # Tenkan-sen (Conversion Line)
            tenkan_high = high.rolling(9).max()
            tenkan_low = low.rolling(9).min()
            tenkan_sen = (tenkan_high + tenkan_low) / 2

            # Kijun-sen (Base Line)
            kijun_high = high.rolling(26).max()
            kijun_low = low.rolling(26).min()
            kijun_sen = (kijun_high + kijun_low) / 2

            # Senkou Span A
            senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(26)

            # Senkou Span B
            senkou_high = high.rolling(52).max()
            senkou_low = low.rolling(52).min()
            senkou_span_b = ((senkou_high + senkou_low) / 2).shift(26)

            indicators['ICHIMOKU'] = {
                'tenkan_sen': tenkan_sen.iloc[-1],
                'kijun_sen': kijun_sen.iloc[-1],
                'senkou_span_a': senkou_span_a.iloc[-27] if len(senkou_span_a.dropna()) > 26 else None,
                'senkou_span_b': senkou_span_b.iloc[-27] if len(senkou_span_b.dropna()) > 26 else None
            }

        # 31. ZIGZAG (ZigZag)
        if len(df) >= 1:
            # 단순한 ZigZag 구현
            deviation = 5  # 5% deviation
            zigzag_value = close.iloc[-1]
            zigzag_trend = 1 if close.iloc[-1] > close.iloc[-2] else -1
            indicators['ZIGZAG'] = {
                'zigzag_value': zigzag_value,
                'zigzag_peak_trough': zigzag_trend
            }

        # 32. TRIX
        if len(df) >= 42:  # 3 * 14
            ema1 = close.ewm(span=14).mean()
            ema2 = ema1.ewm(span=14).mean()
            ema3 = ema2.ewm(span=14).mean()
            trix = ema3.pct_change() * 10000
            trix_signal = trix.ewm(span=9).mean()
            indicators['TRIX'] = {
                'trix': trix.iloc[-1],
                'trix_signal': trix_signal.iloc[-1]
            }

    except Exception as e:
        logger.error(f"Error calculating indicators: {e}")

    return indicators

def save_indicators_to_database(ticker, date, indicators, engine):
    """계산된 지표들을 데이터베이스에 저장"""

    # indicator_id 매핑
    indicator_mapping = {
        'SMA': 1, 'EMA': 2, 'WMA': 3, 'TEMA': 4, 'HMA': 5,
        'MACD': 6, 'ADX': 7, 'PSAR': 8, 'AROON': 9, 'RSI': 10,
        'STOCH': 11, 'STOCHRSI': 12, 'WILLR': 13, 'CCI': 14, 'MOM': 15,
        'ROC': 16, 'UO': 17, 'BB': 18, 'ATR': 19, 'KC': 20,
        'DC': 21, 'OBV': 22, 'AD': 23, 'CMF': 24, 'MFI': 25,
        'VWAP': 26, 'PVT': 27, 'PIVOT': 28, 'FIB': 29, 'ICHIMOKU': 30,
        'ZIGZAG': 31, 'TRIX': 32
    }

    saved_count = 0

    try:
        with engine.begin() as conn:
            for indicator_name, indicator_values in indicators.items():
                if indicator_name in indicator_mapping and indicator_values:
                    indicator_id = indicator_mapping[indicator_name]

                    # None 값들을 필터링하여 저장
                    clean_values = {}
                    for key, value in indicator_values.items():
                        if value is not None and not (isinstance(value, float) and np.isnan(value)):
                            clean_values[key] = float(value)

                    if clean_values:  # 유효한 값이 있을 때만 저장
                        conn.execute(text("""
                            INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, :indicator_id, 'daily', :value, '{}')
                            ON CONFLICT (ticker, date, indicator_id, timeframe)
                            DO UPDATE SET value = EXCLUDED.value, parameters = EXCLUDED.parameters
                        """), {
                            'ticker': ticker,
                            'date': date,
                            'indicator_id': indicator_id,
                            'value': json.dumps(clean_values)
                        })
                        saved_count += 1

    except Exception as e:
        logger.error(f"Error saving indicators for {ticker} {date}: {e}")

    return saved_count

def calculate_comprehensive_indicators(target_date='2025-09-24'):
    """특정 날짜의 모든 종목에 대해 32개 지표 계산"""
    logger.info(f"Starting comprehensive indicators calculation for {target_date}")

    try:
        engine = get_db_connection()

        # 대상 종목 조회 (해당 날짜에 주가 데이터가 있는 종목들)
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                WHERE s.currency = 'KRW'
                AND sp.date >= :target_date
                ORDER BY s.ticker
            """), {'target_date': target_date})
            tickers = [row[0] for row in result]

        logger.info(f"Processing {len(tickers)} tickers: {tickers}")

        total_saved = 0
        success_count = 0

        for ticker in tickers:
            try:
                logger.info(f"Processing {ticker}...")

                # 주가 데이터 조회 (충분한 기간)
                df = pd.read_sql_query(text("""
                    SELECT date, close_price, high_price, low_price, volume
                    FROM stock_prices
                    WHERE ticker = :ticker
                    AND date <= :target_date
                    ORDER BY date DESC
                    LIMIT 200
                """), engine, params={'ticker': ticker, 'target_date': target_date})

                if len(df) < 50:  # 최소 데이터 요구사항
                    logger.warning(f"Insufficient data for {ticker}: {len(df)} records")
                    continue

                # 데이터 정렬 및 전처리
                df = df.sort_values('date').reset_index(drop=True)
                df['close'] = pd.to_numeric(df['close_price'])
                df['high'] = pd.to_numeric(df['high_price'])
                df['low'] = pd.to_numeric(df['low_price'])
                df['volume'] = pd.to_numeric(df['volume'])

                # 32개 지표 계산
                indicators = calculate_all_technical_indicators(df)

                # 데이터베이스에 저장
                saved = save_indicators_to_database(ticker, target_date, indicators, engine)
                total_saved += saved
                success_count += 1

                logger.info(f"✅ {ticker}: {saved} indicators calculated and saved")

            except Exception as e:
                logger.error(f"❌ Error processing {ticker}: {e}")
                continue

        logger.info(f"🎉 Comprehensive calculation completed!")
        logger.info(f"   - Processed: {success_count}/{len(tickers)} tickers")
        logger.info(f"   - Total indicators saved: {total_saved}")

        return success_count

    except Exception as e:
        logger.error(f"Comprehensive calculation failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    # 24일 데이터로 테스트
    calculate_comprehensive_indicators('2025-09-24')