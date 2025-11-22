"""
Trading Service Configuration Example
실제 사용 시 config.py로 복사하고 값을 설정하세요
"""

# 데이터베이스 설정
DATABASE_URL = "postgresql://admin:admin123@postgres:5432/stocktrading"

# 이메일 설정 (Gmail 예시)
EMAIL_CONFIG = {
    'enabled': True,
    'smtp_server': 'smtp.gmail.com',
    'smtp_port': 587,
    'sender_email': 'your-email@gmail.com',  # 발송자 이메일
    'sender_password': 'your-app-password',  # Gmail 앱 비밀번호 (https://support.google.com/accounts/answer/185833)
}

# 카카오톡 설정
# 카카오 개발자 센터에서 앱 생성 후 설정: https://developers.kakao.com/
KAKAO_CONFIG = {
    'enabled': False,  # 사용하려면 True로 변경
    'rest_api_key': 'your-kakao-rest-api-key',
    'access_token': 'your-kakao-access-token',  # 사용자 액세스 토큰
}

# 알림 수신자 설정
NOTIFICATION_RECIPIENTS = {
    'email': 'recipient@example.com',  # 수신자 이메일
    'kakao_id': '',  # 카카오 사용자 ID (선택)
}

# 매매 조건 설정
TRADING_RULES = {
    'buy': {
        'rsi_max': 30,  # RSI < 30 (과매도)
        'ma_condition': 'ma_20 > ma_50',  # MA20 > MA50
        'min_price': 1000,  # 최소 주가
        'min_volume': 10000,  # 최소 거래량
    },
    'sell': {
        'rsi_min': 70,  # RSI > 70 (과매수)
    },
    'stop_loss': {
        'loss_rate': 0.05,  # 5% 손실 시 손절
    },
    'take_profit': {
        'profit_rate': 0.10,  # 10% 수익 목표
    }
}

# 알림 채널 (활성화할 채널 선택)
NOTIFICATION_CHANNELS = ['email']  # ['email', 'kakao']

# Airflow 스케줄 (시장 운영 시간)
MONITORING_SCHEDULE = {
    'interval_minutes': 30,  # 30분마다
    'start_hour': 9,  # 오전 9시부터
    'end_hour': 15,  # 오후 3시까지
    'weekdays': [1, 2, 3, 4, 5],  # 월-금
}
