from sqlalchemy import Column, Integer, String, Float, DateTime, Date, Boolean, ForeignKey, JSON, ARRAY, Text, DECIMAL
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    initial_capital = Column(DECIMAL(15, 2), default=10000000)
    current_assets = Column(DECIMAL(15, 2), default=10000000)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    portfolios = relationship("Portfolio", back_populates="user")
    simulations = relationship("Simulation", back_populates="user")
    alerts = relationship("UserAlert", back_populates="user")

class Sector(Base):
    __tablename__ = "sectors"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    industries = relationship("Industry", back_populates="sector")
    stocks = relationship("Stock", back_populates="sector_obj")

class Industry(Base):
    __tablename__ = "industries"
    
    id = Column(Integer, primary_key=True, index=True)
    sector_id = Column(Integer, ForeignKey("sectors.id"))
    name = Column(String(100), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    sector = relationship("Sector", back_populates="industries")
    stocks = relationship("Stock", back_populates="industry_obj")

class Stock(Base):
    __tablename__ = "stocks"

    ticker = Column(String(10), primary_key=True, index=True)
    company_name = Column(String(200))
    sector = Column(String(100))  # Legacy field
    industry = Column(String(100))  # Legacy field
    market_cap = Column(Integer)  # Legacy field
    market_type = Column(String(20))  # KOSPI or KOSDAQ
    isin_code = Column(String(20))
    sector_id = Column(Integer, ForeignKey("sectors.id"))
    industry_id = Column(Integer, ForeignKey("industries.id"))
    listing_date = Column(Date)
    par_value = Column(Integer)
    face_value = Column(Integer)
    currency = Column(String(3), default='KRW')
    country = Column(String(10), default='KR')  # KR, US, JP, CN 등
    is_active = Column(Boolean, default=True)
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    sector_obj = relationship("Sector", back_populates="stocks")
    industry_obj = relationship("Industry", back_populates="stocks")
    prices = relationship("StockPrice", back_populates="stock")
    indicators = relationship("TechnicalIndicator", back_populates="stock")
    fundamentals = relationship("StockFundamental", back_populates="stock")

class StockFundamental(Base):
    __tablename__ = "stock_fundamentals"
    
    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    market_cap = Column(Integer)
    per = Column(DECIMAL(8, 2))
    pbr = Column(DECIMAL(8, 2))
    eps = Column(Integer)
    bps = Column(Integer)
    dividend_yield = Column(DECIMAL(5, 2))
    roe = Column(DECIMAL(5, 2))
    roa = Column(DECIMAL(5, 2))
    debt_ratio = Column(DECIMAL(5, 2))
    current_ratio = Column(DECIMAL(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    stock = relationship("Stock", back_populates="fundamentals")

class StockClassification(Base):
    __tablename__ = "stock_classifications"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker"))
    classification_type = Column(String(50), nullable=False)
    classification_name = Column(String(100), nullable=False)
    weight = Column(DECIMAL(5, 2))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class StockPrice(Base):
    __tablename__ = "stock_prices"

    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    open_price = Column(DECIMAL(10, 2))
    high_price = Column(DECIMAL(10, 2))
    low_price = Column(DECIMAL(10, 2))
    close_price = Column(DECIMAL(10, 2), nullable=False)
    volume = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock = relationship("Stock", back_populates="prices")

class InvestorTrade(Base):
    __tablename__ = "investor_trades"

    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    foreign_buy = Column(Integer)
    foreign_sell = Column(Integer)
    institution_buy = Column(Integer)
    institution_sell = Column(Integer)
    individual_buy = Column(Integer)
    individual_sell = Column(Integer)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class TechnicalIndicator(Base):
    __tablename__ = "technical_indicators"

    ticker = Column(String(10), ForeignKey("stocks.ticker"), primary_key=True)
    date = Column(Date, primary_key=True)
    stoch_k = Column(DECIMAL(6, 2))
    stoch_d = Column(DECIMAL(6, 2))
    macd = Column(DECIMAL(10, 4))
    macd_signal = Column(DECIMAL(10, 4))
    macd_histogram = Column(DECIMAL(10, 4))
    rsi = Column(DECIMAL(6, 2))
    ma_20 = Column(DECIMAL(10, 2))
    ma_50 = Column(DECIMAL(10, 2))
    ma_200 = Column(DECIMAL(10, 2))
    bollinger_upper = Column(DECIMAL(10, 2))
    bollinger_middle = Column(DECIMAL(10, 2))
    bollinger_lower = Column(DECIMAL(10, 2))
    # 일목균형표 지표
    ichimoku_tenkan = Column(DECIMAL(10, 2))  # 전환선
    ichimoku_kijun = Column(DECIMAL(10, 2))   # 기준선
    ichimoku_senkou_a = Column(DECIMAL(10, 2))  # 선행스팬 A
    ichimoku_senkou_b = Column(DECIMAL(10, 2))  # 선행스팬 B
    ichimoku_chikou = Column(DECIMAL(10, 2))  # 후행스팬
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    stock = relationship("Stock", back_populates="indicators")

class Portfolio(Base):
    __tablename__ = "portfolios"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    quantity = Column(Integer, nullable=False)
    buy_price = Column(DECIMAL(10, 2), nullable=False)
    buy_date = Column(Date, nullable=False)
    sell_price = Column(DECIMAL(10, 2))
    sell_date = Column(Date)
    status = Column(String(20), default="holding")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="portfolios")

class Simulation(Base):
    __tablename__ = "simulations"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(200))
    strategy_config = Column(JSON, nullable=False)
    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)
    initial_capital = Column(DECIMAL(15, 2), nullable=False)
    final_capital = Column(DECIMAL(15, 2))
    roi = Column(DECIMAL(8, 2))
    sharpe_ratio = Column(DECIMAL(6, 3))
    max_drawdown = Column(DECIMAL(6, 2))
    win_rate = Column(DECIMAL(6, 2))
    total_trades = Column(Integer)
    status = Column(String(20), default="pending")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    user = relationship("User", back_populates="simulations")
    trades = relationship("SimulationTrade", back_populates="simulation")

class SimulationTrade(Base):
    __tablename__ = "simulation_trades"
    
    id = Column(Integer, primary_key=True, index=True)
    simulation_id = Column(Integer, ForeignKey("simulations.id"), nullable=False)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    trade_type = Column(String(10), nullable=False)
    quantity = Column(Integer, nullable=False)
    price = Column(DECIMAL(10, 2), nullable=False)
    trade_date = Column(Date, nullable=False)
    reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    simulation = relationship("Simulation", back_populates="trades")

class AIRecommendation(Base):
    __tablename__ = "ai_recommendations"
    
    id = Column(Integer, primary_key=True, index=True)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    recommendation_type = Column(String(10), nullable=False)
    confidence_score = Column(DECIMAL(4, 2))
    target_price = Column(DECIMAL(10, 2))
    stop_loss = Column(DECIMAL(10, 2))
    reason = Column(Text)
    model_version = Column(String(50))
    valid_until = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Pattern(Base):
    __tablename__ = "patterns"
    
    id = Column(Integer, primary_key=True, index=True)
    pattern_type = Column(String(100), nullable=False)
    description = Column(Text)
    affected_tickers = Column(ARRAY(Text))
    confidence_level = Column(DECIMAL(4, 2))
    parameters = Column(JSON)
    alert_sent = Column(Boolean, default=False)
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())

class UserAlert(Base):
    __tablename__ = "user_alerts"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    alert_type = Column(String(50), nullable=False)
    title = Column(String(200), nullable=False)
    message = Column(Text)
    priority = Column(String(20), default="normal")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", back_populates="alerts")

class IndustryCorrelation(Base):
    __tablename__ = "industry_correlations"

    id = Column(Integer, primary_key=True, index=True)
    leader_ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    follower_ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    correlation_coefficient = Column(DECIMAL(4, 3))
    lag_days = Column(Integer)
    confidence_level = Column(DECIMAL(4, 2))
    valid_from = Column(Date, nullable=False)
    valid_until = Column(Date)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Holding(Base):
    """보유종목 모델 - 손절/익절 관리 포함"""
    __tablename__ = "holdings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)
    company_name = Column(String(200))  # 종목명 캐시
    quantity = Column(Integer, nullable=False)  # 보유수량
    avg_buy_price = Column(DECIMAL(10, 2), nullable=False)  # 평균매수가
    buy_date = Column(Date, nullable=False)  # 최초 매수일

    # 손절/익절 설정
    stop_loss_price = Column(DECIMAL(10, 2))  # 손절가 (절대값)
    stop_loss_percent = Column(DECIMAL(5, 2))  # 손절 퍼센트 (예: -5.00)
    take_profit_price = Column(DECIMAL(10, 2))  # 익절가 (절대값)
    take_profit_percent = Column(DECIMAL(5, 2))  # 익절 퍼센트 (예: 10.00)

    # 추가 정보
    memo = Column(Text)  # 메모
    target_quantity = Column(Integer)  # 목표 수량 (추가 매수 계획)
    is_active = Column(Boolean, default=True)  # 활성 상태

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    user = relationship("User", backref="holdings")
    stock = relationship("Stock", backref="holdings")


class SellSignal(Base):
    """매도 신호 모델 - ATS 전략 프레임워크 기반"""
    __tablename__ = "sell_signals"

    id = Column(Integer, primary_key=True, index=True)
    holding_id = Column(Integer, ForeignKey("holdings.id"), nullable=False)
    ticker = Column(String(10), ForeignKey("stocks.ticker"), nullable=False)

    # 신호 정보
    signal_type = Column(String(50), nullable=False)  # ATR_STOP, MACD_CROSS, FIBONACCI 등
    priority = Column(String(20), nullable=False)  # CRITICAL, HIGH, MEDIUM, LOW
    confidence = Column(DECIMAL(4, 2))  # 0.00 ~ 1.00
    reason = Column(Text)
    recommended_action = Column(Text)

    # 매도 정보
    exit_percent = Column(DECIMAL(5, 2))  # 청산 비율 (0~100%)
    target_price = Column(DECIMAL(10, 2))  # 목표 매도가
    current_price = Column(DECIMAL(10, 2))  # 신호 발생 시점 현재가
    total_score = Column(DECIMAL(5, 2))  # 종합 점수

    # 시장 상황
    market_regime = Column(String(20))  # TRENDING, RANGING, VOLATILE
    rsi = Column(DECIMAL(6, 2))
    macd = Column(DECIMAL(10, 4))
    volume_ratio = Column(DECIMAL(6, 2))  # 평균 대비 거래량 비율

    # 상태 관리
    status = Column(String(20), default="PENDING")  # PENDING, NOTIFIED, EXECUTED, EXPIRED, CANCELLED
    notified_at = Column(DateTime(timezone=True))
    executed_at = Column(DateTime(timezone=True))
    execution_price = Column(DECIMAL(10, 2))  # 실제 체결가

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    holding = relationship("Holding", backref="sell_signals")
    stock = relationship("Stock", backref="sell_signals")