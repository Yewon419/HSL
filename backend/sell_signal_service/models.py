"""
Sell Signal Service Models
매도 신호 서비스 데이터 모델
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime, date
from decimal import Decimal


class SellSignalType(str, Enum):
    """매도 신호 유형 (3단계 분류)"""
    # Type A: 리스크 관리 (Hard Stop) - P0 자본 보존
    TYPE_A_ATR_STOP = "ATR_STOP"           # ATR 기반 동적 손절
    TYPE_A_FIXED_STOP = "FIXED_STOP"       # 고정 손실률 손절
    TYPE_A_TIME_STOP = "TIME_STOP"         # 시간 기반 청산
    TYPE_A_VAR_BREACH = "VAR_BREACH"       # VaR 초과
    TYPE_A_MDD_BREACH = "MDD_BREACH"       # MDD 초과
    TYPE_A_VI_TRIGGER = "VI_TRIGGER"       # VI 발동
    TYPE_A_SIDECAR = "SIDECAR"             # 사이드카 발동

    # Type B: 추세 종료 (Trend Termination) - P1 추세 포착
    TYPE_B_SAR_REVERSAL = "SAR_REVERSAL"       # Parabolic SAR 반전
    TYPE_B_MACD_CROSS = "MACD_CROSS"           # MACD 데드크로스
    TYPE_B_MACD_ROLLOVER = "MACD_ROLLOVER"     # MACD 히스토그램 수축
    TYPE_B_DIVERGENCE = "DIVERGENCE"           # RSI/MACD 다이버전스
    TYPE_B_DONCHIAN_BREAK = "DONCHIAN_BREAK"   # Donchian Channel 하단 이탈
    TYPE_B_BUYING_CLIMAX = "BUYING_CLIMAX"     # 매수 절정
    TYPE_B_VOLUME_EXHAUSTION = "VOLUME_EXHAUSTION"  # 거래량 소진
    TYPE_B_CANDLESTICK = "CANDLESTICK"         # 캔들스틱 반전 패턴
    TYPE_B_MA_CROSS = "MA_CROSS"               # 이동평균 데드크로스

    # Type C: 목표 수익 실현 (Take-Profit) - P1 이익 확보
    TYPE_C_RR_TARGET = "RR_TARGET"             # R/R 목표 달성
    TYPE_C_FIBONACCI = "FIBONACCI"             # 피보나치 확장 도달
    TYPE_C_BB_UPPER = "BB_UPPER"               # 볼린저 밴드 상단 터치
    TYPE_C_RSI_OVERBOUGHT = "RSI_OVERBOUGHT"   # RSI 과매수


class SignalPriority(str, Enum):
    """신호 우선순위"""
    CRITICAL = "CRITICAL"    # 즉시 실행 필요 (Type A)
    HIGH = "HIGH"            # 높은 우선순위 (Type B)
    MEDIUM = "MEDIUM"        # 중간 우선순위 (Type C)
    LOW = "LOW"              # 모니터링 (확인 필요)


class MarketRegime(str, Enum):
    """시장 레짐 분류"""
    TRENDING = "TRENDING"      # 강한 추세 (ADX >= 25)
    RANGING = "RANGING"        # 횡보/약세 (ADX < 20)
    VOLATILE = "VOLATILE"      # 변동성 확장


class OrderType(str, Enum):
    """주문 유형"""
    MARKET = "MARKET"          # 시장가
    LIMIT = "LIMIT"            # 지정가
    STOP_LOSS = "STOP_LOSS"    # 손절가


class HoldingStatus(BaseModel):
    """보유 종목 상태"""
    holding_id: int
    user_id: int
    ticker: str
    company_name: Optional[str] = None
    quantity: int
    avg_buy_price: float
    buy_date: date
    current_price: float
    profit_loss_amount: float
    profit_loss_percent: float
    holding_days: int

    # 기술적 지표
    rsi: Optional[float] = None
    macd: Optional[float] = None
    macd_signal: Optional[float] = None
    macd_histogram: Optional[float] = None
    ma_20: Optional[float] = None
    ma_50: Optional[float] = None
    ma_200: Optional[float] = None
    bollinger_upper: Optional[float] = None
    bollinger_lower: Optional[float] = None
    atr: Optional[float] = None
    adx: Optional[float] = None
    volume: Optional[int] = None
    avg_volume_20: Optional[float] = None

    # 손절/익절 설정
    stop_loss_price: Optional[float] = None
    take_profit_price: Optional[float] = None


class SellSignal(BaseModel):
    """개별 매도 신호"""
    signal_type: SellSignalType
    priority: SignalPriority
    confidence: float = Field(ge=0, le=1, description="신뢰도 (0~1)")
    reason: str
    recommended_action: str
    exit_percent: float = Field(ge=0, le=100, description="청산 비율 (%)")
    order_type: OrderType = OrderType.MARKET
    target_price: Optional[float] = None


class SellSignalResponse(BaseModel):
    """매도 신호 응답"""
    holding: HoldingStatus
    signals: List[SellSignal]
    total_score: float = Field(description="총 신호 점수")
    recommendation: str = Field(description="종합 권고사항")
    market_regime: MarketRegime
    urgency_level: SignalPriority

    # 동적 손절매 정보
    atr_stop_price: Optional[float] = None
    trailing_stop_price: Optional[float] = None

    # 피보나치 목표가
    fib_127_price: Optional[float] = None
    fib_161_price: Optional[float] = None
    fib_261_price: Optional[float] = None

    created_at: datetime = Field(default_factory=datetime.now)


class SellSignalSummary(BaseModel):
    """매도 신호 요약"""
    total_holdings: int
    critical_signals: int
    high_signals: int
    medium_signals: int
    holdings_with_signals: List[SellSignalResponse]
    market_regime: MarketRegime
    portfolio_risk_level: str
    generated_at: datetime = Field(default_factory=datetime.now)


class ATRConfig(BaseModel):
    """ATR 설정"""
    period: int = 14
    multiplier: float = 2.0

    # 시장별 권장 승수
    kospi_multiplier: float = 2.0    # KOSPI: 1.8~2.3
    kosdaq_multiplier: float = 2.5   # KOSDAQ: 2.5~3.0


class SignalWeights(BaseModel):
    """신호 가중치 설정"""
    # Type A (리스크 관리) - 최고 우선순위
    type_a_weight: float = 1.0

    # Type B (추세 종료)
    rsi_divergence_weight: float = 0.3
    macd_cross_weight: float = 0.3
    macd_rollover_weight: float = 0.2
    volume_climax_weight: float = 0.25
    candlestick_weight: float = 0.15

    # Type C (수익 목표)
    rr_target_weight: float = 0.4
    fibonacci_weight: float = 0.35
    bb_upper_weight: float = 0.2
    rsi_overbought_weight: float = 0.25


class PartialExitStrategy(BaseModel):
    """부분 매도 전략"""
    # 피보나치 단계적 익절
    fib_127_exit_pct: float = 30.0    # 127.2% 도달 시 30% 청산
    fib_161_exit_pct: float = 50.0    # 161.8% 도달 시 50% 청산
    fib_261_exit_pct: float = 100.0   # 261.8% 도달 시 전량 청산

    # R/R 기반 익절
    rr_1_exit_pct: float = 33.0       # 1R 달성 시 33% 청산
    rr_2_exit_pct: float = 33.0       # 2R 달성 시 추가 33% 청산
    rr_3_exit_pct: float = 34.0       # 3R 달성 시 잔여 청산
