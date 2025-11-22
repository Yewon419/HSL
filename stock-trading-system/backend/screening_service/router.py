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

class StrategyTemplate(BaseModel):
    name: str
    description: str
    conditions: List[ScreeningCondition]
    created_at: Optional[str] = None

class SaveStrategyRequest(BaseModel):
    name: str
    description: str
    conditions: List[ScreeningCondition]

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

# 전략 관리 API
import json
import os
from datetime import datetime

STRATEGIES_FILE = "screening_strategies.json"

def load_strategies():
    """저장된 전략 목록 로드"""
    if os.path.exists(STRATEGIES_FILE):
        try:
            with open(STRATEGIES_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading strategies: {e}")
            return {"strategies": [], "default_strategies": get_default_strategies()}
    return {"strategies": [], "default_strategies": get_default_strategies()}

def save_strategies(strategies_data):
    """전략 목록 저장"""
    try:
        with open(STRATEGIES_FILE, 'w', encoding='utf-8') as f:
            json.dump(strategies_data, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        logger.error(f"Error saving strategies: {e}")
        return False

def get_default_strategies():
    """기본 전략 템플릿 제공"""
    return [
        {
            "name": "모멘텀 돌파 전략",
            "description": "강한 상승 모멘텀을 보이는 종목 선별",
            "conditions": [
                {"indicator": "RSI", "condition": "golden_cross", "lookback_days": 5},
                {"indicator": "MACD", "condition": "golden_cross", "lookback_days": 3},
                {"indicator": "ADX", "condition": "above", "value": 25.0, "lookback_days": 1}
            ],
            "created_at": "2025-09-24"
        },
        {
            "name": "과매도 반등 전략",
            "description": "과도하게 하락한 종목의 반등 기회 포착",
            "conditions": [
                {"indicator": "RSI", "condition": "below", "value": 25.0, "lookback_days": 1},
                {"indicator": "MFI", "condition": "below", "value": 20.0, "lookback_days": 1},
                {"indicator": "CCI", "condition": "below", "value": -100.0, "lookback_days": 1}
            ],
            "created_at": "2025-09-24"
        },
        {
            "name": "안정적 추세 전략",
            "description": "과열되지 않은 상태에서 추세가 시작되는 종목",
            "conditions": [
                {"indicator": "RSI", "condition": "between", "value": 40.0, "value2": 60.0, "lookback_days": 1},
                {"indicator": "ADX", "condition": "above", "value": 20.0, "lookback_days": 1},
                {"indicator": "MACD", "condition": "golden_cross", "lookback_days": 7}
            ],
            "created_at": "2025-09-24"
        }
    ]

@router.get("/strategies")
async def get_strategies():
    """저장된 전략 목록 조회"""
    try:
        strategies_data = load_strategies()
        return strategies_data
    except Exception as e:
        logger.error(f"Error getting strategies: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies")
async def save_strategy(request: SaveStrategyRequest):
    """새로운 전략 저장"""
    try:
        strategies_data = load_strategies()

        # 현재 시간 추가
        strategy_dict = request.dict()
        strategy_dict["created_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 동일한 이름의 전략이 있으면 업데이트, 없으면 추가
        existing_index = -1
        for i, existing_strategy in enumerate(strategies_data["strategies"]):
            if existing_strategy["name"] == strategy_dict["name"]:
                existing_index = i
                break

        if existing_index >= 0:
            strategies_data["strategies"][existing_index] = strategy_dict
        else:
            strategies_data["strategies"].append(strategy_dict)

        if save_strategies(strategies_data):
            return {"message": "전략이 성공적으로 저장되었습니다", "strategy": strategy_dict}
        else:
            raise HTTPException(status_code=500, detail="전략 저장 중 오류가 발생했습니다")
    except Exception as e:
        logger.error(f"Error saving strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/strategies/{strategy_name}")
async def delete_strategy(strategy_name: str):
    """전략 삭제"""
    try:
        strategies_data = load_strategies()

        # 전략 찾아서 삭제
        original_count = len(strategies_data["strategies"])
        strategies_data["strategies"] = [
            s for s in strategies_data["strategies"]
            if s["name"] != strategy_name
        ]

        if len(strategies_data["strategies"]) < original_count:
            if save_strategies(strategies_data):
                return {"message": f"전략 '{strategy_name}'이 삭제되었습니다"}
            else:
                raise HTTPException(status_code=500, detail="전략 삭제 중 오류가 발생했습니다")
        else:
            raise HTTPException(status_code=404, detail=f"전략 '{strategy_name}'을 찾을 수 없습니다")
    except Exception as e:
        logger.error(f"Error deleting strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/strategies/{strategy_name}/execute")
async def execute_strategy(strategy_name: str, start_date: str, end_date: str):
    """저장된 전략 실행"""
    try:
        strategies_data = load_strategies()

        # 기본 전략과 사용자 전략에서 찾기
        all_strategies = strategies_data["strategies"] + strategies_data["default_strategies"]

        target_strategy = None
        for strategy in all_strategies:
            if strategy["name"] == strategy_name:
                target_strategy = strategy
                break

        if not target_strategy:
            raise HTTPException(status_code=404, detail=f"전략 '{strategy_name}'을 찾을 수 없습니다")

        # 스크리닝 실행
        screening_request = ScreeningRequest(
            conditions=[ScreeningCondition(**cond) for cond in target_strategy["conditions"]],
            start_date=start_date,
            end_date=end_date
        )

        # Convert Pydantic models to dict
        conditions = [condition.dict() for condition in screening_request.conditions]

        results = screener.screen_stocks(
            conditions=conditions,
            date_range=(screening_request.start_date, screening_request.end_date)
        )

        return {
            "strategy_name": strategy_name,
            "strategy_description": target_strategy.get("description", ""),
            "execution_date": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "results": results
        }
    except Exception as e:
        logger.error(f"Error executing strategy: {e}")
        raise HTTPException(status_code=500, detail=str(e))