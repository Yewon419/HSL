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
                s.country,
                ti.ticker,
                s.company_name,
                s.sector,
                ti.date,
                sp.open_price,
                sp.high_price,
                sp.low_price,
                sp.close_price,
                sp.volume,
                (SELECT volume FROM stock_prices sp2
                 WHERE sp2.ticker = ti.ticker
                 AND sp2.date < ti.date
                 ORDER BY sp2.date DESC
                 LIMIT 1) as prev_volume,
                ti.rsi,
                CASE
                    WHEN ti.rsi < 30 THEN '매수'
                    WHEN ti.rsi >= 70 THEN '매도'
                    ELSE '보합'
                END as rsi_signal,
                CASE
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL AND ti.ma_200 IS NOT NULL
                        AND ti.ma_20 > ti.ma_50 AND ti.ma_50 > ti.ma_200 THEN '정배열'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL AND ti.ma_200 IS NOT NULL
                        AND ti.ma_20 < ti.ma_50 AND ti.ma_50 < ti.ma_200 THEN '역배열'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL
                        AND ti.ma_20 > ti.ma_50 THEN '단기상승'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL
                        AND ti.ma_20 < ti.ma_50 THEN '단기하락'
                    ELSE '-'
                END as trend,
                ti.macd,
                ti.stoch_k,
                ti.stoch_d,
                CASE
                    WHEN ti.stoch_k > ti.stoch_d THEN '골든'
                    WHEN ti.stoch_k < ti.stoch_d THEN '데드'
                    ELSE '-'
                END as stoch_signal,
                it.foreign_buy,
                it.foreign_sell,
                (it.foreign_buy - it.foreign_sell) as foreign_net,
                it.institution_buy,
                it.institution_sell,
                (it.institution_buy - it.institution_sell) as institution_net,
                it.individual_buy,
                it.individual_sell,
                (it.individual_buy - it.individual_sell) as individual_net
            FROM technical_indicators ti
            LEFT JOIN stocks s ON ti.ticker = s.ticker
            LEFT JOIN stock_prices sp ON ti.ticker = sp.ticker AND ti.date = sp.date
            LEFT JOIN investor_trades it ON ti.ticker = it.ticker AND ti.date = it.date
            WHERE ti.date = :date
            ORDER BY ti.ticker
        """), {"date": date_filter})

        indicators = []
        for row in result:
            # 볼륨 변동 계산 (전일 대비 증감)
            volume_change = 0
            if row.volume and row.prev_volume:
                volume_change = int(row.volume) - int(row.prev_volume)

            indicators.append({
                "country": row.country,
                "ticker": row.ticker,
                "company_name": row.company_name,
                "sector": row.sector,
                "date": str(row.date),
                "open_price": float(row.open_price) if row.open_price else 0,
                "high_price": float(row.high_price) if row.high_price else 0,
                "low_price": float(row.low_price) if row.low_price else 0,
                "close_price": float(row.close_price) if row.close_price else 0,
                "volume": int(row.volume) if row.volume else 0,
                "volume_change": volume_change,
                "rsi": float(row.rsi) if row.rsi else 0,
                "rsi_signal": row.rsi_signal,
                "trend": row.trend,
                "macd": float(row.macd) if row.macd else 0,
                "stoch_k": float(row.stoch_k) if row.stoch_k else 0,
                "stoch_d": float(row.stoch_d) if row.stoch_d else 0,
                "stoch_signal": row.stoch_signal,
                "foreign_buy": int(row.foreign_buy) if row.foreign_buy else 0,
                "foreign_sell": int(row.foreign_sell) if row.foreign_sell else 0,
                "foreign_net": int(row.foreign_net) if row.foreign_net else 0,
                "institution_buy": int(row.institution_buy) if row.institution_buy else 0,
                "institution_sell": int(row.institution_sell) if row.institution_sell else 0,
                "institution_net": int(row.institution_net) if row.institution_net else 0,
                "individual_buy": int(row.individual_buy) if row.individual_buy else 0,
                "individual_sell": int(row.individual_sell) if row.individual_sell else 0,
                "individual_net": int(row.individual_net) if row.individual_net else 0
            })

        return indicators

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/monthly/{ticker}")
def get_ticker_monthly_indicators(
    ticker: str,
    days: int = Query(30, description="Number of days to retrieve"),
    db: Session = Depends(get_db)
):
    """Get monthly indicators data for a specific ticker"""
    try:
        result = db.execute(text("""
            SELECT
                ti.date,
                sp.open_price,
                sp.high_price,
                sp.low_price,
                sp.close_price,
                sp.volume,
                (SELECT volume FROM stock_prices sp2
                 WHERE sp2.ticker = ti.ticker
                 AND sp2.date < ti.date
                 ORDER BY sp2.date DESC
                 LIMIT 1) as prev_volume,
                ti.rsi,
                CASE
                    WHEN ti.rsi < 30 THEN '매수'
                    WHEN ti.rsi >= 70 THEN '매도'
                    ELSE '보합'
                END as rsi_signal,
                CASE
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL AND ti.ma_200 IS NOT NULL
                        AND ti.ma_20 > ti.ma_50 AND ti.ma_50 > ti.ma_200 THEN '정배열'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL AND ti.ma_200 IS NOT NULL
                        AND ti.ma_20 < ti.ma_50 AND ti.ma_50 < ti.ma_200 THEN '역배열'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL
                        AND ti.ma_20 > ti.ma_50 THEN '단기상승'
                    WHEN ti.ma_20 IS NOT NULL AND ti.ma_50 IS NOT NULL
                        AND ti.ma_20 < ti.ma_50 THEN '단기하락'
                    ELSE '-'
                END as trend,
                ti.macd,
                ti.stoch_k,
                ti.stoch_d,
                CASE
                    WHEN ti.stoch_k > ti.stoch_d THEN '골든'
                    WHEN ti.stoch_k < ti.stoch_d THEN '데드'
                    ELSE '-'
                END as stoch_signal,
                it.foreign_buy,
                it.foreign_sell,
                (it.foreign_buy - it.foreign_sell) as foreign_net,
                it.institution_buy,
                it.institution_sell,
                (it.institution_buy - it.institution_sell) as institution_net,
                it.individual_buy,
                it.individual_sell,
                (it.individual_buy - it.individual_sell) as individual_net
            FROM technical_indicators ti
            LEFT JOIN stock_prices sp ON ti.ticker = sp.ticker AND ti.date = sp.date
            LEFT JOIN investor_trades it ON ti.ticker = it.ticker AND ti.date = it.date
            WHERE ti.ticker = :ticker
            ORDER BY ti.date DESC
            LIMIT :days
        """), {"ticker": ticker, "days": days})

        monthly_data = []
        for row in result:
            # 볼륨 변동 계산 (전일 대비 증감)
            volume_change = 0
            if row.volume and row.prev_volume:
                volume_change = int(row.volume) - int(row.prev_volume)

            monthly_data.append({
                "date": str(row.date),
                "open_price": float(row.open_price) if row.open_price else 0,
                "high_price": float(row.high_price) if row.high_price else 0,
                "low_price": float(row.low_price) if row.low_price else 0,
                "close_price": float(row.close_price) if row.close_price else 0,
                "volume": int(row.volume) if row.volume else 0,
                "volume_change": volume_change,
                "rsi": float(row.rsi) if row.rsi else 0,
                "rsi_signal": row.rsi_signal,
                "trend": row.trend,
                "macd": float(row.macd) if row.macd else 0,
                "stoch_k": float(row.stoch_k) if row.stoch_k else 0,
                "stoch_d": float(row.stoch_d) if row.stoch_d else 0,
                "stoch_signal": row.stoch_signal,
                "foreign_buy": int(row.foreign_buy) if row.foreign_buy else 0,
                "foreign_sell": int(row.foreign_sell) if row.foreign_sell else 0,
                "foreign_net": int(row.foreign_net) if row.foreign_net else 0,
                "institution_buy": int(row.institution_buy) if row.institution_buy else 0,
                "institution_sell": int(row.institution_sell) if row.institution_sell else 0,
                "institution_net": int(row.institution_net) if row.institution_net else 0,
                "individual_buy": int(row.individual_buy) if row.individual_buy else 0,
                "individual_sell": int(row.individual_sell) if row.individual_sell else 0,
                "individual_net": int(row.individual_net) if row.individual_net else 0
            })

        return monthly_data

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