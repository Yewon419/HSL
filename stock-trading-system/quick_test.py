import yfinance as yf
import pandas as pd
from datetime import datetime, timedelta
import json

print("=" * 60)
print("Stock Trading System - Quick Data Collection Test")
print("=" * 60)

# Test stocks
TEST_STOCKS = {
    "005930.KS": "Samsung Electronics",
    "000660.KS": "SK Hynix", 
    "AAPL": "Apple",
    "MSFT": "Microsoft",
    "NVDA": "NVIDIA",
    "TSLA": "Tesla"
}

collected_data = {}

for ticker, name in TEST_STOCKS.items():
    print(f"\n📈 Fetching data for {name} ({ticker})...")
    try:
        stock = yf.Ticker(ticker)
        
        # Get historical data (last 30 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=30)
        hist = stock.history(start=start_date, end=end_date)
        
        if not hist.empty:
            latest = hist.iloc[-1]
            
            # Calculate simple indicators
            hist['MA5'] = hist['Close'].rolling(window=5).mean()
            hist['MA20'] = hist['Close'].rolling(window=20).mean()
            hist['Daily_Return'] = hist['Close'].pct_change()
            
            # RSI calculation
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            latest_rsi = rsi.iloc[-1] if not rsi.empty else None
            
            # Store data
            collected_data[ticker] = {
                "name": name,
                "latest_price": round(latest['Close'], 2),
                "volume": int(latest['Volume']),
                "daily_change": round((latest['Close'] - latest['Open']) / latest['Open'] * 100, 2),
                "ma5": round(hist['MA5'].iloc[-1], 2) if not pd.isna(hist['MA5'].iloc[-1]) else None,
                "ma20": round(hist['MA20'].iloc[-1], 2) if not pd.isna(hist['MA20'].iloc[-1]) else None,
                "rsi": round(latest_rsi, 2) if latest_rsi and not pd.isna(latest_rsi) else None,
                "30d_return": round((hist['Close'].iloc[-1] - hist['Close'].iloc[0]) / hist['Close'].iloc[0] * 100, 2)
            }
            
            print(f"  ✅ Latest Price: {collected_data[ticker]['latest_price']:,.2f}")
            print(f"  📊 Daily Change: {collected_data[ticker]['daily_change']:+.2f}%")
            print(f"  📈 30-Day Return: {collected_data[ticker]['30d_return']:+.2f}%")
            if collected_data[ticker]['rsi']:
                rsi_val = collected_data[ticker]['rsi']
                if rsi_val < 30:
                    print(f"  ⚠️ RSI: {rsi_val:.2f} (Oversold)")
                elif rsi_val > 70:
                    print(f"  ⚠️ RSI: {rsi_val:.2f} (Overbought)")
                else:
                    print(f"  📊 RSI: {rsi_val:.2f}")
                    
    except Exception as e:
        print(f"  ❌ Error: {str(e)}")

# Summary
print("\n" + "=" * 60)
print("📊 PORTFOLIO SUMMARY")
print("=" * 60)

# Sort by 30-day return
sorted_stocks = sorted(collected_data.items(), 
                      key=lambda x: x[1].get('30d_return', -999), 
                      reverse=True)

print("\n🏆 Top Performers (30-day):")
for ticker, data in sorted_stocks[:3]:
    if data.get('30d_return'):
        print(f"  • {data['name']}: {data['30d_return']:+.2f}%")

print("\n📉 Bottom Performers (30-day):")
for ticker, data in sorted_stocks[-3:]:
    if data.get('30d_return'):
        print(f"  • {data['name']}: {data['30d_return']:+.2f}%")

# Trading signals
print("\n🤖 TRADING SIGNALS:")
buy_signals = []
sell_signals = []

for ticker, data in collected_data.items():
    if data.get('rsi'):
        if data['rsi'] < 30:
            buy_signals.append((ticker, data['name'], data['rsi']))
        elif data['rsi'] > 70:
            sell_signals.append((ticker, data['name'], data['rsi']))

if buy_signals:
    print("\n💚 BUY Signals (RSI < 30):")
    for ticker, name, rsi in buy_signals:
        print(f"  • {name} ({ticker}): RSI={rsi:.2f}")
else:
    print("\n💚 No strong BUY signals")

if sell_signals:
    print("\n🔴 SELL Signals (RSI > 70):")
    for ticker, name, rsi in sell_signals:
        print(f"  • {name} ({ticker}): RSI={rsi:.2f}")
else:
    print("\n🔴 No strong SELL signals")

# Save to JSON
with open('stock_data.json', 'w', encoding='utf-8') as f:
    json.dump(collected_data, f, indent=2, ensure_ascii=False)

print("\n" + "=" * 60)
print("✅ Data collection complete!")
print("📁 Data saved to: stock_data.json")
print("=" * 60)