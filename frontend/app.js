class StockTradingApp {
    constructor() {
        this.baseURL = API_CONFIG.getBaseURL();
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
        document.getElementById('apply-signal-filter').addEventListener('click', () => this.loadTradingSignals());
        document.getElementById('refresh-signals').addEventListener('click', () => this.loadTradingSignals());

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
                } else if (targetId === '#signals-pane') {
                    // 매매 신호 탭 진입 시 자동 로드
                    this.loadTradingSignals();
                }
            });
        });
    }

    async handleLogin(e) {
        e.preventDefault();
        const username = document.getElementById('username').value;
        const password = document.getElementById('password').value;

        try {
            const response = await fetch(`${this.baseURL}/v1/users/token`, {
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
        const response = await fetch(`${this.baseURL}/v1/users/me`, {
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
                fetch(`${this.baseURL}/v1/indicators/summary/${ticker}`, {
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
        console.log('displayChartWithIndicators called', { ticker, priceDataLength: priceData.length });
        
        const ctx = document.getElementById('price-chart');
        if (!ctx) {
            console.error('Canvas element not found!');
            this.showNotification('차트 캔버스를 찾을 수 없습니다', 'error');
            return;
        }
        
        const chartContext = ctx.getContext('2d');
        if (!chartContext) {
            console.error('Canvas context not available!');
            this.showNotification('차트 컨텍스트를 가져올 수 없습니다', 'error');
            return;
        }
        
        // 기존 차트가 있다면 제거
        if (this.priceChart) {
            this.priceChart.destroy();
            this.priceChart = null;
        }
        if (this.volumeChart) {
            this.volumeChart.destroy();
            this.volumeChart = null;
        }

        // 데이터 검증
        if (!priceData || priceData.length === 0) {
            console.error('No price data available');
            this.showNotification('주가 데이터가 없습니다', 'error');
            return;
        }

        // 차트 제목 업데이트
        const companyName = indicatorData?.company_name || this.stocks.find(s => s.ticker === ticker)?.company_name || '';
        document.getElementById('chart-title').textContent = `${ticker} - ${companyName} 주가 및 기술적 지표`;

        try {
            // 데이터 정렬 및 준비
            const sortedData = [...priceData].sort((a, b) => new Date(a.date) - new Date(b.date));
            console.log('Sorted data length:', sortedData.length);
            
            // 레이블(날짜) 배열 생성
            const labels = sortedData.map(item => {
                const date = new Date(item.date);
                return `${date.getMonth() + 1}/${date.getDate()}`;
            });

            // 주가 데이터 준비
            const priceValues = sortedData.map(item => item.close);
            
            console.log('Labels:', labels.slice(0, 3), '...'); 
            console.log('Prices:', priceValues.slice(0, 3), '...');

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

        // 볼린저 밴드 (API 데이터 사용)
        if (indicators.includes('bb') && indicatorData?.volatility) {
            const bb = indicatorData.volatility;
            if (bb.bb_upper && bb.bb_middle && bb.bb_lower) {
                // 모든 데이터 포인트에 대해 동일한 볼린저 밴드 값 사용 (최신 값)
                const upperData = new Array(sortedData.length).fill(bb.bb_upper);
                const middleData = new Array(sortedData.length).fill(bb.bb_middle);
                const lowerData = new Array(sortedData.length).fill(bb.bb_lower);
                
                datasets.push({
                    label: 'BB Upper',
                    data: upperData,
                    borderColor: 'rgba(255, 193, 7, 0.8)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: '+1'
                });
                datasets.push({
                    label: 'BB Middle',
                    data: middleData,
                    borderColor: 'rgba(255, 193, 7, 0.6)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false,
                    borderDash: [3, 3]
                });
                datasets.push({
                    label: 'BB Lower',
                    data: lowerData,
                    borderColor: 'rgba(255, 193, 7, 0.8)',
                    backgroundColor: 'rgba(255, 193, 7, 0.1)',
                    borderWidth: 1,
                    pointRadius: 0,
                    fill: false
                });
            }
        }

            // 차트 생성 (단순한 라벨 방식 사용)
            console.log('Creating chart...');
            this.priceChart = new Chart(chartContext, {
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

        // 거래량 차트 (항상 표시)
        this.displayVolumeChart(sortedData, labels);

            console.log('Chart created successfully!');
            
            // 차트 컨테이너 표시 및 버튼 활성화
            document.getElementById('chart-container').style.display = 'block';
            document.getElementById('toggle-indicators-btn').style.display = 'inline-block';
            
            this.showNotification('차트가 로드되었습니다', 'success');
            
        } catch (error) {
            console.error('Chart creation error:', error);
            this.showNotification('차트 생성 중 오류 발생: ' + error.message, 'error');
        }
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
                    sum += data[i - j].close;
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
            sum += data[i].close;
        }
        let ema = sum / Math.min(period, data.length);
        
        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
            } else if (i === period - 1) {
                result.push(ema);
            } else {
                ema = (data[i].close - ema) * multiplier + ema;
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
            const response = await fetch(`${this.baseURL}/v1/indicators/summary/${ticker}`, {
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
    async loadTradingSignals() {
        this.showLoading('signals-loading', true);
        document.getElementById('signals-grid-container').style.display = 'none';

        try {
            // 필터 값 가져오기
            let dateFilter = document.getElementById('signal-date-filter').value;

            // 날짜가 없으면 2025-10-02로 설정 (현재 데이터가 있는 날짜)
            if (!dateFilter) {
                dateFilter = '2025-10-02';
                document.getElementById('signal-date-filter').value = dateFilter;
            }

            // API 호출 - /api/trading/signals/all 엔드포인트 사용
            const url = `${this.baseURL}/trading/signals/all?target_date=${dateFilter}`;

            const response = await fetch(url);

            if (response.ok) {
                const data = await response.json();

                // 매수 시그널만 표시
                if (data.signals && data.signals.buy && data.signals.buy.length > 0) {
                    this.displayTradingSignalsGrid(data.signals.buy);
                    document.getElementById('signals-grid-container').style.display = 'block';
                } else {
                    this.showNotification('해당 날짜에 매수 신호가 없습니다', 'info');
                    document.getElementById('signals-grid-container').style.display = 'none';
                }
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

    displayTradingSignalsGrid(signals) {
        const tbody = document.getElementById('signals-grid-body');

        // 필터 적용
        const countryFilter = document.getElementById('signal-country-filter').value;
        const tickerFilter = document.getElementById('signal-ticker-filter').value.toLowerCase();
        const sectorFilter = document.getElementById('signal-sector-filter').value;
        const strategyFilter = document.getElementById('signal-strategy-filter').value;

        let filteredSignals = signals.filter(signal => {
            if (countryFilter && signal.country !== countryFilter) return false;
            if (tickerFilter && !(signal.ticker.toLowerCase().includes(tickerFilter) ||
                (signal.company_name && signal.company_name.toLowerCase().includes(tickerFilter)))) return false;
            if (sectorFilter && signal.sector !== sectorFilter) return false;
            if (strategyFilter && signal.strategy !== strategyFilter) return false;
            return true;
        });

        if (filteredSignals.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="10" class="text-center text-muted py-4">
                        필터 조건에 맞는 매매 신호가 없습니다
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filteredSignals.map(signal => `
            <tr>
                <td>${signal.country || 'KR'}</td>
                <td><strong>${signal.ticker}</strong></td>
                <td>${signal.company_name || 'N/A'}</td>
                <td>${signal.sector || 'N/A'}</td>
                <td>${signal.signal_date || signal.date || 'N/A'}</td>
                <td><span class="badge bg-primary">RSI+MA상승전략</span></td>
                <td class="text-end">${(signal.current_price || 0).toLocaleString()}원</td>
                <td class="text-end text-success">${(signal.target_price || 0).toLocaleString()}원</td>
                <td class="text-end text-danger">${(signal.stop_loss_price || 0).toLocaleString()}원</td>
                <td>
                    <small>${signal.reason || 'N/A'}</small>
                </td>
            </tr>
        `).join('');

        // 업종 필터 옵션 동적 생성 (한 번만)
        this.updateSectorFilter(signals);
    }

    updateSectorFilter(signals) {
        const sectorFilter = document.getElementById('signal-sector-filter');
        const currentValue = sectorFilter.value;

        // 중복 제거한 업종 리스트
        const sectors = [...new Set(signals.map(s => s.sector).filter(s => s))];

        sectorFilter.innerHTML = '<option value="">전체</option>' +
            sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');

        if (currentValue) {
            sectorFilter.value = currentValue;
        }
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