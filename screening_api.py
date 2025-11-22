#!/usr/bin/env python3
"""
주식 스크리닝 및 백테스팅 FastAPI 서버
"""

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Dict, Optional, Any
import pandas as pd
from datetime import datetime, timedelta
import logging
from stock_screener import StockScreener, BacktestEngine

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Stock Screening & Backtesting API",
    description="주식 종목 스크리닝 및 백테스팅 시스템",
    version="1.0.0"
)

# 정적 파일 서빙 (HTML, CSS, JS) - static 디렉토리가 있을 경우에만
import os
if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

# 전역 인스턴스
screener = StockScreener()
backtester = BacktestEngine()

# Pydantic 모델 정의
class ScreeningCondition(BaseModel):
    indicator: str
    condition: str  # golden_cross, death_cross, above, below, between
    value: Optional[float] = None
    value2: Optional[float] = None
    lookback_days: Optional[int] = 5

class ScreeningRequest(BaseModel):
    conditions: List[ScreeningCondition]
    start_date: Optional[str] = None
    end_date: Optional[str] = None

class BacktestRequest(BaseModel):
    tickers: List[str]
    start_date: str
    end_date: str
    initial_capital: Optional[float] = 1000000
    position_size: Optional[float] = 0.1
    transaction_cost: Optional[float] = 0.003

@app.get("/", response_class=HTMLResponse)
async def read_root():
    """메인 페이지"""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>주식 스크리닝 & 백테스팅</title>
        <meta charset="utf-8">
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 20px;
                background-color: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background-color: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .header {
                text-align: center;
                color: #2c3e50;
                margin-bottom: 30px;
            }
            .section {
                margin-bottom: 30px;
                padding: 20px;
                border: 1px solid #ddd;
                border-radius: 8px;
            }
            .section h3 {
                color: #34495e;
                margin-top: 0;
            }
            .form-group {
                margin-bottom: 15px;
            }
            label {
                display: block;
                margin-bottom: 5px;
                font-weight: bold;
                color: #555;
            }
            input, select, button {
                padding: 8px 12px;
                border: 1px solid #ddd;
                border-radius: 4px;
                font-size: 14px;
            }
            input, select {
                width: 200px;
            }
            button {
                background-color: #3498db;
                color: white;
                border: none;
                cursor: pointer;
                margin-right: 10px;
            }
            button:hover {
                background-color: #2980b9;
            }
            .btn-success {
                background-color: #27ae60;
            }
            .btn-success:hover {
                background-color: #229954;
            }
            .btn-danger {
                background-color: #e74c3c;
            }
            .btn-danger:hover {
                background-color: #c0392b;
            }
            .results {
                margin-top: 20px;
                padding: 15px;
                background-color: #f8f9fa;
                border-radius: 5px;
                border-left: 4px solid #3498db;
            }
            .error {
                color: #e74c3c;
                border-left-color: #e74c3c;
            }
            .success {
                color: #27ae60;
                border-left-color: #27ae60;
            }
            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 15px;
            }
            th, td {
                padding: 10px;
                text-align: left;
                border-bottom: 1px solid #ddd;
            }
            th {
                background-color: #34495e;
                color: white;
            }
            tr:hover {
                background-color: #f5f5f5;
            }
            .condition-item {
                background-color: #ecf0f1;
                padding: 10px;
                margin-bottom: 10px;
                border-radius: 5px;
                border-left: 3px solid #3498db;
            }
            .loading {
                text-align: center;
                color: #7f8c8d;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>📈 주식 스크리닝 & 백테스팅 시스템</h1>
                <p>다중 지표 조건으로 종목을 필터링하고 백테스팅 수익률을 확인하세요</p>
            </div>

            <!-- 지표 정보 섹션 -->
            <div class="section">
                <h3>📊 사용 가능한 지표</h3>
                <button onclick="loadIndicators()">지표 목록 조회</button>
                <div id="indicators-result" class="results" style="display:none;"></div>
            </div>

            <!-- 스크리닝 조건 설정 -->
            <div class="section">
                <h3>🔍 스크리닝 조건 설정</h3>
                <div id="conditions-container">
                    <div class="condition-item" data-condition-id="0">
                        <h4>조건 1</h4>
                        <div class="form-group">
                            <label>지표:</label>
                            <select id="indicator-0" onchange="updateConditionOptions(0)">
                                <option value="">선택하세요</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>조건:</label>
                            <select id="condition-0">
                                <option value="golden_cross">골든크로스</option>
                                <option value="death_cross">데드크로스</option>
                                <option value="above">임계값 이상</option>
                                <option value="below">임계값 이하</option>
                                <option value="between">값 범위</option>
                                <option value="bb_breakout_ma_touch">볼린저밴드 하단돌파 → 이평선터치</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>값 1 (선택적):</label>
                            <input type="number" id="value1-0" placeholder="예: 30">
                        </div>
                        <div class="form-group">
                            <label>값 2 (선택적):</label>
                            <input type="number" id="value2-0" placeholder="예: 70">
                        </div>
                        <div class="form-group">
                            <label>조회 기간 (일):</label>
                            <input type="number" id="lookback-0" value="5" min="1" max="30">
                        </div>
                        <button class="btn-danger" onclick="removeCondition(0)">조건 삭제</button>
                    </div>
                </div>
                <button onclick="addCondition()">조건 추가</button>

                <div style="margin-top: 20px;">
                    <div class="form-group">
                        <label>분석 시작일:</label>
                        <input type="date" id="screen-start-date" value="2025-09-01">
                    </div>
                    <div class="form-group">
                        <label>분석 종료일:</label>
                        <input type="date" id="screen-end-date" value="2025-09-24">
                    </div>
                    <button class="btn-success" onclick="runScreening()">스크리닝 실행</button>
                </div>

                <div id="screening-result" class="results" style="display:none;"></div>
            </div>

            <!-- 백테스팅 섹션 -->
            <div class="section">
                <h3>📈 백테스팅</h3>
                <div class="form-group">
                    <label>종목 코드 (쉼표로 구분):</label>
                    <input type="text" id="backtest-tickers" placeholder="예: 005930,000660,035420" style="width: 400px;">
                </div>
                <div class="form-group">
                    <label>백테스트 시작일:</label>
                    <input type="date" id="backtest-start-date" value="2025-09-01">
                </div>
                <div class="form-group">
                    <label>백테스트 종료일:</label>
                    <input type="date" id="backtest-end-date" value="2025-09-24">
                </div>
                <div class="form-group">
                    <label>초기 자본 (원):</label>
                    <input type="number" id="initial-capital" value="1000000" min="100000" step="100000">
                </div>
                <div class="form-group">
                    <label>포지션 크기 (0.0-1.0):</label>
                    <input type="number" id="position-size" value="0.1" min="0.01" max="1.0" step="0.01">
                </div>
                <div class="form-group">
                    <label>거래 비용 (0.0-0.01):</label>
                    <input type="number" id="transaction-cost" value="0.003" min="0" max="0.01" step="0.001">
                </div>
                <button class="btn-success" onclick="runBacktest()">백테스트 실행</button>

                <div id="backtest-result" class="results" style="display:none;"></div>
            </div>
        </div>

        <script>
            let conditionCounter = 1;
            let availableIndicators = [];

            // 페이지 로드 시 지표 목록 자동 로드
            window.addEventListener('DOMContentLoaded', function() {
                loadAllIndicators();
            });

            // 모든 지표를 백그라운드에서 로드하여 콤보박스에 적용
            async function loadAllIndicators() {
                try {
                    const response = await fetch('/api/indicators');
                    const data = await response.json();
                    availableIndicators = data;

                    // 모든 기존 지표 콤보박스에 옵션 추가
                    populateIndicatorSelect('indicator-0');
                } catch (error) {
                    console.error('Failed to load indicators:', error);
                }
            }

            // 특정 지표 선택 콤보박스를 채우는 함수
            function populateIndicatorSelect(selectId) {
                const select = document.getElementById(selectId);
                if (!select) return;

                // 기존 옵션 제거 (첫 번째 기본 옵션 제외)
                while (select.children.length > 1) {
                    select.removeChild(select.lastChild);
                }

                // 새로운 옵션 추가
                availableIndicators.forEach(indicator => {
                    const option = document.createElement('option');
                    option.value = indicator.code;
                    option.textContent = `${indicator.code} - ${indicator.name}`;
                    select.appendChild(option);
                });
            }

            // 지표 목록 조회 (기존 함수)
            async function loadIndicators() {
                try {
                    const response = await fetch('/api/indicators');
                    const data = await response.json();

                    let html = '<h4>사용 가능한 지표 (' + data.length + '개)</h4><table><thead><tr><th>코드</th><th>이름</th></tr></thead><tbody>';
                    data.forEach(indicator => {
                        html += `<tr><td>${indicator.code}</td><td>${indicator.name}</td></tr>`;
                    });
                    html += '</tbody></table>';

                    const resultDiv = document.getElementById('indicators-result');
                    resultDiv.innerHTML = html;
                    resultDiv.className = 'results success';
                    resultDiv.style.display = 'block';
                } catch (error) {
                    showError('indicators-result', '지표 조회 실패: ' + error.message);
                }
            }

            // 조건 추가
            function addCondition() {
                const container = document.getElementById('conditions-container');
                const conditionHtml = `
                    <div class="condition-item" data-condition-id="${conditionCounter}">
                        <h4>조건 ${conditionCounter + 1}</h4>
                        <div class="form-group">
                            <label>지표:</label>
                            <select id="indicator-${conditionCounter}">
                                <option value="">선택하세요</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>조건:</label>
                            <select id="condition-${conditionCounter}">
                                <option value="golden_cross">골든크로스</option>
                                <option value="death_cross">데드크로스</option>
                                <option value="above">임계값 이상</option>
                                <option value="below">임계값 이하</option>
                                <option value="between">값 범위</option>
                                <option value="bb_breakout_ma_touch">볼린저밴드 하단돌파 → 이평선터치</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>값 1 (선택적):</label>
                            <input type="number" id="value1-${conditionCounter}" placeholder="예: 30">
                        </div>
                        <div class="form-group">
                            <label>값 2 (선택적):</label>
                            <input type="number" id="value2-${conditionCounter}" placeholder="예: 70">
                        </div>
                        <div class="form-group">
                            <label>조회 기간 (일):</label>
                            <input type="number" id="lookback-${conditionCounter}" value="5" min="1" max="30">
                        </div>
                        <button class="btn-danger" onclick="removeCondition(${conditionCounter})">조건 삭제</button>
                    </div>
                `;
                container.insertAdjacentHTML('beforeend', conditionHtml);

                // 새로 추가된 조건에도 지표 옵션 적용
                populateIndicatorSelect(`indicator-${conditionCounter}`);
                conditionCounter++;
            }

            // 조건 삭제
            function removeCondition(conditionId) {
                const conditionElement = document.querySelector(`[data-condition-id="${conditionId}"]`);
                if (conditionElement) {
                    conditionElement.remove();
                }
            }

            // 스크리닝 실행
            async function runScreening() {
                const conditions = [];
                const conditionItems = document.querySelectorAll('.condition-item');

                conditionItems.forEach(item => {
                    const id = item.getAttribute('data-condition-id');
                    const indicator = document.getElementById(`indicator-${id}`).value;
                    const condition = document.getElementById(`condition-${id}`).value;
                    const value1 = document.getElementById(`value1-${id}`).value;
                    const value2 = document.getElementById(`value2-${id}`).value;
                    const lookback = document.getElementById(`lookback-${id}`).value;

                    if (indicator) {
                        const conditionObj = {
                            indicator: indicator,
                            condition: condition,
                            lookback_days: parseInt(lookback) || 5
                        };

                        if (value1) conditionObj.value = parseFloat(value1);
                        if (value2) conditionObj.value2 = parseFloat(value2);

                        conditions.push(conditionObj);
                    }
                });

                if (conditions.length === 0) {
                    showError('screening-result', '최소 하나 이상의 조건을 설정해주세요.');
                    return;
                }

                const request = {
                    conditions: conditions,
                    start_date: document.getElementById('screen-start-date').value,
                    end_date: document.getElementById('screen-end-date').value
                };

                showLoading('screening-result', '스크리닝 실행 중...');

                try {
                    const response = await fetch('/api/screen', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(request)
                    });

                    const data = await response.json();

                    if (response.ok) {
                        displayScreeningResults(data);
                    } else {
                        showError('screening-result', '스크리닝 실패: ' + (data.detail || '알 수 없는 오류'));
                    }
                } catch (error) {
                    showError('screening-result', '스크리닝 실행 실패: ' + error.message);
                }
            }

            // 백테스트 실행
            async function runBacktest() {
                const tickers = document.getElementById('backtest-tickers').value
                    .split(',')
                    .map(t => t.trim())
                    .filter(t => t.length > 0);

                if (tickers.length === 0) {
                    showError('backtest-result', '종목 코드를 입력해주세요.');
                    return;
                }

                const request = {
                    tickers: tickers,
                    start_date: document.getElementById('backtest-start-date').value,
                    end_date: document.getElementById('backtest-end-date').value,
                    initial_capital: parseFloat(document.getElementById('initial-capital').value),
                    position_size: parseFloat(document.getElementById('position-size').value),
                    transaction_cost: parseFloat(document.getElementById('transaction-cost').value)
                };

                showLoading('backtest-result', '백테스트 실행 중...');

                try {
                    const response = await fetch('/api/backtest', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(request)
                    });

                    const data = await response.json();

                    if (response.ok) {
                        displayBacktestResults(data);
                    } else {
                        showError('backtest-result', '백테스트 실패: ' + (data.detail || '알 수 없는 오류'));
                    }
                } catch (error) {
                    showError('backtest-result', '백테스트 실행 실패: ' + error.message);
                }
            }

            // 스크리닝 결과 표시
            function displayScreeningResults(data) {
                let html = `<h4>🎯 스크리닝 결과 (${data.results.length}개 매치)</h4>`;

                if (data.results.length > 0) {
                    html += '<table><thead><tr><th>종목코드</th><th>회사명</th><th>날짜</th><th>현재가</th><th>시장구분</th></tr></thead><tbody>';
                    data.results.forEach(result => {
                        html += `<tr>
                            <td>${result.ticker}</td>
                            <td>${result.company_name || '-'}</td>
                            <td>${result.date}</td>
                            <td>${result.current_price ? Number(result.current_price).toLocaleString() + '원' : '-'}</td>
                            <td>${result.market_type || '-'}</td>
                        </tr>`;
                    });
                    html += '</tbody></table>';

                    // 백테스트용 종목 코드 자동 설정
                    const tickers = [...new Set(data.results.map(r => r.ticker))].slice(0, 5);
                    if (tickers.length > 0) {
                        document.getElementById('backtest-tickers').value = tickers.join(',');
                        html += `<p><strong>💡 백테스트 종목이 자동으로 설정되었습니다: ${tickers.join(', ')}</strong></p>`;
                    }
                } else {
                    html += '<p>조건을 만족하는 종목이 없습니다.</p>';
                }

                const resultDiv = document.getElementById('screening-result');
                resultDiv.innerHTML = html;
                resultDiv.className = 'results success';
                resultDiv.style.display = 'block';
            }

            // 백테스트 결과 표시
            function displayBacktestResults(data) {
                let html = '<h4>📊 백테스트 결과</h4>';

                // 포트폴리오 결과
                if (data.portfolio_results && !data.portfolio_results.error) {
                    const portfolio = data.portfolio_results;
                    html += `
                        <div style="background-color: #e8f6f3; padding: 15px; border-radius: 5px; margin-bottom: 20px;">
                            <h5>🎯 포트폴리오 성과</h5>
                            <p><strong>총 수익률:</strong> ${portfolio.total_return_pct}%</p>
                            <p><strong>연간 수익률:</strong> ${portfolio.annualized_return_pct}%</p>
                            <p><strong>변동성:</strong> ${portfolio.volatility_pct}%</p>
                            <p><strong>샤프 비율:</strong> ${portfolio.sharpe_ratio}</p>
                            <p><strong>최대 손실폭:</strong> ${portfolio.max_drawdown_pct}%</p>
                            <p><strong>최종 가치:</strong> ${Number(portfolio.final_value).toLocaleString()}원</p>
                            <p><strong>손익:</strong> ${Number(portfolio.profit_loss).toLocaleString()}원</p>
                        </div>
                    `;
                }

                // 개별 종목 결과
                if (data.individual_results) {
                    html += '<h5>📈 개별 종목 성과</h5>';
                    html += '<table><thead><tr><th>종목</th><th>수익률</th><th>매수가</th><th>매도가</th><th>변동성</th><th>최대손실</th><th>손익</th></tr></thead><tbody>';

                    for (const [ticker, result] of Object.entries(data.individual_results)) {
                        if (!result.error) {
                            const colorClass = result.total_return_pct >= 0 ? 'style="color: #27ae60;"' : 'style="color: #e74c3c;"';
                            html += `<tr>
                                <td>${ticker}</td>
                                <td ${colorClass}>${result.total_return_pct}%</td>
                                <td>${Number(result.buy_price).toLocaleString()}원</td>
                                <td>${Number(result.sell_price).toLocaleString()}원</td>
                                <td>${result.volatility_pct}%</td>
                                <td>${result.max_drawdown_pct}%</td>
                                <td ${colorClass}>${Number(result.profit_loss).toLocaleString()}원</td>
                            </tr>`;
                        }
                    }
                    html += '</tbody></table>';
                }

                // 요약 통계
                if (data.summary && data.summary.individual_stats) {
                    const stats = data.summary.individual_stats;
                    html += `
                        <div style="background-color: #fef9e7; padding: 15px; border-radius: 5px; margin-top: 20px;">
                            <h5>📋 요약 통계</h5>
                            <p><strong>최고 수익 종목:</strong> ${stats.best_performer.ticker} (${stats.best_performer.total_return_pct}%)</p>
                            <p><strong>최저 수익 종목:</strong> ${stats.worst_performer.ticker} (${stats.worst_performer.total_return_pct}%)</p>
                            <p><strong>평균 수익률:</strong> ${stats.avg_return_pct}%</p>
                            <p><strong>성공률:</strong> ${stats.success_rate.toFixed(1)}%</p>
                        </div>
                    `;
                }

                const resultDiv = document.getElementById('backtest-result');
                resultDiv.innerHTML = html;
                resultDiv.className = 'results success';
                resultDiv.style.display = 'block';
            }

            // 에러 표시
            function showError(elementId, message) {
                const resultDiv = document.getElementById(elementId);
                resultDiv.innerHTML = `<h4>❌ 오류</h4><p>${message}</p>`;
                resultDiv.className = 'results error';
                resultDiv.style.display = 'block';
            }

            // 로딩 표시
            function showLoading(elementId, message) {
                const resultDiv = document.getElementById(elementId);
                resultDiv.innerHTML = `<div class="loading"><h4>⏳ ${message}</h4></div>`;
                resultDiv.className = 'results';
                resultDiv.style.display = 'block';
            }
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/api/indicators")
async def get_indicators():
    """사용 가능한 지표 목록 조회"""
    try:
        indicators = screener.get_available_indicators()
        return indicators
    except Exception as e:
        logger.error(f"Error fetching indicators: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/screen")
async def screen_stocks(request: ScreeningRequest):
    """주식 스크리닝 실행"""
    try:
        # 조건 변환
        conditions = []
        for condition in request.conditions:
            cond_dict = {
                'indicator': condition.indicator,
                'condition': condition.condition,
                'lookback_days': condition.lookback_days
            }
            if condition.value is not None:
                cond_dict['value'] = condition.value
            if condition.value2 is not None:
                cond_dict['value2'] = condition.value2

            conditions.append(cond_dict)

        # 날짜 범위 설정
        if request.start_date and request.end_date:
            date_range = (request.start_date, request.end_date)
        else:
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            date_range = (start_date, end_date)

        # 스크리닝 실행
        result_df = screener.screen_stocks(conditions, date_range)

        # DataFrame을 딕셔너리로 변환
        results = result_df.to_dict('records') if not result_df.empty else []

        return {
            'conditions': conditions,
            'date_range': date_range,
            'total_matches': len(results),
            'results': results
        }

    except Exception as e:
        logger.error(f"Error in screening: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/backtest")
async def run_backtest(request: BacktestRequest):
    """백테스트 실행"""
    try:
        result = backtester.run_backtest(
            tickers=request.tickers,
            start_date=request.start_date,
            end_date=request.end_date,
            initial_capital=request.initial_capital,
            position_size=request.position_size,
            transaction_cost=request.transaction_cost
        )

        return result

    except Exception as e:
        logger.error(f"Error in backtesting: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/stocks")
async def get_stock_list():
    """등록된 주식 목록 조회"""
    try:
        with screener.engine.connect() as conn:
            result = conn.execute(text("""
                SELECT ticker, company_name, market_type
                FROM stocks
                WHERE is_active = true
                ORDER BY ticker
            """))
            stocks = []
            for row in result:
                stocks.append({
                    'ticker': row[0],
                    'company_name': row[1],
                    'market_type': row[2]
                })
            return stocks
    except Exception as e:
        logger.error(f"Error fetching stocks: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)