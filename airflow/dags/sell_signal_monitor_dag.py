"""
Sell Signal Monitoring DAG
ATS 매도 전략 프레임워크 기반 매도 시그널 자동 모니터링

스케줄: */10 * * * * (10분마다)
목적: 보유 종목에 대한 매도 타이밍을 자동으로 분석하고,
      조건에 맞는 매도 신호가 발생하면 알림을 전송합니다.

3계층 알고리즘 아키텍처:
- Type A: 리스크 관리 (손절) - CRITICAL
- Type B: 추세 종료 - HIGH
- Type C: 수익 목표 달성 - MEDIUM

작성일: 2025-11-25
"""

from datetime import datetime, timedelta, date
from airflow import DAG
from airflow.operators.python import PythonOperator
import logging
import pandas as pd
import json
from sqlalchemy import text, create_engine

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from common_functions import (
    get_db_engine,
    is_trading_day
)

logger = logging.getLogger(__name__)

# ========================================
# DAG 기본 설정
# ========================================

default_args = {
    'owner': 'stock-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 11, 25),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    dag_id='sell_signal_monitor_dag',
    default_args=default_args,
    description='ATS 프레임워크 기반 매도 시그널 자동 모니터링 (10분마다)',
    schedule_interval='*/10 * * * *',  # 10분마다 실행
    catchup=False,
    max_active_runs=1,
    tags=['sell-signal', 'monitoring', 'ats', 'risk-management']
)


# ========================================
# 매도 신호 감지 설정
# ========================================

# Type A 설정 (리스크 관리)
FIXED_STOP_LOSS_PCT = -5.0  # 고정 손절 %
TIME_STOP_DAYS = 5  # Time Stop 일수

# Type B 설정 (추세 종료)
RSI_OVERBOUGHT = 70
VOLUME_CLIMAX_MULTIPLIER = 2.0

# Type C 설정 (수익 목표)
FIBONACCI_LEVELS = {
    '127.2': 1.272,
    '161.8': 1.618,
    '261.8': 2.618
}


# ========================================
# Task 1: 보유 종목 조회
# ========================================

def task_fetch_holdings(**context):
    """
    모든 활성 보유 종목을 조회합니다.
    """
    logger.info("="*80)
    logger.info("Task 1: 보유 종목 조회 시작")
    logger.info("="*80)

    today = date.today()

    # 거래일 체크
    if not is_trading_day(today):
        logger.warning(f"{today}는 거래일이 아닙니다. 스킵합니다.")
        return 0

    try:
        engine = get_db_engine()

        query = """
            SELECT
                h.id as holding_id,
                h.user_id,
                h.ticker,
                h.company_name,
                h.quantity,
                h.avg_buy_price,
                h.buy_date,
                h.stop_loss_price,
                h.stop_loss_percent,
                h.take_profit_price,
                h.take_profit_percent,
                sp.close_price as current_price,
                sp.volume,
                ti.rsi,
                ti.macd,
                ti.macd_signal,
                ti.macd_histogram,
                ti.ma_20,
                ti.ma_50,
                ti.ma_200,
                ti.bollinger_upper,
                ti.bollinger_lower,
                u.email as user_email
            FROM holdings h
            JOIN users u ON h.user_id = u.id
            JOIN stock_prices sp ON h.ticker = sp.ticker
            LEFT JOIN technical_indicators ti ON h.ticker = ti.ticker AND sp.date = ti.date
            WHERE h.is_active = true
                AND sp.date = (
                    SELECT MAX(date) FROM stock_prices WHERE ticker = h.ticker
                )
            ORDER BY h.user_id, h.ticker
        """

        holdings = pd.read_sql(query, engine)

        logger.info(f"활성 보유 종목: {len(holdings)}개")

        if holdings.empty:
            logger.warning("활성 보유 종목이 없습니다.")
            return 0

        # 수익률 계산
        holdings['profit_loss_percent'] = (
            (holdings['current_price'] - holdings['avg_buy_price']) /
            holdings['avg_buy_price'] * 100
        ).round(2)

        holdings['holding_days'] = (pd.Timestamp(today) - pd.to_datetime(holdings['buy_date'])).dt.days

        # XCom으로 전달
        context['task_instance'].xcom_push(
            key='holdings',
            value=holdings.to_json(orient='records', date_format='iso')
        )

        # 사용자별 종목 수 로깅
        user_counts = holdings.groupby('user_id').size()
        for user_id, count in user_counts.items():
            logger.info(f"  User {user_id}: {count}개 종목")

        logger.info("보유 종목 조회 완료")
        return len(holdings)

    except Exception as e:
        logger.error(f"보유 종목 조회 실패: {str(e)}")
        raise


# ========================================
# Task 2: 매도 신호 감지
# ========================================

def task_detect_sell_signals(**context):
    """
    각 보유 종목에 대해 매도 신호를 감지합니다.
    """
    logger.info("="*80)
    logger.info("Task 2: 매도 신호 감지 시작")
    logger.info("="*80)

    holdings_json = context['task_instance'].xcom_pull(
        task_ids='fetch_holdings',
        key='holdings'
    )

    if not holdings_json:
        logger.warning("보유 종목 데이터가 없습니다.")
        return 0

    holdings = pd.read_json(holdings_json, orient='records')
    all_signals = []

    for _, holding in holdings.iterrows():
        try:
            signals = detect_signals_for_holding(holding)

            if signals:
                logger.info(f"  {holding['ticker']}: {len(signals)}개 신호 감지")
                for signal in signals:
                    signal['holding_id'] = holding['holding_id']
                    signal['user_id'] = holding['user_id']
                    signal['ticker'] = holding['ticker']
                    signal['company_name'] = holding['company_name']
                    signal['current_price'] = float(holding['current_price']) if pd.notna(holding['current_price']) else None
                    signal['avg_buy_price'] = float(holding['avg_buy_price']) if pd.notna(holding['avg_buy_price']) else None
                    signal['profit_loss_percent'] = float(holding['profit_loss_percent']) if pd.notna(holding['profit_loss_percent']) else None
                    signal['quantity'] = int(holding['quantity']) if pd.notna(holding['quantity']) else None
                    signal['user_email'] = holding['user_email']
                    all_signals.append(signal)

        except Exception as e:
            logger.error(f"  {holding['ticker']} 신호 감지 실패: {str(e)}")

    logger.info(f"총 {len(all_signals)}개 매도 신호 감지")

    # 우선순위별 분류
    critical = len([s for s in all_signals if s['priority'] == 'CRITICAL'])
    high = len([s for s in all_signals if s['priority'] == 'HIGH'])
    medium = len([s for s in all_signals if s['priority'] == 'MEDIUM'])

    logger.info(f"  CRITICAL: {critical}개, HIGH: {high}개, MEDIUM: {medium}개")

    context['task_instance'].xcom_push(key='signals', value=all_signals)

    return len(all_signals)


def detect_signals_for_holding(holding: pd.Series) -> list:
    """
    개별 보유 종목에 대해 매도 신호를 감지합니다.
    """
    signals = []

    current_price = holding.get('current_price')
    avg_buy_price = holding.get('avg_buy_price')
    profit_loss_pct = holding.get('profit_loss_percent')
    holding_days = holding.get('holding_days', 0)

    if pd.isna(current_price) or pd.isna(avg_buy_price):
        return signals

    # ========================================
    # Type A 신호 (리스크 관리) - CRITICAL
    # ========================================

    # A1: 고정 손절 도달
    if profit_loss_pct is not None and profit_loss_pct <= FIXED_STOP_LOSS_PCT:
        signals.append({
            'signal_type': 'FIXED_STOP',
            'priority': 'CRITICAL',
            'confidence': 0.90,
            'reason': f"고정 손절 도달: 손실률 {profit_loss_pct:.2f}% <= {FIXED_STOP_LOSS_PCT}%",
            'recommended_action': '즉시 전량 매도',
            'exit_percent': 100.0
        })

    # A2: 설정된 손절가 도달
    stop_loss_price = holding.get('stop_loss_price')
    if pd.notna(stop_loss_price) and current_price <= stop_loss_price:
        signals.append({
            'signal_type': 'STOP_LOSS_PRICE',
            'priority': 'CRITICAL',
            'confidence': 0.95,
            'reason': f"손절가 도달: 현재가 {current_price:,.0f} <= 손절가 {stop_loss_price:,.0f}",
            'recommended_action': '즉시 전량 매도',
            'exit_percent': 100.0
        })

    # A3: Time Stop
    if holding_days >= TIME_STOP_DAYS and profit_loss_pct is not None and profit_loss_pct <= 0:
        signals.append({
            'signal_type': 'TIME_STOP',
            'priority': 'HIGH',
            'confidence': 0.70,
            'reason': f"Time Stop: {holding_days}일 보유, 수익률 {profit_loss_pct:.2f}%",
            'recommended_action': '포지션 정리 검토',
            'exit_percent': 100.0
        })

    # ========================================
    # Type B 신호 (추세 종료) - HIGH
    # ========================================

    rsi = holding.get('rsi')
    macd = holding.get('macd')
    macd_signal = holding.get('macd_signal')
    ma_20 = holding.get('ma_20')
    ma_50 = holding.get('ma_50')
    volume = holding.get('volume')

    # B1: MACD 데드크로스 (양수 영역)
    if pd.notna(macd) and pd.notna(macd_signal):
        if macd < macd_signal and macd > 0:
            signals.append({
                'signal_type': 'MACD_CROSS',
                'priority': 'HIGH',
                'confidence': 0.75,
                'reason': f"MACD 데드크로스: MACD={macd:.4f} < Signal={macd_signal:.4f} (양수 영역)",
                'recommended_action': '부분 매도 또는 손절 타이트하게',
                'exit_percent': 50.0
            })

    # B2: MA 데드크로스
    if pd.notna(ma_20) and pd.notna(ma_50):
        if ma_20 < ma_50:
            signals.append({
                'signal_type': 'MA_CROSS',
                'priority': 'HIGH',
                'confidence': 0.70,
                'reason': f"MA 데드크로스: MA20={ma_20:,.0f} < MA50={ma_50:,.0f}",
                'recommended_action': '추세 전환 - 부분 매도 권고',
                'exit_percent': 50.0
            })

    # B3: RSI 70 하향 돌파 확인 (과매수 영역에서 이탈)
    if pd.notna(rsi) and 65 <= rsi < 70 and profit_loss_pct is not None and profit_loss_pct > 0:
        signals.append({
            'signal_type': 'RSI_REVERSAL',
            'priority': 'MEDIUM',
            'confidence': 0.65,
            'reason': f"RSI 과매수 영역 이탈 경고: RSI={rsi:.1f}",
            'recommended_action': '추세 약화 신호 - 모니터링 강화',
            'exit_percent': 25.0
        })

    # ========================================
    # Type C 신호 (수익 목표) - MEDIUM
    # ========================================

    # C1: RSI 과매수
    if pd.notna(rsi):
        if rsi >= 80:
            signals.append({
                'signal_type': 'RSI_OVERBOUGHT',
                'priority': 'HIGH',
                'confidence': 0.80,
                'reason': f"RSI 극단적 과매수: RSI={rsi:.1f} >= 80",
                'recommended_action': '강한 과열 - 50% 익절 권고',
                'exit_percent': 50.0
            })
        elif rsi >= RSI_OVERBOUGHT:
            signals.append({
                'signal_type': 'RSI_OVERBOUGHT',
                'priority': 'MEDIUM',
                'confidence': 0.65,
                'reason': f"RSI 과매수: RSI={rsi:.1f} >= {RSI_OVERBOUGHT}",
                'recommended_action': '과열 주의 - 25% 부분 익절 고려',
                'exit_percent': 25.0
            })

    # C2: 볼린저 밴드 상단 터치
    bb_upper = holding.get('bollinger_upper')
    if pd.notna(bb_upper) and current_price >= bb_upper:
        signals.append({
            'signal_type': 'BB_UPPER',
            'priority': 'MEDIUM',
            'confidence': 0.70,
            'reason': f"볼린저 밴드 상단 터치: 현재가 {current_price:,.0f} >= BB상단 {bb_upper:,.0f}",
            'recommended_action': '과열 구간 - 25% 부분 익절 고려',
            'exit_percent': 25.0
        })

    # C3: 익절가 도달
    take_profit_price = holding.get('take_profit_price')
    if pd.notna(take_profit_price) and current_price >= take_profit_price:
        signals.append({
            'signal_type': 'TAKE_PROFIT',
            'priority': 'MEDIUM',
            'confidence': 0.85,
            'reason': f"익절가 도달: 현재가 {current_price:,.0f} >= 익절가 {take_profit_price:,.0f}",
            'recommended_action': '목표 달성 - 익절 권고',
            'exit_percent': 50.0
        })

    # C4: R/R 목표 달성
    if profit_loss_pct is not None:
        if profit_loss_pct >= 20:
            signals.append({
                'signal_type': 'RR_TARGET',
                'priority': 'MEDIUM',
                'confidence': 0.85,
                'reason': f"R/R 3:1 목표 달성: 수익률 {profit_loss_pct:.2f}%",
                'recommended_action': '전량 매도 또는 트레일링 스톱',
                'exit_percent': 100.0
            })
        elif profit_loss_pct >= 13:
            signals.append({
                'signal_type': 'RR_TARGET',
                'priority': 'MEDIUM',
                'confidence': 0.75,
                'reason': f"R/R 2:1 목표 달성: 수익률 {profit_loss_pct:.2f}%",
                'recommended_action': '50% 청산 권고',
                'exit_percent': 50.0
            })

    return signals


# ========================================
# Task 3: 신호 저장
# ========================================

def task_save_signals(**context):
    """
    감지된 매도 신호를 데이터베이스에 저장합니다.
    """
    logger.info("="*80)
    logger.info("Task 3: 매도 신호 저장 시작")
    logger.info("="*80)

    signals = context['task_instance'].xcom_pull(
        task_ids='detect_sell_signals',
        key='signals'
    )

    if not signals:
        logger.info("저장할 신호가 없습니다.")
        return 0

    engine = get_db_engine()
    saved_count = 0

    for signal in signals:
        try:
            # 중복 체크 (오늘 같은 종목 + 같은 신호 유형)
            check_query = """
                SELECT id FROM sell_signals
                WHERE holding_id = :holding_id
                AND signal_type = :signal_type
                AND DATE(created_at) = CURRENT_DATE
            """

            with engine.connect() as conn:
                existing = conn.execute(text(check_query), {
                    'holding_id': signal['holding_id'],
                    'signal_type': signal['signal_type']
                }).fetchone()

            if existing:
                logger.debug(f"  중복 신호 스킵: {signal['ticker']} - {signal['signal_type']}")
                continue

            # 새 신호 저장
            insert_query = """
                INSERT INTO sell_signals (
                    holding_id, ticker, signal_type, priority,
                    confidence, reason, recommended_action,
                    exit_percent, current_price, status, created_at
                ) VALUES (
                    :holding_id, :ticker, :signal_type, :priority,
                    :confidence, :reason, :recommended_action,
                    :exit_percent, :current_price, 'PENDING', NOW()
                )
            """

            with engine.begin() as conn:
                conn.execute(text(insert_query), {
                    'holding_id': signal['holding_id'],
                    'ticker': signal['ticker'],
                    'signal_type': signal['signal_type'],
                    'priority': signal['priority'],
                    'confidence': signal['confidence'],
                    'reason': signal['reason'],
                    'recommended_action': signal['recommended_action'],
                    'exit_percent': signal['exit_percent'],
                    'current_price': signal['current_price']
                })

            saved_count += 1
            logger.info(f"  저장: {signal['ticker']} - {signal['signal_type']} ({signal['priority']})")

        except Exception as e:
            logger.error(f"  신호 저장 실패 ({signal.get('ticker')}): {str(e)}")

    logger.info(f"총 {saved_count}개 신호 저장 완료")

    context['task_instance'].xcom_push(key='saved_count', value=saved_count)

    return saved_count


# ========================================
# Task 4: 알림 전송
# ========================================

def task_send_notifications(**context):
    """
    매도 신호 알림을 전송합니다.
    """
    logger.info("="*80)
    logger.info("Task 4: 알림 전송 시작")
    logger.info("="*80)

    signals = context['task_instance'].xcom_pull(
        task_ids='detect_sell_signals',
        key='signals'
    )

    if not signals:
        logger.info("전송할 알림이 없습니다.")
        return 0

    # CRITICAL 및 HIGH 우선순위 신호만 즉시 알림
    urgent_signals = [s for s in signals if s['priority'] in ['CRITICAL', 'HIGH']]

    if not urgent_signals:
        logger.info("긴급 알림 대상 신호가 없습니다.")
        return 0

    sent_count = 0
    engine = get_db_engine()

    # 사용자별로 그룹화
    user_signals = {}
    for signal in urgent_signals:
        user_id = signal['user_id']
        if user_id not in user_signals:
            user_signals[user_id] = {
                'email': signal['user_email'],
                'signals': []
            }
        user_signals[user_id]['signals'].append(signal)

    for user_id, data in user_signals.items():
        try:
            email = data['email']
            user_signals_list = data['signals']

            if not email:
                logger.warning(f"User {user_id}: 이메일 없음, 스킵")
                continue

            # 이메일 메시지 생성
            message = format_sell_signal_email(user_signals_list)

            # 이메일 발송 (실제 구현 필요)
            send_email_notification(email, message)

            # 신호 상태 업데이트
            for signal in user_signals_list:
                update_query = """
                    UPDATE sell_signals
                    SET status = 'NOTIFIED', notified_at = NOW()
                    WHERE holding_id = :holding_id
                    AND signal_type = :signal_type
                    AND DATE(created_at) = CURRENT_DATE
                """

                with engine.begin() as conn:
                    conn.execute(text(update_query), {
                        'holding_id': signal['holding_id'],
                        'signal_type': signal['signal_type']
                    })

            sent_count += 1
            logger.info(f"  User {user_id}: {len(user_signals_list)}개 신호 알림 전송")

        except Exception as e:
            logger.error(f"  User {user_id} 알림 전송 실패: {str(e)}")

    logger.info(f"총 {sent_count}명에게 알림 전송 완료")
    return sent_count


def format_sell_signal_email(signals: list) -> str:
    """
    매도 신호 이메일 포맷팅
    """
    critical_signals = [s for s in signals if s['priority'] == 'CRITICAL']
    high_signals = [s for s in signals if s['priority'] == 'HIGH']

    message = f"""
<html>
<head>
<style>
    body {{ font-family: Arial, sans-serif; }}
    .critical {{ color: red; font-weight: bold; }}
    .high {{ color: orange; font-weight: bold; }}
    table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
    th {{ background-color: #4CAF50; color: white; }}
    .profit {{ color: green; }}
    .loss {{ color: red; }}
</style>
</head>
<body>
<h2>매도 신호 알림</h2>
<p>발생 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
"""

    if critical_signals:
        message += """
<h3 class="critical">CRITICAL - 즉시 대응 필요</h3>
<table>
<tr><th>종목</th><th>현재가</th><th>수익률</th><th>신호</th><th>권고</th></tr>
"""
        for s in critical_signals:
            pnl_class = 'profit' if s['profit_loss_percent'] > 0 else 'loss'
            message += f"""
<tr>
    <td>{s['company_name']} ({s['ticker']})</td>
    <td>{s['current_price']:,.0f}원</td>
    <td class="{pnl_class}">{s['profit_loss_percent']:+.2f}%</td>
    <td>{s['reason']}</td>
    <td><strong>{s['recommended_action']}</strong></td>
</tr>
"""
        message += "</table>"

    if high_signals:
        message += """
<h3 class="high">HIGH - 주의 필요</h3>
<table>
<tr><th>종목</th><th>현재가</th><th>수익률</th><th>신호</th><th>권고</th></tr>
"""
        for s in high_signals:
            pnl_class = 'profit' if s['profit_loss_percent'] > 0 else 'loss'
            message += f"""
<tr>
    <td>{s['company_name']} ({s['ticker']})</td>
    <td>{s['current_price']:,.0f}원</td>
    <td class="{pnl_class}">{s['profit_loss_percent']:+.2f}%</td>
    <td>{s['reason']}</td>
    <td>{s['recommended_action']}</td>
</tr>
"""
        message += "</table>"

    message += """
<hr>
<p><small>이 알림은 HappyStockLife ATS 매도 전략 프레임워크에 의해 자동 생성되었습니다.</small></p>
</body>
</html>
"""
    return message


def send_email_notification(email: str, message: str):
    """
    이메일 알림 전송
    """
    import smtplib
    from email.mime.text import MIMEText
    from email.mime.multipart import MIMEMultipart

    # 환경 변수에서 설정 로드
    smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
    smtp_port = int(os.getenv('SMTP_PORT', '587'))
    smtp_user = os.getenv('SMTP_USER', '')
    smtp_password = os.getenv('SMTP_PASSWORD', '')

    if not smtp_user or not smtp_password:
        logger.warning("SMTP 설정이 없습니다. 이메일 발송을 건너뜁니다.")
        return

    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = '[HappyStockLife] 매도 신호 알림'
        msg['From'] = smtp_user
        msg['To'] = email

        html_part = MIMEText(message, 'html')
        msg.attach(html_part)

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)

        logger.info(f"이메일 발송 완료: {email}")

    except Exception as e:
        logger.error(f"이메일 발송 실패 ({email}): {str(e)}")
        raise


# ========================================
# DAG Task 정의
# ========================================

fetch_task = PythonOperator(
    task_id='fetch_holdings',
    python_callable=task_fetch_holdings,
    provide_context=True,
    dag=dag
)

detect_task = PythonOperator(
    task_id='detect_sell_signals',
    python_callable=task_detect_sell_signals,
    provide_context=True,
    dag=dag
)

save_task = PythonOperator(
    task_id='save_signals',
    python_callable=task_save_signals,
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

fetch_task >> detect_task >> save_task >> notify_task
