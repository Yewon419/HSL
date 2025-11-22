#!/usr/bin/env python3
"""
technical_indicators 테이블의 데이터를 indicator_values 테이블로 동기화
"""

import pandas as pd
import json
from sqlalchemy import create_engine, text
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def sync_technical_indicators_to_grafana():
    """technical_indicators 데이터를 indicator_values로 동기화"""
    logger.info("Starting sync from technical_indicators to indicator_values")

    try:
        engine = get_db_connection()

        with engine.connect() as conn:
            # 최신 technical_indicators 데이터 가져오기 (22일부터)
            result = conn.execute(text("""
                SELECT ticker, date, rsi, macd, macd_signal, macd_histogram,
                       stoch_k, stoch_d, ma_20, ma_50, ma_200,
                       bollinger_upper, bollinger_middle, bollinger_lower
                FROM technical_indicators
                WHERE date >= '2025-09-22'
                ORDER BY ticker, date
            """))

            data = result.fetchall()
            logger.info(f"Found {len(data)} technical indicator records to sync")

        # 데이터 동기화
        success_count = 0
        with engine.begin() as conn:
            for row in data:
                ticker = row[0]
                date = row[1]

                try:
                    # 1. SMA (Simple Moving Average) - MA 값들 사용
                    sma_value = {
                        "sma_20": float(row[8]) if row[8] is not None else None,
                        "sma_50": float(row[9]) if row[9] is not None else None,
                        "sma_200": float(row[10]) if row[10] is not None else None,
                        "rsi": float(row[2]) if row[2] is not None else None,  # SMA 레코드에 RSI도 함께 저장 (기존 데이터 구조 유지)
                        "macd": float(row[3]) if row[3] is not None else None,
                        "macd_signal": float(row[4]) if row[4] is not None else None,
                        "macd_hist": float(row[5]) if row[5] is not None else None,
                        "bb_upper": float(row[11]) if row[11] is not None else None,
                        "bb_middle": float(row[12]) if row[12] is not None else None,
                        "bb_lower": float(row[13]) if row[13] is not None else None
                    }

                    conn.execute(text("""
                        INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                        VALUES (:ticker, :date, 1, 'daily', :value, '{"all_basic_indicators": true}')
                        ON CONFLICT (ticker, date, indicator_id, timeframe)
                        DO UPDATE SET value = EXCLUDED.value, parameters = EXCLUDED.parameters
                    """), {
                        'ticker': ticker,
                        'date': date,
                        'value': json.dumps(sma_value)
                    })

                    # 2. RSI
                    if row[2] is not None:
                        conn.execute(text("""
                            INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, 10, 'daily', :value, '{"period": 14}')
                            ON CONFLICT (ticker, date, indicator_id, timeframe)
                            DO UPDATE SET value = EXCLUDED.value
                        """), {
                            'ticker': ticker,
                            'date': date,
                            'value': json.dumps({"rsi": float(row[2])})
                        })

                    # 3. MACD
                    if row[3] is not None:
                        conn.execute(text("""
                            INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, 6, 'daily', :value, '{"fast": 12, "slow": 26, "signal": 9}')
                            ON CONFLICT (ticker, date, indicator_id, timeframe)
                            DO UPDATE SET value = EXCLUDED.value
                        """), {
                            'ticker': ticker,
                            'date': date,
                            'value': json.dumps({
                                "macd": float(row[3]),
                                "macd_signal": float(row[4]) if row[4] is not None else None,
                                "macd_histogram": float(row[5]) if row[5] is not None else None
                            })
                        })

                    # 4. Stochastic
                    if row[6] is not None:
                        conn.execute(text("""
                            INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, 11, 'daily', :value, '{"d_period": 3, "k_period": 14, "smooth_k": 3}')
                            ON CONFLICT (ticker, date, indicator_id, timeframe)
                            DO UPDATE SET value = EXCLUDED.value
                        """), {
                            'ticker': ticker,
                            'date': date,
                            'value': json.dumps({
                                "stoch_k": float(row[6]),
                                "stoch_d": float(row[7]) if row[7] is not None else None
                            })
                        })

                    # 5. Bollinger Bands
                    if row[11] is not None:
                        conn.execute(text("""
                            INSERT INTO indicator_values (ticker, date, indicator_id, timeframe, value, parameters)
                            VALUES (:ticker, :date, 18, 'daily', :value, '{"period": 20, "std_dev": 2}')
                            ON CONFLICT (ticker, date, indicator_id, timeframe)
                            DO UPDATE SET value = EXCLUDED.value
                        """), {
                            'ticker': ticker,
                            'date': date,
                            'value': json.dumps({
                                "bb_upper": float(row[11]),
                                "bb_middle": float(row[12]) if row[12] is not None else None,
                                "bb_lower": float(row[13]) if row[13] is not None else None,
                                "bb_width": float(row[11]) - float(row[13]) if (row[11] is not None and row[13] is not None) else None,
                                "bb_percent": ((float(row[12]) - float(row[13])) / (float(row[11]) - float(row[13]))) if (row[11] is not None and row[12] is not None and row[13] is not None and row[11] != row[13]) else None
                            })
                        })

                    success_count += 1

                    if success_count % 5 == 0:
                        logger.info(f"Synced {success_count} records...")

                except Exception as e:
                    logger.error(f"Error syncing {ticker} {date}: {e}")
                    continue

        logger.info(f"Sync completed: {success_count} records processed")

        # 동기화 결과 확인
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ticker, MAX(date) as latest_date, COUNT(*) as count
                FROM indicator_values
                WHERE ticker IN ('005930', '000660', '035420', '051910', '006400')
                GROUP BY ticker
                ORDER BY ticker
            """))

            logger.info("Current indicator_values status:")
            for row in result:
                logger.info(f"  {row[0]}: latest={row[1]}, count={row[2]}")

        return success_count

    except Exception as e:
        logger.error(f"Sync failed: {e}")
        import traceback
        traceback.print_exc()
        return 0

if __name__ == "__main__":
    sync_technical_indicators_to_grafana()