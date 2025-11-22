#!/usr/bin/env python3
"""
Stock Trading System Demo
실제 주가 데이터를 수집하고 분석하는 데모 시스템
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
        
        # 테스트할 주식 목록
        self.stocks = {
            "005930.KS": "삼성전자",
            "000660.KS": "SK하이닉스", 
            "035420.KS": "네이버",
            "AAPL": "애플",
            "NVDA": "엔비디아",
            "TSLA": "테슬라",
            "MSFT": "마이크로소프트"
        }
        
        # 가상 포트폴리오
        self.portfolio = {
            "005930.KS": {"shares": 100, "buy_price": 70000},
            "AAPL": {"shares": 50, "buy_price": 150},
            "NVDA": {"shares": 20, "buy_price": 400}
        }
        
    def init_database(self):
        """SQLite 데이터베이스 초기화"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 테이블 생성
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
        """Yahoo Finance에서 주가 데이터 가져오기"""
        try:
            stock = yf.Ticker(ticker)
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            data = stock.history(start=start_date, end=end_date)
            if data.empty:
                print(f"⚠️ {ticker}: 데이터를 가져올 수 없습니다")
                return pd.DataFrame()
                
            print(f"✅ {ticker}: {len(data)}일 데이터 수집 완료")
            return data
            
        except Exception as e:
            print(f"❌ {ticker}: 에러 - {str(e)}")
            return pd.DataFrame()
    
    def calculate_technical_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """기술적 지표 계산"""
        if df.empty:
            return df
            
        # RSI 계산
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        # MACD 계산
        exp1 = df['Close'].ewm(span=12).mean()
        exp2 = df['Close'].ewm(span=26).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_Signal'] = df['MACD'].ewm(span=9).mean()
        
        # 이동평균
        df['MA_20'] = df['Close'].rolling(window=20).mean()
        df['MA_50'] = df['Close'].rolling(window=50).mean()
        
        # 볼린저 밴드
        df['BB_Middle'] = df['Close'].rolling(window=20).mean()
        bb_std = df['Close'].rolling(window=20).std()
        df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
        df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
        
        return df
    
    def save_to_database(self, ticker: str, df: pd.DataFrame):
        """데이터베이스에 데이터 저장"""
        conn = sqlite3.connect(self.db_path)
        
        # 주가 데이터 저장
        price_data = []
        indicator_data = []
        
        for index, row in df.iterrows():
            date_str = index.strftime('%Y-%m-%d')
            
            # 주가 데이터
            price_data.append((
                ticker, date_str, row['Open'], row['High'], 
                row['Low'], row['Close'], int(row['Volume'])
            ))
            
            # 기술지표 데이터
            indicator_data.append((
                ticker, date_str,
                row.get('RSI'), row.get('MACD'), row.get('MACD_Signal'),
                row.get('MA_20'), row.get('MA_50'),
                row.get('BB_Upper'), row.get('BB_Lower')
            ))
        
        cursor = conn.cursor()
        
        # 기존 데이터 삭제 후 삽입
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
        """매매 신호 생성"""
        signals = []
        
        if df.empty or len(df) < 2:
            return signals
            
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # RSI 신호
        if not pd.isna(latest['RSI']):
            if latest['RSI'] < 30:
                signals.append({
                    'type': 'BUY',
                    'indicator': 'RSI',
                    'value': latest['RSI'],
                    'reason': f'RSI가 {latest["RSI"]:.1f}로 과매도 구간',
                    'confidence': min(90, (30 - latest['RSI']) * 3)
                })
            elif latest['RSI'] > 70:
                signals.append({
                    'type': 'SELL',
                    'indicator': 'RSI',
                    'value': latest['RSI'],
                    'reason': f'RSI가 {latest["RSI"]:.1f}로 과매수 구간',
                    'confidence': min(90, (latest['RSI'] - 70) * 3)
                })
        
        # MACD 신호
        if not pd.isna(latest['MACD']) and not pd.isna(latest['MACD_Signal']):
            if (latest['MACD'] > latest['MACD_Signal'] and 
                previous['MACD'] <= previous['MACD_Signal']):
                signals.append({
                    'type': 'BUY',
                    'indicator': 'MACD',
                    'value': latest['MACD'],
                    'reason': 'MACD 골든 크로스 발생',
                    'confidence': 75
                })
            elif (latest['MACD'] < latest['MACD_Signal'] and 
                  previous['MACD'] >= previous['MACD_Signal']):
                signals.append({
                    'type': 'SELL',
                    'indicator': 'MACD',
                    'value': latest['MACD'],
                    'reason': 'MACD 데드 크로스 발생',
                    'confidence': 75
                })
        
        return signals
    
    def save_ai_recommendations(self, ticker: str, signals: List[Dict]):
        """AI 추천을 데이터베이스에 저장"""
        if not signals:
            return
            
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 기존 추천 삭제
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
        """포트폴리오 성과 계산"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        total_value = 0
        total_cost = 0
        portfolio_details = []
        
        for ticker, position in self.portfolio.items():
            # 현재가 조회
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
        """모니터링 리포트 생성"""
        print("\n" + "=" * 80)
        print("📊 STOCK TRADING SYSTEM - 실시간 모니터링 리포트")
        print("=" * 80)
        print(f"📅 생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 포트폴리오 성과
        portfolio = self.calculate_portfolio_performance()
        
        print(f"\n💼 포트폴리오 현황:")
        print(f"  • 총 자산가치: ₩{portfolio['total_value']:,.0f}")
        print(f"  • 투자 원금: ₩{portfolio['total_cost']:,.0f}")
        print(f"  • 손익: ₩{portfolio['total_profit_loss']:,.0f}")
        print(f"  • 수익률: {portfolio['total_return_pct']:+.2f}%")
        
        print(f"\n📈 개별 종목 현황:")
        for pos in portfolio['positions']:
            name = self.stocks.get(pos['ticker'], pos['ticker'])
            print(f"  • {name} ({pos['ticker']})")
            print(f"    보유: {pos['shares']:,}주 × {pos['current_price']:,.0f} = ₩{pos['current_value']:,.0f}")
            print(f"    손익: ₩{pos['profit_loss']:,.0f} ({pos['profit_loss_pct']:+.2f}%)")
        
        # AI 추천 조회
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
            print(f"\n🤖 AI 매매 추천:")
            for ticker, rec_type, confidence, reason in recommendations:
                name = self.stocks.get(ticker, ticker)
                color = "🟢" if rec_type == "BUY" else "🔴"
                print(f"  {color} {name} ({ticker}): {rec_type}")
                print(f"    신뢰도: {confidence:.1f}% | {reason}")
        
        # 시장 상황 요약
        print(f"\n📊 시장 지표 요약:")
        
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
            rsi_status = "과매수" if rsi and rsi > 70 else "과매도" if rsi and rsi < 30 else "중립"
            macd_status = "상승" if macd and macd > 0 else "하락" if macd and macd < 0 else "중립"
            
            print(f"  • {name}: 현재가 {price:,.0f}, RSI {rsi:.1f}({rsi_status}), MACD {macd_status}")
        
        conn.close()
        
        print("=" * 80)
    
    def run_demo(self):
        """데모 실행"""
        print("🚀 주식 투자 시뮬레이션 시스템 시작")
        print("=" * 50)
        
        # 1. 데이터 수집
        print("\n📈 1단계: 실시간 주가 데이터 수집")
        for ticker, name in self.stocks.items():
            print(f"  수집 중: {name} ({ticker})", end="")
            df = self.fetch_stock_data(ticker)
            
            if not df.empty:
                # 2. 기술지표 계산
                df = self.calculate_technical_indicators(df)
                
                # 3. 데이터베이스 저장
                self.save_to_database(ticker, df)
                
                # 4. AI 신호 생성
                signals = self.generate_signals(ticker, df)
                self.save_ai_recommendations(ticker, signals)
                
                time.sleep(1)  # API 제한 방지
        
        print("\n✅ 데이터 수집 및 분석 완료!")
        
        # 5. 모니터링 리포트 생성
        self.generate_monitoring_report()
        
        # 6. JSON 파일로 결과 저장
        portfolio = self.calculate_portfolio_performance()
        
        with open('monitoring_report.json', 'w', encoding='utf-8') as f:
            json.dump({
                'timestamp': datetime.now().isoformat(),
                'portfolio': portfolio,
                'stocks': self.stocks
            }, f, indent=2, ensure_ascii=False)
        
        print(f"\n📁 상세 리포트가 저장되었습니다: monitoring_report.json")
        print(f"📁 SQLite 데이터베이스: {self.db_path}")
        
        return True

if __name__ == "__main__":
    demo = StockTradingDemo()
    demo.run_demo()