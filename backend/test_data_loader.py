import os
import sys
import time
from datetime import datetime, timedelta
import requests
import json

# Configuration
API_BASE_URL = "http://localhost:8000/api/v1"
ADMIN_USER = {
    "username": "admin",
    "email": "admin@stocktrading.com",
    "password": "admin123456",
    "initial_capital": 100000000
}

TEST_STOCKS = [
    "005930.KS",  # Samsung Electronics
    "000660.KS",  # SK Hynix
    "AAPL",       # Apple
    "MSFT",       # Microsoft
    "NVDA",       # NVIDIA
    "TSLA"        # Tesla
]

def register_user():
    print("Registering admin user...")
    response = requests.post(
        f"{API_BASE_URL}/users/register",
        json=ADMIN_USER
    )
    if response.status_code == 200:
        print("✅ User registered successfully")
        return True
    elif response.status_code == 400:
        print("ℹ️ User already exists")
        return True
    else:
        print(f"❌ Failed to register user: {response.text}")
        return False

def login():
    print("Logging in...")
    response = requests.post(
        f"{API_BASE_URL}/users/token",
        data={
            "username": ADMIN_USER["username"],
            "password": ADMIN_USER["password"]
        }
    )
    if response.status_code == 200:
        token = response.json()["access_token"]
        print("✅ Login successful")
        return token
    else:
        print(f"❌ Login failed: {response.text}")
        return None

def update_stock_data(token, ticker):
    print(f"Updating data for {ticker}...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_BASE_URL}/stocks/update/{ticker}",
        headers=headers
    )
    if response.status_code == 200:
        print(f"✅ {ticker} updated successfully")
        return True
    else:
        print(f"❌ Failed to update {ticker}: {response.text}")
        return False

def add_to_portfolio(token, ticker, quantity, price):
    print(f"Adding {ticker} to portfolio...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(
        f"{API_BASE_URL}/users/portfolio",
        headers=headers,
        json={
            "ticker": ticker,
            "quantity": quantity,
            "buy_price": price
        }
    )
    if response.status_code == 200:
        print(f"✅ Added {quantity} shares of {ticker} at {price}")
        return True
    else:
        print(f"❌ Failed to add {ticker}: {response.text}")
        return False

def get_dashboard(token):
    print("Fetching dashboard...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE_URL}/users/dashboard",
        headers=headers
    )
    if response.status_code == 200:
        data = response.json()
        print("\n📊 Dashboard Summary:")
        print(f"Total Assets: ₩{data['total_assets']:,.0f}")
        print(f"Total P&L: ₩{data['total_profit_loss']:,.0f} ({data['total_profit_loss_percentage']:.2f}%)")
        print(f"Active Positions: {data['active_positions']}")
        return True
    else:
        print(f"❌ Failed to get dashboard: {response.text}")
        return False

def get_recommendations(token):
    print("\nFetching AI recommendations...")
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(
        f"{API_BASE_URL}/ai/recommendations",
        headers=headers
    )
    if response.status_code == 200:
        recommendations = response.json()
        if recommendations:
            print("\n🤖 AI Recommendations:")
            for rec in recommendations[:5]:
                print(f"  • {rec['ticker']}: {rec['recommendation_type']} "
                      f"(Confidence: {rec['confidence_score']:.1f}%)")
                print(f"    Reason: {rec['reason']}")
        else:
            print("No recommendations available yet")
        return True
    else:
        print(f"❌ Failed to get recommendations: {response.text}")
        return False

def main():
    print("=" * 50)
    print("Stock Trading System - Test Data Loader")
    print("=" * 50)
    
    # Wait for services to start
    print("\nWaiting for services to start...")
    time.sleep(10)
    
    # Register and login
    if not register_user():
        return
    
    token = login()
    if not token:
        return
    
    # Update stock data
    print("\n📈 Updating stock data...")
    for ticker in TEST_STOCKS:
        update_stock_data(token, ticker)
        time.sleep(2)  # Avoid rate limiting
    
    # Add some positions to portfolio
    print("\n💼 Adding positions to portfolio...")
    test_positions = [
        ("005930.KS", 100, 70000),   # Samsung
        ("AAPL", 50, 150),            # Apple
        ("NVDA", 20, 500),            # NVIDIA
    ]
    
    for ticker, quantity, price in test_positions:
        add_to_portfolio(token, ticker, quantity, price)
    
    # Wait for data processing
    print("\n⏳ Waiting for data processing...")
    time.sleep(5)
    
    # Get dashboard
    get_dashboard(token)
    
    # Get AI recommendations
    get_recommendations(token)
    
    print("\n" + "=" * 50)
    print("✅ Test data loaded successfully!")
    print("📊 Access Grafana at: http://localhost:3000")
    print("   Username: admin, Password: admin123")
    print("📚 API Documentation: http://localhost:8000/docs")
    print("=" * 50)

if __name__ == "__main__":
    main()