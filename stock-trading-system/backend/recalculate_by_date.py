#!/usr/bin/env python
"""
특정 날짜의 기술적 지표 계산 스크립트
"""

import os
import sys
import logging
import pandas as pd
import numpy as np
from datetime import datetime
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

def calculate_indicators_for_date(target_date):
    """특정 날짜의 모든 종목에 대해 기술적 지표 계산"""
    engine = get_db_connection()

    logger.info(f"\n{'='*80}")
    logger.info(f"{target_date} 기술적 지표 계산 시작")
    logger.info(f"{'='*80}\n")

    try:
        with engine.connect() as conn:
            # 해당 날짜에 주가 데이터가 있는 종목 목록 가져오기
            result = conn.execute(text("""
                SELECT DISTINCT sp.ticker, s.company_name
                FROM stock_prices sp
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :target_date
                  AND s.currency = 'KRW'
                  AND s.is_active = true
                ORDER BY sp.ticker
            """), {'target_date': target_date})

            stocks = [{'ticker': row.ticker, 'company_name': row.company_name} for row in result]

        total_stocks = len(stocks)
        logger.info(f"대상 종목 수: {total_stocks}개\n")

        if total_stocks == 0:
            logger.warning(f"{target_date}에 주가 데이터가 없습니다.")
            return 0, 0, 0

        # 각 종목에 대해 지표 계산
        saved_count = 0
        failed_count = 0

        for i, stock in enumerate(stocks, 1):
            ticker = stock['ticker']
            company_name = stock['company_name']

            try:
                with engine.connect() as conn:
                    # 해당 종목의 과거 데이터 가져오기 (최대 200일 + 여유분)
                    price_data = pd.read_sql(text("""
                        SELECT date, open_price, high_price, low_price, close_price, volume
                        FROM stock_prices
                        WHERE ticker = :ticker
                          AND date <= :target_date
                        ORDER BY date ASC
                    """), conn, params={'ticker': ticker, 'target_date': target_date})

                    if len(price_data) < 20:
                        logger.debug(f"[{i}/{total_stocks}] {ticker}: 데이터 부족 ({len(price_data)}일)")
                        failed_count += 1
                        continue

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

                    # 대상 날짜의 데이터만 추출
                    target_row = price_data[price_data['date'] == target_date]

                    if len(target_row) == 0 or pd.isna(target_row.iloc[0]['ma_20']):
                        logger.debug(f"[{i}/{total_stocks}] {ticker}: 지표 계산 불가")
                        failed_count += 1
                        continue

                    row = target_row.iloc[0]

                    # Helper function to safely convert values
                    def safe_float(val):
                        if pd.isna(val) or np.isinf(val):
                            return None
                        return float(val)

                    # 데이터베이스에 저장
                    with engine.begin() as save_conn:
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
                            'date': target_date,
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

                    # 진행 상황 출력 (100개마다)
                    if i % 100 == 0:
                        progress = (i / total_stocks) * 100
                        logger.info(f"진행률: {progress:.1f}% ({i}/{total_stocks}) - 성공: {saved_count}, 실패: {failed_count}")

            except Exception as e:
                logger.error(f"[{i}/{total_stocks}] {ticker} ({company_name}) 오류: {e}")
                failed_count += 1

        # 최종 결과
        logger.info(f"\n{'='*80}")
        logger.info(f"{target_date} 기술적 지표 계산 완료")
        logger.info(f"{'='*80}")
        logger.info(f"대상 종목: {total_stocks}개")
        logger.info(f"성공: {saved_count}개")
        logger.info(f"실패: {failed_count}개")
        logger.info(f"성공률: {(saved_count/total_stocks*100):.1f}%")
        logger.info(f"{'='*80}\n")

        return total_stocks, saved_count, failed_count

    except Exception as e:
        logger.error(f"처리 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()
        return 0, 0, 0

def main():
    """메인 실행 함수"""
    if len(sys.argv) < 2:
        logger.error("사용법: python recalculate_by_date.py YYYY-MM-DD")
        sys.exit(1)

    target_date = sys.argv[1]

    try:
        # 날짜 형식 검증
        datetime.strptime(target_date, '%Y-%m-%d')
    except ValueError:
        logger.error(f"잘못된 날짜 형식: {target_date} (YYYY-MM-DD 형식으로 입력하세요)")
        sys.exit(1)

    total_stocks, saved_count, failed_count = calculate_indicators_for_date(target_date)

    if saved_count > 0:
        logger.info(f"✓ {target_date} 지표 계산 성공")
    else:
        logger.warning(f"✗ {target_date} 지표 계산 실패 또는 데이터 없음")

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
