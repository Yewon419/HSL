from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime
from decimal import Decimal

class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=50)
    email: EmailStr

class UserCreate(UserBase):
    password: str = Field(..., min_length=8)
    initial_capital: Optional[Decimal] = Field(default=10000000)

class UserLogin(BaseModel):
    username: str
    password: str

class UserResponse(UserBase):
    id: int
    initial_capital: Decimal
    current_assets: Decimal
    created_at: datetime
    
    class Config:
        from_attributes = True

class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    username: Optional[str] = None

class PortfolioBase(BaseModel):
    ticker: str
    quantity: int = Field(..., gt=0)
    buy_price: Decimal = Field(..., gt=0)

class PortfolioCreate(PortfolioBase):
    pass

class PortfolioSell(BaseModel):
    portfolio_id: int
    sell_price: Decimal = Field(..., gt=0)

class PortfolioResponse(PortfolioBase):
    id: int
    user_id: int
    buy_date: datetime
    sell_price: Optional[Decimal]
    sell_date: Optional[datetime]
    status: str
    current_value: Optional[Decimal] = None
    profit_loss: Optional[Decimal] = None
    profit_loss_percentage: Optional[Decimal] = None
    
    class Config:
        from_attributes = True

class DashboardResponse(BaseModel):
    total_assets: Decimal
    total_profit_loss: Decimal
    total_profit_loss_percentage: Decimal
    portfolio_count: int
    active_positions: int
    best_performer: Optional[dict]
    worst_performer: Optional[dict]
    portfolios: list[PortfolioResponse]