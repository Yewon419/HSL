"""
Trading Service Database Models
"""

from sqlalchemy import Column, Integer, String, Numeric, DateTime, Boolean, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import enum

Base = declarative_base()

class SignalType(str, enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    STOP_LOSS = "STOP_LOSS"

class SignalStatus(str, enum.Enum):
    PENDING = "PENDING"
    NOTIFIED = "NOTIFIED"
    EXECUTED = "EXECUTED"
    CANCELLED = "CANCELLED"

class PositionStatus(str, enum.Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"

class TradingSignal(Base):
    """매매 시그널"""
    __tablename__ = 'trading_signals'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)
    signal_type = Column(Enum(SignalType), nullable=False)
    signal_date = Column(DateTime, nullable=False, default=datetime.now)

    # 가격 정보
    current_price = Column(Numeric(10, 2), nullable=False)
    target_price = Column(Numeric(10, 2))  # 목표가
    stop_loss_price = Column(Numeric(10, 2))  # 손절가

    # 지표 정보
    rsi = Column(Numeric(6, 2))
    ma_20 = Column(Numeric(10, 2))
    ma_50 = Column(Numeric(10, 2))

    # 상태
    status = Column(Enum(SignalStatus), default=SignalStatus.PENDING)

    # 알림
    notified_at = Column(DateTime)
    notification_channels = Column(String(100))  # 'email,kakao'

    # 메타데이터
    reason = Column(String(500))  # 시그널 발생 이유
    created_at = Column(DateTime, default=datetime.now)

class TradingPosition(Base):
    """보유 포지션"""
    __tablename__ = 'trading_positions'

    id = Column(Integer, primary_key=True, autoincrement=True)
    ticker = Column(String(10), nullable=False)

    # 매수 정보
    buy_date = Column(DateTime, nullable=False)
    buy_price = Column(Numeric(10, 2), nullable=False)
    quantity = Column(Integer, nullable=False)

    # 손익 관리
    target_price = Column(Numeric(10, 2))  # 목표가
    stop_loss_price = Column(Numeric(10, 2))  # 손절가

    # 매도 정보
    sell_date = Column(DateTime)
    sell_price = Column(Numeric(10, 2))

    # 수익률
    profit_loss = Column(Numeric(12, 2))  # 손익
    profit_loss_rate = Column(Numeric(6, 2))  # 수익률(%)

    # 상태
    status = Column(Enum(PositionStatus), default=PositionStatus.OPEN)

    # 메타데이터
    notes = Column(String(500))
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

class NotificationLog(Base):
    """알림 로그"""
    __tablename__ = 'notification_logs'

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(Integer, ForeignKey('trading_signals.id'))

    channel = Column(String(20))  # 'email', 'kakao'
    recipient = Column(String(100))

    subject = Column(String(200))
    message = Column(String(2000))

    sent_at = Column(DateTime, default=datetime.now)
    success = Column(Boolean, default=False)
    error_message = Column(String(500))
