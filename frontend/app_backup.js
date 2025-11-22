class StockTradingApp {
    constructor() {
        this.baseURL = 'http://localhost:8000/api/v1';
        this.token = localStorage.getItem('access_token');
        this.currentUser = null;
        this.stocks = [];
        this.priceChart = null;
        
        this.initializeApp();
    }

    async initializeApp() {
        if (this.token) {
            try {
                await this.getCurrentUser();
                this.showMainApp();
                await this.loadStocks();
            } catch (error) {
                console.error('토큰 검증 실패:', error);
                this.logout();
            }
        } else {
            this.showLogin();
        }

        this.bindEvents();
    }

    bindEvents() {
        // 로그인 폼
        document.getElementById('login-form').addEventListener('submit', (e) => this.handleLogin(e));
        
        // 로그아웃
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());
        
        // 종목 추가 폼
        document.getElementById('add-stock-form').addEventListener('submit', (e) => this.handleAddStock(e));
        
        // 새로고침 버튼
        document.getElementById('refresh-stocks').addEventListener('click', () => this.loadStocks());
        
        // 차트 관련 이벤트
        document.getElementById('load-chart-btn').addEventListener('click', () => this.loadChart());
        
        // 지표 분석 관련 이벤트
        document.getElementById('load-indicators-btn').addEventListener('click', () => this.loadIndicators());
        
        // 매매 신호 관련 이벤트
        document.getElementById('load-signals-btn').addEventListener('click', () => this.loadSignals());
        
        // 탭 변경 이벤트
        const tabElements = document.querySelectorAll('[data-bs-toggle="tab"]');
        tabElements.forEach(tab => {
            tab.addEventListener('shown.bs.tab', (e) => {
                const targetId = e.target.getAttribute('data-bs-target');
                if (targetId === '#charts-pane') {
                    // 차트 탭이 활성화될 때 Chart.js 리사이즈
                    setTimeout(() => {
                        if (this.priceChart) {
                            this.priceChart.resize();
                        }
                    }, 100);
                }
            });
        });
    }

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${this.baseURL}/users/token`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `username=${encodeURIComponent(username)}&password=${encodeURIComponent(password)}`
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('access_token', this.token);
                
                await this.getCurrentUser();
                this.showMainApp();
                await this.loadStocks();
                this.showNotification('로그인 성공', 'success');
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '로그인 실패', 'error');
            }
        } catch (error) {
            console.error('로그인 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        }
    }

    async getCurrentUser() {
        const response = await fetch(`${this.baseURL}/users/me`, {
            headers: {
                'Authorization': `Bearer ${this.token}`
            }
        });

        if (response.ok) {
            this.currentUser = await response.json();
            document.getElementById('user-info').textContent = `${this.currentUser.username}님 환영합니다`;
        } else {
            throw new Error('사용자 정보를 가져올 수 없습니다');
        }
    }

    logout() {
        this.token = null;
        this.currentUser = null;
        localStorage.removeItem('access_token');
        this.showLogin();
        this.showNotification('로그아웃되었습니다', 'info');
    }

    showLogin() {
        document.getElementById('login-section').style.display = 'block';
        document.getElementById('main-app').style.display = 'none';
        document.getElementById('logout-btn').style.display = 'none';
    }

    showMainApp() {
        document.getElementById('login-section').style.display = 'none';
        document.getElementById('main-app').style.display = 'block';
        document.getElementById('logout-btn').style.display = 'block';
    }

    async loadStocks() {
        this.showLoading('stocks-loading', true);
        
        try {
            const response = await fetch(`${this.baseURL}/stocks/?limit=10`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.stocks = await response.json();
                this.displayStocks();
                this.updateTickerSelects();
            } else {
                this.showNotification('종목을 불러올 수 없습니다', 'error');
            }
        } catch (error) {
            console.error('종목 로드 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('stocks-loading', false);
        }
    }

    displayStocks() {
        const stocksList = document.getElementById('stocks-list');
        
        if (this.stocks.length === 0) {
            stocksList.innerHTML = '<p class="text-muted">등록된 종목이 없습니다.</p>';
            return;
        }

        stocksList.innerHTML = this.stocks.map(stock => `
            <div class="stock-item">
                <div class="d-flex justify-content-between align-items-center">
                    <div>
                        <span class="stock-ticker">${stock.ticker}</span>
                        <span class="ms-2">${stock.company_name || 'N/A'}</span>
                        <small class="text-muted d-block">${stock.sector || 'N/A'} - ${stock.industry || 'N/A'}</small>
                    </div>
                    <div>
                        <button class="btn btn-outline-primary btn-sm" onclick="app.viewChart('${stock.ticker}')">
                            <i class="fas fa-chart-line"></i> 차트
                        </button>
                        <button class="btn btn-outline-info btn-sm" onclick="app.viewIndicators('${stock.ticker}')">
                            <i class="fas fa-calculator"></i> 지표
                        </button>
                    </div>
                </div>
            </div>
        `).join('');
    }

    updateTickerSelects() {
        const selects = [
            'chart-ticker-select',
            'indicators-ticker-select', 
            'signals-ticker-select'
        ];
        
        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            const currentValue = select.value;
            
            // 기본 옵션만 남기고 모두 제거
            select.innerHTML = '<option value="">종목을 선택하세요</option>';
            
            // 새로운 옵션 추가
            this.stocks.forEach(stock => {
                const option = document.createElement('option');
                option.value = stock.ticker;
                option.textContent = `${stock.ticker} - ${stock.company_name || 'N/A'}`;
                select.appendChild(option);
            });
            
            // 이전 선택값 복원
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    async handleAddStock(e) {
        e.preventDefault();
        const ticker = document.getElementById('stock-ticker').value.trim();

        if (!ticker) {
            this.showNotification('종목 코드를 입력해주세요', 'error');
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/stocks/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({ ticker: ticker })
            });

            if (response.ok) {
                this.showNotification('종목이 추가되었습니다', 'success');
                document.getElementById('stock-ticker').value = '';
                await this.loadStocks();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '종목 추가에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('종목 추가 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        }
    }

    // 차트 관련 메서드
    async loadChart() {
        const ticker = document.getElementById('chart-ticker-select').value;
        if (!ticker) {
            this.showNotification('종목을 선택해주세요', 'warning');
            return;
        }

        this.showLoading('chart-loading', true);
        document.getElementById('chart-container').style.display = 'none';

        try {
            // 주가 데이터와 지표 요약 데이터를 동시에 가져오기
            const [priceResponse, indicatorResponse] = await Promise.all([
                fetch(`${this.baseURL}/stocks/${ticker}/prices?limit=100`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                }),
                fetch(`${this.baseURL}/indicators/summary/${ticker}`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                })
            ]);

            if (priceResponse.ok && indicatorResponse.ok) {
                const priceData = await priceResponse.json();
                const indicatorData = await indicatorResponse.json();
                
                this.displayChart(ticker, priceData, indicatorData);
                document.getElementById('chart-container').style.display = 'block';
            } else {
                this.showNotification('차트 데이터를 불러올 수 없습니다', 'error');
            }
        } catch (error) {
            console.error('차트 로드 오류:', error);
            this.showNotification('차트 로드 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('chart-loading', false);
        }
    }

    displayChart(ticker, priceData, indicatorData) {
        const ctx = document.getElementById('price-chart').getContext('2d');
        
        // 기존 차트가 있다면 제거
        if (this.priceChart) {
            this.priceChart.destroy();
        }

        // 차트 제목 업데이트
        document.getElementById('chart-title').textContent = 
            `${ticker} - ${indicatorData.company_name || ''} 주가 및 이동평균선`;

        // 주가 데이터를 Chart.js 형식으로 변환
        const chartData = priceData.map(item => ({
            x: new Date(item.date),
            y: item.close_price
        })).sort((a, b) => a.x - b.x);

        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: '종가',
                        data: chartData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        borderWidth: 2,
                        pointRadius: 0
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        title: {
                            display: true,
                            text: '날짜'
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: '가격 (원)'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString() + '원';
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: true,
                        position: 'top'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return context.dataset.label + ': ' + 
                                       context.parsed.y.toLocaleString() + '원';
                            }
                        }
                    }
                },
                interaction: {
                    intersect: false,
                    mode: 'index'
                }
            }
        });

        this.showNotification('차트가 로드되었습니다', 'success');
    }

    // 지표 분석 관련 메서드
    async loadIndicators() {
        const ticker = document.getElementById('indicators-ticker-select').value;
        if (!ticker) {
            this.showNotification('종목을 선택해주세요', 'warning');
            return;
        }

        this.showLoading('indicators-loading', true);
        document.getElementById('indicators-container').style.display = 'none';

        try {
            const response = await fetch(`${this.baseURL}/indicators/summary/${ticker}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.displayIndicators(data);
                document.getElementById('indicators-container').style.display = 'block';
            } else {
                this.showNotification('지표 데이터를 불러올 수 없습니다', 'error');
            }
        } catch (error) {
            console.error('지표 로드 오류:', error);
            this.showNotification('지표 로드 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('indicators-loading', false);
        }
    }

    displayIndicators(data) {
        const container = document.getElementById('indicators-cards');
        
        const formatValue = (value) => {
            if (value === null || value === undefined) return 'N/A';
            return typeof value === 'number' ? value.toFixed(2) : value;
        };

        const formatPrice = (value) => {
            if (value === null || value === undefined) return 'N/A';
            return value.toLocaleString() + '원';
        };

        container.innerHTML = `
            <!-- 현재가 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">현재가</div>
                    <div class="indicator-value text-primary">${formatPrice(data.current_price)}</div>
                    <small class="text-muted">${data.price_date || ''}</small>
                </div>
            </div>
            
            <!-- 이동평균선 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">SMA 20일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages.sma_20)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">SMA 50일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages.sma_50)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">SMA 200일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages.sma_200)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">EMA 20일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages.ema_20)}</div>
                </div>
            </div>
            
            <!-- MACD -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">MACD</div>
                    <div class="indicator-value">${formatValue(data.macd.macd)}</div>
                    <small class="text-muted">Signal: ${formatValue(data.macd.signal)}</small>
                </div>
            </div>
            
            <!-- 볼린저 밴드 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">볼린저 상단</div>
                    <div class="indicator-value">${formatPrice(data.volatility.bb_upper)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">볼린저 하단</div>
                    <div class="indicator-value">${formatPrice(data.volatility.bb_lower)}</div>
                </div>
            </div>
            
            <!-- ADX -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">ADX (추세강도)</div>
                    <div class="indicator-value">${formatValue(data.trend.adx)}</div>
                    <small class="text-muted">${data.trend.adx > 25 ? '강한 추세' : data.trend.adx > 20 ? '보통 추세' : '약한 추세'}</small>
                </div>
            </div>
            
            <!-- ATR -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">ATR (변동성)</div>
                    <div class="indicator-value">${formatValue(data.volatility.atr)}</div>
                </div>
            </div>
            
            <!-- RSI -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">RSI</div>
                    <div class="indicator-value">${formatValue(data.oscillators.rsi)}</div>
                    <small class="text-muted">${
                        data.oscillators.rsi ? (
                            data.oscillators.rsi > 70 ? '과매수' : 
                            data.oscillators.rsi < 30 ? '과매도' : '중립'
                        ) : ''
                    }</small>
                </div>
            </div>
            
            <!-- 스토캐스틱 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">Stochastic K</div>
                    <div class="indicator-value">${formatValue(data.oscillators.stoch_k)}</div>
                </div>
            </div>
        `;

        this.showNotification('지표가 로드되었습니다', 'success');
    }

    // 매매 신호 관련 메서드
    async loadSignals() {
        const ticker = document.getElementById('signals-ticker-select').value;
        if (!ticker) {
            this.showNotification('종목을 선택해주세요', 'warning');
            return;
        }

        this.showLoading('signals-loading', true);
        document.getElementById('signals-container').style.display = 'none';

        try {
            const response = await fetch(`${this.baseURL}/indicators/signals/${ticker}`, {
                headers: { 'Authorization': `Bearer ${this.token}` }
            });

            if (response.ok) {
                const data = await response.json();
                this.displaySignals(data);
                document.getElementById('signals-container').style.display = 'block';
            } else {
                this.showNotification('신호 데이터를 불러올 수 없습니다', 'error');
            }
        } catch (error) {
            console.error('신호 로드 오류:', error);
            this.showNotification('신호 로드 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('signals-loading', false);
        }
    }

    displaySignals(data) {
        const container = document.getElementById('signals-cards');
        
        const getSignalClass = (signal) => {
            if (['Buy', 'Bullish', 'Uptrend'].includes(signal)) return 'signal-bullish';
            if (['Sell', 'Bearish', 'Downtrend'].includes(signal)) return 'signal-bearish';
            return 'signal-neutral';
        };

        container.innerHTML = `
            <!-- 전체 심리 -->
            <div class="col-12">
                <div class="indicator-card">
                    <h5 class="mb-3">${data.ticker} - ${data.company_name}</h5>
                    <div class="row">
                        <div class="col-md-6">
                            <div class="indicator-label">현재가</div>
                            <div class="indicator-value text-primary">${data.current_price ? data.current_price.toLocaleString() + '원' : 'N/A'}</div>
                        </div>
                        <div class="col-md-6">
                            <div class="indicator-label">전체 심리</div>
                            <div class="indicator-value ${getSignalClass(data.overall_sentiment)}">${data.overall_sentiment || 'N/A'}</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- RSI 신호 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">RSI 신호</div>
                    <div class="indicator-value ${getSignalClass(data.signals.rsi_signal)}">${data.signals.rsi_signal || 'N/A'}</div>
                    <small class="text-muted">RSI: ${data.indicators.rsi ? data.indicators.rsi.toFixed(2) : 'N/A'}</small>
                </div>
            </div>
            
            <!-- MACD 신호 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">MACD 신호</div>
                    <div class="indicator-value ${getSignalClass(data.signals.macd_signal)}">${data.signals.macd_signal || 'N/A'}</div>
                    <small class="text-muted">MACD: ${data.indicators.macd ? data.indicators.macd.toFixed(2) : 'N/A'}</small>
                </div>
            </div>
            
            <!-- 스토캐스틱 신호 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">스토캐스틱 신호</div>
                    <div class="indicator-value ${getSignalClass(data.signals.stochastic_signal)}">${data.signals.stochastic_signal || 'N/A'}</div>
                    <small class="text-muted">K: ${data.indicators.stoch_k ? data.indicators.stoch_k.toFixed(2) : 'N/A'}</small>
                </div>
            </div>
            
            <!-- 추세 신호 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">추세 신호</div>
                    <div class="indicator-value ${getSignalClass(data.signals.trend_signal)}">${data.signals.trend_signal || 'N/A'}</div>
                    <small class="text-muted">SMA20: ${data.indicators.sma_20 ? data.indicators.sma_20.toLocaleString() + '원' : 'N/A'}</small>
                </div>
            </div>
            
            <!-- 추세 강도 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">추세 강도</div>
                    <div class="indicator-value">${data.signals.trend_strength || 'N/A'}</div>
                    <small class="text-muted">ADX: ${data.indicators.adx ? data.indicators.adx.toFixed(2) : 'N/A'}</small>
                </div>
            </div>
            
            <!-- 마지막 업데이트 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">분석일</div>
                    <div class="indicator-value">${data.date || 'N/A'}</div>
                </div>
            </div>
        `;

        this.showNotification('매매 신호가 로드되었습니다', 'success');
    }

    // 유틸리티 메서드
    viewChart(ticker) {
        // 차트 탭으로 이동하고 종목 선택
        document.getElementById('charts-tab').click();
        document.getElementById('chart-ticker-select').value = ticker;
        this.loadChart();
    }

    viewIndicators(ticker) {
        // 지표 분석 탭으로 이동하고 종목 선택
        document.getElementById('indicators-tab').click();
        document.getElementById('indicators-ticker-select').value = ticker;
        this.loadIndicators();
    }

    showLoading(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastIcon = document.getElementById('toast-icon');
        const toastTitle = document.getElementById('toast-title');
        const toastBody = document.getElementById('toast-body');

        // 아이콘과 스타일 설정
        const typeConfig = {
            success: { icon: 'fas fa-check-circle', title: '성공', class: 'text-success' },
            error: { icon: 'fas fa-exclamation-circle', title: '오류', class: 'text-danger' },
            warning: { icon: 'fas fa-exclamation-triangle', title: '경고', class: 'text-warning' },
            info: { icon: 'fas fa-info-circle', title: '알림', class: 'text-info' }
        };

        const config = typeConfig[type] || typeConfig.info;
        
        toastIcon.className = config.icon + ' me-2';
        toastIcon.classList.add(config.class);
        toastTitle.textContent = config.title;
        toastBody.textContent = message;

        // Bootstrap Toast 표시
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// 앱 초기화
const app = new StockTradingApp();