from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import uvicorn
import os

from config import settings
from user_service.router import router as user_router
from stock_service.router import router as stock_router
from simulation_service.router import router as simulation_router
from ai_service.router import router as ai_router
from indicators_service.router import router as indicators_router
from screening_service.router import router as screening_router
from trading_service.router import router as trading_router
from holdings_service.router import router as holdings_router
from sell_signal_service.router import router as sell_signal_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting Stock Trading System...")
    yield
    print("Shutting down Stock Trading System...")

app = FastAPI(
    title="Stock Trading System API",
    description="AI-powered stock investment simulation and monitoring system",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user_router, prefix="/api/v1/users", tags=["users"])
app.include_router(stock_router, prefix="/api/stocks", tags=["stocks"])
app.include_router(simulation_router, prefix="/api/v1/simulations", tags=["simulations"])
app.include_router(ai_router, prefix="/api/v1/ai", tags=["ai"])
app.include_router(indicators_router, prefix="/api/v1/indicators", tags=["indicators"])
app.include_router(screening_router, prefix="/api/v1/screening", tags=["screening"])
app.include_router(trading_router, tags=["trading"])
app.include_router(holdings_router, prefix="/api/v1/holdings", tags=["holdings"])
app.include_router(sell_signal_router, tags=["sell-signals"])

# 정적 파일 서빙 설정
frontend_dir = os.path.join(os.path.dirname(__file__), "frontend")
if os.path.exists(frontend_dir):
    app.mount("/static", StaticFiles(directory=frontend_dir), name="static")
    
    @app.get("/")
    async def read_index():
        return FileResponse(os.path.join(frontend_dir, "index.html"))
        
    @app.get("/config.js")
    async def read_config_js():
        return FileResponse(os.path.join(frontend_dir, "config.js"))

    @app.get("/app.js")
    async def read_app_js():
        return FileResponse(os.path.join(frontend_dir, "app.js"))

    @app.get("/debug_chart.html")
    async def read_debug_chart():
        return FileResponse(os.path.join(frontend_dir, "debug_chart.html"))
        
    @app.get("/chart_debug.html")
    async def read_chart_debug():
        return FileResponse(os.path.join(frontend_dir, "chart_debug.html"))
        
    @app.get("/test_api.html")
    async def read_test_api():
        return FileResponse(os.path.join(frontend_dir, "test_api.html"))

    @app.get("/screening.html")
    async def read_screening():
        return FileResponse(os.path.join(frontend_dir, "screening.html"))

    @app.get("/rsi_ma_strategy.html")
    async def read_rsi_ma_strategy():
        # frontend 폴더에 없으면 상위 frontend 폴더 확인
        rsi_ma_path = os.path.join(frontend_dir, "rsi_ma_strategy.html")
        if not os.path.exists(rsi_ma_path):
            # 상위 폴더의 frontend 확인
            parent_frontend = os.path.join(os.path.dirname(os.path.dirname(__file__)), "frontend", "rsi_ma_strategy.html")
            if os.path.exists(parent_frontend):
                return FileResponse(parent_frontend)
        return FileResponse(rsi_ma_path)

    @app.get("/send_notification.html")
    async def read_send_notification():
        return FileResponse(os.path.join(frontend_dir, "send_notification.html"))

    @app.get("/stock_grid.html")
    async def read_stock_grid():
        return FileResponse(os.path.join(frontend_dir, "stock_grid.html"))

    @app.get("/favicon.ico")
    async def read_favicon():
        favicon_path = os.path.join(frontend_dir, "favicon.ico")
        if os.path.exists(favicon_path):
            return FileResponse(favicon_path)
        return FileResponse(favicon_path, status_code=204)
else:
    @app.get("/")
    async def root():
        return {"message": "Stock Trading System API", "version": "1.0.0"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)