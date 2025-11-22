@echo off
echo ========================================
echo Korean Stock Market Data Fetcher
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate

REM Install/Update requirements
echo Installing required packages...
pip install -r backend\requirements.txt

REM Run the fetcher
echo.
echo Starting Korean stock data fetcher...
echo.
python backend\fetch_korea_stocks.py %*

REM Deactivate virtual environment
deactivate

echo.
echo Process completed. Press any key to exit...
pause > nul