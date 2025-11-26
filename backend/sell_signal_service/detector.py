"""
Sell Signal Detector
ATS 매도 전략 통합 프레임워크 기반 매도 신호 감지기

3계층 알고리즘 아키텍처:
- 제1계층 (시스템 제어): VaR/MDD 초과, VI/사이드카 발동
- 제2계층 (상황 인식): 시장 레짐 분류, MTF 분석, ATR 승수 동적 조정
- 제3계층 (실행 신호): Type A/B/C 매도 신호
"""

from sqlalchemy import create_engine, text
from datetime import datetime, date, timedelta
import logging
from typing import List, Dict, Optional, Tuple
import pandas as pd
import numpy as np

from .models import (
    SellSignalType,
    SignalPriority,
    MarketRegime,
    OrderType,
    HoldingStatus,
    SellSignal,
    SellSignalResponse,
    SellSignalSummary,
    ATRConfig,
    SignalWeights
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SellSignalDetector:
    """
    매도 신호 감지기

    ATS 매도 전략 프레임워크 기반:
    - Type A: 리스크 관리 (Hard Stop) - P0 자본 보존
    - Type B: 추세 종료 (Trend Termination) - P1 추세 포착
    - Type C: 목표 수익 실현 (Take-Profit) - P1 이익 확보
    """

    def __init__(self, db_url: str):
        self.engine = create_engine(db_url)
        self.atr_config = ATRConfig()
        self.signal_weights = SignalWeights()

        # 임계값 설정
        self.rsi_overbought = 70
        self.rsi_extreme = 80
        self.volume_climax_multiplier = 2.0
        self.adx_trending_threshold = 25
        self.adx_ranging_threshold = 20

    # ============================================================
    # 제2계층: 시장 레짐 분류
    # ============================================================

    def classify_market_regime(self, adx: Optional[float], atr_percentile: Optional[float]) -> MarketRegime:
        """
        시장 레짐 분류

        - ADX >= 25: 추세 존재
        - ADX < 20: 횡보/약세
        - ATR 상위 20%: 변동성 확장
        """
        if adx is None:
            return MarketRegime.RANGING

        if adx >= self.adx_trending_threshold:
            if atr_percentile and atr_percentile > 80:
                return MarketRegime.VOLATILE
            return MarketRegime.TRENDING
        return MarketRegime.RANGING

    def get_atr_multiplier(self, regime: MarketRegime, market_type: str = 'KOSPI') -> float:
        """
        레짐에 따른 ATR 승수 반환

        강한 추세: 2.5~3.0 (추세 유지)
        횡보/약세: 1.5~2.0 (타이트한 손절)
        변동성 확장: 3.0 이상 (노이즈 필터링)
        """
        base_mult = self.atr_config.kosdaq_multiplier if market_type == 'KOSDAQ' else self.atr_config.kospi_multiplier

        if regime == MarketRegime.VOLATILE:
            return max(3.0, base_mult * 1.2)
        elif regime == MarketRegime.TRENDING:
            return base_mult * 1.1
        else:  # RANGING
            return base_mult * 0.8

    # ============================================================
    # 제3계층: Type A 신호 (리스크 관리)
    # ============================================================

    def detect_type_a_signals(self, holding: HoldingStatus, regime: MarketRegime) -> List[SellSignal]:
        """
        Type A 신호 감지 (리스크 관리 - 최고 우선순위)

        - ATR 기반 동적 손절
        - 고정 손실률 손절
        - Time Stop
        """
        signals = []

        # ATR 기반 동적 손절
        if holding.atr:
            market_type = 'KOSDAQ' if 'KOSDAQ' in str(holding.ticker) else 'KOSPI'
            atr_mult = self.get_atr_multiplier(regime, market_type)
            atr_stop = holding.avg_buy_price - (holding.atr * atr_mult)

            if holding.current_price <= atr_stop:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_A_ATR_STOP,
                    priority=SignalPriority.CRITICAL,
                    confidence=0.95,
                    reason=f"ATR 손절가 도달: 현재가 {holding.current_price:,.0f} <= ATR Stop {atr_stop:,.0f} (ATR={holding.atr:.2f}, 승수={atr_mult})",
                    recommended_action="즉시 전량 매도",
                    exit_percent=100.0,
                    order_type=OrderType.MARKET,
                    target_price=atr_stop
                ))

        # 고정 손실률 손절 (-5%)
        fixed_stop_pct = -5.0
        if holding.profit_loss_percent <= fixed_stop_pct:
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_A_FIXED_STOP,
                priority=SignalPriority.CRITICAL,
                confidence=0.90,
                reason=f"고정 손절 도달: 손실률 {holding.profit_loss_percent:.2f}% <= {fixed_stop_pct}%",
                recommended_action="즉시 전량 매도",
                exit_percent=100.0,
                order_type=OrderType.MARKET
            ))

        # Time Stop (5일 이상 보유 + 수익 없음)
        if holding.holding_days >= 5 and holding.profit_loss_percent <= 0:
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_A_TIME_STOP,
                priority=SignalPriority.HIGH,
                confidence=0.70,
                reason=f"Time Stop: {holding.holding_days}일 보유, 수익률 {holding.profit_loss_percent:.2f}%",
                recommended_action="포지션 정리 검토",
                exit_percent=100.0,
                order_type=OrderType.MARKET
            ))

        return signals

    # ============================================================
    # 제3계층: Type B 신호 (추세 종료)
    # ============================================================

    def detect_type_b_signals(self, holding: HoldingStatus, price_history: Optional[pd.DataFrame] = None) -> List[SellSignal]:
        """
        Type B 신호 감지 (추세 종료)

        - MACD 데드크로스/히스토그램 수축
        - RSI 다이버전스
        - 거래량 매수 절정
        - 캔들스틱 반전 패턴
        - 이동평균 데드크로스
        """
        signals = []

        # MACD 데드크로스
        if holding.macd and holding.macd_signal:
            if holding.macd < holding.macd_signal and holding.macd > 0:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_B_MACD_CROSS,
                    priority=SignalPriority.HIGH,
                    confidence=0.75,
                    reason=f"MACD 데드크로스: MACD={holding.macd:.4f} < Signal={holding.macd_signal:.4f} (양수 영역)",
                    recommended_action="부분 매도 또는 손절 타이트하게",
                    exit_percent=50.0,
                    order_type=OrderType.LIMIT
                ))

        # MACD 히스토그램 수축 (Rolling Over)
        if holding.macd_histogram and holding.macd_histogram > 0:
            # 히스토그램이 양수이지만 감소 추세인 경우 (이전 값과 비교 필요)
            if price_history is not None and 'macd_histogram' in price_history.columns:
                recent_hist = price_history['macd_histogram'].tail(3)
                if len(recent_hist) >= 3:
                    if recent_hist.iloc[-1] < recent_hist.iloc[-2] < recent_hist.iloc[-3]:
                        signals.append(SellSignal(
                            signal_type=SellSignalType.TYPE_B_MACD_ROLLOVER,
                            priority=SignalPriority.MEDIUM,
                            confidence=0.65,
                            reason=f"MACD 히스토그램 수축: 양수 영역에서 고점 하락 중",
                            recommended_action="추세 약화 - 손절 타이트하게 조정",
                            exit_percent=25.0,
                            order_type=OrderType.LIMIT
                        ))

        # 이동평균 데드크로스 (MA20 < MA50)
        if holding.ma_20 and holding.ma_50:
            if holding.ma_20 < holding.ma_50:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_B_MA_CROSS,
                    priority=SignalPriority.HIGH,
                    confidence=0.70,
                    reason=f"MA 데드크로스: MA20={holding.ma_20:,.0f} < MA50={holding.ma_50:,.0f}",
                    recommended_action="추세 전환 - 부분 매도 권고",
                    exit_percent=50.0,
                    order_type=OrderType.LIMIT
                ))

        # 거래량 매수 절정 (Buying Climax)
        if holding.volume and holding.avg_volume_20:
            volume_ratio = holding.volume / holding.avg_volume_20
            if volume_ratio > self.volume_climax_multiplier and holding.profit_loss_percent > 5:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_B_BUYING_CLIMAX,
                    priority=SignalPriority.HIGH,
                    confidence=0.80,
                    reason=f"매수 절정: 거래량 {volume_ratio:.1f}배 급증 (수익 구간)",
                    recommended_action="강력한 매도 신호 - 익절 권고",
                    exit_percent=50.0,
                    order_type=OrderType.MARKET
                ))

        # RSI 과매수 후 하락 반전
        if holding.rsi and holding.rsi < 70:
            if price_history is not None and 'rsi' in price_history.columns:
                recent_rsi = price_history['rsi'].tail(2)
                if len(recent_rsi) >= 2 and recent_rsi.iloc[-2] >= 70:
                    signals.append(SellSignal(
                        signal_type=SellSignalType.TYPE_B_DIVERGENCE,
                        priority=SignalPriority.HIGH,
                        confidence=0.75,
                        reason=f"RSI 70 하향 돌파: {recent_rsi.iloc[-2]:.1f} -> {holding.rsi:.1f}",
                        recommended_action="추세 약화 신호 - 부분 매도 권고",
                        exit_percent=33.0,
                        order_type=OrderType.LIMIT
                    ))

        return signals

    # ============================================================
    # 제3계층: Type C 신호 (수익 목표)
    # ============================================================

    def detect_type_c_signals(self, holding: HoldingStatus) -> List[SellSignal]:
        """
        Type C 신호 감지 (목표 수익 실현)

        - R/R 목표 달성 (1:2, 1:3)
        - 피보나치 확장 레벨 도달
        - 볼린저 밴드 상단 터치
        - RSI 과매수
        """
        signals = []

        # 피보나치 확장 레벨 계산
        if holding.stop_loss_price and holding.avg_buy_price:
            risk = holding.avg_buy_price - holding.stop_loss_price
            if risk > 0:
                fib_127 = holding.avg_buy_price + (risk * 1.272)
                fib_161 = holding.avg_buy_price + (risk * 1.618)
                fib_261 = holding.avg_buy_price + (risk * 2.618)

                if holding.current_price >= fib_261:
                    signals.append(SellSignal(
                        signal_type=SellSignalType.TYPE_C_FIBONACCI,
                        priority=SignalPriority.HIGH,
                        confidence=0.85,
                        reason=f"피보나치 261.8% 도달: 현재가 {holding.current_price:,.0f} >= 목표 {fib_261:,.0f}",
                        recommended_action="전량 매도 권고 - 목표 달성",
                        exit_percent=100.0,
                        order_type=OrderType.LIMIT,
                        target_price=fib_261
                    ))
                elif holding.current_price >= fib_161:
                    signals.append(SellSignal(
                        signal_type=SellSignalType.TYPE_C_FIBONACCI,
                        priority=SignalPriority.MEDIUM,
                        confidence=0.80,
                        reason=f"피보나치 161.8% 도달: 현재가 {holding.current_price:,.0f} >= 목표 {fib_161:,.0f}",
                        recommended_action="50% 청산 + 트레일링 타이트하게",
                        exit_percent=50.0,
                        order_type=OrderType.LIMIT,
                        target_price=fib_161
                    ))
                elif holding.current_price >= fib_127:
                    signals.append(SellSignal(
                        signal_type=SellSignalType.TYPE_C_FIBONACCI,
                        priority=SignalPriority.MEDIUM,
                        confidence=0.75,
                        reason=f"피보나치 127.2% 도달: 현재가 {holding.current_price:,.0f} >= 목표 {fib_127:,.0f}",
                        recommended_action="30% 청산 + 손절을 본절로 이동",
                        exit_percent=30.0,
                        order_type=OrderType.LIMIT,
                        target_price=fib_127
                    ))

        # R/R 목표 달성
        if holding.profit_loss_percent >= 20:  # 3R 달성 (가정: 초기 손절 -6.67%)
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_C_RR_TARGET,
                priority=SignalPriority.MEDIUM,
                confidence=0.85,
                reason=f"R/R 3:1 목표 달성: 수익률 {holding.profit_loss_percent:.2f}%",
                recommended_action="전량 매도 또는 트레일링 스톱",
                exit_percent=100.0,
                order_type=OrderType.LIMIT
            ))
        elif holding.profit_loss_percent >= 13:  # 2R 달성
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_C_RR_TARGET,
                priority=SignalPriority.MEDIUM,
                confidence=0.75,
                reason=f"R/R 2:1 목표 달성: 수익률 {holding.profit_loss_percent:.2f}%",
                recommended_action="50% 청산 권고",
                exit_percent=50.0,
                order_type=OrderType.LIMIT
            ))
        elif holding.profit_loss_percent >= 6.5:  # 1R 달성
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_C_RR_TARGET,
                priority=SignalPriority.LOW,
                confidence=0.65,
                reason=f"R/R 1:1 목표 달성: 수익률 {holding.profit_loss_percent:.2f}%",
                recommended_action="손절을 본절로 이동, 33% 청산 고려",
                exit_percent=33.0,
                order_type=OrderType.LIMIT
            ))

        # 볼린저 밴드 상단 터치
        if holding.bollinger_upper and holding.current_price >= holding.bollinger_upper:
            signals.append(SellSignal(
                signal_type=SellSignalType.TYPE_C_BB_UPPER,
                priority=SignalPriority.MEDIUM,
                confidence=0.70,
                reason=f"볼린저 밴드 상단 터치: 현재가 {holding.current_price:,.0f} >= BB상단 {holding.bollinger_upper:,.0f}",
                recommended_action="과열 구간 - 25% 부분 익절 고려",
                exit_percent=25.0,
                order_type=OrderType.LIMIT
            ))

        # RSI 과매수
        if holding.rsi:
            if holding.rsi >= self.rsi_extreme:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_C_RSI_OVERBOUGHT,
                    priority=SignalPriority.HIGH,
                    confidence=0.80,
                    reason=f"RSI 극단적 과매수: RSI={holding.rsi:.1f} >= {self.rsi_extreme}",
                    recommended_action="강한 과열 - 50% 익절 권고",
                    exit_percent=50.0,
                    order_type=OrderType.LIMIT
                ))
            elif holding.rsi >= self.rsi_overbought:
                signals.append(SellSignal(
                    signal_type=SellSignalType.TYPE_C_RSI_OVERBOUGHT,
                    priority=SignalPriority.MEDIUM,
                    confidence=0.65,
                    reason=f"RSI 과매수: RSI={holding.rsi:.1f} >= {self.rsi_overbought}",
                    recommended_action="과열 주의 - 25% 부분 익절 고려",
                    exit_percent=25.0,
                    order_type=OrderType.LIMIT
                ))

        return signals

    # ============================================================
    # 종합 신호 감지
    # ============================================================

    def calculate_total_score(self, signals: List[SellSignal]) -> float:
        """신호 점수 합산"""
        total = 0.0
        for signal in signals:
            weight = 1.0
            if signal.priority == SignalPriority.CRITICAL:
                weight = 2.0
            elif signal.priority == SignalPriority.HIGH:
                weight = 1.5
            elif signal.priority == SignalPriority.MEDIUM:
                weight = 1.0
            else:
                weight = 0.5

            total += signal.confidence * weight * (signal.exit_percent / 100)

        return min(total, 10.0)  # 최대 10점

    def get_recommendation(self, signals: List[SellSignal], total_score: float) -> Tuple[str, SignalPriority]:
        """종합 권고사항 생성"""
        # Type A 신호가 있으면 즉시 매도
        type_a_signals = [s for s in signals if s.signal_type.value.startswith('TYPE_A') or
                         s.signal_type in [SellSignalType.TYPE_A_ATR_STOP, SellSignalType.TYPE_A_FIXED_STOP,
                                           SellSignalType.TYPE_A_TIME_STOP]]

        if any(s.priority == SignalPriority.CRITICAL for s in signals):
            return "즉시 전량 매도 필요 - 리스크 관리 신호 발동", SignalPriority.CRITICAL

        if total_score >= 5.0:
            return "강한 매도 신호 - 전량 또는 대부분 청산 권고", SignalPriority.HIGH
        elif total_score >= 3.0:
            return "매도 신호 - 부분 청산 및 손절 타이트하게", SignalPriority.HIGH
        elif total_score >= 1.5:
            return "주의 필요 - 부분 익절 및 모니터링 강화", SignalPriority.MEDIUM
        elif total_score >= 0.5:
            return "약한 신호 - 모니터링 지속", SignalPriority.LOW
        else:
            return "신호 없음 - 포지션 유지", SignalPriority.LOW

    def detect_signals_for_holding(self, holding: HoldingStatus,
                                   price_history: Optional[pd.DataFrame] = None) -> SellSignalResponse:
        """개별 보유 종목에 대한 매도 신호 감지"""
        # 시장 레짐 분류
        atr_percentile = None  # 추후 계산 가능
        regime = self.classify_market_regime(holding.adx, atr_percentile)

        # 각 Type별 신호 감지
        signals = []
        signals.extend(self.detect_type_a_signals(holding, regime))
        signals.extend(self.detect_type_b_signals(holding, price_history))
        signals.extend(self.detect_type_c_signals(holding))

        # 점수 계산 및 권고사항
        total_score = self.calculate_total_score(signals)
        recommendation, urgency = self.get_recommendation(signals, total_score)

        # ATR 손절가 계산
        atr_stop_price = None
        if holding.atr:
            market_type = 'KOSDAQ' if 'KOSDAQ' in str(holding.ticker) else 'KOSPI'
            atr_mult = self.get_atr_multiplier(regime, market_type)
            atr_stop_price = holding.avg_buy_price - (holding.atr * atr_mult)

        # 피보나치 목표가 계산
        fib_127, fib_161, fib_261 = None, None, None
        if holding.stop_loss_price and holding.avg_buy_price:
            risk = holding.avg_buy_price - holding.stop_loss_price
            if risk > 0:
                fib_127 = holding.avg_buy_price + (risk * 1.272)
                fib_161 = holding.avg_buy_price + (risk * 1.618)
                fib_261 = holding.avg_buy_price + (risk * 2.618)

        return SellSignalResponse(
            holding=holding,
            signals=signals,
            total_score=total_score,
            recommendation=recommendation,
            market_regime=regime,
            urgency_level=urgency,
            atr_stop_price=atr_stop_price,
            trailing_stop_price=atr_stop_price,  # 초기값은 ATR stop과 동일
            fib_127_price=fib_127,
            fib_161_price=fib_161,
            fib_261_price=fib_261
        )

    # ============================================================
    # 데이터베이스 조회
    # ============================================================

    def get_holdings_with_indicators(self, user_id: int, target_date: Optional[date] = None) -> List[HoldingStatus]:
        """보유 종목 및 기술적 지표 조회"""
        if target_date is None:
            target_date = date.today()

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT
                        h.id as holding_id,
                        h.user_id,
                        h.ticker,
                        h.company_name,
                        h.quantity,
                        h.avg_buy_price,
                        h.buy_date,
                        h.stop_loss_price,
                        h.take_profit_price,
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
                        (
                            SELECT AVG(vol_sub.volume)::float
                            FROM (
                                SELECT volume
                                FROM stock_prices sp2
                                WHERE sp2.ticker = h.ticker
                                AND sp2.date <= :target_date
                                ORDER BY sp2.date DESC
                                LIMIT 20
                            ) vol_sub
                        ) as avg_volume_20
                    FROM holdings h
                    JOIN stock_prices sp ON h.ticker = sp.ticker
                    LEFT JOIN technical_indicators ti ON h.ticker = ti.ticker AND sp.date = ti.date
                    WHERE h.user_id = :user_id
                        AND h.is_active = true
                        AND sp.date = (
                            SELECT MAX(date) FROM stock_prices WHERE ticker = h.ticker AND date <= :target_date
                        )
                    ORDER BY h.ticker
                """)

                result = conn.execute(query, {'user_id': user_id, 'target_date': target_date})
                holdings = []

                for row in result:
                    buy_date = row.buy_date if row.buy_date else target_date
                    holding_days = (target_date - buy_date).days if buy_date else 0

                    current_price = float(row.current_price) if row.current_price else 0
                    avg_buy_price = float(row.avg_buy_price) if row.avg_buy_price else 0

                    profit_loss_amount = (current_price - avg_buy_price) * row.quantity if avg_buy_price else 0
                    profit_loss_percent = ((current_price - avg_buy_price) / avg_buy_price * 100) if avg_buy_price else 0

                    holding = HoldingStatus(
                        holding_id=row.holding_id,
                        user_id=row.user_id,
                        ticker=row.ticker,
                        company_name=row.company_name,
                        quantity=row.quantity,
                        avg_buy_price=avg_buy_price,
                        buy_date=buy_date,
                        current_price=current_price,
                        profit_loss_amount=profit_loss_amount,
                        profit_loss_percent=profit_loss_percent,
                        holding_days=holding_days,
                        rsi=float(row.rsi) if row.rsi else None,
                        macd=float(row.macd) if row.macd else None,
                        macd_signal=float(row.macd_signal) if row.macd_signal else None,
                        macd_histogram=float(row.macd_histogram) if row.macd_histogram else None,
                        ma_20=float(row.ma_20) if row.ma_20 else None,
                        ma_50=float(row.ma_50) if row.ma_50 else None,
                        ma_200=float(row.ma_200) if row.ma_200 else None,
                        bollinger_upper=float(row.bollinger_upper) if row.bollinger_upper else None,
                        bollinger_lower=float(row.bollinger_lower) if row.bollinger_lower else None,
                        volume=int(row.volume) if row.volume else None,
                        avg_volume_20=float(row.avg_volume_20) if row.avg_volume_20 else None,
                        stop_loss_price=float(row.stop_loss_price) if row.stop_loss_price else None,
                        take_profit_price=float(row.take_profit_price) if row.take_profit_price else None
                    )
                    holdings.append(holding)

                logger.info(f"Found {len(holdings)} holdings for user {user_id}")
                return holdings

        except Exception as e:
            logger.error(f"Error getting holdings: {e}")
            raise

    def get_price_history(self, ticker: str, days: int = 30, end_date: Optional[date] = None) -> pd.DataFrame:
        """가격 히스토리 조회"""
        if end_date is None:
            end_date = date.today()

        start_date = end_date - timedelta(days=days)

        try:
            with self.engine.connect() as conn:
                query = text("""
                    SELECT
                        sp.date,
                        sp.open_price,
                        sp.high_price,
                        sp.low_price,
                        sp.close_price,
                        sp.volume,
                        ti.rsi,
                        ti.macd,
                        ti.macd_signal,
                        ti.macd_histogram,
                        ti.ma_20,
                        ti.ma_50,
                        ti.ma_200
                    FROM stock_prices sp
                    LEFT JOIN technical_indicators ti ON sp.ticker = ti.ticker AND sp.date = ti.date
                    WHERE sp.ticker = :ticker
                        AND sp.date BETWEEN :start_date AND :end_date
                    ORDER BY sp.date
                """)

                result = conn.execute(query, {
                    'ticker': ticker,
                    'start_date': start_date,
                    'end_date': end_date
                })

                df = pd.DataFrame(result.fetchall(), columns=result.keys())
                return df

        except Exception as e:
            logger.error(f"Error getting price history for {ticker}: {e}")
            return pd.DataFrame()

    def detect_all_signals(self, user_id: int, target_date: Optional[date] = None) -> SellSignalSummary:
        """모든 보유 종목에 대한 매도 신호 감지"""
        holdings = self.get_holdings_with_indicators(user_id, target_date)

        holdings_with_signals = []
        critical_count = 0
        high_count = 0
        medium_count = 0

        for holding in holdings:
            # 가격 히스토리 조회 (추가 분석용)
            price_history = self.get_price_history(holding.ticker, days=30, end_date=target_date)

            # 신호 감지
            signal_response = self.detect_signals_for_holding(holding, price_history)

            if signal_response.signals:
                holdings_with_signals.append(signal_response)

                if signal_response.urgency_level == SignalPriority.CRITICAL:
                    critical_count += 1
                elif signal_response.urgency_level == SignalPriority.HIGH:
                    high_count += 1
                elif signal_response.urgency_level == SignalPriority.MEDIUM:
                    medium_count += 1

        # 전체 시장 레짐 판단 (가장 빈번한 레짐 사용)
        if holdings_with_signals:
            regimes = [h.market_regime for h in holdings_with_signals]
            market_regime = max(set(regimes), key=regimes.count)
        else:
            market_regime = MarketRegime.RANGING

        # 포트폴리오 리스크 레벨 판단
        if critical_count > 0:
            portfolio_risk = "CRITICAL - 즉시 대응 필요"
        elif high_count >= len(holdings) * 0.3:
            portfolio_risk = "HIGH - 포트폴리오 점검 필요"
        elif medium_count >= len(holdings) * 0.5:
            portfolio_risk = "MEDIUM - 모니터링 강화"
        else:
            portfolio_risk = "LOW - 정상"

        return SellSignalSummary(
            total_holdings=len(holdings),
            critical_signals=critical_count,
            high_signals=high_count,
            medium_signals=medium_count,
            holdings_with_signals=holdings_with_signals,
            market_regime=market_regime,
            portfolio_risk_level=portfolio_risk
        )

    def save_signal_to_db(self, signal_response: SellSignalResponse) -> int:
        """매도 신호 데이터베이스 저장"""
        try:
            with self.engine.begin() as conn:
                for signal in signal_response.signals:
                    conn.execute(text("""
                        INSERT INTO sell_signals (
                            holding_id, ticker, signal_type, priority,
                            confidence, reason, recommended_action,
                            exit_percent, target_price, total_score,
                            market_regime, status, created_at
                        ) VALUES (
                            :holding_id, :ticker, :signal_type, :priority,
                            :confidence, :reason, :recommended_action,
                            :exit_percent, :target_price, :total_score,
                            :market_regime, 'PENDING', :created_at
                        )
                    """), {
                        'holding_id': signal_response.holding.holding_id,
                        'ticker': signal_response.holding.ticker,
                        'signal_type': signal.signal_type.value,
                        'priority': signal.priority.value,
                        'confidence': signal.confidence,
                        'reason': signal.reason,
                        'recommended_action': signal.recommended_action,
                        'exit_percent': signal.exit_percent,
                        'target_price': signal.target_price,
                        'total_score': signal_response.total_score,
                        'market_regime': signal_response.market_regime.value,
                        'created_at': datetime.now()
                    })

                logger.info(f"Saved {len(signal_response.signals)} signals for {signal_response.holding.ticker}")
                return len(signal_response.signals)

        except Exception as e:
            logger.error(f"Error saving signals: {e}")
            raise
