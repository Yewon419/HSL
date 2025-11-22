from celery import Celery
from celery.schedules import crontab
import os
from datetime import datetime
import logging

from database import SessionLocal
from stock_service.data_fetcher import StockDataFetcher
import models

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

celery_app = Celery(
    'stock_trading',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
)

celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Asia/Seoul',
    enable_utc=True,
    beat_schedule={
        'update-stock-data-daily': {
            'task': 'celery_app.update_all_stocks',
            'schedule': crontab(hour=16, minute=0),  # 4 PM KST (after market close)
        },
        'update-stock-data-test': {
            'task': 'celery_app.update_all_stocks',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes for testing
        },
        'generate-ai-recommendations': {
            'task': 'celery_app.generate_recommendations',
            'schedule': crontab(hour=17, minute=0),  # 5 PM KST
        },
    }
)

# Popular Korean and US stocks for testing
DEFAULT_TICKERS = [
    # Korean stocks
    '005930.KS',  # Samsung Electronics
    '000660.KS',  # SK Hynix
    '035420.KS',  # NAVER
    '035720.KS',  # Kakao
    '207940.KS',  # Samsung Biologics
    # US stocks
    'AAPL',       # Apple
    'MSFT',       # Microsoft
    'GOOGL',      # Google
    'NVDA',       # NVIDIA
    'TSLA',       # Tesla
    'META',       # Meta
    'AMZN',       # Amazon
]

@celery_app.task
def update_all_stocks():
    logger.info(f"Starting stock data update at {datetime.now()}")
    db = SessionLocal()
    
    try:
        fetcher = StockDataFetcher(db)
        
        # Get all unique tickers from portfolios
        portfolio_tickers = db.query(models.Portfolio.ticker).distinct().all()
        tickers = [ticker[0] for ticker in portfolio_tickers]
        
        # Add default tickers
        tickers.extend(DEFAULT_TICKERS)
        tickers = list(set(tickers))  # Remove duplicates
        
        results = fetcher.update_multiple_stocks(tickers)
        
        success_count = sum(1 for success in results.values() if success)
        logger.info(f"Updated {success_count}/{len(tickers)} stocks successfully")
        
        return results
        
    except Exception as e:
        logger.error(f"Error updating stocks: {str(e)}")
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def generate_recommendations():
    logger.info("Generating AI recommendations")
    db = SessionLocal()
    
    try:
        # Simple momentum-based recommendations
        from sqlalchemy import and_, func
        
        # Find stocks with positive momentum
        subquery = db.query(
            models.StockPrice.ticker,
            func.max(models.StockPrice.date).label('max_date')
        ).group_by(models.StockPrice.ticker).subquery()
        
        recent_prices = db.query(
            models.StockPrice.ticker,
            models.StockPrice.close_price
        ).join(
            subquery,
            and_(
                models.StockPrice.ticker == subquery.c.ticker,
                models.StockPrice.date == subquery.c.max_date
            )
        ).all()
        
        for ticker, current_price in recent_prices:
            # Get price 5 days ago
            past_price = db.query(models.StockPrice.close_price).filter(
                models.StockPrice.ticker == ticker
            ).order_by(models.StockPrice.date.desc()).offset(5).first()
            
            if past_price and past_price[0]:
                momentum = ((current_price - past_price[0]) / past_price[0]) * 100
                
                # Clear old recommendations
                db.query(models.AIRecommendation).filter(
                    models.AIRecommendation.ticker == ticker
                ).delete()
                
                if momentum > 5:  # Strong upward momentum
                    rec = models.AIRecommendation(
                        ticker=ticker,
                        recommendation_type="BUY",
                        confidence_score=min(80 + momentum, 95),
                        target_price=current_price * 1.1,
                        stop_loss=current_price * 0.95,
                        reason=f"Strong momentum: {momentum:.2f}% gain in 5 days",
                        model_version="momentum_v1",
                        valid_until=datetime.now().date()
                    )
                    db.add(rec)
                elif momentum < -5:  # Strong downward momentum
                    rec = models.AIRecommendation(
                        ticker=ticker,
                        recommendation_type="SELL",
                        confidence_score=min(80 + abs(momentum), 95),
                        target_price=current_price * 0.9,
                        stop_loss=current_price * 1.05,
                        reason=f"Negative momentum: {momentum:.2f}% loss in 5 days",
                        model_version="momentum_v1",
                        valid_until=datetime.now().date()
                    )
                    db.add(rec)
        
        db.commit()
        logger.info("AI recommendations generated successfully")
        return {"status": "success"}
        
    except Exception as e:
        logger.error(f"Error generating recommendations: {str(e)}")
        db.rollback()
        return {"error": str(e)}
    finally:
        db.close()

@celery_app.task
def update_single_stock(ticker: str):
    logger.info(f"Updating data for {ticker}")
    db = SessionLocal()
    
    try:
        fetcher = StockDataFetcher(db)
        success = fetcher.update_stock_data(ticker)
        
        if success:
            logger.info(f"Successfully updated {ticker}")
        else:
            logger.error(f"Failed to update {ticker}")
        
        return {"ticker": ticker, "success": success}
        
    except Exception as e:
        logger.error(f"Error updating {ticker}: {str(e)}")
        return {"ticker": ticker, "error": str(e)}
    finally:
        db.close()