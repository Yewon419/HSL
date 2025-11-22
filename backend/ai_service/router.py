from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta

from database import get_db
import models
from user_service.auth import get_current_user

router = APIRouter()

@router.get("/recommendations")
def get_ai_recommendations(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    today = datetime.now().date()
    
    recommendations = db.query(models.AIRecommendation).filter(
        models.AIRecommendation.valid_until >= today
    ).order_by(models.AIRecommendation.confidence_score.desc()).limit(10).all()
    
    return [
        {
            "ticker": rec.ticker,
            "recommendation_type": rec.recommendation_type,
            "confidence_score": float(rec.confidence_score) if rec.confidence_score else 0,
            "target_price": float(rec.target_price) if rec.target_price else None,
            "stop_loss": float(rec.stop_loss) if rec.stop_loss else None,
            "reason": rec.reason,
            "valid_until": rec.valid_until
        }
        for rec in recommendations
    ]

@router.get("/patterns")
def get_discovered_patterns(
    current_user: models.User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    patterns = db.query(models.Pattern).order_by(
        models.Pattern.discovered_at.desc()
    ).limit(20).all()
    
    return [
        {
            "id": pattern.id,
            "pattern_type": pattern.pattern_type,
            "description": pattern.description,
            "affected_tickers": pattern.affected_tickers,
            "confidence_level": float(pattern.confidence_level) if pattern.confidence_level else 0,
            "discovered_at": pattern.discovered_at
        }
        for pattern in patterns
    ]