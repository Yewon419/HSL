import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, List, Dict
from sqlalchemy.orm import Session
import logging

import models
from .indicators import TechnicalIndicators

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class StockDataFetcher:
    def __init__(self, db: Session):
        self.db = db
        self.indicators = TechnicalIndicators()
    
    def fetch_stock_data(self, ticker: str, start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None) -> pd.DataFrame:
        try:
            if not start_date:
                start_date = datetime.now() - timedelta(days=365)
            if not end_date:
                end_date = datetime.now()
            
            stock = yf.Ticker(ticker)
            df = stock.history(start=start_date, end=end_date)
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return pd.DataFrame()
            
            df = df.reset_index()
            df = self.indicators.calculate_all_indicators(df)
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching data for {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def save_stock_info(self, ticker: str) -> bool:
        try:
            stock = yf.Ticker(ticker)
            info = stock.info
            
            db_stock = self.db.query(models.Stock).filter(models.Stock.ticker == ticker).first()
            
            if not db_stock:
                db_stock = models.Stock(
                    ticker=ticker,
                    company_name=info.get('longName', ''),
                    sector=info.get('sector', ''),
                    industry=info.get('industry', ''),
                    market_cap=info.get('marketCap', 0)
                )
                self.db.add(db_stock)
            else:
                db_stock.company_name = info.get('longName', db_stock.company_name)
                db_stock.sector = info.get('sector', db_stock.sector)
                db_stock.industry = info.get('industry', db_stock.industry)
                db_stock.market_cap = info.get('marketCap', db_stock.market_cap)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving stock info for {ticker}: {str(e)}")
            self.db.rollback()
            return False
    
    def save_stock_prices(self, ticker: str, df: pd.DataFrame) -> bool:
        try:
            for _, row in df.iterrows():
                date = row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date']
                
                existing = self.db.query(models.StockPrice).filter(
                    models.StockPrice.ticker == ticker,
                    models.StockPrice.date == date
                ).first()
                
                if not existing:
                    price_data = models.StockPrice(
                        ticker=ticker,
                        date=date,
                        open_price=row['Open'],
                        high_price=row['High'],
                        low_price=row['Low'],
                        close_price=row['Close'],
                        volume=int(row['Volume'])
                    )
                    self.db.add(price_data)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving prices for {ticker}: {str(e)}")
            self.db.rollback()
            return False
    
    def save_technical_indicators(self, ticker: str, df: pd.DataFrame) -> bool:
        try:
            for _, row in df.iterrows():
                date = row['Date'].date() if isinstance(row['Date'], pd.Timestamp) else row['Date']
                
                existing = self.db.query(models.TechnicalIndicator).filter(
                    models.TechnicalIndicator.ticker == ticker,
                    models.TechnicalIndicator.date == date
                ).first()
                
                if existing:
                    existing.stoch_k = row.get('stoch_k')
                    existing.stoch_d = row.get('stoch_d')
                    existing.macd = row.get('macd')
                    existing.macd_signal = row.get('macd_signal')
                    existing.macd_histogram = row.get('macd_histogram')
                    existing.rsi = row.get('rsi')
                    existing.ma_20 = row.get('ma_20')
                    existing.ma_50 = row.get('ma_50')
                    existing.ma_200 = row.get('ma_200')
                    existing.bollinger_upper = row.get('bollinger_upper')
                    existing.bollinger_middle = row.get('bollinger_middle')
                    existing.bollinger_lower = row.get('bollinger_lower')
                else:
                    indicator_data = models.TechnicalIndicator(
                        ticker=ticker,
                        date=date,
                        stoch_k=row.get('stoch_k'),
                        stoch_d=row.get('stoch_d'),
                        macd=row.get('macd'),
                        macd_signal=row.get('macd_signal'),
                        macd_histogram=row.get('macd_histogram'),
                        rsi=row.get('rsi'),
                        ma_20=row.get('ma_20'),
                        ma_50=row.get('ma_50'),
                        ma_200=row.get('ma_200'),
                        bollinger_upper=row.get('bollinger_upper'),
                        bollinger_middle=row.get('bollinger_middle'),
                        bollinger_lower=row.get('bollinger_lower')
                    )
                    self.db.add(indicator_data)
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving indicators for {ticker}: {str(e)}")
            self.db.rollback()
            return False
    
    def update_stock_data(self, ticker: str) -> bool:
        try:
            last_price = self.db.query(models.StockPrice).filter(
                models.StockPrice.ticker == ticker
            ).order_by(models.StockPrice.date.desc()).first()
            
            if last_price:
                start_date = last_price.date + timedelta(days=1)
            else:
                start_date = datetime.now() - timedelta(days=365)
            
            df = self.fetch_stock_data(ticker, start_date=start_date)
            
            if df.empty:
                logger.info(f"No new data for {ticker}")
                return True
            
            self.save_stock_info(ticker)
            self.save_stock_prices(ticker, df)
            self.save_technical_indicators(ticker, df)
            
            logger.info(f"Successfully updated data for {ticker}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating data for {ticker}: {str(e)}")
            return False
    
    def update_multiple_stocks(self, tickers: List[str]) -> Dict[str, bool]:
        results = {}
        for ticker in tickers:
            results[ticker] = self.update_stock_data(ticker)
        return results

class MarketScreener:
    def __init__(self, db: Session):
        self.db = db
    
    def find_oversold_stocks(self, rsi_threshold: float = 30) -> List[Dict]:
        query = self.db.query(
            models.TechnicalIndicator.ticker,
            models.TechnicalIndicator.rsi,
            models.StockPrice.close_price
        ).join(
            models.StockPrice,
            (models.TechnicalIndicator.ticker == models.StockPrice.ticker) &
            (models.TechnicalIndicator.date == models.StockPrice.date)
        ).filter(
            models.TechnicalIndicator.rsi < rsi_threshold
        ).order_by(
            models.TechnicalIndicator.date.desc()
        ).limit(20)
        
        results = []
        for row in query.all():
            results.append({
                'ticker': row.ticker,
                'rsi': float(row.rsi),
                'price': float(row.close_price)
            })
        
        return results
    
    def find_overbought_stocks(self, rsi_threshold: float = 70) -> List[Dict]:
        query = self.db.query(
            models.TechnicalIndicator.ticker,
            models.TechnicalIndicator.rsi,
            models.StockPrice.close_price
        ).join(
            models.StockPrice,
            (models.TechnicalIndicator.ticker == models.StockPrice.ticker) &
            (models.TechnicalIndicator.date == models.StockPrice.date)
        ).filter(
            models.TechnicalIndicator.rsi > rsi_threshold
        ).order_by(
            models.TechnicalIndicator.date.desc()
        ).limit(20)
        
        results = []
        for row in query.all():
            results.append({
                'ticker': row.ticker,
                'rsi': float(row.rsi),
                'price': float(row.close_price)
            })
        
        return results
    
    def find_macd_crossovers(self) -> List[Dict]:
        subquery = self.db.query(
            models.TechnicalIndicator.ticker,
            models.TechnicalIndicator.date,
            models.TechnicalIndicator.macd,
            models.TechnicalIndicator.macd_signal
        ).subquery()
        
        query = self.db.query(
            models.TechnicalIndicator.ticker,
            models.TechnicalIndicator.macd,
            models.TechnicalIndicator.macd_signal,
            models.StockPrice.close_price
        ).join(
            models.StockPrice,
            (models.TechnicalIndicator.ticker == models.StockPrice.ticker) &
            (models.TechnicalIndicator.date == models.StockPrice.date)
        ).order_by(
            models.TechnicalIndicator.date.desc()
        ).limit(50)
        
        results = []
        current_data = {}
        
        for row in query.all():
            if row.ticker not in current_data:
                current_data[row.ticker] = []
            current_data[row.ticker].append({
                'macd': float(row.macd) if row.macd else 0,
                'signal': float(row.macd_signal) if row.macd_signal else 0,
                'price': float(row.close_price)
            })
        
        for ticker, data in current_data.items():
            if len(data) >= 2:
                current = data[0]
                previous = data[1]
                
                if (current['macd'] > current['signal'] and 
                    previous['macd'] <= previous['signal']):
                    results.append({
                        'ticker': ticker,
                        'type': 'bullish',
                        'macd': current['macd'],
                        'signal': current['signal'],
                        'price': current['price']
                    })
                elif (current['macd'] < current['signal'] and 
                      previous['macd'] >= previous['signal']):
                    results.append({
                        'ticker': ticker,
                        'type': 'bearish',
                        'macd': current['macd'],
                        'signal': current['signal'],
                        'price': current['price']
                    })
        
        return results