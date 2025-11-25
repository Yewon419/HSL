from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from typing import List, Optional
from pydantic import BaseModel
from datetime import date, datetime
from decimal import Decimal

from database import get_db
from models import Holding, Stock, StockPrice, User
from user_service.auth import get_current_user

router = APIRouter()


# Pydantic Schemas
class HoldingCreate(BaseModel):
    ticker: str
    quantity: int
    avg_buy_price: float
    buy_date: date
    stop_loss_price: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_price: Optional[float] = None
    take_profit_percent: Optional[float] = None
    memo: Optional[str] = None
    target_quantity: Optional[int] = None


class HoldingUpdate(BaseModel):
    quantity: Optional[int] = None
    avg_buy_price: Optional[float] = None
    stop_loss_price: Optional[float] = None
    stop_loss_percent: Optional[float] = None
    take_profit_price: Optional[float] = None
    take_profit_percent: Optional[float] = None
    memo: Optional[str] = None
    target_quantity: Optional[int] = None
    is_active: Optional[bool] = None


class HoldingResponse(BaseModel):
    id: int
    ticker: str
    company_name: Optional[str]
    quantity: int
    avg_buy_price: float
    buy_date: date
    stop_loss_price: Optional[float]
    stop_loss_percent: Optional[float]
    take_profit_price: Optional[float]
    take_profit_percent: Optional[float]
    memo: Optional[str]
    target_quantity: Optional[int]
    is_active: bool
    created_at: datetime
    # 계산된 필드
    current_price: Optional[float] = None
    current_value: Optional[float] = None
    profit_loss: Optional[float] = None
    profit_loss_percent: Optional[float] = None
    stop_loss_status: Optional[str] = None  # 'safe', 'warning', 'triggered'
    take_profit_status: Optional[str] = None  # 'safe', 'near', 'triggered'

    class Config:
        from_attributes = True


class HoldingSummary(BaseModel):
    total_holdings: int
    total_buy_value: float
    total_current_value: float
    total_profit_loss: float
    total_profit_loss_percent: float
    stop_loss_triggered: int
    take_profit_triggered: int
    warning_count: int


@router.get("/", response_model=List[HoldingResponse])
async def get_holdings(
    is_active: Optional[bool] = Query(True, description="활성 보유종목만 조회"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """사용자의 보유종목 목록 조회"""
    query = db.query(Holding).filter(Holding.user_id == current_user.id)

    if is_active is not None:
        query = query.filter(Holding.is_active == is_active)

    holdings = query.order_by(desc(Holding.created_at)).all()

    result = []
    for holding in holdings:
        holding_data = _calculate_holding_status(db, holding)
        result.append(holding_data)

    return result


@router.get("/summary", response_model=HoldingSummary)
async def get_holdings_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """보유종목 요약 정보"""
    holdings = db.query(Holding).filter(
        Holding.user_id == current_user.id,
        Holding.is_active == True
    ).all()

    total_buy_value = 0.0
    total_current_value = 0.0
    stop_loss_triggered = 0
    take_profit_triggered = 0
    warning_count = 0

    for holding in holdings:
        holding_data = _calculate_holding_status(db, holding)

        buy_value = float(holding.avg_buy_price) * holding.quantity
        total_buy_value += buy_value

        if holding_data.get('current_value'):
            total_current_value += holding_data['current_value']
        else:
            total_current_value += buy_value

        if holding_data.get('stop_loss_status') == 'triggered':
            stop_loss_triggered += 1
        elif holding_data.get('stop_loss_status') == 'warning':
            warning_count += 1

        if holding_data.get('take_profit_status') == 'triggered':
            take_profit_triggered += 1
        elif holding_data.get('take_profit_status') == 'near':
            warning_count += 1

    total_profit_loss = total_current_value - total_buy_value
    total_profit_loss_percent = (total_profit_loss / total_buy_value * 100) if total_buy_value > 0 else 0

    return HoldingSummary(
        total_holdings=len(holdings),
        total_buy_value=round(total_buy_value, 2),
        total_current_value=round(total_current_value, 2),
        total_profit_loss=round(total_profit_loss, 2),
        total_profit_loss_percent=round(total_profit_loss_percent, 2),
        stop_loss_triggered=stop_loss_triggered,
        take_profit_triggered=take_profit_triggered,
        warning_count=warning_count
    )


@router.post("/", response_model=HoldingResponse)
async def create_holding(
    holding_data: HoldingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """보유종목 추가"""
    # 종목 존재 확인
    stock = db.query(Stock).filter(Stock.ticker == holding_data.ticker).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"종목 {holding_data.ticker}을 찾을 수 없습니다")

    # 이미 보유중인지 확인
    existing = db.query(Holding).filter(
        Holding.user_id == current_user.id,
        Holding.ticker == holding_data.ticker,
        Holding.is_active == True
    ).first()

    if existing:
        raise HTTPException(status_code=400, detail=f"이미 보유중인 종목입니다. 수정하려면 PUT 요청을 사용하세요.")

    # 손절가/익절가 자동 계산
    stop_loss_price = holding_data.stop_loss_price
    take_profit_price = holding_data.take_profit_price

    if holding_data.stop_loss_percent and not stop_loss_price:
        stop_loss_price = holding_data.avg_buy_price * (1 + holding_data.stop_loss_percent / 100)

    if holding_data.take_profit_percent and not take_profit_price:
        take_profit_price = holding_data.avg_buy_price * (1 + holding_data.take_profit_percent / 100)

    new_holding = Holding(
        user_id=current_user.id,
        ticker=holding_data.ticker,
        company_name=stock.company_name,
        quantity=holding_data.quantity,
        avg_buy_price=holding_data.avg_buy_price,
        buy_date=holding_data.buy_date,
        stop_loss_price=stop_loss_price,
        stop_loss_percent=holding_data.stop_loss_percent,
        take_profit_price=take_profit_price,
        take_profit_percent=holding_data.take_profit_percent,
        memo=holding_data.memo,
        target_quantity=holding_data.target_quantity,
        is_active=True
    )

    db.add(new_holding)
    db.commit()
    db.refresh(new_holding)

    return _calculate_holding_status(db, new_holding)


@router.get("/{holding_id}", response_model=HoldingResponse)
async def get_holding(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """특정 보유종목 조회"""
    holding = db.query(Holding).filter(
        Holding.id == holding_id,
        Holding.user_id == current_user.id
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail="보유종목을 찾을 수 없습니다")

    return _calculate_holding_status(db, holding)


@router.put("/{holding_id}", response_model=HoldingResponse)
async def update_holding(
    holding_id: int,
    holding_data: HoldingUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """보유종목 수정"""
    holding = db.query(Holding).filter(
        Holding.id == holding_id,
        Holding.user_id == current_user.id
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail="보유종목을 찾을 수 없습니다")

    update_data = holding_data.dict(exclude_unset=True)

    # 손절가 퍼센트로 자동 계산
    if 'stop_loss_percent' in update_data and update_data['stop_loss_percent'] is not None:
        avg_price = update_data.get('avg_buy_price', float(holding.avg_buy_price))
        update_data['stop_loss_price'] = avg_price * (1 + update_data['stop_loss_percent'] / 100)

    # 익절가 퍼센트로 자동 계산
    if 'take_profit_percent' in update_data and update_data['take_profit_percent'] is not None:
        avg_price = update_data.get('avg_buy_price', float(holding.avg_buy_price))
        update_data['take_profit_price'] = avg_price * (1 + update_data['take_profit_percent'] / 100)

    for key, value in update_data.items():
        setattr(holding, key, value)

    db.commit()
    db.refresh(holding)

    return _calculate_holding_status(db, holding)


@router.delete("/{holding_id}")
async def delete_holding(
    holding_id: int,
    hard_delete: bool = Query(False, description="완전 삭제 여부"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """보유종목 삭제 (기본: 비활성화, hard_delete=True: 완전삭제)"""
    holding = db.query(Holding).filter(
        Holding.id == holding_id,
        Holding.user_id == current_user.id
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail="보유종목을 찾을 수 없습니다")

    if hard_delete:
        db.delete(holding)
    else:
        holding.is_active = False

    db.commit()

    return {"message": "보유종목이 삭제되었습니다", "holding_id": holding_id}


@router.get("/{holding_id}/status")
async def get_holding_status(
    holding_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """보유종목 손절/익절 상태 확인"""
    holding = db.query(Holding).filter(
        Holding.id == holding_id,
        Holding.user_id == current_user.id
    ).first()

    if not holding:
        raise HTTPException(status_code=404, detail="보유종목을 찾을 수 없습니다")

    status = _calculate_holding_status(db, holding)

    alerts = []
    if status.get('stop_loss_status') == 'triggered':
        alerts.append({
            "type": "stop_loss",
            "level": "danger",
            "message": f"손절가 도달! 현재가 {status['current_price']:,.0f}원이 손절가 {status['stop_loss_price']:,.0f}원 이하입니다."
        })
    elif status.get('stop_loss_status') == 'warning':
        alerts.append({
            "type": "stop_loss",
            "level": "warning",
            "message": f"손절가 임박! 현재가가 손절가에 5% 이내로 접근했습니다."
        })

    if status.get('take_profit_status') == 'triggered':
        alerts.append({
            "type": "take_profit",
            "level": "success",
            "message": f"익절가 도달! 현재가 {status['current_price']:,.0f}원이 익절가 {status['take_profit_price']:,.0f}원 이상입니다."
        })
    elif status.get('take_profit_status') == 'near':
        alerts.append({
            "type": "take_profit",
            "level": "info",
            "message": f"익절가 임박! 현재가가 익절가에 5% 이내로 접근했습니다."
        })

    return {
        "holding": status,
        "alerts": alerts
    }


def _calculate_holding_status(db: Session, holding: Holding) -> dict:
    """보유종목의 현재 상태 계산 (현재가, 수익률, 손절/익절 상태)"""
    # 최신 주가 조회
    latest_price = db.query(StockPrice).filter(
        StockPrice.ticker == holding.ticker
    ).order_by(desc(StockPrice.date)).first()

    current_price = float(latest_price.close_price) if latest_price else None
    avg_buy_price = float(holding.avg_buy_price)

    result = {
        "id": holding.id,
        "ticker": holding.ticker,
        "company_name": holding.company_name,
        "quantity": holding.quantity,
        "avg_buy_price": avg_buy_price,
        "buy_date": holding.buy_date,
        "stop_loss_price": float(holding.stop_loss_price) if holding.stop_loss_price else None,
        "stop_loss_percent": float(holding.stop_loss_percent) if holding.stop_loss_percent else None,
        "take_profit_price": float(holding.take_profit_price) if holding.take_profit_price else None,
        "take_profit_percent": float(holding.take_profit_percent) if holding.take_profit_percent else None,
        "memo": holding.memo,
        "target_quantity": holding.target_quantity,
        "is_active": holding.is_active,
        "created_at": holding.created_at,
        "current_price": current_price,
        "current_value": None,
        "profit_loss": None,
        "profit_loss_percent": None,
        "stop_loss_status": "safe",
        "take_profit_status": "safe"
    }

    if current_price:
        current_value = current_price * holding.quantity
        buy_value = avg_buy_price * holding.quantity
        profit_loss = current_value - buy_value
        profit_loss_percent = (profit_loss / buy_value) * 100 if buy_value > 0 else 0

        result["current_value"] = round(current_value, 2)
        result["profit_loss"] = round(profit_loss, 2)
        result["profit_loss_percent"] = round(profit_loss_percent, 2)

        # 손절 상태 확인
        if holding.stop_loss_price:
            stop_loss = float(holding.stop_loss_price)
            if current_price <= stop_loss:
                result["stop_loss_status"] = "triggered"
            elif current_price <= stop_loss * 1.05:  # 5% 이내
                result["stop_loss_status"] = "warning"

        # 익절 상태 확인
        if holding.take_profit_price:
            take_profit = float(holding.take_profit_price)
            if current_price >= take_profit:
                result["take_profit_status"] = "triggered"
            elif current_price >= take_profit * 0.95:  # 5% 이내
                result["take_profit_status"] = "near"

    return result
