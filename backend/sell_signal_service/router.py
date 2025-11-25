"""
Sell Signal Service Router
매도 신호 API 엔드포인트
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from datetime import datetime, date
from typing import List, Optional
import logging

from database import get_db
from config import settings
from .detector import SellSignalDetector
from .models import (
    SellSignalResponse,
    SellSignalSummary,
    HoldingStatus,
    SignalPriority,
    MarketRegime
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/sell-signals", tags=["Sell Signals"])

# 데이터베이스 URL
DATABASE_URL = settings.DATABASE_URL if hasattr(settings, 'DATABASE_URL') else "postgresql://admin:admin123@localhost:5435/stocktrading"


def get_detector():
    """SellSignalDetector 인스턴스 반환"""
    return SellSignalDetector(DATABASE_URL)


@router.get("/check/{user_id}", response_model=SellSignalSummary)
async def check_sell_signals(
    user_id: int,
    target_date: Optional[date] = Query(None, description="분석 기준일 (기본: 오늘)"),
    db: Session = Depends(get_db)
):
    """
    사용자의 모든 보유 종목에 대한 매도 신호 확인

    3계층 알고리즘 아키텍처 기반:
    - Type A: 리스크 관리 (손절)
    - Type B: 추세 종료
    - Type C: 수익 목표 달성
    """
    try:
        detector = get_detector()
        summary = detector.detect_all_signals(user_id, target_date)

        logger.info(f"Checked sell signals for user {user_id}: "
                   f"{summary.critical_signals} critical, "
                   f"{summary.high_signals} high, "
                   f"{summary.medium_signals} medium signals")

        return summary

    except Exception as e:
        logger.error(f"Error checking sell signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/holding/{holding_id}", response_model=SellSignalResponse)
async def check_holding_signals(
    holding_id: int,
    target_date: Optional[date] = Query(None, description="분석 기준일"),
    db: Session = Depends(get_db)
):
    """
    특정 보유 종목에 대한 상세 매도 신호 확인
    """
    try:
        detector = get_detector()

        # 보유 종목 조회
        with detector.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT user_id FROM holdings WHERE id = :holding_id AND is_active = true
            """), {'holding_id': holding_id})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail="보유 종목을 찾을 수 없습니다")

            user_id = row[0]

        # 해당 종목의 신호 확인
        holdings = detector.get_holdings_with_indicators(user_id, target_date)
        target_holding = next((h for h in holdings if h.holding_id == holding_id), None)

        if not target_holding:
            raise HTTPException(status_code=404, detail="보유 종목 데이터를 찾을 수 없습니다")

        # 가격 히스토리 조회 및 신호 감지
        price_history = detector.get_price_history(target_holding.ticker, days=30, end_date=target_date)
        signal_response = detector.detect_signals_for_holding(target_holding, price_history)

        return signal_response

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking holding signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/ticker/{ticker}", response_model=dict)
async def check_ticker_signals(
    ticker: str,
    buy_price: float = Query(..., description="매수가"),
    quantity: int = Query(1, description="수량"),
    stop_loss_price: Optional[float] = Query(None, description="손절가"),
    target_date: Optional[date] = Query(None, description="분석 기준일"),
    db: Session = Depends(get_db)
):
    """
    특정 종목에 대한 매도 신호 확인 (보유 종목이 아닌 경우)

    시뮬레이션용 - 가상의 포지션으로 신호 확인
    """
    try:
        detector = get_detector()
        if target_date is None:
            target_date = date.today()

        # 종목 가격 및 지표 조회
        with detector.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    s.ticker,
                    s.company_name,
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
                    ti.bollinger_lower
                FROM stocks s
                JOIN stock_prices sp ON s.ticker = sp.ticker
                LEFT JOIN technical_indicators ti ON s.ticker = ti.ticker AND sp.date = ti.date
                WHERE s.ticker = :ticker
                    AND sp.date = (
                        SELECT MAX(date) FROM stock_prices WHERE ticker = :ticker AND date <= :target_date
                    )
            """), {'ticker': ticker, 'target_date': target_date})
            row = result.fetchone()

            if not row:
                raise HTTPException(status_code=404, detail=f"종목 {ticker}의 데이터를 찾을 수 없습니다")

            current_price = float(row.current_price) if row.current_price else 0
            profit_loss_amount = (current_price - buy_price) * quantity
            profit_loss_percent = ((current_price - buy_price) / buy_price * 100) if buy_price else 0

            # 가상의 HoldingStatus 생성
            holding = HoldingStatus(
                holding_id=0,
                user_id=0,
                ticker=ticker,
                company_name=row.company_name,
                quantity=quantity,
                avg_buy_price=buy_price,
                buy_date=target_date,
                current_price=current_price,
                profit_loss_amount=profit_loss_amount,
                profit_loss_percent=profit_loss_percent,
                holding_days=0,
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
                stop_loss_price=stop_loss_price
            )

        # 신호 감지
        price_history = detector.get_price_history(ticker, days=30, end_date=target_date)
        signal_response = detector.detect_signals_for_holding(holding, price_history)

        return {
            "ticker": ticker,
            "company_name": row.company_name,
            "buy_price": buy_price,
            "current_price": current_price,
            "profit_loss_percent": profit_loss_percent,
            "signals": [s.dict() for s in signal_response.signals],
            "total_score": signal_response.total_score,
            "recommendation": signal_response.recommendation,
            "market_regime": signal_response.market_regime.value,
            "urgency_level": signal_response.urgency_level.value,
            "atr_stop_price": signal_response.atr_stop_price,
            "fib_127_price": signal_response.fib_127_price,
            "fib_161_price": signal_response.fib_161_price,
            "fib_261_price": signal_response.fib_261_price
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error checking ticker signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/critical", response_model=List[dict])
async def get_critical_signals(
    user_id: int = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db)
):
    """
    긴급 매도 신호만 조회 (Type A - CRITICAL)

    즉시 대응이 필요한 신호:
    - ATR 손절가 도달
    - 고정 손실률 초과
    - VaR/MDD 초과
    """
    try:
        detector = get_detector()
        summary = detector.detect_all_signals(user_id)

        critical_holdings = [
            {
                "ticker": h.holding.ticker,
                "company_name": h.holding.company_name,
                "current_price": h.holding.current_price,
                "profit_loss_percent": h.holding.profit_loss_percent,
                "signals": [s.dict() for s in h.signals if s.priority == SignalPriority.CRITICAL],
                "recommendation": h.recommendation
            }
            for h in summary.holdings_with_signals
            if h.urgency_level == SignalPriority.CRITICAL
        ]

        return critical_holdings

    except Exception as e:
        logger.error(f"Error getting critical signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/profit-targets", response_model=List[dict])
async def get_profit_target_signals(
    user_id: int = Query(..., description="사용자 ID"),
    db: Session = Depends(get_db)
):
    """
    익절 신호 조회 (Type C)

    수익 실현 기회:
    - R/R 목표 달성
    - 피보나치 레벨 도달
    - RSI 과매수
    - 볼린저 밴드 상단 터치
    """
    try:
        detector = get_detector()
        summary = detector.detect_all_signals(user_id)

        type_c_signals = []
        for h in summary.holdings_with_signals:
            profit_signals = [
                s for s in h.signals
                if s.signal_type.value.startswith('TYPE_C') or
                   s.signal_type.value in ['RR_TARGET', 'FIBONACCI', 'BB_UPPER', 'RSI_OVERBOUGHT']
            ]

            if profit_signals and h.holding.profit_loss_percent > 0:
                type_c_signals.append({
                    "ticker": h.holding.ticker,
                    "company_name": h.holding.company_name,
                    "current_price": h.holding.current_price,
                    "profit_loss_percent": h.holding.profit_loss_percent,
                    "signals": [s.dict() for s in profit_signals],
                    "fib_127_price": h.fib_127_price,
                    "fib_161_price": h.fib_161_price,
                    "fib_261_price": h.fib_261_price,
                    "recommendation": h.recommendation
                })

        # 수익률 높은 순으로 정렬
        type_c_signals.sort(key=lambda x: x['profit_loss_percent'], reverse=True)

        return type_c_signals

    except Exception as e:
        logger.error(f"Error getting profit target signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/notify/{user_id}")
async def send_sell_signal_notifications(
    user_id: int,
    priority_filter: Optional[str] = Query(None, description="우선순위 필터 (CRITICAL, HIGH, MEDIUM, LOW)"),
    db: Session = Depends(get_db)
):
    """
    매도 신호 알림 발송

    - Email, Kakao, Slack 등 설정된 채널로 알림 발송
    - priority_filter로 특정 우선순위 신호만 발송 가능
    """
    try:
        detector = get_detector()
        summary = detector.detect_all_signals(user_id)

        # 필터링
        filtered_holdings = summary.holdings_with_signals
        if priority_filter:
            priority = SignalPriority(priority_filter)
            filtered_holdings = [
                h for h in filtered_holdings
                if h.urgency_level == priority
            ]

        if not filtered_holdings:
            return {"status": "success", "message": "발송할 신호가 없습니다", "sent_count": 0}

        # 알림 메시지 생성
        from trading_service.notification_service import NotificationService
        notification_service = NotificationService()

        sent_count = 0
        for holding_signal in filtered_holdings:
            try:
                message = format_sell_signal_message(holding_signal)

                # 데이터베이스에서 사용자 이메일 조회
                with detector.engine.connect() as conn:
                    result = conn.execute(text("""
                        SELECT email FROM users WHERE id = :user_id
                    """), {'user_id': user_id})
                    user_row = result.fetchone()

                if user_row and user_row.email:
                    notification_service.send_email(
                        recipient=user_row.email,
                        subject=f"[매도 신호] {holding_signal.holding.ticker} - {holding_signal.urgency_level.value}",
                        message=message
                    )
                    sent_count += 1

                # 신호 저장
                detector.save_signal_to_db(holding_signal)

            except Exception as e:
                logger.error(f"Error sending notification for {holding_signal.holding.ticker}: {e}")

        return {
            "status": "success",
            "message": f"{sent_count}개 알림 발송 완료",
            "sent_count": sent_count,
            "total_signals": len(filtered_holdings)
        }

    except Exception as e:
        logger.error(f"Error sending notifications: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history/{user_id}")
async def get_signal_history(
    user_id: int,
    days: int = Query(7, description="조회 기간 (일)"),
    status: Optional[str] = Query(None, description="상태 필터"),
    db: Session = Depends(get_db)
):
    """
    매도 신호 히스토리 조회
    """
    try:
        detector = get_detector()

        with detector.engine.connect() as conn:
            query = """
                SELECT
                    ss.id,
                    ss.ticker,
                    s.company_name,
                    ss.signal_type,
                    ss.priority,
                    ss.confidence,
                    ss.reason,
                    ss.recommended_action,
                    ss.exit_percent,
                    ss.target_price,
                    ss.current_price,
                    ss.total_score,
                    ss.market_regime,
                    ss.status,
                    ss.created_at,
                    ss.notified_at,
                    ss.executed_at,
                    ss.execution_price
                FROM sell_signals ss
                JOIN holdings h ON ss.holding_id = h.id
                JOIN stocks s ON ss.ticker = s.ticker
                WHERE h.user_id = :user_id
                    AND ss.created_at >= NOW() - INTERVAL ':days days'
            """

            if status:
                query += " AND ss.status = :status"

            query += " ORDER BY ss.created_at DESC"

            params = {'user_id': user_id, 'days': days}
            if status:
                params['status'] = status

            result = conn.execute(text(query), params)

            signals = []
            for row in result:
                signals.append({
                    "id": row.id,
                    "ticker": row.ticker,
                    "company_name": row.company_name,
                    "signal_type": row.signal_type,
                    "priority": row.priority,
                    "confidence": float(row.confidence) if row.confidence else None,
                    "reason": row.reason,
                    "recommended_action": row.recommended_action,
                    "exit_percent": float(row.exit_percent) if row.exit_percent else None,
                    "target_price": float(row.target_price) if row.target_price else None,
                    "current_price": float(row.current_price) if row.current_price else None,
                    "total_score": float(row.total_score) if row.total_score else None,
                    "market_regime": row.market_regime,
                    "status": row.status,
                    "created_at": row.created_at.isoformat() if row.created_at else None,
                    "notified_at": row.notified_at.isoformat() if row.notified_at else None,
                    "executed_at": row.executed_at.isoformat() if row.executed_at else None,
                    "execution_price": float(row.execution_price) if row.execution_price else None
                })

            return {"signals": signals, "count": len(signals)}

    except Exception as e:
        logger.error(f"Error getting signal history: {e}")
        raise HTTPException(status_code=500, detail=str(e))


def format_sell_signal_message(signal_response: SellSignalResponse) -> str:
    """매도 신호 알림 메시지 포맷"""
    holding = signal_response.holding

    message = f"""
<h2>매도 신호 알림</h2>

<h3>종목 정보</h3>
<table>
    <tr><td>종목코드</td><td>{holding.ticker}</td></tr>
    <tr><td>종목명</td><td>{holding.company_name}</td></tr>
    <tr><td>현재가</td><td>{holding.current_price:,.0f}원</td></tr>
    <tr><td>평균매수가</td><td>{holding.avg_buy_price:,.0f}원</td></tr>
    <tr><td>수익률</td><td style="color: {'green' if holding.profit_loss_percent > 0 else 'red'}">{holding.profit_loss_percent:+.2f}%</td></tr>
    <tr><td>보유수량</td><td>{holding.quantity:,}주</td></tr>
    <tr><td>보유기간</td><td>{holding.holding_days}일</td></tr>
</table>

<h3>신호 분석</h3>
<table>
    <tr><td>총 점수</td><td>{signal_response.total_score:.2f}/10</td></tr>
    <tr><td>긴급도</td><td style="color: {'red' if signal_response.urgency_level.value == 'CRITICAL' else 'orange' if signal_response.urgency_level.value == 'HIGH' else 'black'}">{signal_response.urgency_level.value}</td></tr>
    <tr><td>시장 레짐</td><td>{signal_response.market_regime.value}</td></tr>
    <tr><td>권고사항</td><td><strong>{signal_response.recommendation}</strong></td></tr>
</table>

<h3>감지된 신호</h3>
<ul>
"""

    for signal in signal_response.signals:
        color = 'red' if signal.priority.value == 'CRITICAL' else 'orange' if signal.priority.value == 'HIGH' else 'blue'
        message += f"""
    <li>
        <strong style="color: {color}">[{signal.priority.value}]</strong> {signal.signal_type.value}<br>
        {signal.reason}<br>
        <em>권고: {signal.recommended_action} (청산 {signal.exit_percent:.0f}%)</em>
    </li>
"""

    message += """
</ul>

<h3>목표가 정보</h3>
<table>
"""

    if signal_response.atr_stop_price:
        message += f"<tr><td>ATR 손절가</td><td>{signal_response.atr_stop_price:,.0f}원</td></tr>"
    if signal_response.fib_127_price:
        message += f"<tr><td>피보나치 127.2%</td><td>{signal_response.fib_127_price:,.0f}원</td></tr>"
    if signal_response.fib_161_price:
        message += f"<tr><td>피보나치 161.8%</td><td>{signal_response.fib_161_price:,.0f}원</td></tr>"
    if signal_response.fib_261_price:
        message += f"<tr><td>피보나치 261.8%</td><td>{signal_response.fib_261_price:,.0f}원</td></tr>"

    message += f"""
</table>

<p><small>생성시간: {signal_response.created_at.strftime('%Y-%m-%d %H:%M:%S')}</small></p>
"""

    return message
