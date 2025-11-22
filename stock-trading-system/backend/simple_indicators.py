#!/usr/bin/env python3
import pandas as pd
import numpy as np
from sqlalchemy import create_engine, text
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    engine = create_engine('postgresql://admin:admin123@postgres:5432/stocktrading')

    # 9월 26일에 데이터가 있는 모든 한국 주식 가져오기
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT s.ticker FROM stocks s
            JOIN stock_prices sp ON s.ticker = sp.ticker
            WHERE s.currency = 'KRW' AND sp.date = '2025-09-26'
            ORDER BY s.ticker
        """))
        tickers = [row[0] for row in result]

    logger.info(f"Processing {len(tickers)} Korean stocks")

    success_count = 0

    for i, ticker in enumerate(tickers):
        try:
            # 각 종목별로 새 연결 사용
            with engine.connect() as conn:
                # 최근 100일 데이터 가져오기
                df = pd.read_sql(text("""
                    SELECT date, close_price, high_price, low_price, volume
                    FROM stock_prices
                    WHERE ticker = :ticker
                    AND date <= '2025-09-26'
                    AND date >= '2025-06-01'
                    ORDER BY date ASC
                """), conn, params={'ticker': ticker})

                if len(df) < 20:  # 최소 20일 데이터 필요
                    continue

                # 데이터 타입 변환
                df['close'] = pd.to_numeric(df['close_price'], errors='coerce')
                df['high'] = pd.to_numeric(df['high_price'], errors='coerce')
                df['low'] = pd.to_numeric(df['low_price'], errors='coerce')

                # RSI 계산 (14일)
                delta = df['close'].diff()
                gain = delta.where(delta > 0, 0)
                loss = -delta.where(delta < 0, 0)
                avg_gain = gain.rolling(14).mean()
                avg_loss = loss.rolling(14).mean()
                rs = avg_gain / avg_loss
                rsi = 100 - (100 / (1 + rs))

                # MACD 계산
                ema12 = df['close'].ewm(span=12).mean()
                ema26 = df['close'].ewm(span=26).mean()
                macd_line = ema12 - ema26
                macd_signal = macd_line.ewm(span=9).mean()
                macd_hist = macd_line - macd_signal

                # 이동평균 계산
                ma20 = df['close'].rolling(20).mean()
                ma50 = df['close'].rolling(50).mean()

                # 볼린저 밴드
                bb_middle = df['close'].rolling(20).mean()
                bb_std = df['close'].rolling(20).std()
                bb_upper = bb_middle + (2 * bb_std)
                bb_lower = bb_middle - (2 * bb_std)

                # 스토캐스틱
                lowest_low = df['low'].rolling(14).min()
                highest_high = df['high'].rolling(14).max()
                stoch_k = 100 * ((df['close'] - lowest_low) / (highest_high - lowest_low))
                stoch_d = stoch_k.rolling(3).mean()

                # 최신 값 추출
                latest_idx = -1
                indicators = {
                    'ticker': ticker,
                    'date': '2025-09-26',
                    'rsi': float(rsi.iloc[latest_idx]) if pd.notna(rsi.iloc[latest_idx]) else None,
                    'macd': float(macd_line.iloc[latest_idx]) if pd.notna(macd_line.iloc[latest_idx]) else None,
                    'macd_signal': float(macd_signal.iloc[latest_idx]) if pd.notna(macd_signal.iloc[latest_idx]) else None,
                    'macd_histogram': float(macd_hist.iloc[latest_idx]) if pd.notna(macd_hist.iloc[latest_idx]) else None,
                    'ma_20': float(ma20.iloc[latest_idx]) if pd.notna(ma20.iloc[latest_idx]) else None,
                    'ma_50': float(ma50.iloc[latest_idx]) if pd.notna(ma50.iloc[latest_idx]) else None,
                    'bollinger_upper': float(bb_upper.iloc[latest_idx]) if pd.notna(bb_upper.iloc[latest_idx]) else None,
                    'bollinger_middle': float(bb_middle.iloc[latest_idx]) if pd.notna(bb_middle.iloc[latest_idx]) else None,
                    'bollinger_lower': float(bb_lower.iloc[latest_idx]) if pd.notna(bb_lower.iloc[latest_idx]) else None,
                    'stoch_k': float(stoch_k.iloc[latest_idx]) if pd.notna(stoch_k.iloc[latest_idx]) else None,
                    'stoch_d': float(stoch_d.iloc[latest_idx]) if pd.notna(stoch_d.iloc[latest_idx]) else None
                }

                # 데이터베이스에 저장
                with engine.begin() as save_conn:
                    save_conn.execute(text("""
                        INSERT INTO technical_indicators (
                            ticker, date, rsi, macd, macd_signal, macd_histogram,
                            ma_20, ma_50, bollinger_upper, bollinger_middle, bollinger_lower,
                            stoch_k, stoch_d, created_at
                        ) VALUES (
                            :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                            :ma_20, :ma_50, :bollinger_upper, :bollinger_middle, :bollinger_lower,
                            :stoch_k, :stoch_d, NOW()
                        ) ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            macd_histogram = EXCLUDED.macd_histogram,
                            ma_20 = EXCLUDED.ma_20,
                            ma_50 = EXCLUDED.ma_50,
                            bollinger_upper = EXCLUDED.bollinger_upper,
                            bollinger_middle = EXCLUDED.bollinger_middle,
                            bollinger_lower = EXCLUDED.bollinger_lower,
                            stoch_k = EXCLUDED.stoch_k,
                            stoch_d = EXCLUDED.stoch_d,
                            created_at = NOW()
                    """), indicators)

                success_count += 1

                if success_count % 50 == 0:
                    logger.info(f"Processed {success_count} stocks ({i+1}/{len(tickers)})")

        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            continue

    logger.info(f"Successfully calculated indicators for {success_count}/{len(tickers)} stocks")

if __name__ == "__main__":
    main()