#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime
import logging
from pykrx import stock
from database import SessionLocal
from models import StockFundamental, Stock
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_fundamentals():
    """Update fundamental data for all stocks"""
    db = SessionLocal()
    
    try:
        # Get all stocks from database
        stocks = db.query(Stock).all()
        logger.info(f"Found {len(stocks)} stocks to update")
        
        today = datetime.now().strftime("%Y%m%d")
        updated_count = 0
        
        for stock_obj in stocks:
            ticker = stock_obj.ticker
            try:
                # Get fundamental data
                fundamental = stock.get_market_fundamental(today, today, ticker)
                
                if not fundamental.empty:
                    info = fundamental.iloc[-1]
                    
                    # Parse the data
                    per = float(info.get('PER', 0)) if info.get('PER') is not None and str(info.get('PER')) != 'nan' and info.get('PER') != 0 else None
                    pbr = float(info.get('PBR', 0)) if info.get('PBR') is not None and str(info.get('PBR')) != 'nan' and info.get('PBR') != 0 else None
                    eps = int(info.get('EPS', 0)) if info.get('EPS') is not None and str(info.get('EPS')) != 'nan' and info.get('EPS') != 0 else None
                    bps = int(info.get('BPS', 0)) if info.get('BPS') is not None and str(info.get('BPS')) != 'nan' and info.get('BPS') != 0 else None
                    div = float(info.get('DIV', 0)) if info.get('DIV') is not None and str(info.get('DIV')) != 'nan' and info.get('DIV') != 0 else None
                    
                    # Check if we have any data
                    if any([per, pbr, eps, bps, div]):
                        # Check if fundamentals already exist for today
                        existing = db.query(StockFundamental).filter(
                            StockFundamental.ticker == ticker,
                            StockFundamental.date == datetime.now().date()
                        ).first()
                        
                        if existing:
                            # Update existing fundamentals
                            existing.per = per
                            existing.pbr = pbr
                            existing.eps = eps
                            existing.bps = bps
                            existing.dividend_yield = div
                            logger.info(f"Updated fundamentals for {ticker}: PER={per}, PBR={pbr}, EPS={eps}")
                        else:
                            # Create new fundamentals
                            new_fundamentals = StockFundamental(
                                ticker=ticker,
                                date=datetime.now().date(),
                                per=per,
                                pbr=pbr,
                                eps=eps,
                                bps=bps,
                                dividend_yield=div
                            )
                            db.add(new_fundamentals)
                            logger.info(f"Added fundamentals for {ticker}: PER={per}, PBR={pbr}, EPS={eps}")
                        
                        updated_count += 1
                        
                        # Commit every 10 updates
                        if updated_count % 10 == 0:
                            db.commit()
                            logger.info(f"Committed {updated_count} updates")
                
                # Small delay to avoid API rate limiting
                time.sleep(0.1)
                
            except Exception as e:
                logger.warning(f"Error updating fundamentals for {ticker}: {e}")
                continue
        
        # Final commit
        db.commit()
        logger.info(f"Successfully updated fundamentals for {updated_count} stocks")
        
    except Exception as e:
        logger.error(f"Error in update_fundamentals: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    update_fundamentals()