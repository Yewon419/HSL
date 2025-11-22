#!/usr/bin/env python3
"""
Stock Trading System Demo - English Version
Real stock data collection and analysis demo system
"""

import os
import sqlite3
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple
import time

class StockTradingDemo:
    def __init__(self):
        self.db_path = "stock_demo.db"
        self.init_database()
        
        # Test stock list
        self.stocks = {
            "005930.KS": "Samsung Electronics",
            "000660.KS": "SK Hynix", 
            "035420.KS": "NAVER",
            "AAPL": "Apple",
            "NVDA": "NVIDIA",
            "TSLA": "Tesla",
            "MSFT": "Microsoft"
        }
        
        # Virtual portfolio
        self.portfolio = {
            "005930.KS": {"shares": 100, "buy_price": 70000},
            "AAPL": {"shares": 50, "buy_price": 150},
            "NVDA": {"shares": 20, "buy_price": 400}
        }
        
    def init_database(self):
        """Initialize SQLite database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.executescript("""
            DROP TABLE IF EXISTS stock_prices;
            DROP TABLE IF EXISTS technical_indicators;
            DROP TABLE IF EXISTS ai_recommendations;
            
            CREATE TABLE stock_prices (
                ticker TEXT,
                date TEXT,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                PRIMARY KEY (ticker, date)
            );
            
            CREATE TABLE technical_indicators (
                ticker TEXT,
                date TEXT,
                rsi REAL,
                macd REAL,
                macd_signal REAL,
                ma_20 REAL,
                ma_50 REAL,
                bollinger_upper REAL,
                bollinger_lower REAL,
                PRIMARY KEY (ticker, date)
            );
            
            CREATE TABLE ai_recommendations (
                ticker TEXT,
                recommendation_type TEXT,
                confidence_score REAL,
                target_price REAL,
                reason TEXT,
                created_at TEXT,
                PRIMARY KEY (ticker, created_at)
            );
        """)
        
        conn.commit()
        conn.close()
        
    def fetch_stock_data(self, ticker: str, days: int = 100) -> pd.DataFrame:
        """Fetch stock data from Yahoo Finance"""
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = stock.history(start=start_date, end=end_date)
            if data.empty:
                print(f"WARNING {ticker}: Cannot fetch data")
                return pd.DataFrame()
                
            print(f"SUCCESS {ticker}: Collected {len(data)} days of data")
            return data
            
        except Exception as e:
            print(f"ERROR {ticker}: {str(e)}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate technical indicators"""
        if df.empty:
            return df
            
        # RSI calculation
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD calculation
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        
        # Moving averages
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['MA_50'] = df['Close'].rolling(window=50).mean()
        
        # Bollinger Bands
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        return df
    
    def save_to_database(self, ticker: str, df: pd.DataFrame):
        """Save data to database"""
        conn = sqlite3.connect(self.db_path)
        
        price_data = []
        indicator_data = []
        
        for index, row in df.iterrows():
            date_str = index.strftime('%Y-%m-%d')
            
            # Price data
            price_data.append((
                ticker, date_str, row['Open'], row['High'], 
                row['Low'], row['Close'], int(row['Volume'])
            ))
            
            # Technical indicators data
            indicator_data.append((
                ticker, date_str,
                row.get('RSI'), row.get('MACD'), row.get('MACD_Signal'),
                row.get('MA_20'), row.get('MA_50'),
                row.get('BB_Upper'), row.get('BB_Lower')
            ))
        
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM stock_prices WHERE ticker = ?", (ticker,))
        cursor.execute("DELETE FROM technical_indicators WHERE ticker = ?", (ticker,))
        
        cursor.executemany("""
            INSERT INTO stock_prices 
            (ticker, date, open_price, high_price, low_price, close_price, volume)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, price_data)
        
        cursor.executemany("""
            INSERT INTO technical_indicators 
            (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, bollinger_upper, bollinger_lower)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, indicator_data)
        
        conn.commit()
        conn.close()
    
    def generate_signals(self, ticker: str, df: pd.DataFrame) -> List[Dict]:
        """Generate trading signals"""
        signals = []
        
        if df.empty or len(df) < 2:
            return signals
            
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # RSI signals
        if not pd.isna(latest['RSI']):
            if latest['RSI'] < 30:
                signals.append({
                    'type': 'BUY',
                    'indicator': 'RSI',
                    'value': latest['RSI'],
                    'reason': f'RSI {latest["RSI"]:.1f} oversold condition',
                    'confidence': min(90, (30 - latest['RSI']) * 3)
                })
            elif latest['RSI'] > 70:
                signals.append({
                    'type': 'SELL',
                    'indicator': 'RSI',
                    'value': latest['RSI'],
                    'reason': f'RSI {latest["RSI"]:.1f} overbought condition',
                    'confidence': min(90, (latest['RSI'] - 70) * 3)
                })
        
        # MACD signals
        if not pd.isna(latest['MACD']) and not pd.isna(latest['MACD_Signal']):
            if (latest['MACD'] > latest['MACD_Signal'] and 
                previous['MACD'] <= previous['MACD_Signal']):
                signals.append({
                    'type': 'BUY',
                    'indicator': 'MACD',
                    'value': latest['MACD'],
                    'reason': 'MACD Golden Cross occurred',
                    'confidence': 75
                })
            elif (latest['MACD'] < latest['MACD_Signal'] and 
                  previous['MACD'] >= previous['MACD_Signal']):
                signals.append({
                    'type': 'SELL',
                    'indicator': 'MACD',
                    'value': latest['MACD'],
                    'reason': 'MACD Death Cross occurred',
                    'confidence': 75
                })
        
        return signals
    
    def save_ai_recommendations(self, ticker: str, signals: List[Dict]):
        """Save AI recommendations to database"""
        if not signals:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM ai_recommendations WHERE ticker = ?", (ticker,))
        
        for signal in signals:
            cursor.execute("""
                INSERT INTO ai_recommendations 
                (ticker, recommendation_type, confidence_score, target_price, reason, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                ticker, signal['type'], signal['confidence'], 
                None, signal['reason'], datetime.now().isoformat()
            ))
        
        conn.commit()
        conn.close()
    
    def calculate_portfolio_performance(self) -> Dict:
        """Calculate portfolio performance"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_value = 0
        total_cost = 0
        portfolio_details = []
        
        for ticker, position in self.portfolio.items():
            cursor.execute("""
                SELECT close_price FROM stock_prices 
                WHERE ticker = ? ORDER BY date DESC LIMIT 1
            """, (ticker,))
            
            result = cursor.fetchone()
            if result:
                current_price = result[0]
                shares = position['shares']
                buy_price = position['buy_price']
                
                current_value = current_price * shares
                cost_basis = buy_price * shares
                profit_loss = current_value - cost_basis
                profit_loss_pct = (profit_loss / cost_basis) * 100
                
                total_value += current_value
                total_cost += cost_basis
                
                portfolio_details.append({
                    'ticker': ticker,
                    'shares': shares,
                    'buy_price': buy_price,
                    'current_price': current_price,
                    'current_value': current_value,
                    'profit_loss': profit_loss,
                    'profit_loss_pct': profit_loss_pct
                })
        
        conn.close()
        
        return {
            'total_value': total_value,
            'total_cost': total_cost,
            'total_profit_loss': total_value - total_cost,
            'total_return_pct': ((total_value - total_cost) / total_cost * 100) if total_cost > 0 else 0,
            'positions': portfolio_details
        }
    
    def generate_monitoring_report(self):
        """Generate monitoring report"""
        print("\n" + "=" * 80)
        print("STOCK TRADING SYSTEM - Real-time Monitoring Report")
        print("=" * 80)
        print(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # Portfolio performance
        portfolio = self.calculate_portfolio_performance()
        
        print(f"\nPORTFOLIO STATUS:")
        print(f"  - Total Asset Value: ${portfolio['total_value']:,.0f}")
        print(f"  - Initial Investment: ${portfolio['total_cost']:,.0f}")
        print(f"  - Profit/Loss: ${portfolio['total_profit_loss']:,.0f}")
        print(f"  - Return Rate: {portfolio['total_return_pct']:+.2f}%")
        
        print(f"\nINDIVIDUAL STOCK STATUS:")
        for pos in portfolio['positions']:
            name = self.stocks.get(pos['ticker'], pos['ticker'])
            print(f"  - {name} ({pos['ticker']})")
            print(f"    Holdings: {pos['shares']:,} shares x ${pos['current_price']:,.0f} = ${pos['current_value']:,.0f}")
            print(f"    P&L: ${pos['profit_loss']:,.0f} ({pos['profit_loss_pct']:+.2f}%)")
        
        # AI recommendations
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT ticker, recommendation_type, confidence_score, reason
            FROM ai_recommendations
            ORDER BY confidence_score DESC
            LIMIT 10
        """)
        
        recommendations = cursor.fetchall()
        conn.close()
        
        if recommendations:
            print(f"\nAI TRADING RECOMMENDATIONS:")
            for ticker, rec_type, confidence, reason in recommendations:
                name = self.stocks.get(ticker, ticker)
                color = "BUY" if rec_type == "BUY" else "SELL"
                print(f"  {color} {name} ({ticker}): {rec_type}")
                print(f"    Confidence: {confidence:.1f}% | {reason}")
        
        # Market indicators summary
        print(f"\nMARKET INDICATORS SUMMARY:")
        
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ticker, rsi, macd, close_price
            FROM technical_indicators t1
            JOIN stock_prices p1 ON t1.ticker = p1.ticker AND t1.date = p1.date
            WHERE t1.date = (
                SELECT MAX(date) FROM technical_indicators t2 WHERE t2.ticker = t1.ticker
            )
        """)
        
        indicators = cursor.fetchall()
        
        for ticker, rsi, macd, price in indicators:
            name = self.stocks.get(ticker, ticker)
            rsi_status = "Overbought" if rsi and rsi > 70 else "Oversold" if rsi and rsi < 30 else "Neutral"
            macd_status = "Bullish" if macd and macd > 0 else "Bearish" if macd and macd < 0 else "Neutral"
            
            print(f"  - {name}: Price ${price:,.0f}, RSI {rsi:.1f}({rsi_status}), MACD {macd_status}")
        
        conn.close()
        print("=" * 80)
    
    def run_demo(self):
        """Run demo"""
        print("Stock Investment Simulation System Started")
        print("=" * 50)
        
        # 1. Data collection
        print("\nStep 1: Real-time Stock Data Collection")
        for ticker, name in self.stocks.items():
            print(f"  Collecting: {name} ({ticker})", end="")
            df = self.fetch_stock_data(ticker)
            
            if not df.empty:
                # 2. Calculate technical indicators
                df = self.calculate_technical_indicators(df)
                
                # 3. Save to database
                self.save_to_database(ticker, df)
                
                # 4. Generate AI signals
                signals = self.generate_signals(ticker, df)
                self.save_ai_recommendations(ticker, signals)
                
                time.sleep(1)  # Prevent API rate limiting
        
        print("\nData collection and analysis completed!")
        
        # 5. Generate monitoring report
        self.generate_monitoring_report()
        
        # 6. Save results to JSON
        portfolio = self.calculate_portfolio_performance()
        
        with open('monitoring_report.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio,
                'stocks': self.stocks
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\nDetailed report saved: monitoring_report.json")
        print(f"SQLite database: {self.db_path}")
        
        return True

if __name__ == "__main__":
    demo = StockTradingDemo()
    demo.run_demo()