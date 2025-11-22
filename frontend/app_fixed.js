class StockTradingApp {
    constructor() {
        this.baseURL = 'http://localhost:8000/api/v1';
        this.token = localStorage.getItem('access_token');
        this.currentUser = null;
        this.stocks = [];
        this.priceChart = null;
        this.volumeChart = null;
        this.currentChartData = null;
        this.currentIndicatorData = null;
        
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
        
        // 지표 토글 버튼
        document.getElementById('toggle-indicators-btn').addEventListener('click', () => {
            const togglePanel = document.getElementById('indicator-toggles');
            togglePanel.style.display = togglePanel.style.display === 'none' ? 'block' : 'none';
        });
        
        // 차트 업데이트 버튼
        document.getElementById('update-chart-btn').addEventListener('click', () => this.updateChartWithIndicators());
        
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
                    setTimeout(() => {
                        if (this.priceChart) {
                            this.priceChart.resize();
                        }
                        if (this.volumeChart) {
                            this.volumeChart.resize();
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
            const response = await fetch(`${this.baseURL}/stocks/?limit=100`, {
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
            
            select.innerHTML = '<option value="">종목을 선택하세요</option>' +
                this.stocks.map(stock => 
                    `<option value="${stock.ticker}">${stock.ticker} - ${stock.company_name || 'N/A'}</option>`
                ).join('');
            
            if (currentValue) {
                select.value = currentValue;
            }
        });
    }

    viewChart(ticker) {
        const chartTab = document.getElementById('charts-tab');
        const tabTrigger = new bootstrap.Tab(chartTab);
        tabTrigger.show();
        
        document.getElementById('chart-ticker-select').value = ticker;
        setTimeout(() => this.loadChart(), 100);
    }

    viewIndicators(ticker) {
        const indicatorsTab = document.getElementById('indicators-tab');
        const tabTrigger = new bootstrap.Tab(indicatorsTab);
        tabTrigger.show();
        
        document.getElementById('indicators-ticker-select').value = ticker;
        setTimeout(() => this.loadIndicators(), 100);
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
        document.getElementById('toggle-indicators-btn').style.display = 'none';
        document.getElementById('indicator-toggles').style.display = 'none';

        try {
            const [priceResponse, indicatorResponse] = await Promise.all([
                fetch(`${this.baseURL}/stocks/${ticker}/prices?limit=200`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                }),
                fetch(`${this.baseURL}/indicators/summary/${ticker}`, {
                    headers: { 'Authorization': `Bearer ${this.token}` }
                })
            ]);

            if (priceResponse.ok) {
                const priceData = await priceResponse.json();
                let indicatorData = null;
                
                if (indicatorResponse.ok) {
                    indicatorData = await indicatorResponse.json();
                }
                
                this.currentChartData = priceData;
                this.currentIndicatorData = indicatorData;
                
                this.displayChartWithIndicators(ticker, priceData, indicatorData);
                document.getElementById('chart-container').style.display = 'block';
                document.getElementById('toggle-indicators-btn').style.display = 'inline-block';
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

    displayChartWithIndicators(ticker, priceData, indicatorData) {
        const ctx = document.getElementById('price-chart').getContext('2d');
        
        // 기존 차트가 있다면 제거
        if (this.priceChart) {
            this.priceChart.destroy();
        }
        if (this.volumeChart) {
            this.volumeChart.destroy();
        }

        // 차트 제목 업데이트
        const companyName = indicatorData?.company_name || this.stocks.find(s => s.ticker === ticker)?.company_name || '';
        document.getElementById('chart-title').textContent = `${ticker} - ${companyName} 주가 및 기술적 지표`;

        // 데이터 정렬 및 준비
        const sortedData = [...priceData].sort((a, b) => new Date(a.date) - new Date(b.date));
        
        // 레이블(날짜) 배열 생성 - 단순한 문자열로 변환
        const labels = sortedData.map(item => {
            const date = new Date(item.date);
            return `${date.getMonth() + 1}/${date.getDate()}`;
        });

        // 주가 데이터 준비 (y 값만)
        const priceValues = sortedData.map(item => item.close_price);

        // 기본 데이터셋 설정
        const datasets = [
            {
                label: '종가',
                data: priceValues,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                tension: 0.1,
                borderWidth: 2,
                pointRadius: 0,
                fill: false
            }
        ];

        // 선택된 지표 추가
        const indicators = this.getSelectedIndicators();
        
        if (indicators.includes('sma20')) {
            const sma20 = this.calculateSMA(sortedData, 20);
            datasets.push({
                label: 'SMA 20',
                data: sma20,
                borderColor: 'rgb(255, 99, 132)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            });
        }
        
        if (indicators.includes('sma50')) {
            const sma50 = this.calculateSMA(sortedData, 50);
            datasets.push({
                label: 'SMA 50',
                data: sma50,
                borderColor: 'rgb(54, 162, 235)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            });
        }
        
        if (indicators.includes('sma200')) {
            const sma200 = this.calculateSMA(sortedData, 200);
            datasets.push({
                label: 'SMA 200',
                data: sma200,
                borderColor: 'rgb(255, 206, 86)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            });
        }
        
        if (indicators.includes('ema20')) {
            const ema20 = this.calculateEMA(sortedData, 20);
            datasets.push({
                label: 'EMA 20',
                data: ema20,
                borderColor: 'rgb(153, 102, 255)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                borderDash: [5, 5]
            });
        }

        // 차트 생성 (단순한 라벨 방식 사용)
        this.priceChart = new Chart(ctx, {
            type: 'line',
            data: { 
                labels: labels,
                datasets: datasets 
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
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

        // 거래량 차트
        if (indicators.includes('volume')) {
            this.displayVolumeChart(sortedData, labels);
        } else {
            document.getElementById('volume-chart-row').style.display = 'none';
        }

        this.showNotification('차트가 로드되었습니다', 'success');
    }

    displayVolumeChart(data, labels) {
        document.getElementById('volume-chart-row').style.display = 'block';
        const ctx = document.getElementById('volume-chart').getContext('2d');
        
        if (this.volumeChart) {
            this.volumeChart.destroy();
        }

        const volumeData = data.map(item => item.volume);

        this.volumeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '거래량',
                    data: volumeData,
                    backgroundColor: 'rgba(54, 162, 235, 0.5)',
                    borderColor: 'rgba(54, 162, 235, 1)',
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        title: {
                            display: true,
                            text: '거래량'
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toLocaleString();
                            }
                        }
                    }
                },
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return '거래량: ' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    getSelectedIndicators() {
        const checkboxes = document.querySelectorAll('.indicator-toggle:checked');
        return Array.from(checkboxes).map(cb => cb.value);
    }

    updateChartWithIndicators() {
        if (!this.currentChartData || !this.currentChartData.length) {
            this.showNotification('차트 데이터가 없습니다', 'warning');
            return;
        }
        
        const ticker = document.getElementById('chart-ticker-select').value;
        this.displayChartWithIndicators(ticker, this.currentChartData, this.currentIndicatorData);
    }

    // 기술적 지표 계산 함수들
    calculateSMA(data, period) {
        const result = [];
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null); // 충분한 데이터가 없는 경우
            } else {
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    sum += data[i - j].close_price;
                }
                result.push(sum / period);
            }
        }
        return result;
    }

    calculateEMA(data, period) {
        const result = [];
        const multiplier = 2 / (period + 1);
        
        // 첫 EMA는 SMA로 계산
        let sum = 0;
        for (let i = 0; i < Math.min(period, data.length); i++) {
            sum += data[i].close_price;
        }
        let ema = sum / Math.min(period, data.length);
        
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
            } else if (i === period - 1) {
                result.push(ema);
            } else {
                ema = (data[i].close_price - ema) * multiplier + ema;
                result.push(ema);
            }
        }
        return result;
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
                    <div class="indicator-value">${formatPrice(data.moving_averages?.sma_20)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">SMA 50일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages?.sma_50)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">SMA 200일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages?.sma_200)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">EMA 20일</div>
                    <div class="indicator-value">${formatPrice(data.moving_averages?.ema_20)}</div>
                </div>
            </div>
            
            <!-- MACD -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">MACD</div>
                    <div class="indicator-value">${formatValue(data.macd?.macd)}</div>
                    <small class="text-muted">Signal: ${formatValue(data.macd?.signal)}</small>
                </div>
            </div>
            
            <!-- 볼린저 밴드 -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">볼린저 상단</div>
                    <div class="indicator-value">${formatPrice(data.volatility?.bb_upper)}</div>
                </div>
            </div>
            
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">볼린저 하단</div>
                    <div class="indicator-value">${formatPrice(data.volatility?.bb_lower)}</div>
                </div>
            </div>
            
            <!-- RSI -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">RSI</div>
                    <div class="indicator-value ${data.oscillators?.rsi > 70 ? 'text-danger' : data.oscillators?.rsi < 30 ? 'text-success' : ''}">${formatValue(data.oscillators?.rsi)}</div>
                    <small class="text-muted">${data.oscillators?.rsi > 70 ? '과매수' : data.oscillators?.rsi < 30 ? '과매도' : '중립'}</small>
                </div>
            </div>
            
            <!-- ADX -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">ADX (추세강도)</div>
                    <div class="indicator-value">${formatValue(data.trend?.adx)}</div>
                    <small class="text-muted">${data.trend?.adx > 25 ? '강한 추세' : data.trend?.adx > 20 ? '보통 추세' : '약한 추세'}</small>
                </div>
            </div>
            
            <!-- ATR -->
            <div class="col-md-6 col-lg-4">
                <div class="indicator-card">
                    <div class="indicator-label">ATR (변동성)</div>
                    <div class="indicator-value">${formatValue(data.volatility?.atr)}</div>
                </div>
            </div>
        `;
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
            if (signal === 'BUY' || signal === 'STRONG_BUY') return 'signal-bullish';
            if (signal === 'SELL' || signal === 'STRONG_SELL') return 'signal-bearish';
            return 'signal-neutral';
        };

        const getSignalText = (signal) => {
            const signalMap = {
                'STRONG_BUY': '강력 매수',
                'BUY': '매수',
                'NEUTRAL': '중립',
                'SELL': '매도',
                'STRONG_SELL': '강력 매도'
            };
            return signalMap[signal] || signal;
        };

        container.innerHTML = `
            <!-- 종합 신호 -->
            <div class="col-12">
                <div class="indicator-card">
                    <h5>종합 매매 신호</h5>
                    <div class="indicator-value ${getSignalClass(data.overall_signal)}">
                        ${getSignalText(data.overall_signal)}
                    </div>
                    <small class="text-muted">신뢰도: ${(data.signal_strength * 100).toFixed(0)}%</small>
                </div>
            </div>
            
            <!-- 개별 신호들 -->
            ${Object.entries(data.signals || {}).map(([key, value]) => `
                <div class="col-md-6 col-lg-4">
                    <div class="indicator-card">
                        <div class="indicator-label">${key.replace(/_/g, ' ').toUpperCase()}</div>
                        <div class="indicator-value ${getSignalClass(value)}">
                            ${getSignalText(value)}
                        </div>
                    </div>
                </div>
            `).join('')}
            
            <!-- 추가 정보 -->
            <div class="col-12">
                <div class="indicator-card">
                    <h6>분석 요약</h6>
                    <ul class="mb-0">
                        <li>이동평균 신호: ${getSignalText(data.signals?.moving_average)}</li>
                        <li>MACD 신호: ${getSignalText(data.signals?.macd)}</li>
                        <li>RSI 신호: ${getSignalText(data.signals?.rsi)}</li>
                        <li>볼린저 밴드 신호: ${getSignalText(data.signals?.bollinger_bands)}</li>
                    </ul>
                </div>
            </div>
        `;
    }

    // 유틸리티 메서드
    showLoading(elementId, show) {
        const element = document.getElementById(elementId);
        if (element) {
            element.style.display = show ? 'block' : 'none';
        }
    }

    showNotification(message, type = 'info') {
        const toast = document.getElementById('toast');
        const toastBody = document.getElementById('toast-body');
        const toastIcon = document.getElementById('toast-icon');
        
        toastBody.textContent = message;
        
        if (type === 'success') {
            toastIcon.className = 'fas fa-check-circle text-success me-2';
        } else if (type === 'error') {
            toastIcon.className = 'fas fa-exclamation-circle text-danger me-2';
        } else if (type === 'warning') {
            toastIcon.className = 'fas fa-exclamation-triangle text-warning me-2';
        } else {
            toastIcon.className = 'fas fa-info-circle text-info me-2';
        }
        
        const bsToast = new bootstrap.Toast(toast);
        bsToast.show();
    }
}

// 앱 초기화
const app = new StockTradingApp();