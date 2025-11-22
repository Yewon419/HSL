#!/usr/bin/env python3
"""
주식 스크리닝 통합 테스트
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.screening_service.router import router as screening_router
import uvicorn

app = FastAPI(
    title="Stock Screening Test API",
    description="Test integration for screening and backtesting system",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 스크리닝 라우터 추가
app.include_router(screening_router, prefix="/api/v1/screening", tags=["screening"])

@app.get("/")
async def root():
    return {"message": "Stock Screening Integration Test", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    print("Starting Screening Integration Test Server...")
    print("Visit: http://localhost:8000/docs for API documentation")
    print("Test API endpoints:")
    print("  GET  /api/v1/screening/indicators")
    print("  POST /api/v1/screening/screen")
    print("  POST /api/v1/screening/backtest")
    uvicorn.run("test_screening_integration:app", host="0.0.0.0", port=8000, reload=True)