"""
Trading Signal Monitoring DAG
자동매매 시그널 모니터링 및 알림
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
import sys
import os
import logging

# Add backend path
sys.path.append('/app')

from trading_service.signal_detector import SignalDetector
from trading_service.notification_service import NotificationService

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

default_args = {
    'owner': 'trading-system',
    'depends_on_past': False,
    'start_date': datetime(2025, 10, 4),
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=2),
}

dag = DAG(
    'trading_signal_monitoring',
    default_args=default_args,
    description='자동매매 시그널 감지 및 알림',
    schedule_interval='*/30 9-15 * * 1-5',  # 월-금, 9시-15시, 30분마다
    catchup=False,
    max_active_runs=1,
    tags=['trading', 'signals', 'monitoring']
)

# 설정
DB_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"

# 알림 설정
NOTIFICATION_CONFIG = {
    'email': {
        'enabled': True,  # 이메일 활성화 여부
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'sender_email': os.getenv('SMTP_EMAIL', ''),  # 환경 변수로 설정
        'sender_password': os.getenv('SMTP_PASSWORD', '')  # 환경 변수로 설정
    },
    'kakao': {
        'enabled': False,  # 카카오톡 활성화 여부 (API 키 필요)
        'rest_api_key': os.getenv('KAKAO_REST_API_KEY', ''),
        'access_token': os.getenv('KAKAO_ACCESS_TOKEN', '')
    }
}

# 수신자 설정
RECIPIENTS = {
    'email': os.getenv('NOTIFICATION_EMAIL', 'your-email@example.com'),
    'kakao': os.getenv('NOTIFICATION_KAKAO_ID', '')
}

def detect_and_notify_buy_signals(**context):
    """매수 시그널 감지 및 알림"""
    logger.info("Detecting buy signals...")

    try:
        detector = SignalDetector(DB_URL)
        notifier = NotificationService(DB_URL, NOTIFICATION_CONFIG)

        # 매수 시그널 감지
        buy_signals = detector.detect_buy_signals()

        logger.info(f"Found {len(buy_signals)} buy signals")

        # 시그널 저장 및 알림
        for signal in buy_signals:
            try:
                # 시그널 저장
                signal_id = detector.save_signal(signal)

                # 알림 발송
                channels = []
                if NOTIFICATION_CONFIG['email']['enabled']:
                    channels.append('email')
                if NOTIFICATION_CONFIG['kakao']['enabled']:
                    channels.append('kakao')

                if channels:
                    notifier.send_signal_notification(
                        signal,
                        signal_id,
                        channels,
                        RECIPIENTS
                    )
                    logger.info(f"Notification sent for {signal['ticker']}")
                else:
                    logger.warning("No notification channels enabled")

            except Exception as e:
                logger.error(f"Error processing signal for {signal['ticker']}: {e}")
                continue

        return len(buy_signals)

    except Exception as e:
        logger.error(f"Error in detect_and_notify_buy_signals: {e}")
        raise

def detect_and_notify_sell_signals(**context):
    """매도 시그널 감지 및 알림"""
    logger.info("Detecting sell signals...")

    try:
        detector = SignalDetector(DB_URL)
        notifier = NotificationService(DB_URL, NOTIFICATION_CONFIG)

        # 매도 시그널 감지
        sell_signals = detector.detect_sell_signals()

        logger.info(f"Found {len(sell_signals)} sell signals")

        # 시그널 저장 및 알림
        for signal in buy_signals:
            try:
                signal_id = detector.save_signal(signal)

                channels = []
                if NOTIFICATION_CONFIG['email']['enabled']:
                    channels.append('email')
                if NOTIFICATION_CONFIG['kakao']['enabled']:
                    channels.append('kakao')

                if channels:
                    notifier.send_signal_notification(
                        signal,
                        signal_id,
                        channels,
                        RECIPIENTS
                    )
                    logger.info(f"Notification sent for {signal['ticker']}")

            except Exception as e:
                logger.error(f"Error processing signal for {signal['ticker']}: {e}")
                continue

        return len(sell_signals)

    except Exception as e:
        logger.error(f"Error in detect_and_notify_sell_signals: {e}")
        raise

def detect_and_notify_stop_loss_signals(**context):
    """손절 시그널 감지 및 알림"""
    logger.info("Detecting stop-loss signals...")

    try:
        detector = SignalDetector(DB_URL)
        notifier = NotificationService(DB_URL, NOTIFICATION_CONFIG)

        # 손절 시그널 감지
        stop_loss_signals = detector.detect_stop_loss_signals()

        logger.info(f"Found {len(stop_loss_signals)} stop-loss signals")

        # 시그널 저장 및 알림 (손절은 우선순위 높음)
        for signal in stop_loss_signals:
            try:
                signal_id = detector.save_signal(signal)

                channels = []
                if NOTIFICATION_CONFIG['email']['enabled']:
                    channels.append('email')
                if NOTIFICATION_CONFIG['kakao']['enabled']:
                    channels.append('kakao')

                if channels:
                    notifier.send_signal_notification(
                        signal,
                        signal_id,
                        channels,
                        RECIPIENTS
                    )
                    logger.info(f"URGENT notification sent for stop-loss: {signal['ticker']}")

            except Exception as e:
                logger.error(f"Error processing stop-loss signal for {signal['ticker']}: {e}")
                continue

        return len(stop_loss_signals)

    except Exception as e:
        logger.error(f"Error in detect_and_notify_stop_loss_signals: {e}")
        raise

def generate_daily_summary(**context):
    """일일 매매 요약 생성"""
    logger.info("Generating daily trading summary...")

    try:
        from trading_service.position_manager import PositionManager

        manager = PositionManager(DB_URL)
        summary = manager.get_performance_summary()

        logger.info(f"Trading Summary: {summary}")

        # 요약 정보를 XCom에 푸시 (다른 태스크에서 사용 가능)
        context['task_instance'].xcom_push(key='daily_summary', value=summary)

        return summary

    except Exception as e:
        logger.error(f"Error generating daily summary: {e}")
        raise

# Define tasks
buy_signals_task = PythonOperator(
    task_id='detect_buy_signals',
    python_callable=detect_and_notify_buy_signals,
    dag=dag,
)

sell_signals_task = PythonOperator(
    task_id='detect_sell_signals',
    python_callable=detect_and_notify_sell_signals,
    dag=dag,
)

stop_loss_task = PythonOperator(
    task_id='detect_stop_loss_signals',
    python_callable=detect_and_notify_stop_loss_signals,
    dag=dag,
)

summary_task = PythonOperator(
    task_id='generate_daily_summary',
    python_callable=generate_daily_summary,
    dag=dag,
)

# Task dependencies
# 병렬로 시그널 감지, 완료 후 요약
[buy_signals_task, sell_signals_task, stop_loss_task] >> summary_task
