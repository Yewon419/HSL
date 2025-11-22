import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional
import time
import logging
from pykrx import stock
from pykrx import bond
import yfinance as yf
from sqlalchemy.orm import Session
from sqlalchemy import text
import asyncio
from concurrent.futures import ThreadPoolExecutor
from tqdm import tqdm

from database import SessionLocal
from models import Stock, StockPrice, Sector, Industry, StockFundamental

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class KoreaStockFetcher:
    def __init__(self):
        self.db = SessionLocal()
        self.executor = ThreadPoolExecutor(max_workers=10)
        
    def __del__(self):
        if hasattr(self, 'db'):
            self.db.close()
        if hasattr(self, 'executor'):
            self.executor.shutdown()
    
    def get_all_tickers(self) -> Dict[str, List[Dict]]:
        """Get all Korean stock tickers from KOSPI and KOSDAQ"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            
            # KOSPI tickers
            kospi_tickers = stock.get_market_ticker_list(today, market="KOSPI")
            kospi_list = []
            
            for ticker in kospi_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    kospi_list.append({
                        'ticker': ticker,
                        'name': name,
                        'market': 'KOSPI'
                    })
                except Exception as e:
                    logger.warning(f"Error getting KOSPI ticker {ticker} info: {e}")
                    continue
            
            # KOSDAQ tickers
            kosdaq_tickers = stock.get_market_ticker_list(today, market="KOSDAQ")
            kosdaq_list = []
            
            for ticker in kosdaq_tickers:
                try:
                    name = stock.get_market_ticker_name(ticker)
                    kosdaq_list.append({
                        'ticker': ticker,
                        'name': name,
                        'market': 'KOSDAQ'
                    })
                except Exception as e:
                    logger.warning(f"Error getting KOSDAQ ticker {ticker} info: {e}")
                    continue
            
            logger.info(f"Found {len(kospi_list)} KOSPI stocks and {len(kosdaq_list)} KOSDAQ stocks")
            
            return {
                'KOSPI': kospi_list,
                'KOSDAQ': kosdaq_list
            }
            
        except Exception as e:
            logger.error(f"Error fetching tickers: {e}")
            return {'KOSPI': [], 'KOSDAQ': []}
    
    def get_or_create_sector(self, sector_name: str) -> Optional[int]:
        """Get or create sector and return its ID"""
        if not sector_name or sector_name.strip() == '':
            return None
            
        try:
            # Check if sector exists
            sector = self.db.query(Sector).filter(Sector.name == sector_name).first()
            
            if not sector:
                # Create new sector
                sector = Sector(name=sector_name)
                self.db.add(sector)
                self.db.flush()  # Get the ID without committing
                
            return sector.id
            
        except Exception as e:
            logger.warning(f"Error handling sector {sector_name}: {e}")
            return None
    
    def get_or_create_industry(self, industry_name: str, sector_id: Optional[int] = None) -> Optional[int]:
        """Get or create industry and return its ID"""
        if not industry_name or industry_name.strip() == '':
            return None
            
        try:
            # Check if industry exists
            industry = self.db.query(Industry).filter(
                Industry.name == industry_name,
                Industry.sector_id == sector_id
            ).first()
            
            if not industry:
                # Create new industry
                industry = Industry(name=industry_name, sector_id=sector_id)
                self.db.add(industry)
                self.db.flush()  # Get the ID without committing
                
            return industry.id
            
        except Exception as e:
            logger.warning(f"Error handling industry {industry_name}: {e}")
            return None
    
    def get_stock_info(self, ticker: str, market: str) -> Optional[Dict]:
        """Get detailed stock information including sector/industry"""
        try:
            today = datetime.now().strftime("%Y%m%d")
            
            # Get company name
            company_name = stock.get_market_ticker_name(ticker)
            
            # Get fundamental info
            fundamental_data = {}
            try:
                # Get fundamental data for specific ticker
                fundamental = stock.get_market_fundamental(today, today, ticker)
                if not fundamental.empty:
                    info = fundamental.iloc[-1]  # Get the latest row
                    fundamental_data = {
                        'per': float(info.get('PER', 0)) if info.get('PER') is not None and str(info.get('PER')) != 'nan' and info.get('PER') != 0 else None,
                        'pbr': float(info.get('PBR', 0)) if info.get('PBR') is not None and str(info.get('PBR')) != 'nan' and info.get('PBR') != 0 else None,
                        'eps': int(info.get('EPS', 0)) if info.get('EPS') is not None and str(info.get('EPS')) != 'nan' and info.get('EPS') != 0 else None,
                        'bps': int(info.get('BPS', 0)) if info.get('BPS') is not None and str(info.get('BPS')) != 'nan' and info.get('BPS') != 0 else None,
                        'dividend_yield': float(info.get('DIV', 0)) if info.get('DIV') is not None and str(info.get('DIV')) != 'nan' and info.get('DIV') != 0 else None
                    }
                    logger.info(f"Got fundamental data for {ticker}: {fundamental_data}")
            except Exception as e:
                logger.warning(f"Error getting fundamental data for {ticker}: {e}")
            
            # Get market cap
            market_cap = None
            try:
                cap = stock.get_market_cap_by_ticker(today, market=market)
                if ticker in cap.index:
                    market_cap = int(cap.loc[ticker, '시가총액']) if cap.loc[ticker, '시가총액'] else None
            except Exception as e:
                logger.warning(f"Error getting market cap for {ticker}: {e}")
            
            # Get sector/industry info from company name or ticker patterns
            sector_name, industry_name = self._infer_sector_industry(ticker, company_name)
            
            return {
                'ticker': ticker,
                'company_name': company_name,
                'market_type': market,
                'market_cap': market_cap,
                'sector_name': sector_name,
                'industry_name': industry_name,
                'fundamentals': fundamental_data
            }
            
        except Exception as e:
            logger.warning(f"Error getting stock info for {ticker}: {e}")
            return None
    
    def _infer_sector_industry(self, ticker: str, company_name: str) -> tuple:
        """Infer sector and industry from company name and ticker"""
        # Simple keyword-based classification
        company_lower = company_name.lower() if company_name else ""
        
        # 제조업
        if any(word in company_lower for word in ['제철', '철강', '강관', '금속']):
            return '소재', '철강'
        elif any(word in company_lower for word in ['화학', '케미칼', '폴리', '화섬']):
            return '소재', '화학'
        elif any(word in company_lower for word in ['반도체', '전자', '디스플레이', '메모리']) or ticker in ['005930']:
            return 'IT', '반도체'
        elif any(word in company_lower for word in ['자동차', '타이어', '부품']) or ticker in ['000270']:
            return '경기소비재', '자동차'
        elif any(word in company_lower for word in ['건설', '플랜트', '중공업']):
            return '산업재', '건설'
        elif any(word in company_lower for word in ['은행', '저축', '카드', '캐피탈']):
            return '금융', '은행'
        elif any(word in company_lower for word in ['보험', '생명', '손해']):
            return '금융', '보험'
        elif any(word in company_lower for word in ['증권', '자산운용', '투자']):
            return '금융', '증권'
        elif any(word in company_lower for word in ['제약', '바이오', '의료', '헬스케어', '셀트리온']) or ticker in ['068270']:
            return '헬스케어', '제약/바이오'
        elif any(word in company_lower for word in ['통신', '텔레콤', 'kt', 'lg유플러스']):
            return '통신서비스', '통신'
        elif any(word in company_lower for word in ['전력', '발전', '에너지']):
            return '유틸리티', '전력'
        elif any(word in company_lower for word in ['식품', '음료', '제과']):
            return '필수소비재', '식품/음료'
        elif any(word in company_lower for word in ['유통', '마트', '백화점']):
            return '경기소비재', '유통'
        elif any(word in company_lower for word in ['항공', '해운', '운송']):
            return '산업재', '운송'
        elif any(word in company_lower for word in ['게임', '엔터', '미디어', 'naver']) or ticker in ['035420']:
            return '통신서비스', 'IT서비스'
        
        # 기본값
        if ticker.startswith('00'):  # 대형주 패턴
            return 'IT', '기타'
        else:
            return '기타', '기타'
    
    def fetch_historical_prices(self, ticker: str, start_date: str, end_date: str) -> pd.DataFrame:
        """Fetch historical price data for a stock"""
        try:
            # Use pykrx for Korean stock data
            df = stock.get_market_ohlcv_by_date(start_date, end_date, ticker)
            
            if df.empty:
                logger.warning(f"No data found for {ticker}")
                return pd.DataFrame()
            
            # Rename columns to match our schema
            df = df.reset_index()
            # pykrx returns 7 columns after reset_index: date, open, high, low, close, volume, change_rate
            # We only need the first 6 columns
            df = df.iloc[:, :6]  # Take only first 6 columns
            df.columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            df['ticker'] = ticker
            
            return df
            
        except Exception as e:
            logger.error(f"Error fetching prices for {ticker}: {e}")
            return pd.DataFrame()
    
    def save_stock_to_db(self, stock_info: Dict) -> bool:
        """Save enhanced stock information to database"""
        try:
            ticker = stock_info['ticker']
            
            # Get or create sector and industry IDs
            sector_id = None
            industry_id = None
            
            if 'sector_name' in stock_info and stock_info['sector_name']:
                sector_id = self.get_or_create_sector(stock_info['sector_name'])
                
            if 'industry_name' in stock_info and stock_info['industry_name']:
                industry_id = self.get_or_create_industry(stock_info['industry_name'], sector_id)
            
            # Check if stock exists
            existing = self.db.query(Stock).filter(Stock.ticker == ticker).first()
            
            if existing:
                # Update existing stock
                existing.company_name = stock_info.get('company_name') or existing.company_name
                existing.market_type = stock_info.get('market_type') or existing.market_type
                existing.market_cap = stock_info.get('market_cap') or existing.market_cap
                existing.sector_id = sector_id
                existing.industry_id = industry_id
                # Keep legacy fields for backward compatibility
                existing.sector = stock_info.get('sector_name')
                existing.industry = stock_info.get('industry_name')
            else:
                # Create new stock
                new_stock = Stock(
                    ticker=ticker,
                    company_name=stock_info.get('company_name') or stock_info.get('name'),
                    market_type=stock_info.get('market_type'),
                    market_cap=stock_info.get('market_cap'),
                    sector_id=sector_id,
                    industry_id=industry_id,
                    # Legacy fields
                    sector=stock_info.get('sector_name'),
                    industry=stock_info.get('industry_name')
                )
                self.db.add(new_stock)
            
            # Save fundamentals if available
            if 'fundamentals' in stock_info and stock_info['fundamentals']:
                self.save_fundamentals_to_db(ticker, stock_info['fundamentals'])
            
            self.db.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error saving stock {stock_info.get('ticker')} to DB: {e}")
            self.db.rollback()
            return False
    
    def save_fundamentals_to_db(self, ticker: str, fundamentals: Dict) -> bool:
        """Save fundamental data to database"""
        try:
            today = datetime.now().date()
            
            # Check if fundamentals already exist for today
            existing = self.db.query(StockFundamental).filter(
                StockFundamental.ticker == ticker,
                StockFundamental.date == today
            ).first()
            
            if existing:
                # Update existing fundamentals
                for key, value in fundamentals.items():
                    if hasattr(existing, key) and value is not None:
                        setattr(existing, key, value)
            else:
                # Create new fundamentals
                new_fundamentals = StockFundamental(
                    ticker=ticker,
                    date=today,
                    per=fundamentals.get('per'),
                    pbr=fundamentals.get('pbr'),
                    eps=fundamentals.get('eps'),
                    bps=fundamentals.get('bps'),
                    dividend_yield=fundamentals.get('dividend_yield')
                )
                self.db.add(new_fundamentals)
            
            return True
            
        except Exception as e:
            logger.warning(f"Error saving fundamentals for {ticker}: {e}")
            return False
    
    def save_prices_to_db(self, prices_df: pd.DataFrame) -> int:
        """Save price data to database"""
        if prices_df.empty:
            return 0
            
        try:
            # Convert DataFrame to list of dicts
            records = prices_df.to_dict('records')
            saved_count = 0
            
            for record in records:
                try:
                    # Convert date to date object if it's a Timestamp
                    if hasattr(record['date'], 'date'):
                        date_obj = record['date'].date()
                    else:
                        date_obj = record['date']
                    
                    # Check if price already exists
                    existing = self.db.query(StockPrice).filter(
                        StockPrice.ticker == record['ticker'],
                        StockPrice.date == date_obj
                    ).first()
                    
                    if not existing:
                        new_price = StockPrice(
                            ticker=record['ticker'],
                            date=date_obj,
                            open_price=float(record['open']),
                            high_price=float(record['high']),
                            low_price=float(record['low']),
                            close_price=float(record['close']),
                            volume=int(record['volume'])
                        )
                        self.db.add(new_price)
                        saved_count += 1
                        
                except Exception as e:
                    logger.warning(f"Error saving price record: {e}")
                    continue
            
            self.db.commit()
            logger.info(f"Saved {saved_count} price records")
            return saved_count
            
        except Exception as e:
            logger.error(f"Error saving prices to DB: {e}")
            self.db.rollback()
            return 0
    
    def fetch_and_save_all_stocks(self, years: int = 5):
        """Main function to fetch and save all Korean stocks"""
        # Get all tickers
        all_tickers = self.get_all_tickers()
        
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365 * years)
        start_str = start_date.strftime("%Y%m%d")
        end_str = end_date.strftime("%Y%m%d")
        
        total_stocks = len(all_tickers['KOSPI']) + len(all_tickers['KOSDAQ'])
        logger.info(f"Starting to fetch data for {total_stocks} stocks from {start_str} to {end_str}")
        
        # Process KOSPI stocks
        logger.info("Processing KOSPI stocks...")
        for stock_data in tqdm(all_tickers['KOSPI'], desc="KOSPI"):
            try:
                # Get detailed stock info including sector/industry
                detailed_info = self.get_stock_info(stock_data['ticker'], 'KOSPI')
                if detailed_info:
                    self.save_stock_to_db(detailed_info)
                else:
                    # Fallback to basic info
                    basic_info = {
                        'ticker': stock_data['ticker'],
                        'company_name': stock_data['name'],
                        'market_type': 'KOSPI'
                    }
                    self.save_stock_to_db(basic_info)
                
                # Fetch and save price data
                prices = self.fetch_historical_prices(stock_data['ticker'], start_str, end_str)
                self.save_prices_to_db(prices)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing KOSPI stock {stock_data['ticker']}: {e}")
                continue
        
        # Process KOSDAQ stocks
        logger.info("Processing KOSDAQ stocks...")
        for stock_data in tqdm(all_tickers['KOSDAQ'], desc="KOSDAQ"):
            try:
                # Get detailed stock info including sector/industry
                detailed_info = self.get_stock_info(stock_data['ticker'], 'KOSDAQ')
                if detailed_info:
                    self.save_stock_to_db(detailed_info)
                else:
                    # Fallback to basic info
                    basic_info = {
                        'ticker': stock_data['ticker'],
                        'company_name': stock_data['name'],
                        'market_type': 'KOSDAQ'
                    }
                    self.save_stock_to_db(basic_info)
                
                # Fetch and save price data
                prices = self.fetch_historical_prices(stock_data['ticker'], start_str, end_str)
                self.save_prices_to_db(prices)
                
                # Rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.error(f"Error processing KOSDAQ stock {stock_data['ticker']}: {e}")
                continue
        
        logger.info("Completed fetching all stock data")
    
    def update_recent_prices(self, days: int = 30):
        """Update recent price data for all stocks"""
        try:
            # Get all stocks from DB
            stocks = self.db.query(Stock).all()
            
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            start_str = start_date.strftime("%Y%m%d")
            end_str = end_date.strftime("%Y%m%d")
            
            logger.info(f"Updating prices for {len(stocks)} stocks from {start_str} to {end_str}")
            
            for stock in tqdm(stocks, desc="Updating prices"):
                try:
                    prices = self.fetch_historical_prices(stock.ticker, start_str, end_str)
                    self.save_prices_to_db(prices)
                    time.sleep(0.1)
                except Exception as e:
                    logger.error(f"Error updating prices for {stock.ticker}: {e}")
                    continue
            
            logger.info("Completed updating recent prices")
            
        except Exception as e:
            logger.error(f"Error in update_recent_prices: {e}")

if __name__ == "__main__":
    fetcher = KoreaStockFetcher()
    
    # Fetch all stocks with 5 years of history
    fetcher.fetch_and_save_all_stocks(years=5)
    
    # Or update only recent prices
    # fetcher.update_recent_prices(days=30)