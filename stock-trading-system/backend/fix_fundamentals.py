#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from datetime import datetime, timedelta
import logging
import time
from database import SessionLocal
from models import StockFundamental, Stock

# yfinance를 사용해보겠습니다 (한국 주식도 지원)
import yfinance as yf

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_fundamentals():
    """Fix fundamental data using yfinance"""
    db = SessionLocal()
    
    try:
        # 주요 종목들에 대해 테스트
        major_stocks = {
            '005930': '005930.KS',  # 삼성전자
            '000660': '000660.KS',  # SK하이닉스  
            '035420': '035420.KS',  # 네이버
        }
        
        for ticker, yf_ticker in major_stocks.items():
            try:
                logger.info(f"Processing {ticker} ({yf_ticker})")
                
                # yfinance로 데이터 가져오기
                stock = yf.Ticker(yf_ticker)
                info = stock.info
                
                logger.info(f"Retrieved info keys: {list(info.keys())[:10]}...")  # 처음 10개 키만 로그
                
                # 기본 재무 정보 추출
                per = info.get('trailingPE')
                pbr = info.get('priceToBook')
                eps = info.get('trailingEps')
                bps = info.get('bookValue')
                dividend_yield = info.get('dividendYield')
                
                logger.info(f"Extracted data - PER: {per}, PBR: {pbr}, EPS: {eps}, BPS: {bps}, Div: {dividend_yield}")
                
                if any([per, pbr, eps, bps, dividend_yield]):
                    today = datetime.now().date()
                    
                    # 기존 데이터 업데이트 또는 새로 생성
                    existing = db.query(StockFundamental).filter(
                        StockFundamental.ticker == ticker,
                        StockFundamental.date == today
                    ).first()
                    
                    if existing:
                        existing.per = per
                        existing.pbr = pbr  
                        existing.eps = eps
                        existing.bps = bps
                        existing.dividend_yield = dividend_yield if dividend_yield else None
                    else:
                        new_fundamental = StockFundamental(
                            ticker=ticker,
                            date=today,
                            per=per,
                            pbr=pbr,
                            eps=eps, 
                            bps=bps,
                            dividend_yield=dividend_yield if dividend_yield else None
                        )
                        db.add(new_fundamental)
                    
                    db.commit()
                    logger.info(f"Updated fundamentals for {ticker}")
                else:
                    logger.warning(f"No fundamental data found for {ticker}")
                
                # API 호출 제한 방지
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"Error processing {ticker}: {e}")
                db.rollback()
                continue
                
    except Exception as e:
        logger.error(f"General error: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    fix_fundamentals()