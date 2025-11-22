"""
Trading Service API Router
자동매매 REST API
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import List, Optional
from datetime import date, datetime
import logging
import os

from trading_service.signal_detector import SignalDetector
from trading_service.position_manager import PositionManager
from trading_service.notification_service import NotificationService

router = APIRouter(prefix="/api/trading", tags=["trading"])

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Database URL (환경 변수로 관리 권장)
# 운영 DB (192.168.219.103)를 기본값으로 사용
# Docker 내부 테스트: DATABASE_URL 환경변수 설정 시 그 값 사용
DB_URL = os.getenv("DATABASE_URL", "postgresql://admin:admin123@192.168.219.103:5432/stocktrading")

# Pydantic Models
class BuyRequest(BaseModel):
    ticker: str
    buy_price: float
    quantity: int
    target_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    notes: Optional[str] = None

class SellRequest(BaseModel):
    position_id: int
    sell_price: float
    notes: Optional[str] = None

class NotificationConfig(BaseModel):
    email: Optional[str] = None
    kakao_id: Optional[str] = None
    slack_webhook: Optional[str] = None
    channels: List[str] = ['email']

class SendSignalsRequest(BaseModel):
    target_date: Optional[str] = None
    email: Optional[str] = None
    kakao_access_token: Optional[str] = None
    slack_webhook: Optional[str] = None
    channels: List[str] = ['email']

# Endpoints

@router.get("/signals/buy")
async def get_buy_signals(
    target_date: Optional[date] = Query(None, description="Target date (default: today)")
):
    """
    매수 시그널 조회

    조건: RSI < 30 AND MA20 > MA50
    """
    try:
        detector = SignalDetector(DB_URL)
        signals = detector.detect_buy_signals(target_date)

        return {
            "status": "success",
            "count": len(signals),
            "signals": signals
        }

    except Exception as e:
        logger.error(f"Error getting buy signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/sell")
async def get_sell_signals(
    target_date: Optional[date] = Query(None, description="Target date (default: today)")
):
    """
    매도 시그널 조회

    조건: RSI > 70 (보유 포지션 대상)
    """
    try:
        detector = SignalDetector(DB_URL)
        signals = detector.detect_sell_signals(target_date)

        return {
            "status": "success",
            "count": len(signals),
            "signals": signals
        }

    except Exception as e:
        logger.error(f"Error getting sell signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/stop-loss")
async def get_stop_loss_signals(
    target_date: Optional[date] = Query(None, description="Target date (default: today)")
):
    """
    손절 시그널 조회

    조건: 현재가 <= 손절가 (5% 손실)
    """
    try:
        detector = SignalDetector(DB_URL)
        signals = detector.detect_stop_loss_signals(target_date)

        return {
            "status": "success",
            "count": len(signals),
            "signals": signals
        }

    except Exception as e:
        logger.error(f"Error getting stop-loss signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/all")
async def get_all_signals(
    target_date: Optional[date] = Query(None, description="Target date (default: today)")
):
    """모든 시그널 한번에 조회"""
    try:
        detector = SignalDetector(DB_URL)
        all_signals = detector.detect_all_signals(target_date)

        return {
            "status": "success",
            "buy_count": len(all_signals['buy']),
            "sell_count": len(all_signals['sell']),
            "stop_loss_count": len(all_signals['stop_loss']),
            "signals": all_signals
        }

    except Exception as e:
        logger.error(f"Error getting all signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/positions/buy")
async def buy_stock(request: BuyRequest):
    """
    주식 매수 (포지션 오픈)
    """
    try:
        manager = PositionManager(DB_URL)

        position_id = manager.open_position(
            ticker=request.ticker,
            buy_price=request.buy_price,
            quantity=request.quantity,
            target_price=request.target_price,
            stop_loss_price=request.stop_loss_price,
            notes=request.notes
        )

        return {
            "status": "success",
            "message": "Position opened successfully",
            "position_id": position_id
        }

    except Exception as e:
        logger.error(f"Error buying stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/positions/sell")
async def sell_stock(request: SellRequest):
    """
    주식 매도 (포지션 클로즈)
    """
    try:
        manager = PositionManager(DB_URL)

        success = manager.close_position(
            position_id=request.position_id,
            sell_price=request.sell_price,
            notes=request.notes
        )

        if success:
            return {
                "status": "success",
                "message": "Position closed successfully"
            }
        else:
            raise HTTPException(status_code=404, detail="Position not found or already closed")

    except Exception as e:
        logger.error(f"Error selling stock: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/open")
async def get_open_positions():
    """보유 포지션 목록 조회"""
    try:
        manager = PositionManager(DB_URL)
        positions = manager.get_open_positions()

        return {
            "status": "success",
            "count": len(positions),
            "positions": positions
        }

    except Exception as e:
        logger.error(f"Error getting open positions: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/positions/history")
async def get_position_history(
    limit: int = Query(100, description="Maximum number of records")
):
    """포지션 이력 조회"""
    try:
        manager = PositionManager(DB_URL)
        positions = manager.get_position_history(limit=limit)

        return {
            "status": "success",
            "count": len(positions),
            "positions": positions
        }

    except Exception as e:
        logger.error(f"Error getting position history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/performance/summary")
async def get_performance_summary():
    """수익률 요약"""
    try:
        manager = PositionManager(DB_URL)
        summary = manager.get_performance_summary()

        return {
            "status": "success",
            "summary": summary
        }

    except Exception as e:
        logger.error(f"Error getting performance summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/test")
async def test_notification(config: NotificationConfig):
    """알림 테스트"""
    try:
        notification_config = {
            'email': {
                'enabled': 'email' in config.channels,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': '',  # 설정 필요
                'sender_password': ''  # 설정 필요
            },
            'kakao': {
                'enabled': 'kakao' in config.channels,
                'rest_api_key': '',  # 설정 필요
                'access_token': ''  # 설정 필요
            }
        }

        notifier = NotificationService(DB_URL, notification_config)

        # 테스트 시그널
        test_signal = {
            'ticker': 'TEST',
            'company_name': '테스트 종목',
            'signal_type': 'BUY',
            'signal_date': datetime.now(),
            'current_price': 50000,
            'target_price': 55000,
            'stop_loss_price': 47500,
            'rsi': 25.5,
            'ma_20': 49000,
            'ma_50': 48000,
            'reason': 'Test notification'
        }

        recipients = {
            'email': config.email,
            'kakao': config.kakao_id
        }

        success = notifier.send_signal_notification(
            test_signal,
            0,  # Test signal ID
            config.channels,
            recipients
        )

        return {
            "status": "success" if success else "partial_success",
            "message": "Test notification sent" if success else "Some notifications failed"
        }

    except Exception as e:
        logger.error(f"Error sending test notification: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/rsi-ma-strategy")
async def get_rsi_ma_strategy_signals(
    target_date: Optional[date] = Query(None, description="Target date (default: latest)")
):
    """
    RSI+MA 상승전략 시그널 조회

    조건: RSI < 30 AND MA20 > MA50
    - 과매도 구간에서 상승 추세인 종목 발굴
    """
    try:
        detector = SignalDetector(DB_URL)
        signals = detector.detect_buy_signals(target_date)

        return {
            "status": "success",
            "strategy": "RSI+MA상승전략",
            "description": "RSI < 30 (과매도) AND MA20 > MA50 (상승추세)",
            "count": len(signals),
            "signals": signals,
            "target_date": str(target_date) if target_date else "latest"
        }

    except Exception as e:
        logger.error(f"Error getting RSI+MA strategy signals: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/notifications/send-signals")
async def send_signals_notification(request: SendSignalsRequest):
    """
    시그널 알림 전송 (카카오톡/Slack)

    웹 UI에서 현재 시그널을 카카오톡이나 Slack으로 전송
    """
    try:
        logger.info(f"Notification request received: {request.channels}")

        # 시그널 조회
        detector = SignalDetector(DB_URL)
        target_date = datetime.strptime(request.target_date, '%Y-%m-%d').date() if request.target_date else None
        signals = detector.detect_buy_signals(target_date)

        logger.info(f"Found {len(signals)} signals for {target_date}")

        if not signals:
            return {
                "status": "success",
                "message": "전송할 시그널이 없습니다",
                "sent_count": 0
            }

        # 알림 설정
        notification_config = {
            'email': {
                'enabled': 'email' in request.channels and request.email,
                'smtp_server': 'smtp.gmail.com',
                'smtp_port': 587,
                'sender_email': request.email or '',
                'sender_password': ''  # 환경변수에서 로드 필요
            },
            'kakao': {
                'enabled': 'kakao' in request.channels and request.kakao_access_token,
                'access_token': request.kakao_access_token or ''
            },
            'slack': {
                'enabled': 'slack' in request.channels and request.slack_webhook,
                'webhook_url': request.slack_webhook or ''
            }
        }

        notifier = NotificationService(DB_URL, notification_config)

        # 요약 메시지 생성
        summary_message = f"""
📊 RSI+MA 상승전략 시그널 알림

📅 날짜: {target_date if target_date else '최신'}
📈 매수 시그널: {len(signals)}개

상위 5개 종목:
"""

        for i, signal in enumerate(signals[:5], 1):
            # None 값 안전 처리
            rsi = signal.get('rsi') or 0
            ma20 = signal.get('ma_20') or 0
            ma50 = signal.get('ma_50') or 0
            current_price = signal.get('current_price') or 0

            summary_message += f"""
{i}. {signal['ticker']} - {signal.get('company_name', 'N/A')}
   현재가: {current_price:,.0f}원
   RSI: {rsi:.2f}
   MA20: {ma20:,.0f} > MA50: {ma50:,.0f}
"""

        summary_message += f"\n💻 전체 시그널 확인: http://localhost:8000/rsi_ma_strategy.html"

        # 알림 전송
        success_count = 0
        errors = []

        if 'email' in request.channels and request.email:
            try:
                if notifier.send_email(request.email, f"[매수시그널] RSI+MA 전략 - {len(signals)}개 발견", summary_message):
                    success_count += 1
                    logger.info("Email sent successfully")
                else:
                    errors.append("Email send failed")
            except Exception as e:
                logger.error(f"Email error: {e}")
                errors.append(f"Email: {str(e)}")

        if 'kakao' in request.channels and request.kakao_access_token:
            try:
                if notifier.send_kakao('me', summary_message):
                    success_count += 1
                    logger.info("Kakao sent successfully")
                else:
                    errors.append("Kakao send failed")
            except Exception as e:
                logger.error(f"Kakao error: {e}")
                errors.append(f"Kakao: {str(e)}")

        if 'slack' in request.channels and request.slack_webhook:
            try:
                logger.info(f"Attempting to send Slack notification to {request.slack_webhook[:50]}...")
                if notifier.send_slack(request.slack_webhook, summary_message):
                    success_count += 1
                    logger.info("Slack sent successfully")
                else:
                    errors.append("Slack send failed - check webhook URL")
            except Exception as e:
                logger.error(f"Slack error: {e}")
                errors.append(f"Slack: {str(e)}")

        result = {
            "status": "success" if success_count > 0 else "error",
            "message": f"{success_count}/{len(request.channels)}개 채널로 알림 전송 완료",
            "signal_count": len(signals),
            "sent_count": success_count,
            "channels": request.channels
        }

        if errors:
            result["errors"] = errors

        return result

    except Exception as e:
        logger.error(f"Error sending signals notification: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
