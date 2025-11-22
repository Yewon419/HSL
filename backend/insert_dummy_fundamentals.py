#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime
import logging
from database import SessionLocal
from models import StockFundamental

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def insert_dummy_fundamentals():
    """Insert dummy fundamental data for testing"""
    db = SessionLocal()
    
    try:
        today = datetime.now().date()
        
        # 더미 펀더멘털 데이터
        dummy_data = {
            '005930': {'per': 15.2, 'pbr': 1.3, 'eps': 4500, 'bps': 50000, 'dividend_yield': 2.1},
            '000660': {'per': 18.5, 'pbr': 1.8, 'eps': 3200, 'bps': 42000, 'dividend_yield': 1.8},
            '035420': {'per': 22.1, 'pbr': 2.2, 'eps': 2800, 'bps': 38000, 'dividend_yield': 0.5},
        }
        
        for ticker, data in dummy_data.items():
            # 기존 데이터 삭제
            db.query(StockFundamental).filter(
                StockFundamental.ticker == ticker,
                StockFundamental.date == today
            ).delete()
            
            # 새 데이터 삽입
            new_fundamental = StockFundamental(
                ticker=ticker,
                date=today,
                per=data['per'],
                pbr=data['pbr'],
                eps=data['eps'],
                bps=data['bps'],
                dividend_yield=data['dividend_yield']
            )
            db.add(new_fundamental)
            logger.info(f"Inserted dummy data for {ticker}: {data}")
        
        db.commit()
        logger.info("Successfully inserted dummy fundamental data")
        
    except Exception as e:
        logger.error(f"Error inserting dummy data: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    insert_dummy_fundamentals()