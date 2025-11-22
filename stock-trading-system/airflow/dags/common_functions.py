"""
공통 유틸 함수 및 데이터베이스 연동
DAG에서 공통으로 사용되는 함수들을 정의합니다.
"""

import logging
from datetime import datetime, date
from typing import List, Optional, Dict, Tuple
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.pool import NullPool
import pandas as pd
import sys
import os

# Add backend path for imports
sys.path.append('/app')

logger = logging.getLogger(__name__)

# ========================================
# 데이터베이스 연결 설정
# ========================================

def get_database_url(host: str = "192.168.219.103", port: int = 5432,
                     db: str = "stocktrading", user: str = "admin",
                     password: str = "admin123") -> str:
    """데이터베이스 URL 생성"""
    return f"postgresql://{user}:{password}@{host}:{port}/{db}"

def get_db_engine(database_url: Optional[str] = None):
    """데이터베이스 엔진 생성"""
    if database_url is None:
        database_url = get_database_url()

    engine = create_engine(
        database_url,
        connect_args={"options": "-c client_encoding=utf8"},
        poolclass=NullPool  # 연결 풀 미사용 (Airflow 직렬화 문제 방지)
    )
    return engine

# ========================================
# 날짜 관련 함수
# ========================================

def get_execution_date(context) -> date:
    """execution_date에서 date 객체 추출"""
    execution_date = context['execution_date']
    if hasattr(execution_date, 'date'):
        return execution_date.date()
    return execution_date

def is_trading_day(target_date: date) -> bool:
    """거래일 여부 확인 (평일: True, 주말: False)"""
    # 월(0) ~ 금(4)이면 거래일
    return target_date.weekday() < 5

# ========================================
# 데이터 수집 함수
# ========================================

def fetch_stock_prices_api(target_date: date, engine=None) -> pd.DataFrame:
    """
    주식 API에서 주가 데이터 수집 (KOSPI + KOSDAQ)

    방법 1: 마켓별 별도 수집으로 2,700+ 종목 모두 수집 가능

    Args:
        target_date: 수집 대상 날짜
        engine: 데이터베이스 엔진

    Returns:
        주가 데이터 DataFrame
    """
    try:
        from pykrx import stock as pykrx_stock
        import psycopg2

        if engine is None:
            engine = get_db_engine()

        if not is_trading_day(target_date):
            logger.warning(f"{target_date} is not a trading day (weekend or holiday)")
            return pd.DataFrame()

        date_str = target_date.strftime("%Y%m%d")

        # Get valid tickers from database
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()
        cursor.execute("SELECT ticker FROM stocks ORDER BY ticker")
        valid_tickers = set([row[0] for row in cursor.fetchall()])
        cursor.close()
        raw_conn.close()
        logger.info(f"Valid tickers in database: {len(valid_tickers)}")

        # ========================================
        # 방법 1: 마켓별 별도 수집 (권장)
        # ========================================
        all_prices = []

        # 1단계: KOSPI 종목 수집
        try:
            kospi_tickers = pykrx_stock.get_market_ticker_list(market="KOSPI", date=date_str)
            logger.info(f"Found {len(kospi_tickers)} KOSPI tickers for {target_date}")

            for ticker in kospi_tickers:
                if ticker not in valid_tickers:
                    continue
                try:
                    df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                    if not df.empty:
                        df['ticker'] = ticker
                        df['date'] = target_date
                        all_prices.append(df)
                except Exception as e:
                    logger.debug(f"Failed to fetch KOSPI {ticker}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching KOSPI tickers: {str(e)}")

        # 2단계: KOSDAQ 종목 수집
        try:
            kosdaq_tickers = pykrx_stock.get_market_ticker_list(market="KOSDAQ", date=date_str)
            logger.info(f"Found {len(kosdaq_tickers)} KOSDAQ tickers for {target_date}")

            for ticker in kosdaq_tickers:
                if ticker not in valid_tickers:
                    continue
                try:
                    df = pykrx_stock.get_market_ohlcv(date_str, date_str, ticker)
                    if not df.empty:
                        df['ticker'] = ticker
                        df['date'] = target_date
                        all_prices.append(df)
                except Exception as e:
                    logger.debug(f"Failed to fetch KOSDAQ {ticker}: {str(e)}")
                    continue
        except Exception as e:
            logger.error(f"Error fetching KOSDAQ tickers: {str(e)}")

        if all_prices:
            result_df = pd.concat(all_prices, ignore_index=True)
            logger.info(f"Collected {len(result_df)} price records for {target_date}")
            return result_df
        else:
            logger.warning(f"No price data collected for {target_date}")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error fetching stock prices: {str(e)}")
        raise

def fetch_market_indices_api(target_date: date) -> pd.DataFrame:
    """
    시장 지수 데이터 수집 (KOSPI, KOSDAQ)

    Args:
        target_date: 수집 대상 날짜

    Returns:
        시장 지수 데이터 DataFrame
    """
    try:
        from pykrx import stock as pykrx_stock

        if not is_trading_day(target_date):
            logger.warning(f"{target_date} is not a trading day")
            return pd.DataFrame()

        date_str = target_date.strftime("%Y%m%d")
        indices_data = []

        # KOSPI 지수 조회 (코드: 1001)
        try:
            kospi = pykrx_stock.get_index_ohlcv(date_str, date_str, "1001")
            if not kospi.empty:
                kospi['index_name'] = "KOSPI"
                kospi['date'] = target_date
                indices_data.append(kospi)
        except Exception as e:
            logger.warning(f"Failed to fetch KOSPI: {str(e)}")

        # KOSDAQ 지수 조회 (코드: 1002)
        try:
            kosdaq = pykrx_stock.get_index_ohlcv(date_str, date_str, "1002")
            if not kosdaq.empty:
                kosdaq['index_name'] = "KOSDAQ"
                kosdaq['date'] = target_date
                indices_data.append(kosdaq)
        except Exception as e:
            logger.warning(f"Failed to fetch KOSDAQ: {str(e)}")

        if indices_data:
            result_df = pd.concat(indices_data, ignore_index=True)
            logger.info(f"Collected {len(result_df)} index records for {target_date}")
            return result_df
        else:
            logger.warning(f"No index data collected for {target_date}")
            return pd.DataFrame()

    except Exception as e:
        logger.error(f"Error fetching market indices: {str(e)}")
        raise

# ========================================
# 데이터베이스 저장 함수
# ========================================

def save_stock_prices(prices_df: pd.DataFrame, target_date: date, engine=None) -> int:
    """
    주가 데이터를 데이터베이스에 저장 (UPSERT 방식 - TimescaleDB 호환)

    Args:
        prices_df: 주가 DataFrame
        target_date: 저장 대상 날짜
        engine: 데이터베이스 엔진

    Returns:
        저장된 레코드 수
    """
    if engine is None:
        engine = get_db_engine()

    if prices_df.empty:
        logger.warning(f"No stock prices to save for {target_date}")
        return 0

    try:
        # DataFrame 정규화
        normalized_df = pd.DataFrame({
            'ticker': prices_df['ticker'],
            'date': target_date,
            'open_price': prices_df['시가'].astype(float),
            'high_price': prices_df['고가'].astype(float),
            'low_price': prices_df['저가'].astype(float),
            'close_price': prices_df['종가'].astype(float),
            'volume': prices_df['거래량'].astype(int),
            'created_at': datetime.now()
        })

        if len(normalized_df) == 0:
            logger.info(f"No data to save for {target_date} (empty DataFrame)")
            return 0

        # UPSERT 방식으로 데이터 저장 (DELETE 대신 ON CONFLICT 사용)
        # 이 방식은 TimescaleDB의 dimension_slice 메타데이터 충돌 문제를 회피
        raw_conn = engine.raw_connection()
        cursor = raw_conn.cursor()

        try:
            # 데이터 준비 (UPSERT)
            insert_data = [
                (str(row['ticker']), row['date'],
                 float(row['open_price']), float(row['high_price']),
                 float(row['low_price']), float(row['close_price']),
                 int(row['volume']), row['created_at'])
                for _, row in normalized_df.iterrows()
            ]

            # PostgreSQL UPSERT 문법 (ON CONFLICT DO UPDATE)
            cursor.executemany("""
                INSERT INTO stock_prices
                (ticker, date, open_price, high_price, low_price, close_price, volume, created_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume,
                    created_at = EXCLUDED.created_at
            """, insert_data)

            raw_conn.commit()
            logger.info(f"Saved {len(normalized_df)} stock prices for {target_date} using UPSERT")
            return len(normalized_df)

        except Exception as e:
            raw_conn.rollback()
            logger.error(f"Error saving stock prices: {str(e)}")
            raise
        finally:
            cursor.close()
            raw_conn.close()

    except Exception as e:
        logger.error(f"Error saving stock prices: {str(e)}")
        raise

def save_market_indices(indices_df: pd.DataFrame, target_date: date, engine=None) -> int:
    """
    시장 지수를 데이터베이스에 저장

    Args:
        indices_df: 시장 지수 DataFrame
        target_date: 저장 대상 날짜
        engine: 데이터베이스 엔진

    Returns:
        저장된 레코드 수
    """
    if engine is None:
        engine = get_db_engine()

    if indices_df.empty:
        logger.warning(f"No market indices to save for {target_date}")
        return 0

    try:
        # market_indices 테이블 스키마에 맞게 정규화
        # (id, index_name, date, index_value, stock_count, total_volume, total_market_cap, created_at)
        normalized_df = pd.DataFrame({
            'date': target_date,
            'index_name': indices_df['index_name'],
            'index_value': indices_df['종가'].astype(float),  # Close price를 index_value로
            'total_volume': indices_df['거래량'].astype(int),
            'created_at': datetime.now()
        })

        with engine.begin() as conn:
            for _, row in normalized_df.iterrows():
                conn.execute(text("""
                    INSERT INTO market_indices
                    (date, index_name, index_value, total_volume, created_at)
                    VALUES (:date, :index_name, :index_value, :total_volume, :created_at)
                    ON CONFLICT (date, index_name) DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        total_volume = EXCLUDED.total_volume
                """), {
                    'date': row['date'],
                    'index_name': row['index_name'],
                    'index_value': row['index_value'],
                    'total_volume': row['total_volume'],
                    'created_at': row['created_at']
                })

        saved_count = len(normalized_df)
        logger.info(f"Saved {saved_count} market indices for {target_date}")
        return saved_count

    except Exception as e:
        logger.error(f"Error saving market indices: {str(e)}")
        raise

# ========================================
# 데이터 조회 함수
# ========================================

def get_max_price_date(engine=None) -> Optional[date]:
    """stock_prices 테이블의 최신 날짜 조회"""
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(date) FROM stock_prices"))
            max_date = result.scalar()
            return max_date
    except Exception as e:
        logger.error(f"Error getting max price date: {str(e)}")
        return None

def get_max_indicator_date(engine=None) -> Optional[date]:
    """technical_indicators 테이블의 최신 날짜 조회"""
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT MAX(date) FROM technical_indicators"))
            max_date = result.scalar()
            return max_date
    except Exception as e:
        logger.error(f"Error getting max indicator date: {str(e)}")
        return None

def get_all_tickers(engine=None) -> List[str]:
    """모든 활성 티커 조회"""
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT ticker FROM stock_prices
                ORDER BY ticker
            """))
            return [row[0] for row in result]
    except Exception as e:
        logger.error(f"Error getting tickers: {str(e)}")
        return []

def get_stock_data(target_date: date, engine=None) -> pd.DataFrame:
    """특정 날짜의 주가 데이터 조회"""
    if engine is None:
        engine = get_db_engine()

    try:
        query = """
            SELECT ticker, date, open_price, high_price, low_price, close_price, volume
            FROM stock_prices
            WHERE date = :date
            ORDER BY ticker
        """
        df = pd.read_sql(query, engine, params={'date': target_date})
        logger.info(f"Retrieved {len(df)} stock records for {target_date}")
        return df
    except Exception as e:
        logger.error(f"Error getting stock data: {str(e)}")
        return pd.DataFrame()

# ========================================
# 기술적 지표 계산 함수
# ========================================

def calculate_rsi(prices: pd.Series, period: int = 14) -> pd.Series:
    """RSI (Relative Strength Index) 계산"""
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def calculate_macd(prices: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9) -> Tuple[pd.Series, pd.Series]:
    """MACD 계산"""
    ema_fast = prices.ewm(span=fast).mean()
    ema_slow = prices.ewm(span=slow).mean()
    macd = ema_fast - ema_slow
    signal_line = macd.ewm(span=signal).mean()
    return macd, signal_line

def calculate_sma(prices: pd.Series, period: int = 20) -> pd.Series:
    """SMA (Simple Moving Average) 계산"""
    return prices.rolling(window=period).mean()

def calculate_bollinger_bands(prices: pd.Series, period: int = 20, std_dev: int = 2) -> Tuple[pd.Series, pd.Series]:
    """Bollinger Bands 계산"""
    sma = prices.rolling(window=period).mean()
    std = prices.rolling(window=period).std()
    upper_band = sma + (std * std_dev)
    lower_band = sma - (std * std_dev)
    return upper_band, lower_band

def calculate_indicators_for_ticker(ticker: str, target_date: date, engine=None) -> Optional[Dict]:
    """특정 티커의 기술적 지표 계산"""
    if engine is None:
        engine = get_db_engine()

    try:
        # 해당 티커의 최근 60일 데이터 조회
        query = text("""
            SELECT date, close_price
            FROM stock_prices
            WHERE ticker = :ticker
            AND date <= :target_date
            ORDER BY date DESC
            LIMIT 60
        """)

        df = pd.read_sql(query, engine, params={'ticker': ticker, 'target_date': target_date})

        if df.empty or len(df) < 20:
            logger.warning(f"Insufficient data for {ticker} on {target_date}")
            return None

        df = df.sort_values('date')
        prices = df['close_price']

        # 지표 계산
        rsi = calculate_rsi(prices)
        macd, signal = calculate_macd(prices)
        sma_20 = calculate_sma(prices, 20)
        bb_upper, bb_lower = calculate_bollinger_bands(prices)

        # 가장 최신 값 추출
        indicators = {
            'ticker': ticker,
            'date': target_date,
            'rsi': float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
            'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
            'macd_signal': float(signal.iloc[-1]) if pd.notna(signal.iloc[-1]) else None,
            'sma_20': float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None,
            'bb_upper': float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None,
            'bb_lower': float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None,
        }

        return indicators

    except Exception as e:
        logger.error(f"Error calculating indicators for {ticker}: {str(e)}")
        return None

# ========================================
# 데이터베이스 저장 함수 (지표)
# ========================================

def save_technical_indicators(indicators_list: List[Dict], engine=None) -> int:
    """기술적 지표를 데이터베이스에 저장"""
    if engine is None:
        engine = get_db_engine()

    if not indicators_list:
        logger.warning("No indicators to save")
        return 0

    try:
        with engine.begin() as conn:
            for ind in indicators_list:
                conn.execute(text("""
                    INSERT INTO technical_indicators
                    (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, ma_200, bollinger_upper, bollinger_lower, created_at)
                    VALUES (:ticker, :date, :rsi, :macd, :macd_signal, :ma_20, :ma_50, :ma_200, :bollinger_upper, :bollinger_lower, :created_at)
                    ON CONFLICT (ticker, date) DO UPDATE SET
                        rsi = EXCLUDED.rsi,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        ma_20 = EXCLUDED.ma_20,
                        ma_50 = EXCLUDED.ma_50,
                        ma_200 = EXCLUDED.ma_200,
                        bollinger_upper = EXCLUDED.bollinger_upper,
                        bollinger_lower = EXCLUDED.bollinger_lower
                """), {
                    'ticker': ind['ticker'],
                    'date': ind['date'],
                    'rsi': ind.get('rsi'),
                    'macd': ind.get('macd'),
                    'macd_signal': ind.get('macd_signal'),
                    'ma_20': ind.get('sma_20'),
                    'ma_50': ind.get('sma_50'),
                    'ma_200': ind.get('sma_200'),
                    'bollinger_upper': ind.get('bb_upper'),
                    'bollinger_lower': ind.get('bb_lower'),
                    'created_at': datetime.now()
                })

        logger.info(f"Saved {len(indicators_list)} technical indicators")
        return len(indicators_list)

    except Exception as e:
        logger.error(f"Error saving technical indicators: {str(e)}")
        raise

# ========================================
# 누락 감지 함수
# ========================================

def detect_missing_dates(engine=None) -> List[date]:
    """
    누락된 거래일 감지
    주가 데이터는 있지만 기술 지표가 없는 날짜를 식별합니다.
    """
    if engine is None:
        engine = get_db_engine()

    try:
        # DB에서 주가 데이터의 최신 날짜 조회
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT DISTINCT date FROM stock_prices
                WHERE date >= DATE(NOW()) - INTERVAL '30 days'
                ORDER BY date DESC
            """))
            price_dates = [row[0] for row in result.fetchall()]

        if not price_dates:
            logger.warning("No stock prices found in database")
            return []

        missing_indicator_dates = []

        # 각 주가 데이터 날짜에 대해 지표가 충분한지 확인
        for check_date in price_dates:
            with engine.connect() as conn:
                # 해당 날짜의 주가 티커 수
                price_result = conn.execute(text("""
                    SELECT COUNT(DISTINCT ticker) FROM stock_prices WHERE date = :date
                """), {'date': check_date})
                price_ticker_count = price_result.scalar() or 0

                # 해당 날짜의 지표 티커 수
                indicator_result = conn.execute(text("""
                    SELECT COUNT(DISTINCT ticker) FROM technical_indicators WHERE date = :date
                """), {'date': check_date})
                indicator_ticker_count = indicator_result.scalar() or 0

            # 지표가 주가의 90% 이상이 아닌 경우 누락으로 판단
            if price_ticker_count > 0:
                coverage = indicator_ticker_count / price_ticker_count
                logger.info(f"{check_date}: Price tickers={price_ticker_count}, Indicator tickers={indicator_ticker_count}, Coverage={coverage:.1%}")

                if coverage < 0.9:  # 90% 미만이면 누락
                    missing_indicator_dates.append(check_date)
                    logger.warning(f"Missing indicators for {check_date} (only {coverage:.1%} coverage)")

        logger.info(f"Detected {len(missing_indicator_dates)} dates with missing indicators: {missing_indicator_dates}")
        return missing_indicator_dates

    except Exception as e:
        logger.error(f"Error detecting missing dates: {str(e)}")
        return []

# ========================================
# 수집 상태 추적 함수 (collection_log)
# ========================================

def update_collection_log_price(target_date: date, status: str, count: int = None, error: str = None, engine=None):
    """
    주가 수집 상태 업데이트 → collection_log

    Args:
        target_date: 수집 대상 날짜
        status: pending, success, failed, retrying
        count: 수집된 주가 수
        error: 에러 메시지
        engine: 데이터베이스 엔진
    """
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.begin() as conn:
            # 기존 로그 조회
            result = conn.execute(text("""
                SELECT id, price_retry_count, indices_status FROM collection_log
                WHERE collection_date = :date
            """), {'date': target_date})
            row = result.first()

            if row is None:
                # 신규 생성
                conn.execute(text("""
                    INSERT INTO collection_log
                    (collection_date, price_status, price_count, price_last_error, price_retry_count)
                    VALUES (:date, :status, :count, :error, 0)
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error
                })
                logger.info(f"Created collection_log for {target_date}: price_status={status}")
            else:
                # 기존 로그 업데이트
                retry_count = row[1]
                indices_status = row[2]

                # retrying 상태면 retry_count 증가
                if status == 'retrying':
                    retry_count += 1

                # 완료 시간 설정
                completed_at = datetime.now() if status == 'success' else None

                conn.execute(text("""
                    UPDATE collection_log
                    SET price_status = :status,
                        price_count = COALESCE(:count, price_count),
                        price_last_error = :error,
                        price_retry_count = :retry_count,
                        price_completed_at = COALESCE(:completed_at, price_completed_at)
                    WHERE collection_date = :date
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error,
                    'retry_count': retry_count,
                    'completed_at': completed_at
                })

                # overall_status 업데이트
                if status == 'success' and indices_status == 'success':
                    overall_status = 'success'
                elif status == 'success' or indices_status == 'success':
                    overall_status = 'partial'
                else:
                    overall_status = status or 'pending'

                conn.execute(text("""
                    UPDATE collection_log
                    SET overall_status = :overall_status
                    WHERE collection_date = :date
                """), {
                    'date': target_date,
                    'overall_status': overall_status
                })

                logger.info(f"Updated collection_log for {target_date}: price_status={status}, retry_count={retry_count}, overall_status={overall_status}")

    except Exception as e:
        logger.error(f"Error updating collection_log price: {e}")
        raise

def update_collection_log_indices(target_date: date, status: str, count: int = None, error: str = None, engine=None):
    """
    지수 수집 상태 업데이트 → collection_log

    Args:
        target_date: 수집 대상 날짜
        status: pending, success, failed, retrying
        count: 수집된 지수 수
        error: 에러 메시지
        engine: 데이터베이스 엔진
    """
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.begin() as conn:
            # 기존 로그 조회
            result = conn.execute(text("""
                SELECT id, indices_retry_count, price_status FROM collection_log
                WHERE collection_date = :date
            """), {'date': target_date})
            row = result.first()

            if row is None:
                # 신규 생성
                conn.execute(text("""
                    INSERT INTO collection_log
                    (collection_date, indices_status, indices_count, indices_last_error, indices_retry_count)
                    VALUES (:date, :status, :count, :error, 0)
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error
                })
                logger.info(f"Created collection_log for {target_date}: indices_status={status}")
            else:
                # 기존 로그 업데이트
                retry_count = row[1]
                price_status = row[2]

                # retrying 상태면 retry_count 증가
                if status == 'retrying':
                    retry_count += 1

                # 완료 시간 설정
                completed_at = datetime.now() if status == 'success' else None

                conn.execute(text("""
                    UPDATE collection_log
                    SET indices_status = :status,
                        indices_count = COALESCE(:count, indices_count),
                        indices_last_error = :error,
                        indices_retry_count = :retry_count,
                        indices_completed_at = COALESCE(:completed_at, indices_completed_at)
                    WHERE collection_date = :date
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error,
                    'retry_count': retry_count,
                    'completed_at': completed_at
                })

                # overall_status 업데이트
                if price_status == 'success' and status == 'success':
                    overall_status = 'success'
                elif price_status == 'success' or status == 'success':
                    overall_status = 'partial'
                else:
                    overall_status = status or 'pending'

                conn.execute(text("""
                    UPDATE collection_log
                    SET overall_status = :overall_status
                    WHERE collection_date = :date
                """), {
                    'date': target_date,
                    'overall_status': overall_status
                })

                logger.info(f"Updated collection_log for {target_date}: indices_status={status}, retry_count={retry_count}, overall_status={overall_status}")

    except Exception as e:
        logger.error(f"Error updating collection_log indices: {e}")
        raise

def get_collection_status(target_date: date, engine=None) -> dict:
    """
    수집 상태 조회

    Args:
        target_date: 대상 날짜
        engine: 데이터베이스 엔진

    Returns:
        상태 정보 딕셔너리
    """
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT overall_status, price_status, indices_status,
                       price_retry_count, indices_retry_count
                FROM collection_log
                WHERE collection_date = :date
            """), {'date': target_date})
            row = result.first()

            if row is None:
                return {
                    'status': 'not_found',
                    'overall_status': None,
                    'price_status': None,
                    'indices_status': None,
                    'price_retry_count': 0,
                    'indices_retry_count': 0
                }

            return {
                'status': 'found',
                'overall_status': row[0],
                'price_status': row[1],
                'indices_status': row[2],
                'price_retry_count': row[3] or 0,
                'indices_retry_count': row[4] or 0
            }

    except Exception as e:
        logger.error(f"Error getting collection_status: {e}")
        raise

# ========================================
# 지표 상태 추적 함수 (indicator_log)
# ========================================

def update_indicator_log(target_date: date, status: str, count: int = None, error: str = None,
                        required_prices: int = None, collected_prices: int = None, engine=None):
    """
    기술적 지표 계산 상태 업데이트 → indicator_log

    Args:
        target_date: 대상 날짜
        status: pending, success, failed, retrying
        count: 계산된 지표 수
        error: 에러 메시지
        required_prices: 필요한 주가 수
        collected_prices: 실제 수집된 주가 수
        engine: 데이터베이스 엔진
    """
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.begin() as conn:
            # 기존 로그 조회
            result = conn.execute(text("""
                SELECT id, retry_count FROM indicator_log
                WHERE indicator_date = :date
            """), {'date': target_date})
            row = result.first()

            retry_count = 0

            if row is None:
                # 신규 생성
                if status == 'retrying':
                    retry_count = 1

                conn.execute(text("""
                    INSERT INTO indicator_log
                    (indicator_date, status, indicators_count, last_error, retry_count,
                     required_prices_count, collected_prices_count)
                    VALUES (:date, :status, :count, :error, :retry_count, :required, :collected)
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error,
                    'retry_count': retry_count,
                    'required': required_prices,
                    'collected': collected_prices
                })
                logger.info(f"Created indicator_log for {target_date}: status={status}")
            else:
                # 기존 로그 업데이트
                retry_count = row[1] or 0

                # retrying 상태면 retry_count 증가
                if status == 'retrying':
                    retry_count += 1

                # 완료 시간 설정
                completed_at = datetime.now() if status == 'success' else None

                conn.execute(text("""
                    UPDATE indicator_log
                    SET status = :status,
                        indicators_count = COALESCE(:count, indicators_count),
                        last_error = :error,
                        retry_count = :retry_count,
                        completed_at = COALESCE(:completed_at, completed_at),
                        required_prices_count = COALESCE(:required, required_prices_count),
                        collected_prices_count = COALESCE(:collected, collected_prices_count)
                    WHERE indicator_date = :date
                """), {
                    'date': target_date,
                    'status': status,
                    'count': count,
                    'error': error,
                    'retry_count': retry_count,
                    'completed_at': completed_at,
                    'required': required_prices,
                    'collected': collected_prices
                })

                logger.info(f"Updated indicator_log for {target_date}: status={status}, retry_count={retry_count}")

    except Exception as e:
        logger.error(f"Error updating indicator_log: {e}")
        raise

def get_indicator_status(target_date: date, engine=None) -> dict:
    """
    지표 계산 상태 조회

    Args:
        target_date: 대상 날짜
        engine: 데이터베이스 엔진

    Returns:
        상태 정보 딕셔너리
    """
    if engine is None:
        engine = get_db_engine()

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT status, indicators_count, retry_count,
                       required_prices_count, collected_prices_count
                FROM indicator_log
                WHERE indicator_date = :date
            """), {'date': target_date})
            row = result.first()

            if row is None:
                return {
                    'status': 'not_found',
                    'indicators_count': None,
                    'retry_count': 0,
                    'required_prices': None,
                    'collected_prices': None
                }

            return {
                'status': row[0],
                'indicators_count': row[1],
                'retry_count': row[2] or 0,
                'required_prices': row[3],
                'collected_prices': row[4]
            }

    except Exception as e:
        logger.error(f"Error getting indicator_status: {e}")
        raise
