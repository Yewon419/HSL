from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime, timedelta
from decimal import Decimal

from database import get_db
import models
from . import schemas, auth

router = APIRouter()

@router.post("/register", response_model=schemas.UserResponse)
def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(
        (models.User.username == user.username) | (models.User.email == user.email)
    ).first()
    if db_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )
    
    hashed_password = auth.get_password_hash(user.password)
    db_user = models.User(
        username=user.username,
        email=user.email,
        password_hash=hashed_password,
        initial_capital=user.initial_capital,
        current_assets=user.initial_capital
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

@router.post("/token", response_model=schemas.Token)
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(models.User).filter(models.User.username == form_data.username).first()
    if not user or not auth.verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth.create_access_token(data={"sub": user.username})
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=schemas.UserResponse)
def get_current_user(current_user: models.User = Depends(auth.get_current_user)):
    return current_user

@router.get("/dashboard", response_model=schemas.DashboardResponse)
def get_dashboard(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    portfolios = db.query(models.Portfolio).filter(
        models.Portfolio.user_id == current_user.id
    ).all()
    
    total_assets = Decimal('0')
    total_profit_loss = Decimal('0')
    active_positions = 0
    portfolio_data = []
    
    for portfolio in portfolios:
        latest_price = db.query(models.StockPrice).filter(
            models.StockPrice.ticker == portfolio.ticker
        ).order_by(models.StockPrice.date.desc()).first()
        
        if portfolio.status == "holding":
            active_positions += 1
            if latest_price:
                current_value = latest_price.close_price * portfolio.quantity
                profit_loss = current_value - (portfolio.buy_price * portfolio.quantity)
                profit_loss_percentage = (profit_loss / (portfolio.buy_price * portfolio.quantity)) * 100
            else:
                current_value = portfolio.buy_price * portfolio.quantity
                profit_loss = Decimal('0')
                profit_loss_percentage = Decimal('0')
        else:
            current_value = portfolio.sell_price * portfolio.quantity if portfolio.sell_price else 0
            profit_loss = (portfolio.sell_price - portfolio.buy_price) * portfolio.quantity if portfolio.sell_price else 0
            profit_loss_percentage = (profit_loss / (portfolio.buy_price * portfolio.quantity)) * 100 if profit_loss else 0
        
        total_assets += current_value
        total_profit_loss += profit_loss
        
        portfolio_response = schemas.PortfolioResponse(
            id=portfolio.id,
            user_id=portfolio.user_id,
            ticker=portfolio.ticker,
            quantity=portfolio.quantity,
            buy_price=portfolio.buy_price,
            buy_date=portfolio.buy_date,
            sell_price=portfolio.sell_price,
            sell_date=portfolio.sell_date,
            status=portfolio.status,
            current_value=current_value,
            profit_loss=profit_loss,
            profit_loss_percentage=profit_loss_percentage
        )
        portfolio_data.append(portfolio_response)
    
    total_profit_loss_percentage = (total_profit_loss / current_user.initial_capital) * 100 if current_user.initial_capital else 0
    
    best_performer = max(portfolio_data, key=lambda x: x.profit_loss_percentage, default=None)
    worst_performer = min(portfolio_data, key=lambda x: x.profit_loss_percentage, default=None)
    
    return schemas.DashboardResponse(
        total_assets=total_assets,
        total_profit_loss=total_profit_loss,
        total_profit_loss_percentage=total_profit_loss_percentage,
        portfolio_count=len(portfolios),
        active_positions=active_positions,
        best_performer={"ticker": best_performer.ticker, "profit_loss_percentage": best_performer.profit_loss_percentage} if best_performer else None,
        worst_performer={"ticker": worst_performer.ticker, "profit_loss_percentage": worst_performer.profit_loss_percentage} if worst_performer else None,
        portfolios=portfolio_data
    )

@router.post("/portfolio", response_model=schemas.PortfolioResponse)
def add_to_portfolio(
    portfolio: schemas.PortfolioCreate,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    stock = db.query(models.Stock).filter(models.Stock.ticker == portfolio.ticker).first()
    if not stock:
        stock = models.Stock(ticker=portfolio.ticker)
        db.add(stock)
        db.commit()
    
    db_portfolio = models.Portfolio(
        user_id=current_user.id,
        ticker=portfolio.ticker,
        quantity=portfolio.quantity,
        buy_price=portfolio.buy_price,
        buy_date=datetime.now().date(),
        status="holding"
    )
    db.add(db_portfolio)
    db.commit()
    db.refresh(db_portfolio)
    
    return schemas.PortfolioResponse(
        id=db_portfolio.id,
        user_id=db_portfolio.user_id,
        ticker=db_portfolio.ticker,
        quantity=db_portfolio.quantity,
        buy_price=db_portfolio.buy_price,
        buy_date=db_portfolio.buy_date,
        sell_price=db_portfolio.sell_price,
        sell_date=db_portfolio.sell_date,
        status=db_portfolio.status
    )

@router.post("/portfolio/sell", response_model=schemas.PortfolioResponse)
def sell_from_portfolio(
    sell_data: schemas.PortfolioSell,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    portfolio = db.query(models.Portfolio).filter(
        models.Portfolio.id == sell_data.portfolio_id,
        models.Portfolio.user_id == current_user.id,
        models.Portfolio.status == "holding"
    ).first()
    
    if not portfolio:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Portfolio position not found or already sold"
        )
    
    portfolio.sell_price = sell_data.sell_price
    portfolio.sell_date = datetime.now().date()
    portfolio.status = "sold"
    
    db.commit()
    db.refresh(portfolio)
    
    return schemas.PortfolioResponse(
        id=portfolio.id,
        user_id=portfolio.user_id,
        ticker=portfolio.ticker,
        quantity=portfolio.quantity,
        buy_price=portfolio.buy_price,
        buy_date=portfolio.buy_date,
        sell_price=portfolio.sell_price,
        sell_date=portfolio.sell_date,
        status=portfolio.status
    )

@router.get("/alerts", response_model=List[dict])
def get_user_alerts(
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    alerts = db.query(models.UserAlert).filter(
        models.UserAlert.user_id == current_user.id,
        models.UserAlert.is_read == False
    ).order_by(models.UserAlert.created_at.desc()).limit(20).all()
    
    return [
        {
            "id": alert.id,
            "type": alert.alert_type,
            "title": alert.title,
            "message": alert.message,
            "priority": alert.priority,
            "created_at": alert.created_at
        }
        for alert in alerts
    ]

@router.put("/alerts/{alert_id}/read")
def mark_alert_read(
    alert_id: int,
    current_user: models.User = Depends(auth.get_current_user),
    db: Session = Depends(get_db)
):
    alert = db.query(models.UserAlert).filter(
        models.UserAlert.id == alert_id,
        models.UserAlert.user_id == current_user.id
    ).first()
    
    if not alert:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Alert not found"
        )
    
    alert.is_read = True
    db.commit()
    
    return {"message": "Alert marked as read"}