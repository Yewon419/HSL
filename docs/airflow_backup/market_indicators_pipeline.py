from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task_sensor import ExternalTaskSensor
import pandas as pd
import numpy as np
import sqlalchemy
from sqlalchemy import create_engine, text
import logging
from typing import Dict, List, Tuple

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 9, 25),  # 최근 날짜로 수정
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

dag = DAG(
    'market_indicators_calculation',
    default_args=default_args,
    description='Market indicators and technical analysis calculation',
    schedule_interval='0 20 * * 1-5',  # 데이터 수집 후 오후 8시 실행 (평일만)
    catchup=True,  # 누락된 실행을 따라잡도록 설정
    max_active_runs=1,
    tags=['indicators', 'analysis', 'calculation']
)

def get_db_connection():
    """데이터베이스 연결 생성"""
    DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"
    engine = create_engine(DATABASE_URL)
    return engine

def check_data_availability(**context):
    """오늘 수집된 데이터 확인"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Checking data availability for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 오늘 수집된 주식 데이터 개수 확인
            result = conn.execute(text("""
                SELECT COUNT(DISTINCT sp.ticker) as stock_count,
                       COUNT(*) as total_records
                FROM stock_prices sp
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :target_date
                AND s.is_active = true
            """), {'target_date': target_date})

            row = result.fetchone()
            stock_count = row[0]
            total_records = row[1]

            logging.info(f"Found {stock_count} stocks with {total_records} price records")

            if stock_count < 5:
                raise ValueError(f"Insufficient data: only {stock_count} stocks found")

            # 데이터 품질 확인
            result = conn.execute(text("""
                SELECT COUNT(*) as invalid_count
                FROM stock_prices sp
                WHERE sp.date = :target_date
                AND (sp.close_price <= 0 OR sp.volume < 0)
            """), {'target_date': target_date})

            invalid_count = result.fetchone()[0]

            if invalid_count > 0:
                logging.warning(f"Found {invalid_count} records with invalid data")

            return {'stock_count': stock_count, 'total_records': total_records}

    except Exception as e:
        logging.error(f"Error checking data availability: {e}")
        raise

def calculate_technical_indicators(**context):
    """기술적 지표 계산 (RSI, MACD, Bollinger Bands, Moving Averages)"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Calculating technical indicators for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 활성 주식 목록 가져오기
            result = conn.execute(text("""
                SELECT DISTINCT s.ticker
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                WHERE s.is_active = true
                AND sp.date = :target_date
                ORDER BY s.ticker
            """), {'target_date': target_date})

            tickers = [row[0] for row in result]
            logging.info(f"Processing technical indicators for {len(tickers)} stocks")

            indicators_data = []

            # 각 주식별로 기술적 지표 계산
            for ticker in tickers:
                try:
                    # 최근 200일 데이터 가져오기 (기술적 지표 계산을 위해)
                    price_data = pd.read_sql(text("""
                        SELECT date, open_price, high_price, low_price, close_price, volume
                        FROM stock_prices
                        WHERE ticker = :ticker
                        AND date <= :target_date
                        ORDER BY date DESC
                        LIMIT 200
                    """), conn, params={'ticker': ticker, 'target_date': target_date})

                    if len(price_data) < 20:  # 최소 20일 데이터 필요
                        continue

                    # 데이터 정렬 (날짜 오름차순)
                    price_data = price_data.sort_values('date')

                    # 기술적 지표 계산
                    indicators = calculate_stock_indicators(price_data)

                    if indicators:
                        indicators['ticker'] = ticker
                        indicators['date'] = target_date
                        indicators['created_at'] = datetime.now()
                        indicators_data.append(indicators)

                except Exception as e:
                    logging.warning(f"Error calculating indicators for {ticker}: {e}")
                    continue

            # 계산된 지표 데이터베이스에 저장
            if indicators_data:
                save_technical_indicators(indicators_data, engine)

            logging.info(f"Successfully calculated indicators for {len(indicators_data)} stocks")
            return len(indicators_data)

    except Exception as e:
        logging.error(f"Error calculating technical indicators: {e}")
        raise

def calculate_stock_indicators(price_data: pd.DataFrame) -> Dict:
    """개별 주식의 기술적 지표 계산"""
    try:
        close_prices = price_data['close_price'].values
        high_prices = price_data['high_price'].values
        low_prices = price_data['low_price'].values
        volume = price_data['volume'].values

        indicators = {}

        # 이동평균 계산
        if len(close_prices) >= 20:
            indicators['ma_20'] = np.mean(close_prices[-20:])
        if len(close_prices) >= 50:
            indicators['ma_50'] = np.mean(close_prices[-50:])
        if len(close_prices) >= 200:
            indicators['ma_200'] = np.mean(close_prices[-200:])

        # RSI 계산 (14일)
        if len(close_prices) >= 15:
            indicators['rsi'] = calculate_rsi(close_prices, 14)

        # MACD 계산
        if len(close_prices) >= 26:
            macd_data = calculate_macd(close_prices)
            indicators.update(macd_data)

        # Bollinger Bands 계산 (20일, 2 표준편차)
        if len(close_prices) >= 20:
            bb_data = calculate_bollinger_bands(close_prices, 20, 2)
            indicators.update(bb_data)

        # Stochastic Oscillator 계산
        if len(close_prices) >= 14:
            stoch_data = calculate_stochastic(high_prices, low_prices, close_prices, 14)
            indicators.update(stoch_data)

        return indicators

    except Exception as e:
        logging.warning(f"Error in indicator calculation: {e}")
        return {}

def calculate_rsi(prices: np.ndarray, period: int = 14) -> float:
    """RSI (Relative Strength Index) 계산"""
    deltas = np.diff(prices)
    gains = np.where(deltas > 0, deltas, 0)
    losses = np.where(deltas < 0, -deltas, 0)

    avg_gain = np.mean(gains[-period:])
    avg_loss = np.mean(losses[-period:])

    if avg_loss == 0:
        return 100.0

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return round(rsi, 2)

def calculate_macd(prices: np.ndarray) -> Dict:
    """MACD 계산"""
    ema_12 = calculate_ema(prices, 12)
    ema_26 = calculate_ema(prices, 26)

    macd_line = ema_12 - ema_26

    # Signal line (MACD의 9일 EMA)
    macd_values = []
    for i in range(26, len(prices)):
        ema_12_i = calculate_ema(prices[:i+1], 12)
        ema_26_i = calculate_ema(prices[:i+1], 26)
        macd_values.append(ema_12_i - ema_26_i)

    if len(macd_values) >= 9:
        signal_line = calculate_ema(np.array(macd_values), 9)
        histogram = macd_line - signal_line
    else:
        signal_line = macd_line
        histogram = 0

    return {
        'macd': round(macd_line, 4),
        'macd_signal': round(signal_line, 4),
        'macd_histogram': round(histogram, 4)
    }

def calculate_ema(prices: np.ndarray, period: int) -> float:
    """지수이동평균 계산"""
    alpha = 2 / (period + 1)
    ema = prices[0]

    for price in prices[1:]:
        ema = alpha * price + (1 - alpha) * ema

    return ema

def calculate_bollinger_bands(prices: np.ndarray, period: int = 20, std_dev: int = 2) -> Dict:
    """볼린저 밴드 계산"""
    recent_prices = prices[-period:]
    middle = np.mean(recent_prices)
    std = np.std(recent_prices)

    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)

    return {
        'bollinger_upper': round(upper, 2),
        'bollinger_middle': round(middle, 2),
        'bollinger_lower': round(lower, 2)
    }

def calculate_stochastic(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int = 14) -> Dict:
    """스토캐스틱 오실레이터 계산"""
    recent_high = high[-period:]
    recent_low = low[-period:]
    current_close = close[-1]

    highest_high = np.max(recent_high)
    lowest_low = np.min(recent_low)

    if highest_high == lowest_low:
        k_percent = 50.0
    else:
        k_percent = ((current_close - lowest_low) / (highest_high - lowest_low)) * 100

    # D% 계산을 위해 최근 3일의 K% 값이 필요하지만 단순화
    d_percent = k_percent  # 실제로는 K%의 3일 이동평균

    return {
        'stoch_k': round(k_percent, 2),
        'stoch_d': round(d_percent, 2)
    }

def save_technical_indicators(indicators_data: List[Dict], engine):
    """기술적 지표를 데이터베이스에 저장"""
    try:
        with engine.begin() as conn:
            for data in indicators_data:
                # 기본값 설정
                indicator_record = {
                    'ticker': data['ticker'],
                    'date': data['date'],
                    'created_at': data['created_at'],
                    'stoch_k': data.get('stoch_k'),
                    'stoch_d': data.get('stoch_d'),
                    'macd': data.get('macd'),
                    'macd_signal': data.get('macd_signal'),
                    'macd_histogram': data.get('macd_histogram'),
                    'rsi': data.get('rsi'),
                    'ma_20': data.get('ma_20'),
                    'ma_50': data.get('ma_50'),
                    'ma_200': data.get('ma_200'),
                    'bollinger_upper': data.get('bollinger_upper'),
                    'bollinger_middle': data.get('bollinger_middle'),
                    'bollinger_lower': data.get('bollinger_lower')
                }

                conn.execute(text("""
                    INSERT INTO technical_indicators (
                        ticker, date, stoch_k, stoch_d, macd, macd_signal, macd_histogram,
                        rsi, ma_20, ma_50, ma_200, bollinger_upper, bollinger_middle,
                        bollinger_lower, created_at
                    )
                    VALUES (
                        :ticker, :date, :stoch_k, :stoch_d, :macd, :macd_signal, :macd_histogram,
                        :rsi, :ma_20, :ma_50, :ma_200, :bollinger_upper, :bollinger_middle,
                        :bollinger_lower, :created_at
                    )
                    ON CONFLICT (ticker, date)
                    DO UPDATE SET
                        stoch_k = EXCLUDED.stoch_k,
                        stoch_d = EXCLUDED.stoch_d,
                        macd = EXCLUDED.macd,
                        macd_signal = EXCLUDED.macd_signal,
                        macd_histogram = EXCLUDED.macd_histogram,
                        rsi = EXCLUDED.rsi,
                        ma_20 = EXCLUDED.ma_20,
                        ma_50 = EXCLUDED.ma_50,
                        ma_200 = EXCLUDED.ma_200,
                        bollinger_upper = EXCLUDED.bollinger_upper,
                        bollinger_middle = EXCLUDED.bollinger_middle,
                        bollinger_lower = EXCLUDED.bollinger_lower
                """), indicator_record)

        logging.info(f"Successfully saved {len(indicators_data)} technical indicator records")

    except Exception as e:
        logging.error(f"Error saving technical indicators: {e}")
        raise

def calculate_market_indices(**context):
    """시장 지수 계산 (KOSPI, KOSDAQ 등)"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Calculating market indices for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            market_indices = {}

            # KOSPI 지수 계산
            kospi_data = calculate_market_index(conn, target_date, 'KOSPI')
            if kospi_data:
                market_indices['KOSPI'] = kospi_data

            # KOSDAQ 지수 계산
            kosdaq_data = calculate_market_index(conn, target_date, 'KOSDAQ')
            if kosdaq_data:
                market_indices['KOSDAQ'] = kosdaq_data

            # 전체 시장 지수 계산
            total_market_data = calculate_market_index(conn, target_date, None)
            if total_market_data:
                market_indices['TOTAL'] = total_market_data

            # 시장 지수 데이터베이스에 저장
            save_market_indices(market_indices, target_date, engine)

            logging.info(f"Successfully calculated {len(market_indices)} market indices")
            return len(market_indices)

    except Exception as e:
        logging.error(f"Error calculating market indices: {e}")
        raise

def calculate_market_index(conn, target_date, market_type):
    """특정 시장의 지수 계산"""
    try:
        # 시장별 주식 데이터 가져오기
        if market_type:
            query = text("""
                SELECT sp.close_price, sp.volume, s.market_cap
                FROM stock_prices sp
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :target_date
                AND s.market_type = :market_type
                AND s.is_active = true
                AND sp.close_price > 0
            """)
            params = {'target_date': target_date, 'market_type': market_type}
        else:
            query = text("""
                SELECT sp.close_price, sp.volume, s.market_cap
                FROM stock_prices sp
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :target_date
                AND s.is_active = true
                AND sp.close_price > 0
                AND s.currency = 'KRW'
            """)
            params = {'target_date': target_date}

        result = conn.execute(query, params)
        data = result.fetchall()

        if not data:
            return None

        prices = [row[0] for row in data]
        volumes = [row[1] for row in data]
        market_caps = [row[2] or 1000000000 for row in data]  # 기본값 설정

        # 가중평균 지수 계산 (시가총액 가중)
        total_market_cap = sum(market_caps)
        if total_market_cap == 0:
            return None

        weighted_price = sum(price * cap for price, cap in zip(prices, market_caps)) / total_market_cap

        return {
            'index_value': round(weighted_price, 2),
            'stock_count': len(data),
            'total_volume': sum(volumes),
            'total_market_cap': total_market_cap
        }

    except Exception as e:
        logging.warning(f"Error calculating market index for {market_type}: {e}")
        return None

def save_market_indices(indices_data: Dict, target_date, engine):
    """시장 지수를 데이터베이스에 저장"""
    try:
        # 시장 지수 테이블이 없다면 생성
        with engine.begin() as conn:
            conn.execute(text("""
                CREATE TABLE IF NOT EXISTS market_indices (
                    id SERIAL PRIMARY KEY,
                    index_name VARCHAR(20) NOT NULL,
                    date DATE NOT NULL,
                    index_value DECIMAL(15, 2),
                    stock_count INTEGER,
                    total_volume BIGINT,
                    total_market_cap BIGINT,
                    created_at TIMESTAMP DEFAULT NOW(),
                    UNIQUE(index_name, date)
                )
            """))

            for index_name, data in indices_data.items():
                conn.execute(text("""
                    INSERT INTO market_indices (
                        index_name, date, index_value, stock_count, total_volume,
                        total_market_cap, created_at
                    )
                    VALUES (
                        :index_name, :date, :index_value, :stock_count, :total_volume,
                        :total_market_cap, NOW()
                    )
                    ON CONFLICT (index_name, date)
                    DO UPDATE SET
                        index_value = EXCLUDED.index_value,
                        stock_count = EXCLUDED.stock_count,
                        total_volume = EXCLUDED.total_volume,
                        total_market_cap = EXCLUDED.total_market_cap
                """), {
                    'index_name': index_name,
                    'date': target_date,
                    'index_value': data['index_value'],
                    'stock_count': data['stock_count'],
                    'total_volume': data['total_volume'],
                    'total_market_cap': data['total_market_cap']
                })

        logging.info(f"Successfully saved market indices: {list(indices_data.keys())}")

    except Exception as e:
        logging.error(f"Error saving market indices: {e}")
        raise

def generate_daily_summary(**context):
    """일일 시장 요약 리포트 생성"""
    execution_date = context['execution_date']
    target_date = execution_date.date()

    logging.info(f"Generating daily market summary for {target_date}")

    engine = get_db_connection()

    try:
        with engine.connect() as conn:
            # 시장 요약 데이터 수집
            summary = {}

            # 전체 거래 통계
            result = conn.execute(text("""
                SELECT
                    COUNT(DISTINCT sp.ticker) as active_stocks,
                    AVG(sp.close_price) as avg_price,
                    SUM(sp.volume) as total_volume,
                    COUNT(CASE WHEN sp.close_price > prev.close_price THEN 1 END) as rising_stocks,
                    COUNT(CASE WHEN sp.close_price < prev.close_price THEN 1 END) as falling_stocks
                FROM stock_prices sp
                LEFT JOIN stock_prices prev ON sp.ticker = prev.ticker
                    AND prev.date = sp.date - INTERVAL '1 day'
                JOIN stocks s ON sp.ticker = s.ticker
                WHERE sp.date = :target_date
                AND s.is_active = true
                AND s.currency = 'KRW'
            """), {'target_date': target_date})

            market_stats = result.fetchone()

            summary = {
                'date': str(target_date),
                'active_stocks': market_stats[0],
                'average_price': float(market_stats[1]) if market_stats[1] else 0,
                'total_volume': int(market_stats[2]) if market_stats[2] else 0,
                'rising_stocks': market_stats[3] or 0,
                'falling_stocks': market_stats[4] or 0,
                'generated_at': str(datetime.now())
            }

            logging.info(f"Daily summary: {summary}")
            return summary

    except Exception as e:
        logging.error(f"Error generating daily summary: {e}")
        raise

# 데이터 수집 완료 대기 - 데이터베이스에서 직접 확인
def wait_for_korean_data(**context):
    """한국 주식 데이터 수집 완료 대기"""
    import time
    execution_date = context['execution_date']

    logging.info(f"Waiting for Korean stock data collection to complete for {execution_date.date()}")

    engine = get_db_connection()
    max_attempts = 60  # 최대 1시간 대기 (1분 간격)

    for attempt in range(max_attempts):
        try:
            with engine.connect() as conn:
                # 오늘 날짜의 한국 주식 데이터가 있는지 확인
                result = conn.execute(text("""
                    SELECT COUNT(*) as count
                    FROM stock_prices sp
                    JOIN stocks s ON sp.ticker = s.ticker
                    WHERE sp.date = :target_date
                    AND s.currency = 'KRW'
                    AND s.is_active = true
                """), {'target_date': execution_date.date()})

                count = result.fetchone()[0]

                if count >= 3:  # 최소 3개 종목 이상
                    logging.info(f"Korean stock data collection completed: {count} records found")
                    return count
                else:
                    logging.info(f"Waiting for data... Current count: {count} (attempt {attempt + 1}/{max_attempts})")
                    time.sleep(60)  # 1분 대기

        except Exception as e:
            logging.warning(f"Error checking data availability: {e}")
            time.sleep(60)

    raise Exception(f"Timeout waiting for Korean stock data collection after {max_attempts} minutes")

wait_for_data_collection = PythonOperator(
    task_id='wait_for_data_collection',
    python_callable=wait_for_korean_data,
    dag=dag,
)

# Task 정의
check_data_task = PythonOperator(
    task_id='check_data_availability',
    python_callable=check_data_availability,
    dag=dag,
)

calculate_indicators_task = PythonOperator(
    task_id='calculate_technical_indicators',
    python_callable=calculate_technical_indicators,
    dag=dag,
)

calculate_indices_task = PythonOperator(
    task_id='calculate_market_indices',
    python_callable=calculate_market_indices,
    dag=dag,
)

generate_summary_task = PythonOperator(
    task_id='generate_daily_summary',
    python_callable=generate_daily_summary,
    dag=dag,
)

# 알림 Task
notify_completion_task = BashOperator(
    task_id='notify_indicators_completion',
    bash_command='echo "Market indicators calculation completed at $(date)"',
    dag=dag,
)

# Task 의존성 설정
wait_for_data_collection >> check_data_task >> [calculate_indicators_task, calculate_indices_task] >> generate_summary_task >> notify_completion_task