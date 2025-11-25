"""
Sell Signal Service
매도 타이밍 알림 서비스

ATS(자동매매 시스템) 매도 전략 통합 프레임워크 기반
3계층 알고리즘 아키텍처 구현:
- 제1계층: 시스템 제어 (VaR/MDD, VI/사이드카)
- 제2계층: 상황 인식 (시장 레짐, MTF 분석)
- 제3계층: 실행 신호 (Type A/B/C 매도 신호)
"""

from .detector import SellSignalDetector
from .models import (
    SellSignalType,
    SignalPriority,
    MarketRegime,
    SellSignalResponse,
    HoldingStatus
)

__all__ = [
    'SellSignalDetector',
    'SellSignalType',
    'SignalPriority',
    'MarketRegime',
    'SellSignalResponse',
    'HoldingStatus'
]
