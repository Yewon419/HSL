"""
Buy Signal Monitoring DAG
스크리닝 전략 자동 모니터링 및 매수 시그널 생성

스케줄: */5 * * * * (5분마다)
목적: HappyStockLife 백테스팅 플랫폼에 등록된 관심 전략을 자동으로 체크하고,
      조건에 맞는 종목이 발견되면 매수 시그널을 생성하여 알림을 전송합니다.

작성일: 2025-01-18
"""

from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
import pandas as pd
import json
from sqlalchemy import text

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from common_functions import (
    get_db_engine,
    get_supabase_connection,
    is_trading_day
)

logger = logging.getLogger(__name__)

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 1, 18),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    dag_id='buy_signal_monitor_dag',
    default_args=default_args,
    description='매수 시그널 자동 모니터링 (5분마다)',
    schedule_interval='*/5 * * * *',  # 5분마다 실행
    catchup=False,
    max_active_runs=1,
    tags=['buy-signal', 'monitoring', 'screening', 'happystocklife']
)

# ========================================
# Task 1: 활성화된 전략 조회
# ========================================

def task_fetch_active_strategies(**context):
    """
    Supabase에서 활성화된 관심 전략을 조회합니다.

    Returns:
        활성 전략 수
    """
    logger.info("="*80)
    logger.info("Task 1: 활성화된 전략 조회 시작")
    logger.info("="*80)

    try:
        supabase_engine = get_supabase_connection()

        query = """
            SELECT
                id,
                user_id,
                name,
                description,
                conditions,
                target_market,
                notification_enabled,
                last_run_at
            FROM saved_strategies
            WHERE is_active = true
            ORDER BY created_at DESC
        """

        strategies = pd.read_sql(query, supabase_engine)

        logger.info(f"활성화된 전략: {len(strategies)}개")

        if strategies.empty:
            logger.warning("활성화된 전략이 없습니다.")
            return 0

        # 전략 목록 로깅
        for _, strategy in strategies.iterrows():
            logger.info(f"  - {strategy['name']} (ID: {strategy['id']})")

        # XCom으로 다음 Task에 전달
        context['task_instance'].xcom_push(
            key='active_strategies',
            value=strategies.to_json(orient='records', date_format='iso')
        )

        logger.info("활성 전략 조회 완료")
        return len(strategies)

    except Exception as e:
        logger.error(f"활성 전략 조회 실패: {str(e)}")
        raise


# ========================================
# Task 2: 스크리닝 실행
# ========================================

def task_run_screening(**context):
    """
    각 전략의 조건으로 스크리닝을 실행합니다.

    Returns:
        발견된 시그널 수
    """
    logger.info("="*80)
    logger.info("Task 2: 스크리닝 실행 시작")
    logger.info("="*80)

    # 전략 조회
    strategies_json = context['task_instance'].xcom_pull(
        task_ids='fetch_active_strategies',
        key='active_strategies'
    )

    if not strategies_json:
        logger.warning("전략 데이터가 없습니다.")
        return 0

    strategies = pd.read_json(strategies_json, orient='records')

    # 오늘 날짜 확인
    today = date.today()

    # 주말이면 가장 최근 거래일 사용
    if not is_trading_day(today):
        logger.warning(f"{today}는 거래일이 아닙니다. 스크리닝을 건너뜁니다.")
        return 0

    # 주식 데이터 조회 (stock_prices + technical_indicators)
    main_db_engine = get_db_engine()

    query = """
        SELECT
            sp.ticker,
            s.company_name as name,
            sp.close_price as price,
            sp.volume,
            ((sp.close_price - LAG(sp.close_price, 1) OVER (PARTITION BY sp.ticker ORDER BY sp.date))
             / LAG(sp.close_price, 1) OVER (PARTITION BY sp.ticker ORDER BY sp.date) * 100) as change_percent,
            ti.rsi,
            ti.macd,
            ti.macd_signal,
            ti.ma_20,
            ti.ma_50,
            ti.ma_200,
            ti.bollinger_upper,
            ti.bollinger_lower
        FROM stock_prices sp
        JOIN stocks s ON sp.ticker = s.ticker
        LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
        WHERE sp.date = :today
        AND s.is_active = true
    """

    stock_data = pd.read_sql(query, main_db_engine, params={'today': today})

    logger.info(f"오늘({today}) 주식 데이터: {len(stock_data)}개")

    if stock_data.empty:
        logger.warning("오늘 주식 데이터가 없습니다.")
        return 0

    # 전략별 스크리닝 실행
    all_signals = []

    for _, strategy in strategies.iterrows():
        strategy_name = strategy['name']
        conditions = strategy['conditions']  # JSONB (list of dict)

        logger.info(f"전략 '{strategy_name}' 스크리닝 시작...")

        try:
            # 조건 적용
            matched_stocks = apply_screening_conditions(stock_data.copy(), conditions)

            if not matched_stocks.empty:
                logger.info(f"  ✅ {len(matched_stocks)}개 종목 발견")

                for _, stock in matched_stocks.iterrows():
                    signal = {
                        'strategy_id': strategy['id'],
                        'user_id': strategy['user_id'],
                        'symbol': stock['ticker'],
                        'name': stock['name'],
                        'price': float(stock['price']) if pd.notna(stock['price']) else None,
                        'change_percent': float(stock['change_percent']) if pd.notna(stock['change_percent']) else None,
                        'volume': int(stock['volume']) if pd.notna(stock['volume']) else None,
                        'indicators': {
                            'rsi': float(stock['rsi']) if pd.notna(stock['rsi']) else None,
                            'macd': float(stock['macd']) if pd.notna(stock['macd']) else None,
                            'macd_signal': float(stock['macd_signal']) if pd.notna(stock['macd_signal']) else None,
                            'ma_20': float(stock['ma_20']) if pd.notna(stock['ma_20']) else None,
                            'ma_50': float(stock['ma_50']) if pd.notna(stock['ma_50']) else None
                        },
                        'matched_conditions': describe_matched_conditions(stock, conditions)
                    }
                    all_signals.append(signal)
            else:
                logger.info(f"  ℹ️  조건 만족 종목 없음")

        except Exception as e:
            logger.error(f"  ❌ 전략 '{strategy_name}' 스크리닝 실패: {str(e)}")

    logger.info(f"총 {len(all_signals)}개 시그널 발견")

    # XCom으로 전달
    context['task_instance'].xcom_push(key='signals', value=all_signals)

    return len(all_signals)


def apply_screening_conditions(stock_data: pd.DataFrame, conditions: list) -> pd.DataFrame:
    """
    스크리닝 조건을 적용하여 종목을 필터링합니다.

    Args:
        stock_data: 주식 데이터 DataFrame
        conditions: 조건 리스트 (JSON 형태)

    Returns:
        필터링된 DataFrame
    """
    filtered = stock_data.copy()

    for condition in conditions:
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if not field or not operator:
            continue

        # 필드가 데이터에 없으면 스킵
        if field not in filtered.columns:
            logger.warning(f"필드 '{field}'가 데이터에 없습니다.")
            continue

        try:
            if operator == '>':
                filtered = filtered[filtered[field] > value]
            elif operator == '<':
                filtered = filtered[filtered[field] < value]
            elif operator == '>=':
                filtered = filtered[filtered[field] >= value]
            elif operator == '<=':
                filtered = filtered[filtered[field] <= value]
            elif operator == '==':
                filtered = filtered[filtered[field] == value]
            elif operator == 'between':
                if isinstance(value, list) and len(value) == 2:
                    filtered = filtered[(filtered[field] >= value[0]) & (filtered[field] <= value[1])]
            else:
                logger.warning(f"알 수 없는 연산자: {operator}")

        except Exception as e:
            logger.error(f"조건 적용 중 오류: {condition}, 오류: {str(e)}")

    return filtered


def describe_matched_conditions(stock: pd.Series, conditions: list) -> list:
    """
    매칭된 조건을 사람이 읽을 수 있는 형태로 설명합니다.

    Args:
        stock: 종목 데이터
        conditions: 조건 리스트

    Returns:
        조건 설명 리스트
    """
    descriptions = []

    for condition in conditions:
        field = condition.get('field')
        operator = condition.get('operator')
        value = condition.get('value')

        if not field or not operator:
            continue

        # 필드 값
        field_value = stock.get(field)
        if pd.isna(field_value):
            continue

        # 설명 생성
        if operator == '>':
            descriptions.append(f"{field} > {value} (현재: {field_value:.2f})")
        elif operator == '<':
            descriptions.append(f"{field} < {value} (현재: {field_value:.2f})")
        elif operator == '>=':
            descriptions.append(f"{field} >= {value} (현재: {field_value:.2f})")
        elif operator == '<=':
            descriptions.append(f"{field} <= {value} (현재: {field_value:.2f})")
        elif operator == '==':
            descriptions.append(f"{field} == {value} (현재: {field_value})")
        elif operator == 'between':
            if isinstance(value, list) and len(value) == 2:
                descriptions.append(f"{value[0]} <= {field} <= {value[1]} (현재: {field_value:.2f})")

    return descriptions


# ========================================
# Task 3: 매수 시그널 저장
# ========================================

def task_create_buy_signals(**context):
    """
    발견된 시그널을 Supabase buy_signals 테이블에 저장합니다.

    Returns:
        저장된 시그널 수
    """
    logger.info("="*80)
    logger.info("Task 3: 매수 시그널 저장 시작")
    logger.info("="*80)

    signals = context['task_instance'].xcom_pull(
        task_ids='run_screening',
        key='signals'
    )

    if not signals:
        logger.info("저장할 시그널이 없습니다.")
        return 0

    supabase_engine = get_supabase_connection()
    saved_count = 0

    for signal in signals:
        try:
            # 중복 체크 (오늘 같은 전략 + 종목 시그널이 이미 있는지)
            check_query = """
                SELECT id FROM buy_signals
                WHERE strategy_id = :strategy_id
                AND symbol = :symbol
                AND DATE(created_at) = CURRENT_DATE
            """

            existing = pd.read_sql(
                check_query,
                supabase_engine,
                params={
                    'strategy_id': signal['strategy_id'],
                    'symbol': signal['symbol']
                }
            )

            if not existing.empty:
                logger.info(f"  중복 시그널 스킵: {signal['name']} ({signal['symbol']})")
                continue

            # 새 시그널 저장
            insert_query = """
                INSERT INTO buy_signals (
                    strategy_id, user_id, symbol, name,
                    price, change_percent, volume, indicators,
                    matched_conditions, is_read, notification_sent
                ) VALUES (
                    :strategy_id, :user_id, :symbol, :name,
                    :price, :change_percent, :volume, :indicators,
                    :matched_conditions, false, false
                )
            """

            with supabase_engine.begin() as conn:
                conn.execute(text(insert_query), {
                    'strategy_id': signal['strategy_id'],
                    'user_id': signal['user_id'],
                    'symbol': signal['symbol'],
                    'name': signal['name'],
                    'price': signal['price'],
                    'change_percent': signal['change_percent'],
                    'volume': signal['volume'],
                    'indicators': json.dumps(signal['indicators']),
                    'matched_conditions': signal['matched_conditions']
                })

            saved_count += 1
            logger.info(f"  ✅ 시그널 저장: {signal['name']} ({signal['symbol']})")

        except Exception as e:
            logger.error(f"  ❌ 시그널 저장 실패 ({signal.get('symbol')}): {str(e)}")

    logger.info(f"총 {saved_count}개 시그널 저장 완료")

    # 저장된 시그널 ID 목록 전달
    context['task_instance'].xcom_push(key='saved_count', value=saved_count)

    return saved_count


# ========================================
# Task 4: Slack 알림 전송
# ========================================

def task_send_notifications(**context):
    """
    미발송 시그널을 Slack으로 알림 전송합니다.

    Returns:
        전송된 알림 수
    """
    logger.info("="*80)
    logger.info("Task 4: Slack 알림 전송 시작")
    logger.info("="*80)

    saved_count = context['task_instance'].xcom_pull(
        task_ids='create_buy_signals',
        key='saved_count'
    )

    if saved_count == 0:
        logger.info("전송할 알림이 없습니다.")
        return 0

    # 미발송 시그널 조회
    supabase_engine = get_supabase_connection()

    query = """
        SELECT
            bs.id,
            bs.symbol,
            bs.name,
            bs.price,
            bs.change_percent,
            bs.volume,
            bs.indicators,
            bs.matched_conditions,
            ss.name as strategy_name
        FROM buy_signals bs
        JOIN saved_strategies ss ON bs.strategy_id = ss.id
        WHERE bs.notification_sent = false
        AND DATE(bs.created_at) = CURRENT_DATE
        ORDER BY bs.created_at DESC
    """

    pending_signals = pd.read_sql(query, supabase_engine)

    logger.info(f"미발송 시그널: {len(pending_signals)}개")

    sent_count = 0

    for _, signal in pending_signals.iterrows():
        try:
            # Slack 메시지 생성
            message = format_slack_message(signal)

            # Slack 전송 (실제 Webhook URL 설정 필요)
            send_slack_webhook(message)

            # 발송 완료 표시
            update_query = """
                UPDATE buy_signals
                SET notification_sent = true, notified_at = NOW()
                WHERE id = :id
            """

            with supabase_engine.begin() as conn:
                conn.execute(text(update_query), {'id': signal['id']})

            sent_count += 1
            logger.info(f"  ✅ Slack 알림 전송: {signal['name']} ({signal['symbol']})")

        except Exception as e:
            logger.error(f"  ❌ Slack 알림 실패 ({signal['symbol']}): {str(e)}")

            # 에러 기록
            error_query = """
                UPDATE buy_signals
                SET notification_error = :error
                WHERE id = :id
            """

            try:
                with supabase_engine.begin() as conn:
                    conn.execute(text(error_query), {
                        'id': signal['id'],
                        'error': str(e)[:500]
                    })
            except:
                pass

    logger.info(f"총 {sent_count}개 알림 전송 완료")
    return sent_count


def format_slack_message(signal: pd.Series) -> str:
    """
    Slack 메시지 포맷팅

    Args:
        signal: 시그널 데이터

    Returns:
        포맷된 메시지
    """
    # 지표 파싱
    indicators = signal.get('indicators')
    if isinstance(indicators, str):
        indicators = json.loads(indicators)

    # 조건 파싱
    conditions = signal.get('matched_conditions')
    if isinstance(conditions, str):
        conditions = json.loads(conditions)

    # 메시지 생성
    message = f"""
🔔 *매수 시그널 발생!*

📊 *전략*: {signal['strategy_name']}
📈 *종목*: {signal['name']} ({signal['symbol']})
💰 *가격*: {signal['price']:,.0f}원
{'📉' if signal.get('change_percent', 0) < 0 else '📈'} *등락률*: {signal.get('change_percent', 0):.2f}%
📊 *거래량*: {signal.get('volume', 0):,}

*기술적 지표*:
• RSI: {indicators.get('rsi', 'N/A')}
• MACD: {indicators.get('macd', 'N/A')}
• MA20: {indicators.get('ma_20', 'N/A'):,.0f}원

*매칭된 조건*:
"""

    for condition in conditions:
        message += f"• {condition}\n"

    message += f"\n_시그널 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}_"

    return message


def send_slack_webhook(message: str):
    """
    Slack Webhook으로 메시지 전송

    Args:
        message: 전송할 메시지

    Note:
        실제 Webhook URL을 설정해야 합니다.
    """
    import requests

    # TODO: 실제 Slack Webhook URL로 변경
    SLACK_WEBHOOK_URL = os.getenv('SLACK_WEBHOOK_URL', '')

    if not SLACK_WEBHOOK_URL:
        logger.warning("Slack Webhook URL이 설정되지 않았습니다.")
        return

    payload = {
        "text": message,
        "username": "HappyStockLife Bot",
        "icon_emoji": ":chart_with_upwards_trend:"
    }

    response = requests.post(SLACK_WEBHOOK_URL, json=payload, timeout=10)
    response.raise_for_status()


# ========================================
# DAG Task 정의
# ========================================

fetch_task = PythonOperator(
    task_id='fetch_active_strategies',
    python_callable=task_fetch_active_strategies,
    provide_context=True,
    dag=dag
)

screening_task = PythonOperator(
    task_id='run_screening',
    python_callable=task_run_screening,
    provide_context=True,
    dag=dag
)

create_signals_task = PythonOperator(
    task_id='create_buy_signals',
    python_callable=task_create_buy_signals,
    provide_context=True,
    dag=dag
)

notify_task = PythonOperator(
    task_id='send_notifications',
    python_callable=task_send_notifications,
    provide_context=True,
    dag=dag
)

# ========================================
# Task 의존성 설정
# ========================================

fetch_task >> screening_task >> create_signals_task >> notify_task
