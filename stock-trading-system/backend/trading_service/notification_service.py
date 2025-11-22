"""
Notification Service
카카오톡 및 이메일 알림 서비스
"""

import smtplib
import requests
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Dict, List, Optional
from datetime import datetime
from sqlalchemy import create_engine, text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NotificationService:
    """
    알림 서비스

    지원 채널:
    - 이메일 (SMTP)
    - 카카오톡 (KakaoTalk API)
    """

    def __init__(self, db_url: str, config: Dict):
        self.engine = create_engine(db_url)
        self.config = config

    def send_email(self, recipient: str, subject: str, message: str) -> bool:
        """이메일 발송"""
        try:
            email_config = self.config.get('email', {})

            if not email_config.get('enabled', False):
                logger.warning("Email notifications disabled")
                return False

            smtp_server = email_config.get('smtp_server', 'smtp.gmail.com')
            smtp_port = email_config.get('smtp_port', 587)
            sender_email = email_config.get('sender_email')
            sender_password = email_config.get('sender_password')

            if not sender_email or not sender_password:
                logger.error("Email credentials not configured")
                return False

            # 이메일 작성
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = sender_email
            msg['To'] = recipient

            # HTML 본문
            html_body = f"""
            <html>
              <head></head>
              <body>
                <h2>{subject}</h2>
                <pre>{message}</pre>
                <hr>
                <p style="color: gray; font-size: 12px;">
                    자동매매 시스템 알림<br>
                    발송 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </p>
              </body>
            </html>
            """

            part = MIMEText(html_body, 'html')
            msg.attach(part)

            # 발송
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)

            logger.info(f"Email sent to {recipient}")
            return True

        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False

    def send_kakao(self, recipient: str, message: str) -> bool:
        """카카오톡 발송 (KakaoTalk API)"""
        try:
            kakao_config = self.config.get('kakao', {})

            if not kakao_config.get('enabled', False):
                logger.warning("KakaoTalk notifications disabled")
                return False

            # KakaoTalk API 설정
            rest_api_key = kakao_config.get('rest_api_key')
            access_token = kakao_config.get('access_token')

            if not rest_api_key or not access_token:
                logger.error("KakaoTalk credentials not configured")
                return False

            # 카카오톡 메시지 전송 API 호출
            url = "https://kapi.kakao.com/v2/api/talk/memo/default/send"

            headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/x-www-form-urlencoded"
            }

            # 템플릿 객체 (기본 템플릿)
            template = {
                "object_type": "text",
                "text": message,
                "link": {
                    "web_url": "http://localhost:8000/rsi_ma_strategy.html",
                    "mobile_web_url": "http://localhost:8000/rsi_ma_strategy.html"
                },
                "button_title": "시그널 확인"
            }

            import json
            data = {
                "template_object": json.dumps(template)
            }

            response = requests.post(url, headers=headers, data=data)

            if response.status_code == 200:
                logger.info(f"KakaoTalk sent successfully")
                return True
            else:
                logger.error(f"KakaoTalk send failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending KakaoTalk: {e}")
            return False

    def send_slack(self, webhook_url: str, message: str) -> bool:
        """Slack 발송 (Webhook)"""
        try:
            slack_config = self.config.get('slack', {})

            if not slack_config.get('enabled', False):
                logger.warning("Slack notifications disabled")
                return False

            webhook = slack_config.get('webhook_url') or webhook_url

            if not webhook:
                logger.error("Slack webhook URL not configured")
                return False

            # Slack 메시지 포맷
            payload = {
                "text": message,
                "username": "자동매매 시스템",
                "icon_emoji": ":chart_with_upwards_trend:",
                "attachments": [
                    {
                        "color": "#36a64f",
                        "footer": "Stock Trading System",
                        "footer_icon": "https://platform.slack-edge.com/img/default_application_icon.png",
                        "ts": int(datetime.now().timestamp())
                    }
                ]
            }

            response = requests.post(webhook, json=payload)

            if response.status_code == 200:
                logger.info(f"Slack message sent successfully")
                return True
            else:
                logger.error(f"Slack send failed: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            logger.error(f"Error sending Slack: {e}")
            return False

    def format_buy_signal_message(self, signal: Dict) -> str:
        """매수 시그널 메시지 포맷"""
        return f"""
🔔 매수 시그널 발생!

📊 종목 정보:
  - 종목: {signal['ticker']} ({signal.get('company_name', 'N/A')})
  - 현재가: {signal['current_price']:,.0f}원
  - 목표가: {signal.get('target_price', 0):,.0f}원 (+10%)
  - 손절가: {signal.get('stop_loss_price', 0):,.0f}원 (-5%)

📈 기술적 지표:
  - RSI: {signal.get('rsi', 0):.2f} (< 30, 과매도)
  - MA20: {signal.get('ma_20', 0):,.0f}원
  - MA50: {signal.get('ma_50', 0):,.0f}원
  - MA20 > MA50: ✅

💡 시그널 이유:
{signal.get('reason', 'N/A')}

⏰ 발생 시각: {signal['signal_date'].strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_sell_signal_message(self, signal: Dict) -> str:
        """매도 시그널 메시지 포맷"""
        profit_emoji = "📈" if signal.get('profit_rate', 0) > 0 else "📉"

        return f"""
🔔 매도 시그널 발생!

📊 종목 정보:
  - 종목: {signal['ticker']} ({signal.get('company_name', 'N/A')})
  - 매수가: {signal.get('buy_price', 0):,.0f}원
  - 현재가: {signal['current_price']:,.0f}원

{profit_emoji} 수익 정보:
  - 손익: {signal.get('profit_loss', 0):,.0f}원
  - 수익률: {signal.get('profit_rate', 0):.2f}%
  - 수량: {signal.get('quantity', 0)}주

📈 기술적 지표:
  - RSI: {signal.get('rsi', 0):.2f} (> 70, 과매수)

💡 시그널 이유:
{signal.get('reason', 'N/A')}

⏰ 발생 시각: {signal['signal_date'].strftime('%Y-%m-%d %H:%M:%S')}
"""

    def format_stop_loss_message(self, signal: Dict) -> str:
        """손절 시그널 메시지 포맷"""
        return f"""
⚠️ 손절 시그널 발생!

📊 종목 정보:
  - 종목: {signal['ticker']} ({signal.get('company_name', 'N/A')})
  - 매수가: {signal.get('buy_price', 0):,.0f}원
  - 현재가: {signal['current_price']:,.0f}원
  - 손절가: {signal.get('stop_loss_price', 0):,.0f}원

📉 손실 정보:
  - 손실: {signal.get('profit_loss', 0):,.0f}원
  - 손실률: {signal.get('loss_rate', 0):.2f}%
  - 수량: {signal.get('quantity', 0)}주
  - 보유 기간: {signal.get('buy_date', 'N/A')}부터

💡 시그널 이유:
{signal.get('reason', 'N/A')}

⚡ 즉시 매도 검토가 필요합니다!

⏰ 발생 시각: {signal['signal_date'].strftime('%Y-%m-%d %H:%M:%S')}
"""

    def send_signal_notification(
        self,
        signal: Dict,
        signal_id: int,
        channels: List[str],
        recipients: Dict[str, str]
    ) -> bool:
        """
        시그널 알림 발송

        Args:
            signal: 시그널 정보
            signal_id: 시그널 ID
            channels: 알림 채널 리스트 ['email', 'kakao']
            recipients: 수신자 정보 {'email': 'user@example.com', 'kakao': 'user_id'}

        Returns:
            성공 여부
        """
        signal_type = signal['signal_type']

        # 메시지 포맷
        if signal_type == 'BUY':
            message = self.format_buy_signal_message(signal)
            subject = f"[매수] {signal['ticker']} 매수 시그널"
        elif signal_type == 'SELL':
            message = self.format_sell_signal_message(signal)
            subject = f"[매도] {signal['ticker']} 매도 시그널"
        elif signal_type == 'STOP_LOSS':
            message = self.format_stop_loss_message(signal)
            subject = f"[손절] {signal['ticker']} 손절 시그널"
        else:
            logger.error(f"Unknown signal type: {signal_type}")
            return False

        all_success = True

        # 이메일 발송
        if 'email' in channels and recipients.get('email'):
            email_success = self.send_email(recipients['email'], subject, message)
            self._log_notification(signal_id, 'email', recipients['email'], subject, message, email_success)
            all_success = all_success and email_success

        # 카카오톡 발송
        if 'kakao' in channels and recipients.get('kakao'):
            kakao_message = f"{subject}\n\n{message}"
            kakao_success = self.send_kakao(recipients['kakao'], kakao_message)
            self._log_notification(signal_id, 'kakao', recipients['kakao'], subject, kakao_message, kakao_success)
            all_success = all_success and kakao_success

        # Slack 발송
        if 'slack' in channels and recipients.get('slack'):
            slack_message = f"*{subject}*\n\n```{message}```"
            slack_success = self.send_slack(recipients['slack'], slack_message)
            self._log_notification(signal_id, 'slack', recipients['slack'], subject, slack_message, slack_success)
            all_success = all_success and slack_success

        # 시그널 상태 업데이트
        if all_success:
            self._update_signal_status(signal_id, 'NOTIFIED', ','.join(channels))

        return all_success

    def _log_notification(
        self,
        signal_id: int,
        channel: str,
        recipient: str,
        subject: str,
        message: str,
        success: bool,
        error_message: Optional[str] = None
    ):
        """알림 로그 저장"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    INSERT INTO notification_logs (
                        signal_id, channel, recipient,
                        subject, message,
                        sent_at, success, error_message
                    ) VALUES (
                        :signal_id, :channel, :recipient,
                        :subject, :message,
                        :sent_at, :success, :error_message
                    )
                """), {
                    'signal_id': signal_id,
                    'channel': channel,
                    'recipient': recipient,
                    'subject': subject,
                    'message': message,
                    'sent_at': datetime.now(),
                    'success': success,
                    'error_message': error_message
                })
        except Exception as e:
            logger.error(f"Error logging notification: {e}")

    def _update_signal_status(self, signal_id: int, status: str, channels: str):
        """시그널 상태 업데이트"""
        try:
            with self.engine.begin() as conn:
                conn.execute(text("""
                    UPDATE trading_signals
                    SET status = :status,
                        notified_at = :notified_at,
                        notification_channels = :channels
                    WHERE id = :signal_id
                """), {
                    'signal_id': signal_id,
                    'status': status,
                    'notified_at': datetime.now(),
                    'channels': channels
                })
        except Exception as e:
            logger.error(f"Error updating signal status: {e}")
