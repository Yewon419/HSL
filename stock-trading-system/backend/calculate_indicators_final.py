#!/usr/bin/env python3
"""
기술 지표 계산 스크립트 (최종 수정판)
- 200일 역사 데이터로 지표 계산
- 올바른 DB 컬럼명 매핑 (sma_20 → ma_20, etc)
"""

import sys
import os
from datetime import datetime, timedelta, date
import pandas as pd
import logging

# Add paths
sys.path.insert(0, '/app')
os.environ['DB_HOST'] = 'stock-db'

from common_functions import (
    get_db_engine,
    calculate_rsi,
    calculate_macd,
    calculate_sma,
    calculate_bollinger_bands,
    update_indicator_log,
    logger
)

def load_historical_stock_data(target_date):
    """200일 역사 데이터 로드"""
    engine = get_db_engine()
    
    start_date = target_date - timedelta(days=200)
    
    query = f"""
        SELECT ticker, date, close_price
        FROM stock_prices
        WHERE date >= '{start_date}' AND date <= '{target_date}'
        ORDER BY ticker, date
    """
    
    df = pd.read_sql(query, engine)
    logger.info(f"Loaded {len(df)} records from {start_date} to {target_date}")
    return df

def calculate_and_save_indicators():
    """지표 계산 및 저장"""
    target_date = date(2025, 10, 23)
    logger.info(f"===== 지표 계산 시작: {target_date} =====")
    
    try:
        engine = get_db_engine()
        
        # 역사 데이터 로드
        stock_data = load_historical_stock_data(target_date)
        
        if stock_data.empty:
            logger.error("No historical data found")
            update_indicator_log(target_date, 'failed', 0, 'No historical data', engine)
            raise Exception("No historical data available")
        
        tickers = stock_data['ticker'].unique()
        logger.info(f"Processing {len(tickers)} tickers")
        
        indicators_list = []
        skipped = 0
        
        for ticker in tickers:
            try:
                ticker_data = stock_data[stock_data['ticker'] == ticker].copy()
                
                if len(ticker_data) < 20:
                    skipped += 1
                    continue
                
                prices = ticker_data.sort_values('date')['close_price'].astype(float)
                
                # 지표 계산
                rsi = calculate_rsi(prices, period=14)
                macd, macd_signal = calculate_macd(prices, fast=12, slow=26, signal=9)
                sma_20 = calculate_sma(prices, period=20)
                sma_50 = calculate_sma(prices, period=50)
                sma_200 = calculate_sma(prices, period=200)
                bb_upper, bb_lower = calculate_bollinger_bands(prices, period=20, std_dev=2)
                
                # 최신값 추출
                indicators = {
                    'ticker': ticker,
                    'date': target_date,
                    'rsi': float(rsi.iloc[-1]) if pd.notna(rsi.iloc[-1]) else None,
                    'macd': float(macd.iloc[-1]) if pd.notna(macd.iloc[-1]) else None,
                    'macd_signal': float(macd_signal.iloc[-1]) if pd.notna(macd_signal.iloc[-1]) else None,
                    'sma_20': float(sma_20.iloc[-1]) if pd.notna(sma_20.iloc[-1]) else None,
                    'sma_50': float(sma_50.iloc[-1]) if pd.notna(sma_50.iloc[-1]) else None,
                    'sma_200': float(sma_200.iloc[-1]) if pd.notna(sma_200.iloc[-1]) else None,
                    'bb_upper': float(bb_upper.iloc[-1]) if pd.notna(bb_upper.iloc[-1]) else None,
                    'bb_lower': float(bb_lower.iloc[-1]) if pd.notna(bb_lower.iloc[-1]) else None,
                }
                
                indicators_list.append(indicators)
                
            except Exception as e:
                logger.warning(f"Error for {ticker}: {e}")
                skipped += 1
                continue
        
        logger.info(f"Calculated: {len(indicators_list)}, Skipped: {skipped}")
        
        if not indicators_list:
            logger.error("No indicators calculated")
            update_indicator_log(target_date, 'failed', 0, 'No indicators', engine)
            raise Exception("No indicators calculated")
        
        # DB에 저장
        from sqlalchemy import text
        
        with engine.connect() as conn:
            for ind in indicators_list:
                try:
                    conn.execute(text("""
                        INSERT INTO technical_indicators
                        (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, ma_200, bollinger_upper, bollinger_lower, created_at)
                        VALUES (:ticker, :date, :rsi, :macd, :macd_signal, :ma_20, :ma_50, :ma_200, :bollinger_upper, :bollinger_lower, :created_at)
                        ON CONFLICT (ticker, date) DO UPDATE SET
                            rsi = EXCLUDED.rsi,
                            macd = EXCLUDED.macd,
                            macd_signal = EXCLUDED.macd_signal,
                            ma_20 = EXCLUDED.ma_20,
                            ma_50 = EXCLUDED.ma_50,
                            ma_200 = EXCLUDED.ma_200,
                            bollinger_upper = EXCLUDED.bollinger_upper,
                            bollinger_lower = EXCLUDED.bollinger_lower,
                            updated_at = NOW()
                    """), {
                        'ticker': ind['ticker'],
                        'date': ind['date'],
                        'rsi': ind.get('rsi'),
                        'macd': ind.get('macd'),
                        'macd_signal': ind.get('macd_signal'),
                        'ma_20': ind.get('sma_20'),  # 매핑: sma_20 → ma_20
                        'ma_50': ind.get('sma_50'),  # 매핑: sma_50 → ma_50
                        'ma_200': ind.get('sma_200'),  # 매핑: sma_200 → ma_200
                        'bollinger_upper': ind.get('bb_upper'),  # 매핑: bb_upper → bollinger_upper
                        'bollinger_lower': ind.get('bb_lower'),  # 매핑: bb_lower → bollinger_lower
                        'created_at': datetime.now()
                    })
                except Exception as e:
                    logger.error(f"Error saving {ind['ticker']}: {e}")
                    raise
            
            conn.commit()
        
        logger.info(f"✅ Successfully saved {len(indicators_list)} indicators for {target_date}")
        
        # 상태 업데이트
        update_indicator_log(
            target_date=target_date,
            status='success',
            count=len(indicators_list),
            engine=engine
        )
        
        print(f"\n✅✅✅ 지표 계산 완료: {len(indicators_list)}개 지표 저장 ({target_date}) ✅✅✅\n")
        
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        update_indicator_log(target_date, 'failed', 0, str(e), engine)
        raise

if __name__ == '__main__':
    calculate_and_save_indicators()
