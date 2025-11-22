#!/usr/bin/env python
"""
특정 날짜부터 지표를 재계산하는 스크립트 (개발용)
추석 연휴(2025-10-03 ~ 2025-10-09)를 고려하여 실제 거래일만 처리합니다.
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
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# 추석 연휴 (거래 없는 날)
HOLIDAY_DATES = [
    '2025-10-03', '2025-10-04', '2025-10-05',
    '2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09'
]

def get_db_connection():
    """데이터베이스 연결 생성"""
    # Docker 컨테이너 내부에서는 postgres 호스트 사용
    # 호스트에서 실행 시에는 localhost:5435 사용
    import os
    if os.path.exists('/.dockerenv'):
        db_url = f"postgresql://admin:admin123@postgres:5432/stocktrading"
    else:
        db_url = f"postgresql://admin:admin123@localhost:5435/stocktrading"
    engine = create_engine(
        db_url,
        pool_pre_ping=True,
        pool_recycle=3600
    )
    return engine

def calculate_rsi(prices, period=14):
    """RSI 계산"""
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

def get_trading_dates(start_date, end_date, engine):
    """실제 거래가 있었던 날짜 목록 가져오기"""
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT date
            FROM stock_prices
            WHERE date >= :start_date
              AND date <= :end_date
            ORDER BY date
        """), {'start_date': start_date, 'end_date': end_date})

        dates = [row.date for row in result]

    logger.info(f"거래일 조회: {len(dates)}일")
    logger.info(f"기간: {dates[0] if dates else 'N/A'} ~ {dates[-1] if dates else 'N/A'}")

    return dates

def calculate_indicators_for_date(engine, ticker, company_name, target_date):
    """특정 종목의 특정 날짜 지표 계산"""
    try:
        with engine.connect() as conn:
            # 해당 종목의 과거 데이터 가져오기
            price_data = pd.read_sql(text("""
                SELECT date, open_price, high_price, low_price, close_price, volume
                FROM stock_prices
                WHERE ticker = :ticker
                  AND date <= :target_date
                ORDER BY date ASC
            """), conn, params={'ticker': ticker, 'target_date': target_date})

            if len(price_data) < 20:
                return 0, "데이터 부족"

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

            macd_result = calculate_macd(price_data['close'])
            price_data['macd'] = macd_result[0]
            price_data['macd_signal'] = macd_result[1]
            price_data['macd_histogram'] = macd_result[2]

            bb_result = calculate_bollinger_bands(price_data['close'])
            price_data['bb_upper'] = bb_result[0]
            price_data['bb_middle'] = bb_result[1]
            price_data['bb_lower'] = bb_result[2]

            stoch_result = calculate_stochastic(
                price_data['high'], price_data['low'], price_data['close']
            )
            price_data['stoch_k'] = stoch_result[0]
            price_data['stoch_d'] = stoch_result[1]

            # 대상 날짜의 데이터만 추출
            target_row = price_data[price_data['date'] == target_date]

            if len(target_row) == 0 or pd.isna(target_row.iloc[0]['ma_20']):
                return 0, "지표 계산 불가"

            row = target_row.iloc[0]

            # Helper function
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

            return 1, "성공"

    except Exception as e:
        return 0, f"오류: {str(e)}"

def process_chunk(engine, tickers, target_dates, chunk_id, total_chunks):
    """Chunk 단위로 처리"""
    logger.info("="*80)
    logger.info(f"Chunk {chunk_id}/{total_chunks} 처리 시작")
    logger.info(f"종목 수: {len(tickers)}개")
    logger.info(f"날짜 수: {len(target_dates)}일")
    logger.info("="*80)

    total_saved = 0
    successful_stocks = 0
    failed_stocks = 0

    for i, stock_info in enumerate(tickers, 1):
        ticker = stock_info['ticker']
        company_name = stock_info['company_name']

        stock_saved = 0

        try:
            for target_date in target_dates:
                saved, msg = calculate_indicators_for_date(
                    engine, ticker, company_name, target_date
                )
                stock_saved += saved

            total_saved += stock_saved

            if stock_saved > 0:
                successful_stocks += 1
                logger.info(f"[{i}/{len(tickers)}] ✅ {ticker} ({company_name}): {stock_saved}개 저장")
            else:
                failed_stocks += 1
                logger.warning(f"[{i}/{len(tickers)}] ⚠️  {ticker} ({company_name}): 저장 실패")

            # 10개마다 진행 상황 출력
            if i % 10 == 0:
                progress = (i / len(tickers)) * 100
                logger.info(f"--- 진행률: {progress:.1f}% ({i}/{len(tickers)}) ---")

        except Exception as e:
            failed_stocks += 1
            logger.error(f"[{i}/{len(tickers)}] ❌ {ticker} ({company_name}): {e}")

    logger.info("="*80)
    logger.info(f"Chunk {chunk_id}/{total_chunks} 처리 완료")
    logger.info(f"성공: {successful_stocks}/{len(tickers)}")
    logger.info(f"실패: {failed_stocks}/{len(tickers)}")
    logger.info(f"저장된 지표: {total_saved:,}개")
    logger.info("="*80)

    return total_saved, successful_stocks, failed_stocks

def main():
    """메인 실행 함수"""
    start_date = '2025-10-13'
    end_date = '2025-10-15'
    chunk_size = 50  # 한 번에 50개 종목씩 처리

    logger.info("="*80)
    logger.info("지표 재계산 시작")
    logger.info(f"시작 날짜: {start_date}")
    logger.info(f"종료 날짜: {end_date}")
    logger.info(f"Chunk 크기: {chunk_size}개")
    logger.info("="*80)

    engine = get_db_connection()

    # 1. 실제 거래일 가져오기
    logger.info("\n[1/4] 실제 거래일 조회 중...")
    trading_dates = get_trading_dates(start_date, end_date, engine)

    if not trading_dates:
        logger.error("거래일이 없습니다!")
        return

    # 2. 대상 종목 가져오기
    logger.info("\n[2/4] 대상 종목 조회 중...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT DISTINCT sp.ticker, s.company_name
            FROM stock_prices sp
            JOIN stocks s ON sp.ticker = s.ticker
            WHERE s.currency = 'KRW'
              AND s.is_active = true
              AND sp.date >= :start_date
            ORDER BY sp.ticker
        """), {'start_date': start_date})

        all_tickers = [
            {'ticker': row.ticker, 'company_name': row.company_name}
            for row in result
        ]

    total_tickers = len(all_tickers)
    logger.info(f"대상 종목: {total_tickers}개")

    if total_tickers == 0:
        logger.error("대상 종목이 없습니다!")
        return

    # 3. Chunk로 분할
    logger.info("\n[3/4] Chunk 분할 중...")
    chunks = []
    for i in range(0, total_tickers, chunk_size):
        chunks.append(all_tickers[i:i+chunk_size])

    total_chunks = len(chunks)
    logger.info(f"총 {total_chunks}개 Chunk로 분할")

    # 4. 각 Chunk 처리
    logger.info("\n[4/4] 지표 계산 시작...")
    logger.info(f"총 처리량: {total_tickers}개 종목 × {len(trading_dates)}일 = {total_tickers * len(trading_dates):,}개")

    grand_total_saved = 0
    grand_successful = 0
    grand_failed = 0

    start_time = datetime.now()

    for chunk_id, chunk_tickers in enumerate(chunks, 1):
        chunk_saved, chunk_success, chunk_failed = process_chunk(
            engine, chunk_tickers, trading_dates, chunk_id, total_chunks
        )

        grand_total_saved += chunk_saved
        grand_successful += chunk_success
        grand_failed += chunk_failed

        # 예상 남은 시간 계산
        elapsed = (datetime.now() - start_time).total_seconds()
        avg_time_per_chunk = elapsed / chunk_id
        remaining_chunks = total_chunks - chunk_id
        eta_seconds = avg_time_per_chunk * remaining_chunks
        eta = timedelta(seconds=int(eta_seconds))

        logger.info(f"\n📊 전체 진행률: {chunk_id}/{total_chunks} ({chunk_id/total_chunks*100:.1f}%)")
        logger.info(f"⏱️  예상 남은 시간: {eta}")
        logger.info("")

    # 최종 결과
    end_time = datetime.now()
    total_time = end_time - start_time

    logger.info("\n" + "="*80)
    logger.info("지표 재계산 완료!")
    logger.info("="*80)
    logger.info(f"처리 기간: {start_date} ~ {end_date}")
    logger.info(f"거래일: {len(trading_dates)}일")
    logger.info(f"대상 종목: {total_tickers}개")
    logger.info(f"성공: {grand_successful}개")
    logger.info(f"실패: {grand_failed}개")
    logger.info(f"저장된 지표: {grand_total_saved:,}개")
    logger.info(f"총 소요 시간: {total_time}")
    logger.info("="*80)

    # 결과 검증
    logger.info("\n[검증] 저장된 데이터 확인 중...")
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT
                COUNT(DISTINCT ticker) as ticker_count,
                COUNT(DISTINCT date) as date_count,
                COUNT(*) as total_count,
                MIN(date) as min_date,
                MAX(date) as max_date
            FROM technical_indicators
            WHERE date >= :start_date
        """), {'start_date': start_date})

        row = result.fetchone()

        logger.info(f"DB 저장 확인:")
        logger.info(f"  - 종목 수: {row.ticker_count}개")
        logger.info(f"  - 날짜 수: {row.date_count}일")
        logger.info(f"  - 총 레코드: {row.total_count:,}개")
        logger.info(f"  - 기간: {row.min_date} ~ {row.max_date}")

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
