#!/usr/bin/env python3
"""
Simple data migration from SQLite to PostgreSQL
"""

import sqlite3
import psycopg2
from datetime import datetime
import sys

def migrate_data():
    # SQLite connection
    sqlite_conn = sqlite3.connect('stock_demo.db')
    sqlite_cursor = sqlite_conn.cursor()
    
    # PostgreSQL connection
    try:
        pg_conn = psycopg2.connect(
            host="localhost",
            port=5435,
            database="stocktrading", 
            user="admin",
            password="admin123"
        )
        pg_cursor = pg_conn.cursor()
        print("Connected to PostgreSQL successfully")
    except Exception as e:
        print(f"PostgreSQL connection failed: {e}")
        return False
    
    try:
        # 1. Migrate stock basic info
        print("\nMigrating stock information...")
        stocks = {
            "005930.KS": ("Samsung Electronics", "Technology", "Semiconductors"),
            "000660.KS": ("SK Hynix", "Technology", "Memory Chips"), 
            "035420.KS": ("NAVER", "Technology", "Internet Services"),
            "AAPL": ("Apple Inc", "Technology", "Consumer Electronics"),
            "NVDA": ("NVIDIA Corporation", "Technology", "Graphics Cards"),
            "TSLA": ("Tesla Inc", "Automotive", "Electric Vehicles"),
            "MSFT": ("Microsoft Corporation", "Technology", "Software")
        }
        
        for ticker, (name, sector, industry) in stocks.items():
            pg_cursor.execute("""
                INSERT INTO stocks (ticker, company_name, sector, industry)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (ticker) DO UPDATE SET
                    company_name = EXCLUDED.company_name,
                    sector = EXCLUDED.sector,
                    industry = EXCLUDED.industry
            """, (ticker, name, sector, industry))
        
        # 2. Migrate stock prices
        print("Migrating stock prices...")
        sqlite_cursor.execute("SELECT * FROM stock_prices ORDER BY ticker, date")
        price_rows = sqlite_cursor.fetchall()
        
        for row in price_rows:
            ticker, date, open_price, high_price, low_price, close_price, volume = row
            
            pg_cursor.execute("""
                INSERT INTO stock_prices 
                (ticker, date, open_price, high_price, low_price, close_price, volume)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    open_price = EXCLUDED.open_price,
                    high_price = EXCLUDED.high_price,
                    low_price = EXCLUDED.low_price,
                    close_price = EXCLUDED.close_price,
                    volume = EXCLUDED.volume
            """, (ticker, date, open_price, high_price, low_price, close_price, volume))
        
        print(f"Migrated {len(price_rows)} price records")
        
        # 3. Migrate technical indicators  
        print("Migrating technical indicators...")
        sqlite_cursor.execute("SELECT * FROM technical_indicators ORDER BY ticker, date")
        indicator_rows = sqlite_cursor.fetchall()
        
        for row in indicator_rows:
            ticker, date, rsi, macd, macd_signal, ma_20, ma_50, bb_upper, bb_lower = row
            
            pg_cursor.execute("""
                INSERT INTO technical_indicators 
                (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, bollinger_upper, bollinger_lower)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (ticker, date) DO UPDATE SET
                    rsi = EXCLUDED.rsi,
                    macd = EXCLUDED.macd,
                    macd_signal = EXCLUDED.macd_signal,
                    ma_20 = EXCLUDED.ma_20,
                    ma_50 = EXCLUDED.ma_50,
                    bollinger_upper = EXCLUDED.bollinger_upper,
                    bollinger_lower = EXCLUDED.bollinger_lower
            """, (ticker, date, rsi, macd, macd_signal, ma_20, ma_50, bb_upper, bb_lower))
        
        print(f"Migrated {len(indicator_rows)} indicator records")
        
        # 4. Create sample user and portfolio for demo
        print("Creating demo user and portfolio...")
        
        pg_cursor.execute("""
            INSERT INTO users (username, email, password_hash, initial_capital, current_assets)
            VALUES ('demo', 'demo@stocktrading.com', '$2b$12$demo_hash', 7015500, 6985231)
            ON CONFLICT (username) DO UPDATE SET
                initial_capital = EXCLUDED.initial_capital,
                current_assets = EXCLUDED.current_assets
        """)
        
        # Get user ID
        pg_cursor.execute("SELECT id FROM users WHERE username = 'demo'")
        user_id = pg_cursor.fetchone()[0]
        
        # Create portfolio positions
        portfolio_positions = [
            ("005930.KS", 100, 70000, "2025-08-01"),
            ("AAPL", 50, 150, "2025-08-01"), 
            ("NVDA", 20, 400, "2025-08-01")
        ]
        
        for ticker, quantity, buy_price, buy_date in portfolio_positions:
            pg_cursor.execute("""
                INSERT INTO portfolios (user_id, ticker, quantity, buy_price, buy_date, status)
                VALUES (%s, %s, %s, %s, %s, 'holding')
                ON CONFLICT DO NOTHING
            """, (user_id, ticker, quantity, buy_price, buy_date))
        
        # 5. Migrate AI recommendations
        print("Migrating AI recommendations...")
        sqlite_cursor.execute("SELECT * FROM ai_recommendations")
        ai_rows = sqlite_cursor.fetchall()
        
        for row in ai_rows:
            ticker, rec_type, confidence, target_price, reason, created_at = row
            
            pg_cursor.execute("""
                INSERT INTO ai_recommendations 
                (ticker, recommendation_type, confidence_score, target_price, reason, created_at)
                VALUES (%s, %s, %s, %s, %s, %s)
                ON CONFLICT DO NOTHING
            """, (ticker, rec_type, confidence, target_price, reason, created_at))
        
        print(f"Migrated {len(ai_rows)} AI recommendations")
        
        # Commit all changes
        pg_conn.commit()
        
        # Verification
        print("\nVerifying migration...")
        pg_cursor.execute("SELECT COUNT(*) FROM stocks")
        stock_count = pg_cursor.fetchone()[0]
        
        pg_cursor.execute("SELECT COUNT(*) FROM stock_prices")  
        price_count = pg_cursor.fetchone()[0]
        
        pg_cursor.execute("SELECT COUNT(*) FROM technical_indicators")
        indicator_count = pg_cursor.fetchone()[0]
        
        pg_cursor.execute("SELECT COUNT(*) FROM portfolios")
        portfolio_count = pg_cursor.fetchone()[0]
        
        print(f"Stocks: {stock_count}")
        print(f"Prices: {price_count}")
        print(f"Indicators: {indicator_count}")
        print(f"Portfolio positions: {portfolio_count}")
        
        print("\nMigration completed successfully!")
        return True
        
    except Exception as e:
        print(f"Migration error: {e}")
        pg_conn.rollback()
        return False
        
    finally:
        sqlite_conn.close()
        pg_conn.close()

if __name__ == "__main__":
    print("Starting data migration from SQLite to PostgreSQL...")
    success = migrate_data()
    
    if success:
        print("\nReady for Grafana!")
        print("Access: http://localhost:3000")
        print("Login: admin / admin123")
    else:
        print("\nMigration failed!")
        sys.exit(1)