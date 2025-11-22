@echo off
echo ========================================
echo Stock Trading System Demo
echo ========================================
echo.

echo Installing required packages...
pip install yfinance pandas numpy sqlite3 --quiet

echo.
echo Starting stock data collection and analysis...
echo.

python demo.py

echo.
echo Demo completed! Check the generated files:
echo - monitoring_report.json (Portfolio analysis)
echo - stock_demo.db (SQLite database)
echo.

pause