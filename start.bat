@echo off
echo ========================================
echo Starting Stock Trading System
echo ========================================

echo.
echo Stopping any existing containers...
docker-compose down

echo.
echo Starting Docker containers...
docker-compose up -d

echo.
echo Waiting for services to be ready (30 seconds)...
timeout /t 30 /nobreak

echo.
echo Loading test data...
cd backend
python test_data_loader.py
cd ..

echo.
echo ========================================
echo System Started Successfully!
echo ========================================
echo.
echo Access Points:
echo - API: http://localhost:8000
echo - API Docs: http://localhost:8000/docs
echo - Grafana: http://localhost:3000 (admin/admin123)
echo.
echo To stop the system, run: docker-compose down
echo ========================================
pause