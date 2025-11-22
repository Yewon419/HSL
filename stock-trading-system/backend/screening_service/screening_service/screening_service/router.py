"""
Stock Screening and Backtesting Router
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
import logging

from .screener import StockScreener, BacktestEngine

logger = logging.getLogger(__name__)

router = APIRouter()

class ScreeningCondition(BaseModel):
    indicator: str
    condition: str  # golden_cross, death_cross, above, below, between
    lookback_days: Optional[int] = 5
    value: Optional[float] = None
    value2: Optional[float] = None

class ScreeningRequest(BaseModel):
    conditions: List[ScreeningCondition]
    start_date: str
    end_date: str

class BacktestRequest(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str
    initial_capital: float = 1000000
    position_size: float = 0.1
    transaction_cost: float = 0.003

# Initialize screener and backtester
screener = StockScreener()
backtester = BacktestEngine()

@router.get("/indicators")
async def get_available_indicators():
    """사용 가능한 지표 목록 조회"""
    try:
        indicators = screener.get_available_indicators()
        return indicators
    except Exception as e:
        logger.error(f"Error getting indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/screen")
async def screen_stocks(request: ScreeningRequest):
    """다중 조건 스크리닝 실행"""
    try:
        # Convert Pydantic models to dict
        conditions = [condition.dict() for condition in request.conditions]

        results = screener.screen_stocks(
            conditions=conditions,
            date_range=(request.start_date, request.end_date)
        )

        return results
    except Exception as e:
        logger.error(f"Error in screening: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/backtest")
async def run_backtest(request: BacktestRequest):
    """백테스팅 실행"""
    try:
        results = backtester.run_backtest(
            tickers=request.tickers,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            position_size=request.position_size,
            transaction_cost=request.transaction_cost
        )

        return results
    except Exception as e:
        logger.error(f"Error in backtesting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/health")
async def health_check():
    """스크리닝 서비스 헬스 체크"""
    return {"service": "screening", "status": "healthy"}