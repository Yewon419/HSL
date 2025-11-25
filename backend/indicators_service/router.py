"""
Technical Indicators API Router
Provides endpoints for accessing technical indicators data
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional, Dict, Any
from datetime import datetime, date
import json
import math


def safe_float(value, default=0):
    """NaN/None을 안전하게 처리하여 JSON 호환 값 반환"""
    if value is None:
        return default
    try:
        f = float(value)
        if math.isnan(f) or math.isinf(f):
            return default
        return f
    except (ValueError, TypeError):
        return default

from database import get_db
from user_service.auth import get_current_user
import models

router = APIRouter()

@router.get("/categories")
def get_indicator_categories(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get all indicator categories"""
    result = db.execute(text("""
        SELECT 
            ic.id,
            ic.name,
            ic.description,
            ic.parent_id,
            COUNT(DISTINCT id.id) as indicator_count
        FROM indicator_categories ic
        LEFT JOIN indicator_definitions id ON ic.id = id.category_id AND id.is_active = true
        GROUP BY ic.id, ic.name, ic.description, ic.parent_id
        ORDER BY ic.display_order, ic.name
    """))
    
    categories = []
    for row in result:
        categories.append({
            "id": row.id,
            "name": row.name,
            "description": row.description,
            "parent_id": row.parent_id,
            "indicator_count": row.indicator_count
        })
    
    return categories

@router.get("/definitions")
def get_indicator_definitions(
    category_id: Optional[int] = Query(None, description="Filter by category ID"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get indicator definitions"""
    query = """
        SELECT 
            id.id,
            id.code,
            id.name,
            id.name_kr,
            id.description,
            id.parameters,
            id.output_columns,
            id.calculation_type,
            ic.name as category_name
        FROM indicator_definitions id
        JOIN indicator_categories ic ON id.category_id = ic.id
        WHERE id.is_active = true
    """
    
    params = {}
    if category_id:
        query += " AND id.category_id = :category_id"
        params['category_id'] = category_id
    
    query += " ORDER BY ic.display_order, id.display_order"
    
    result = db.execute(text(query), params)
    
    definitions = []
    for row in result:
        # Handle JSON fields
        parameters = row.parameters
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
        
        output_columns = row.output_columns
        if isinstance(output_columns, str):
            output_columns = json.loads(output_columns)
            
        definitions.append({
            "id": row.id,
            "code": row.code,
            "name": row.name,
            "name_kr": row.name_kr,
            "description": row.description,
            "parameters": parameters,
            "output_columns": output_columns,
            "calculation_type": row.calculation_type,
            "category_name": row.category_name
        })
    
    return definitions

@router.get("/summary/{ticker}")
def get_indicator_summary(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get indicator summary for a specific ticker"""
    result = db.execute(text("""
        SELECT 
            ticker,
            company_name,
            current_price,
            price_date,
            sma_20,
            sma_50,
            sma_200,
            ema_20,
            macd,
            macd_signal,
            macd_histogram,
            rsi,
            stoch_k,
            stoch_d,
            bb_upper,
            bb_middle,
            bb_lower,
            adx,
            atr
        FROM v_indicator_summary
        WHERE ticker = :ticker
    """), {"ticker": ticker})
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No indicator data found for ticker {ticker}")
    
    return {
        "ticker": row.ticker,
        "company_name": row.company_name,
        "current_price": float(row.current_price) if row.current_price else None,
        "price_date": row.price_date,
        "moving_averages": {
            "sma_20": float(row.sma_20) if row.sma_20 else None,
            "sma_50": float(row.sma_50) if row.sma_50 else None,
            "sma_200": float(row.sma_200) if row.sma_200 else None,
            "ema_20": float(row.ema_20) if row.ema_20 else None,
        },
        "macd": {
            "macd": float(row.macd) if row.macd else None,
            "signal": float(row.macd_signal) if row.macd_signal else None,
            "histogram": float(row.macd_histogram) if row.macd_histogram else None,
        },
        "oscillators": {
            "rsi": float(row.rsi) if row.rsi else None,
            "stoch_k": float(row.stoch_k) if row.stoch_k else None,
            "stoch_d": float(row.stoch_d) if row.stoch_d else None,
        },
        "volatility": {
            "bb_upper": float(row.bb_upper) if row.bb_upper else None,
            "bb_middle": float(row.bb_middle) if row.bb_middle else None,
            "bb_lower": float(row.bb_lower) if row.bb_lower else None,
            "atr": float(row.atr) if row.atr else None,
        },
        "trend": {
            "adx": float(row.adx) if row.adx else None,
        }
    }

@router.get("/timeseries/{ticker}")
def get_indicator_timeseries(
    ticker: str,
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    indicators: Optional[str] = Query(None, description="Comma-separated list of indicator codes"),
    limit: int = Query(100, description="Maximum number of records"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get historical indicator data for a ticker"""
    query = """
        SELECT 
            iv.date,
            id.code as indicator_code,
            id.name as indicator_name,
            ic.name as category,
            iv.value,
            iv.parameters
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        JOIN indicator_categories ic ON id.category_id = ic.id
        WHERE iv.ticker = :ticker
    """
    
    params = {"ticker": ticker}
    
    if start_date:
        query += " AND iv.date >= :start_date"
        params["start_date"] = start_date
    
    if end_date:
        query += " AND iv.date <= :end_date"
        params["end_date"] = end_date
    
    if indicators:
        indicator_list = [i.strip() for i in indicators.split(',')]
        query += " AND id.code = ANY(:indicators)"
        params["indicators"] = indicator_list
    
    query += " ORDER BY iv.date DESC, id.code LIMIT :limit"
    params["limit"] = limit
    
    result = db.execute(text(query), params)
    
    timeseries_data = []
    for row in result:
        # Parse JSON value
        value_data = row.value
        if isinstance(value_data, str):
            value_data = json.loads(value_data)
        
        parameters = row.parameters
        if isinstance(parameters, str):
            parameters = json.loads(parameters)
            
        timeseries_data.append({
            "date": row.date,
            "indicator_code": row.indicator_code,
            "indicator_name": row.indicator_name,
            "category": row.category,
            "values": value_data,
            "parameters": parameters
        })
    
    return {
        "ticker": ticker,
        "data_points": len(timeseries_data),
        "data": timeseries_data
    }

@router.get("/grid")
def get_indicators_grid(
    date: Optional[str] = Query(None, description="Date filter (YYYY-MM-DD)"),
    db: Session = Depends(get_db)
):
    """Get indicators grid data for all stocks on a specific date"""
    try:
        date_filter = date if date else '2025-10-02'

        result = db.execute(text("""
            SELECT
                ti.ticker,
                s.company_name,
                s.sector,
                s.country,
                ti.date,
                sp.close_price,
                sp.high_price,
                sp.low_price,
                sp.volume,
                ti.rsi,
                ti.ma_20,
                ti.ma_50,
                ti.ma_200,
                ti.macd,
                ti.macd_signal,
                ti.stoch_k,
                ti.stoch_d,
                ti.bollinger_upper,
                ti.bollinger_lower
            FROM technical_indicators ti
            LEFT JOIN stocks s ON ti.ticker = s.ticker
            LEFT JOIN stock_prices sp ON ti.ticker = sp.ticker AND ti.date = sp.date
            WHERE ti.date = :date
            ORDER BY ti.ticker
        """), {"date": date_filter})

        indicators = []
        for row in result:
            indicators.append({
                "ticker": row.ticker,
                "company_name": row.company_name,
                "sector": row.sector,
                "country": row.country,
                "date": str(row.date),
                "close": safe_float(row.close_price),
                "high": safe_float(row.high_price),
                "low": safe_float(row.low_price),
                "volume": safe_float(row.volume) if row.volume else 0,
                "rsi": safe_float(row.rsi),
                "ma_20": safe_float(row.ma_20),
                "ma_50": safe_float(row.ma_50),
                "ma_200": safe_float(row.ma_200),
                "macd": safe_float(row.macd),
                "macd_signal": safe_float(row.macd_signal),
                "stoch_k": safe_float(row.stoch_k),
                "stoch_d": safe_float(row.stoch_d),
                "bb_upper": safe_float(row.bollinger_upper),
                "bb_lower": safe_float(row.bollinger_lower),
                "foreign_net": 0,
                "institution_net": 0,
                "individual_net": 0
            })

        return indicators

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/signals/{ticker}")
def get_trading_signals(
    ticker: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Get trading signals for a ticker"""
    result = db.execute(text("""
        SELECT
            ticker,
            company_name,
            date,
            current_price,
            rsi,
            macd,
            macd_signal,
            stoch_k,
            stoch_d,
            sma_20,
            sma_50,
            adx,
            rsi_signal,
            macd_signal_type,
            stoch_signal,
            trend_signal,
            trend_strength
        FROM v_trading_signals
        WHERE ticker = :ticker
    """), {"ticker": ticker})
    
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail=f"No trading signals found for ticker {ticker}")
    
    return {
        "ticker": row.ticker,
        "company_name": row.company_name,
        "date": row.date,
        "current_price": float(row.current_price) if row.current_price else None,
        "indicators": {
            "rsi": float(row.rsi) if row.rsi else None,
            "macd": float(row.macd) if row.macd else None,
            "macd_signal": float(row.macd_signal) if row.macd_signal else None,
            "stoch_k": float(row.stoch_k) if row.stoch_k else None,
            "stoch_d": float(row.stoch_d) if row.stoch_d else None,
            "sma_20": float(row.sma_20) if row.sma_20 else None,
            "sma_50": float(row.sma_50) if row.sma_50 else None,
            "adx": float(row.adx) if row.adx else None,
        },
        "signals": {
            "rsi_signal": row.rsi_signal,
            "macd_signal": row.macd_signal_type,
            "stochastic_signal": row.stoch_signal,
            "trend_signal": row.trend_signal,
            "trend_strength": row.trend_strength,
        },
        "overall_sentiment": _calculate_overall_sentiment(
            row.rsi_signal, row.macd_signal_type, row.stoch_signal, row.trend_signal
        )
    }

def _calculate_overall_sentiment(rsi_signal, macd_signal, stoch_signal, trend_signal):
    """Calculate overall market sentiment based on signals"""
    bullish_signals = 0
    bearish_signals = 0
    neutral_signals = 0
    
    signals = [rsi_signal, macd_signal, stoch_signal, trend_signal]
    
    for signal in signals:
        if signal in ['Buy', 'Bullish', 'Uptrend', 'Strong Trend']:
            bullish_signals += 1
        elif signal in ['Sell', 'Bearish', 'Downtrend']:
            bearish_signals += 1
        else:
            neutral_signals += 1
    
    if bullish_signals > bearish_signals + 1:
        return "Bullish"
    elif bearish_signals > bullish_signals + 1:
        return "Bearish"
    else:
        return "Neutral"

@router.get("/comparison")
def compare_indicators(
    tickers: str = Query(..., description="Comma-separated list of tickers to compare"),
    indicator: str = Query("RSI", description="Indicator code to compare"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user)
):
    """Compare specific indicator across multiple tickers"""
    ticker_list = [t.strip() for t in tickers.split(',')]
    
    if len(ticker_list) > 10:
        raise HTTPException(status_code=400, detail="Maximum 10 tickers allowed for comparison")
    
    result = db.execute(text("""
        SELECT 
            iv.ticker,
            s.company_name,
            iv.date,
            id.code as indicator_code,
            iv.value
        FROM indicator_values iv
        JOIN indicator_definitions id ON iv.indicator_id = id.id
        JOIN stocks s ON iv.ticker = s.ticker
        WHERE iv.ticker = ANY(:tickers)
          AND id.code = :indicator
          AND iv.date = (
              SELECT MAX(date) 
              FROM indicator_values iv2 
              WHERE iv2.ticker = iv.ticker 
              AND iv2.indicator_id = iv.indicator_id
          )
        ORDER BY iv.ticker
    """), {"tickers": ticker_list, "indicator": indicator})
    
    comparison_data = []
    for row in result:
        value_data = row.value
        if isinstance(value_data, str):
            value_data = json.loads(value_data)
            
        comparison_data.append({
            "ticker": row.ticker,
            "company_name": row.company_name,
            "date": row.date,
            "indicator_code": row.indicator_code,
            "values": value_data
        })
    
    return {
        "indicator": indicator,
        "comparison_data": comparison_data,
        "total_tickers": len(comparison_data)
    }