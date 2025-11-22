#!/usr/bin/env python
"""
누락된 기술적 지표 재계산 스크립트
주가 데이터는 있지만 기술적 지표가 누락된 종목들에 대해 전체 기간 지표를 계산합니다.
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from sqlalchemy import create_engine, text

# 프로젝트 경로 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import settings

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_db_connection():
    """데이터베이스 연결 생성"""
    engine = create_engine(settings.DATABASE_URL)
    return engine

def calculate_rsi(prices, period=14):
    """RSI (Relative Strength Index) 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices, fast=12, slow=26, signal=9):
    """MACD 계산"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd_line = ema_fast - ema_slow
    macd_signal = macd_line.ewm(span=signal).mean()
    macd_histogram = macd_line - macd_signal
    return macd_line, macd_signal, macd_histogram

def calculate_bollinger_bands(prices, period=20, std_dev=2):
    """볼린저 밴드 계산"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std_dev * std)
    lower_band = sma - (std_dev * std)
    return upper_band, sma, lower_band

def calculate_stochastic(high, low, close, period=14):
    """스토캐스틱 오실레이터 계산"""
    lowest_low = low.rolling(window=period).min()
    highest_high = high.rolling(window=period).max()
    k_percent = 100 * ((close - lowest_low) / (highest_high - lowest_low))
    d_percent = k_percent.rolling(3).mean()
    return k_percent, d_percent

def get_stocks_with_missing_indicators():
    """기술적 지표가 누락된 종목 목록 가져오기"""
    engine = get_db_connection()

    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                sp.ticker,
                s.company_name,
                COUNT(DISTINCT sp.date) as price_days,
                COALESCE(COUNT(DISTINCT ti.date), 0) as indicator_days,
                (COUNT(DISTINCT sp.date) - COALESCE(COUNT(DISTINCT ti.date), 0)) as missing_days,
                MIN(sp.date) as start_date,
                MAX(sp.date) as end_date
            FROM stock_prices sp
            LEFT JOIN stocks s ON sp.ticker = s.ticker
            LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
            WHERE s.currency = 'KRW' AND s.is_active = true
            GROUP BY sp.ticker, s.company_name
            HAVING COUNT(DISTINCT sp.date) > COALESCE(COUNT(DISTINCT ti.date), 0)
            ORDER BY missing_days DESC
        """))

        stocks = []
        for row in result:
            stocks.append({
                'ticker': row.ticker,
                'company_name': row.company_name,
                'price_days': row.price_days,
                'indicator_days': row.indicator_days,
                'missing_days': row.missing_days,
                'start_date': row.start_date,
                'end_date': row.end_date
            })

        return stocks

def calculate_indicators_for_stock(ticker, company_name, start_date, end_date):
    """특정 종목의 전체 기간에 대해 기술적 지표 계산"""
    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 전체 기간 데이터 가져오기
            price_data = pd.read_sql(text("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                ORDER BY date ASC
            """), conn, params={'ticker': ticker})

            if len(price_data) < 20:
                logger.warning(f"{ticker} ({company_name}): 데이터 부족 ({len(price_data)}일)")
                return 0

            # 데이터 처리
            price_data['close'] = pd.to_numeric(price_data['close_price'])
            price_data['high'] = pd.to_numeric(price_data['high_price'])
            price_data['low'] = pd.to_numeric(price_data['low_price'])
            price_data['volume'] = pd.to_numeric(price_data['volume'])

            # 기술적 지표 계산
            price_data['ma_20'] = price_data['close'].rolling(20).mean()
            price_data['ma_50'] = price_data['close'].rolling(50).mean()
            price_data['ma_200'] = price_data['close'].rolling(200).mean()
            price_data['rsi'] = calculate_rsi(price_data['close'])
            price_data['macd'], price_data['macd_signal'], price_data['macd_histogram'] = calculate_macd(price_data['close'])
            price_data['bb_upper'], price_data['bb_middle'], price_data['bb_lower'] = calculate_bollinger_bands(price_data['close'])
            price_data['stoch_k'], price_data['stoch_d'] = calculate_stochastic(
                price_data['high'], price_data['low'], price_data['close']
            )

            # NaN이 아닌 데이터만 저장 (최소 20일 이후부터)
            valid_data = price_data[price_data['ma_20'].notna()].copy()

            if len(valid_data) == 0:
                logger.warning(f"{ticker} ({company_name}): 유효한 지표 데이터 없음")
                return 0

            # 데이터베이스에 저장
            saved_count = 0
            with engine.begin() as save_conn:
                for _, row in valid_data.iterrows():
                    # Helper function to safely convert values (handles inf and NaN)
                    def safe_float(val):
                        if pd.isna(val) or np.isinf(val):
                            return None
                        return float(val)

                    save_conn.execute(text("""
                        INSERT INTO technical_indicators (
                            ticker, date, rsi, macd, macd_signal, macd_histogram,
                            stoch_k, stoch_d, ma_20, ma_50, ma_200,
                            bollinger_upper, bollinger_middle, bollinger_lower,
                            created_at
                        ) VALUES (
                            :ticker, :date, :rsi, :macd, :macd_signal, :macd_histogram,
                            :stoch_k, :stoch_d, :ma_20, :ma_50, :ma_200,
                            :bb_upper, :bb_middle, :bb_lower, NOW()
                        ) ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            macd_histogram = EXCLUDED.macd_histogram,
                            stoch_k = EXCLUDED.stoch_k,
                            stoch_d = EXCLUDED.stoch_d,
                            ma_20 = EXCLUDED.ma_20,
                            ma_50 = EXCLUDED.ma_50,
                            ma_200 = EXCLUDED.ma_200,
                            bollinger_upper = EXCLUDED.bollinger_upper,
                            bollinger_middle = EXCLUDED.bollinger_middle,
                            bollinger_lower = EXCLUDED.bollinger_lower,
                            created_at = NOW()
                    """), {
                        'ticker': ticker,
                        'date': row['date'],
                        'rsi': safe_float(row['rsi']),
                        'macd': safe_float(row['macd']),
                        'macd_signal': safe_float(row['macd_signal']),
                        'macd_histogram': safe_float(row['macd_histogram']),
                        'stoch_k': safe_float(row['stoch_k']),
                        'stoch_d': safe_float(row['stoch_d']),
                        'ma_20': safe_float(row['ma_20']),
                        'ma_50': safe_float(row['ma_50']),
                        'ma_200': safe_float(row['ma_200']),
                        'bb_upper': safe_float(row['bb_upper']),
                        'bb_middle': safe_float(row['bb_middle']),
                        'bb_lower': safe_float(row['bb_lower'])
                    })
                    saved_count += 1

            return saved_count

    except Exception as e:
        logger.error(f"{ticker} ({company_name}) 처리 중 오류: {e}")
        return 0

def main():
    """메인 실행 함수"""
    logger.info("=" * 80)
    logger.info("누락된 기술적 지표 재계산 시작")
    logger.info("=" * 80)

    # 누락된 종목 목록 가져오기
    stocks = get_stocks_with_missing_indicators()
    total_stocks = len(stocks)

    logger.info(f"\n총 {total_stocks}개 종목에서 기술적 지표 누락 발견")
    logger.info("-" * 80)

    if total_stocks == 0:
        logger.info("모든 종목의 기술적 지표가 최신 상태입니다.")
        return

    # 각 종목에 대해 지표 계산
    total_indicators_saved = 0
    successful_stocks = 0
    failed_stocks = 0

    for i, stock in enumerate(stocks, 1):
        ticker = stock['ticker']
        company_name = stock['company_name']
        missing_days = stock['missing_days']

        logger.info(f"\n[{i}/{total_stocks}] {ticker} ({company_name})")
        logger.info(f"  - 주가 데이터: {stock['price_days']}일")
        logger.info(f"  - 지표 데이터: {stock['indicator_days']}일")
        logger.info(f"  - 누락: {missing_days}일")
        logger.info(f"  - 기간: {stock['start_date']} ~ {stock['end_date']}")

        saved_count = calculate_indicators_for_stock(
            ticker, company_name,
            stock['start_date'], stock['end_date']
        )

        if saved_count > 0:
            total_indicators_saved += saved_count
            successful_stocks += 1
            logger.info(f"  ✓ {saved_count}개 지표 저장 완료")
        else:
            failed_stocks += 1
            logger.info(f"  ✗ 실패")

        # 진행률 표시
        progress = (i / total_stocks) * 100
        logger.info(f"  진행률: {progress:.1f}% ({i}/{total_stocks})")

    # 최종 결과
    logger.info("\n" + "=" * 80)
    logger.info("기술적 지표 재계산 완료")
    logger.info("=" * 80)
    logger.info(f"총 처리 종목: {total_stocks}")
    logger.info(f"성공: {successful_stocks}")
    logger.info(f"실패: {failed_stocks}")
    logger.info(f"저장된 지표 수: {total_indicators_saved:,}")
    logger.info("=" * 80)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("\n사용자에 의해 중단되었습니다.")
        sys.exit(1)
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
