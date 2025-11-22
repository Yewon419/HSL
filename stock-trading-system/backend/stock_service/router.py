from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timedelta
from pydantic import BaseModel

from database import get_db
import models
from .data_fetcher import StockDataFetcher, MarketScreener
from user_service.auth import get_current_user

router = APIRouter()

class StockCreate(BaseModel):
    ticker: str
    company_name: str
    sector: Optional[str] = None
    industry: Optional[str] = None

class StockResponse(BaseModel):
    ticker: str
    company_name: Optional[str] = None
    sector: Optional[str] = None
    industry: Optional[str] = None
    market_cap: Optional[int] = None
    
class StockUpdate(BaseModel):
    ticker: str

# 종목 관리 API 엔드포인트들
@router.get("/list-with-indicators")
def get_stocks_with_indicators(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    country: Optional[str] = Query(default=None),
    sector: Optional[str] = Query(default=None),
    sort_by: Optional[str] = Query(default="ticker"),
    sort_order: Optional[str] = Query(default="asc"),
    db: Session = Depends(get_db)
):
    """종목 목록과 최신 지표를 함께 조회합니다."""
    from sqlalchemy import desc, asc

    # 최신 데이터만 가져오기 위한 서브쿼리
    from sqlalchemy import func, or_
    latest_price_subq = db.query(
        models.StockPrice.ticker,
        func.max(models.StockPrice.date).label('max_date')
    ).group_by(models.StockPrice.ticker).subquery()

    # 기본 쿼리 - investor는 별도 조회로 처리
    query = db.query(
        models.Stock,
        models.StockPrice,
        models.TechnicalIndicator
    ).outerjoin(
        models.StockPrice,
        models.Stock.ticker == models.StockPrice.ticker
    ).join(
        latest_price_subq,
        (models.StockPrice.ticker == latest_price_subq.c.ticker) &
        (models.StockPrice.date == latest_price_subq.c.max_date)
    ).outerjoin(
        models.TechnicalIndicator,
        (models.Stock.ticker == models.TechnicalIndicator.ticker) &
        (models.StockPrice.date == models.TechnicalIndicator.date)
    )

    # 필터 적용
    if country:
        query = query.filter(models.Stock.country == country)
    if sector:
        query = query.filter(models.Stock.sector == sector)

    # 정렬
    sort_column = getattr(models.Stock, sort_by, models.Stock.ticker)
    if sort_order == "desc":
        query = query.order_by(desc(sort_column))
    else:
        query = query.order_by(asc(sort_column))

    # 전체 개수
    total = query.count()

    # 페이징
    results = query.offset(skip).limit(limit).all()

    # 모든 결과의 ticker 목록 (base ticker로 변환)
    stock_tickers = [row[0].ticker for row in results]
    base_tickers = [ticker.split('.')[0] for ticker in stock_tickers]

    # investor 데이터를 별도로 조회 (최신 날짜만)
    # 간단한 방법: 각 base ticker에 대해 최신 데이터 조회
    investor_dict = {}
    if base_tickers:
        # 모든 investor 데이터 가져오기
        all_investor_data = db.query(models.InvestorTrade).filter(
            func.split_part(models.InvestorTrade.ticker, '.', 1).in_(base_tickers)
        ).all()

        # base ticker별로 최신 날짜 데이터만 선택
        temp_dict = {}
        for inv in all_investor_data:
            base = inv.ticker.split('.')[0]
            if base not in temp_dict or inv.date > temp_dict[base].date:
                temp_dict[base] = inv
        investor_dict = temp_dict

    # 결과 포맷팅
    stocks_data = []
    for row in results:
        stock, price, indicator = row
        base_ticker = stock.ticker.split('.')[0]
        investor = investor_dict.get(base_ticker)
        data = {
            "ticker": stock.ticker,
            "company_name": stock.company_name,
            "country": stock.country or "KR",
            "sector": stock.sector,
            "industry": stock.industry,
            "market_type": stock.market_type,
        }

        if price:
            data.update({
                "date": price.date.isoformat(),
                "close_price": float(price.close_price) if price.close_price else None,
                "high_price": float(price.high_price) if price.high_price else None,
                "low_price": float(price.low_price) if price.low_price else None,
                "volume": price.volume,
            })

        if indicator:
            # 추세 판단
            trend = "N/A"
            if indicator.ma_20 and indicator.ma_50:
                if indicator.ma_20 > indicator.ma_50:
                    trend = "정배열"
                else:
                    trend = "역배열"

            data.update({
                "rsi": float(indicator.rsi) if indicator.rsi else None,
                "macd": float(indicator.macd) if indicator.macd else None,
                "macd_signal": float(indicator.macd_signal) if indicator.macd_signal else None,
                "stoch_k": float(indicator.stoch_k) if indicator.stoch_k else None,
                "stoch_d": float(indicator.stoch_d) if indicator.stoch_d else None,
                "ma_20": float(indicator.ma_20) if indicator.ma_20 else None,
                "ma_50": float(indicator.ma_50) if indicator.ma_50 else None,
                "ma_200": float(indicator.ma_200) if indicator.ma_200 else None,
                "bollinger_upper": float(indicator.bollinger_upper) if indicator.bollinger_upper else None,
                "bollinger_middle": float(indicator.bollinger_middle) if indicator.bollinger_middle else None,
                "bollinger_lower": float(indicator.bollinger_lower) if indicator.bollinger_lower else None,
                "ichimoku_tenkan": float(indicator.ichimoku_tenkan) if indicator.ichimoku_tenkan else None,
                "ichimoku_kijun": float(indicator.ichimoku_kijun) if indicator.ichimoku_kijun else None,
                "ichimoku_senkou_a": float(indicator.ichimoku_senkou_a) if indicator.ichimoku_senkou_a else None,
                "ichimoku_senkou_b": float(indicator.ichimoku_senkou_b) if indicator.ichimoku_senkou_b else None,
                "ichimoku_chikou": float(indicator.ichimoku_chikou) if indicator.ichimoku_chikou else None,
                "trend": trend,
                "ma_filter": indicator.ma_20 > indicator.ma_50 if (indicator.ma_20 and indicator.ma_50) else None,
            })

        if investor:
            data.update({
                "foreign_buy": investor.foreign_buy,
                "foreign_sell": investor.foreign_sell,
                "institution_buy": investor.institution_buy,
                "institution_sell": investor.institution_sell,
                "individual_buy": investor.individual_buy,
                "individual_sell": investor.individual_sell,
            })

        stocks_data.append(data)

    return {
        "total": total,
        "page": skip // limit + 1,
        "page_size": limit,
        "data": stocks_data
    }

@router.get("/", response_model=List[StockResponse])
def get_stocks(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=50000),
    db: Session = Depends(get_db)
):
    """등록된 종목 목록을 조회합니다."""
    stocks = db.query(models.Stock).offset(skip).limit(limit).all()
    return stocks

@router.post("/", response_model=StockResponse)
def create_stock(
    stock: StockCreate,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """새로운 종목을 추가합니다."""
    # 이미 존재하는지 확인
    existing_stock = db.query(models.Stock).filter(models.Stock.ticker == stock.ticker.upper()).first()
    if existing_stock:
        raise HTTPException(status_code=400, detail=f"Stock {stock.ticker} already exists")
    
    # 새 종목 생성
    db_stock = models.Stock(
        ticker=stock.ticker.upper(),
        company_name=stock.company_name,
        sector=stock.sector,
        industry=stock.industry
    )
    db.add(db_stock)
    db.commit()
    db.refresh(db_stock)
    return db_stock

@router.delete("/{ticker}")
def delete_stock(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """종목을 삭제합니다."""
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    
    db.delete(stock)
    db.commit()
    return {"message": f"Stock {ticker} deleted successfully"}

@router.get("/{ticker}", response_model=StockResponse)
def get_stock(ticker: str, db: Session = Depends(get_db)):
    """특정 종목 정보를 조회합니다."""
    stock = db.query(models.Stock).filter(models.Stock.ticker == ticker.upper()).first()
    if not stock:
        raise HTTPException(status_code=404, detail=f"Stock {ticker} not found")
    return stock

@router.post("/update/{ticker}")
def update_stock_data(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fetcher = StockDataFetcher(db)
    success = fetcher.update_stock_data(ticker.upper())
    
    if success:
        return {"message": f"Successfully updated data for {ticker}"}
    else:
        raise HTTPException(status_code=500, detail=f"Failed to update data for {ticker}")

@router.post("/update-batch")
def update_multiple_stocks(
    tickers: List[str],
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    fetcher = StockDataFetcher(db)
    tickers = [t.upper() for t in tickers]
    results = fetcher.update_multiple_stocks(tickers)
    
    return {"results": results}

@router.get("/{ticker}/prices")
def get_stock_prices(
    ticker: str,
    days: int = Query(default=None, ge=1, le=3650),
    start_date: str = Query(default=None),
    end_date: str = Query(default=None),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # 날짜 범위 결정
    if start_date and end_date:
        # 직접 지정한 날짜 사용
        start = datetime.strptime(start_date, "%Y-%m-%d").date()
        end = datetime.strptime(end_date, "%Y-%m-%d").date()
    elif days:
        # days 파라미터 사용
        end = datetime.now().date()
        start = end - timedelta(days=days)
    else:
        # 기본값: 30일
        end = datetime.now().date()
        start = end - timedelta(days=30)

    prices = db.query(models.StockPrice).filter(
        models.StockPrice.ticker == ticker.upper(),
        models.StockPrice.date >= start,
        models.StockPrice.date <= end
    ).order_by(models.StockPrice.date).all()
    
    if not prices:
        raise HTTPException(status_code=404, detail=f"No price data found for {ticker}")
    
    return [
        {
            "date": price.date,
            "open": float(price.open_price),
            "high": float(price.high_price),
            "low": float(price.low_price),
            "close": float(price.close_price),
            "volume": price.volume
        }
        for price in prices
    ]

@router.get("/{ticker}/indicators")
def get_technical_indicators(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    indicators = db.query(models.TechnicalIndicator).filter(
        models.TechnicalIndicator.ticker == ticker.upper(),
        models.TechnicalIndicator.date >= start_date,
        models.TechnicalIndicator.date <= end_date
    ).order_by(models.TechnicalIndicator.date).all()

    if not indicators:
        raise HTTPException(status_code=404, detail=f"No indicator data found for {ticker}")

    return [
        {
            "date": ind.date,
            "stoch_k": float(ind.stoch_k) if ind.stoch_k else None,
            "stoch_d": float(ind.stoch_d) if ind.stoch_d else None,
            "macd": float(ind.macd) if ind.macd else None,
            "macd_signal": float(ind.macd_signal) if ind.macd_signal else None,
            "macd_histogram": float(ind.macd_histogram) if ind.macd_histogram else None,
            "rsi": float(ind.rsi) if ind.rsi else None,
            "ma_20": float(ind.ma_20) if ind.ma_20 else None,
            "ma_50": float(ind.ma_50) if ind.ma_50 else None,
            "ma_200": float(ind.ma_200) if ind.ma_200 else None,
            "bollinger_upper": float(ind.bollinger_upper) if ind.bollinger_upper else None,
            "bollinger_middle": float(ind.bollinger_middle) if ind.bollinger_middle else None,
            "bollinger_lower": float(ind.bollinger_lower) if ind.bollinger_lower else None
        }
        for ind in indicators
    ]

@router.get("/{ticker}/investor-trades")
def get_investor_trades(
    ticker: str,
    days: int = Query(default=30, ge=1, le=365),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    end_date = datetime.now().date()
    start_date = end_date - timedelta(days=days)

    trades = db.query(models.InvestorTrade).filter(
        models.InvestorTrade.ticker == ticker.upper(),
        models.InvestorTrade.date >= start_date,
        models.InvestorTrade.date <= end_date
    ).order_by(models.InvestorTrade.date).all()

    return [
        {
            "date": trade.date,
            "foreign_buy": trade.foreign_buy,
            "foreign_sell": trade.foreign_sell,
            "institution_buy": trade.institution_buy,
            "institution_sell": trade.institution_sell,
            "individual_buy": trade.individual_buy,
            "individual_sell": trade.individual_sell
        }
        for trade in trades
    ]

@router.get("/{ticker}/analysis")
def get_stock_analysis(
    ticker: str,
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    latest_price = db.query(models.StockPrice).filter(
        models.StockPrice.ticker == ticker.upper()
    ).order_by(models.StockPrice.date.desc()).first()
    
    latest_indicators = db.query(models.TechnicalIndicator).filter(
        models.TechnicalIndicator.ticker == ticker.upper()
    ).order_by(models.TechnicalIndicator.date.desc()).first()
    
    if not latest_price or not latest_indicators:
        raise HTTPException(status_code=404, detail=f"No data found for {ticker}")
    
    analysis = {
        "ticker": ticker.upper(),
        "latest_price": float(latest_price.close_price),
        "date": latest_price.date,
        "indicators": {
            "stoch_k": float(latest_indicators.stoch_k) if latest_indicators.stoch_k else None,
            "stoch_d": float(latest_indicators.stoch_d) if latest_indicators.stoch_d else None,
            "macd": float(latest_indicators.macd) if latest_indicators.macd else None,
            "macd_signal": float(latest_indicators.macd_signal) if latest_indicators.macd_signal else None,
            "rsi": float(latest_indicators.rsi) if latest_indicators.rsi else None
        },
        "signals": []
    }
    
    if latest_indicators.rsi:
        if latest_indicators.rsi < 30:
            analysis["signals"].append({"type": "oversold", "indicator": "RSI", "value": float(latest_indicators.rsi)})
        elif latest_indicators.rsi > 70:
            analysis["signals"].append({"type": "overbought", "indicator": "RSI", "value": float(latest_indicators.rsi)})
    
    if latest_indicators.stoch_k and latest_indicators.stoch_d:
        if latest_indicators.stoch_k < 20 and latest_indicators.stoch_d < 20:
            analysis["signals"].append({"type": "oversold", "indicator": "Stochastic", "k": float(latest_indicators.stoch_k), "d": float(latest_indicators.stoch_d)})
        elif latest_indicators.stoch_k > 80 and latest_indicators.stoch_d > 80:
            analysis["signals"].append({"type": "overbought", "indicator": "Stochastic", "k": float(latest_indicators.stoch_k), "d": float(latest_indicators.stoch_d)})
    
    return analysis

@router.get("/screen/oversold")
def screen_oversold_stocks(
    rsi_threshold: float = Query(default=30, ge=10, le=50),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    screener = MarketScreener(db)
    results = screener.find_oversold_stocks(rsi_threshold)
    return {"oversold_stocks": results}

@router.get("/screen/overbought")
def screen_overbought_stocks(
    rsi_threshold: float = Query(default=70, ge=50, le=90),
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    screener = MarketScreener(db)
    results = screener.find_overbought_stocks(rsi_threshold)
    return {"overbought_stocks": results}

@router.get("/screen/macd-crossover")
def screen_macd_crossovers(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    screener = MarketScreener(db)
    results = screener.find_macd_crossovers()
    return {"crossovers": results}

@router.get("/watchlist")
def get_user_watchlist(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    portfolios = db.query(models.Portfolio.ticker).filter(
        models.Portfolio.user_id == current_user.id,
        models.Portfolio.status == "holding"
    ).distinct().all()
    
    watchlist = []
    for (ticker,) in portfolios:
        latest_price = db.query(models.StockPrice).filter(
            models.StockPrice.ticker == ticker
        ).order_by(models.StockPrice.date.desc()).first()
        
        latest_indicators = db.query(models.TechnicalIndicator).filter(
            models.TechnicalIndicator.ticker == ticker
        ).order_by(models.TechnicalIndicator.date.desc()).first()
        
        if latest_price:
            item = {
                "ticker": ticker,
                "price": float(latest_price.close_price),
                "date": latest_price.date
            }
            
            if latest_indicators:
                item["rsi"] = float(latest_indicators.rsi) if latest_indicators.rsi else None
                item["macd"] = float(latest_indicators.macd) if latest_indicators.macd else None
            
            watchlist.append(item)
    
    return {"watchlist": watchlist}