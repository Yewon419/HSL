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
        this.holdings = [];
        this.sellSignalsCache = {};  // 매도 신호 캐시

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
                // 토큰 유효성 검사 실패 - 로그인 페이지로 이동
                this.token = null;
                localStorage.removeItem('access_token');
                this.showLogin();
                this.showNotification('세션이 만료되었습니다. 다시 로그인해주세요.', 'warning');
            }
        } else {
            this.showLogin();
        }

        this.bindEvents();
    }

    bindEvents() {
        // 날짜 필터 초기화 - 오늘 날짜로 설정
        const today = new Date().toISOString().split('T')[0];
        const indicatorDateFilter = document.getElementById('indicator-date-filter');
        const signalDateFilter = document.getElementById('signal-date-filter');
        if (indicatorDateFilter && !indicatorDateFilter.value) {
            indicatorDateFilter.value = today;
        }
        if (signalDateFilter && !signalDateFilter.value) {
            signalDateFilter.value = today;
        }

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

        // 차트 종목 선택 자동완성 초기화
        this.initChartTickerAutocomplete();

        // 지표분석 탭 종목 선택 자동완성 초기화
        this.initIndicatorTickerAutocomplete();

        // 매매신호 탭 종목 선택 자동완성 초기화
        this.initSignalTickerAutocomplete();

        // 지표 토글 버튼
        document.getElementById('toggle-indicators-btn').addEventListener('click', () => {
            const togglePanel = document.getElementById('indicator-toggles');
            togglePanel.style.display = togglePanel.style.display === 'none' ? 'block' : 'none';
        });

        // 차트 업데이트 버튼
        document.getElementById('update-chart-btn').addEventListener('click', () => this.updateChartWithIndicators());

        // 지표 분석 관련 이벤트
        document.getElementById('apply-indicator-filter').addEventListener('click', () => this.loadIndicatorsGrid());
        document.getElementById('refresh-indicators').addEventListener('click', () => this.loadIndicatorsGrid());

        // 매매 신호 관련 이벤트
        document.getElementById('apply-signal-filter').addEventListener('click', () => this.loadTradingSignals());
        document.getElementById('refresh-signals').addEventListener('click', () => this.loadTradingSignals());

        // 보유종목 관련 이벤트
        document.getElementById('holding-add-form')?.addEventListener('submit', (e) => this.handleAddHolding(e));
        document.getElementById('refresh-holdings')?.addEventListener('click', () => this.loadHoldings());
        document.getElementById('check-sell-signals')?.addEventListener('click', () => this.checkAllSellSignals());
        this.initHoldingTickerAutocomplete();

        // 매수일 기본값 설정 (오늘)
        const holdingBuyDate = document.getElementById('holding-buy-date');
        if (holdingBuyDate && !holdingBuyDate.value) {
            holdingBuyDate.value = new Date().toISOString().split('T')[0];
        }

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
                } else if (targetId === '#indicators-pane') {
                    // 지표 분석 탭 진입 시 자동 로드
                    this.loadIndicatorsGrid();
                } else if (targetId === '#signals-pane') {
                    // 매매 신호 탭 진입 시 자동 로드
                    this.loadTradingSignals();
                } else if (targetId === '#holdings-pane') {
                    // 보유종목 탭 진입 시 자동 로드
                    this.loadHoldings();
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
            const response = await fetch(`${this.baseURL}/stocks/?limit=1000`, {
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
        // chart-ticker-select는 이제 input 필드이므로 자동완성으로 처리됨
        // 다른 select 요소들은 필요시 유지
        const selects = [
            'indicators-ticker-select',
            'signals-ticker-select'
        ];

        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (!select) return; // 요소가 없으면 건너뛰기

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

    initChartTickerAutocomplete() {
        const chartTickerInput = document.getElementById('chart-ticker-select');
        const autocompleteList = document.getElementById('chart-autocomplete-list');

        if (!chartTickerInput || !autocompleteList) return;

        // 입력 시 자동완성 표시
        chartTickerInput.addEventListener('input', (e) => {
            let value = e.target.value.trim();
            autocompleteList.innerHTML = '';

            if (value.length < 1) {
                autocompleteList.style.display = 'none';
                return;
            }

            // "종목코드 - 종목명" 형식의 값을 처리하기 위해 파싱
            // 예: "005930 - 삼성전자" -> "삼성전자"로 검색
            const dashIndex = value.indexOf(' - ');
            if (dashIndex !== -1) {
                value = value.substring(dashIndex + 3).trim();
            }

            // 종목코드 또는 종목명으로 검색
            const matches = this.stocks.filter(s => {
                const tickerMatch = s.ticker.toUpperCase().includes(value.toUpperCase());
                const nameMatch = s.company_name && s.company_name.toLowerCase().includes(value.toLowerCase());
                return tickerMatch || nameMatch;
            }).slice(0, 10);

            if (matches.length === 0) {
                autocompleteList.style.display = 'none';
                return;
            }

            matches.forEach(match => {
                const item = document.createElement('div');
                item.className = 'px-3 py-2 cursor-pointer';
                item.style.cursor = 'pointer';
                item.style.borderBottom = '1px solid #f0f0f0';
                item.style.transition = 'background-color 0.2s';
                item.textContent = `${match.ticker} - ${match.company_name || match.ticker}`;

                item.addEventListener('mouseover', () => {
                    item.style.backgroundColor = '#f8f9fa';
                });

                item.addEventListener('mouseout', () => {
                    item.style.backgroundColor = 'transparent';
                });

                item.addEventListener('click', () => {
                    chartTickerInput.value = `${match.ticker} - ${match.company_name || match.ticker}`;
                    autocompleteList.style.display = 'none';
                    // 자동으로 차트 로드
                    this.loadChart();
                });

                autocompleteList.appendChild(item);
            });

            autocompleteList.style.display = 'block';
        });

        // Enter 키로 검색
        chartTickerInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                autocompleteList.style.display = 'none';
                this.loadChart();
            }
        });

        // 외부 클릭 시 자동완성 닫기
        document.addEventListener('click', (e) => {
            if (!chartTickerInput.contains(e.target) && !autocompleteList.contains(e.target)) {
                autocompleteList.style.display = 'none';
            }
        });
    }

    initIndicatorTickerAutocomplete() {
        const indicatorTickerInput = document.getElementById('indicator-ticker-filter');
        const autocompleteList = document.getElementById('indicator-autocomplete-list');

        if (!indicatorTickerInput || !autocompleteList) return;

        // 입력 시 자동완성 표시
        indicatorTickerInput.addEventListener('input', (e) => {
            let value = e.target.value.trim();
            autocompleteList.innerHTML = '';

            if (value.length < 1) {
                autocompleteList.style.display = 'none';
                return;
            }

            // "종목코드 - 종목명" 형식의 값을 처리하기 위해 파싱
            // 예: "005930 - 삼성전자" -> "삼성전자"로 검색
            const dashIndex = value.indexOf(' - ');
            if (dashIndex !== -1) {
                value = value.substring(dashIndex + 3).trim();
            }

            // 종목코드 또는 종목명으로 검색
            const matches = this.stocks.filter(s => {
                const tickerMatch = s.ticker.toUpperCase().includes(value.toUpperCase());
                const nameMatch = s.company_name && s.company_name.toLowerCase().includes(value.toLowerCase());
                return tickerMatch || nameMatch;
            }).slice(0, 10);

            if (matches.length === 0) {
                autocompleteList.style.display = 'none';
                return;
            }

            matches.forEach(match => {
                const item = document.createElement('div');
                item.className = 'px-3 py-2 cursor-pointer';
                item.style.cursor = 'pointer';
                item.style.borderBottom = '1px solid #f0f0f0';
                item.style.transition = 'background-color 0.2s';
                item.textContent = `${match.ticker} - ${match.company_name || match.ticker}`;

                item.addEventListener('mouseover', () => {
                    item.style.backgroundColor = '#f8f9fa';
                });

                item.addEventListener('mouseout', () => {
                    item.style.backgroundColor = 'transparent';
                });

                item.addEventListener('click', () => {
                    indicatorTickerInput.value = `${match.ticker} - ${match.company_name || match.ticker}`;
                    autocompleteList.style.display = 'none';
                });

                autocompleteList.appendChild(item);
            });

            autocompleteList.style.display = 'block';
        });

        // Enter 키로 검색
        indicatorTickerInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                autocompleteList.style.display = 'none';
            }
        });

        // 외부 클릭 시 자동완성 닫기
        document.addEventListener('click', (e) => {
            if (!indicatorTickerInput.contains(e.target) && !autocompleteList.contains(e.target)) {
                autocompleteList.style.display = 'none';
            }
        });
    }

    initSignalTickerAutocomplete() {
        const signalTickerInput = document.getElementById('signal-ticker-filter');
        const autocompleteList = document.getElementById('signal-autocomplete-list');

        if (!signalTickerInput || !autocompleteList) return;

        // 입력 시 자동완성 표시
        signalTickerInput.addEventListener('input', (e) => {
            let value = e.target.value.trim();
            autocompleteList.innerHTML = '';

            if (value.length < 1) {
                autocompleteList.style.display = 'none';
                return;
            }

            // "종목코드 - 종목명" 형식의 값을 처리하기 위해 파싱
            // 예: "005930 - 삼성전자" -> "삼성전자"로 검색
            const dashIndex = value.indexOf(' - ');
            if (dashIndex !== -1) {
                value = value.substring(dashIndex + 3).trim();
            }

            // 종목코드 또는 종목명으로 검색
            const matches = this.stocks.filter(s => {
                const tickerMatch = s.ticker.toUpperCase().includes(value.toUpperCase());
                const nameMatch = s.company_name && s.company_name.toLowerCase().includes(value.toLowerCase());
                return tickerMatch || nameMatch;
            }).slice(0, 10);

            if (matches.length === 0) {
                autocompleteList.style.display = 'none';
                return;
            }

            matches.forEach(match => {
                const item = document.createElement('div');
                item.className = 'px-3 py-2 cursor-pointer';
                item.style.cursor = 'pointer';
                item.style.borderBottom = '1px solid #f0f0f0';
                item.style.transition = 'background-color 0.2s';
                item.textContent = `${match.ticker} - ${match.company_name || match.ticker}`;

                item.addEventListener('mouseover', () => {
                    item.style.backgroundColor = '#f8f9fa';
                });

                item.addEventListener('mouseout', () => {
                    item.style.backgroundColor = 'transparent';
                });

                item.addEventListener('click', () => {
                    signalTickerInput.value = `${match.ticker} - ${match.company_name || match.ticker}`;
                    autocompleteList.style.display = 'none';
                });

                autocompleteList.appendChild(item);
            });

            autocompleteList.style.display = 'block';
        });

        // Enter 키로 검색
        signalTickerInput.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                autocompleteList.style.display = 'none';
            }
        });

        // 외부 클릭 시 자동완성 닫기
        document.addEventListener('click', (e) => {
            if (!signalTickerInput.contains(e.target) && !autocompleteList.contains(e.target)) {
                autocompleteList.style.display = 'none';
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
        let ticker = document.getElementById('chart-ticker-select').value.trim();

        if (!ticker) {
            this.showNotification('종목을 선택해주세요', 'warning');
            return;
        }

        // 입력값에서 종목코드 추출 (예: "005930 - 삼성전자" → "005930")
        const tickerMatch = ticker.match(/^([A-Z0-9]+)/i);
        if (tickerMatch) {
            ticker = tickerMatch[1].toUpperCase();
        } else {
            // 종목명으로 검색
            const stock = this.stocks.find(s => s.company_name?.toLowerCase() === ticker.toLowerCase());
            if (stock) {
                ticker = stock.ticker;
            } else {
                this.showNotification('존재하지 않는 종목입니다', 'warning');
                return;
            }
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
    async loadIndicatorsGrid() {
        this.showLoading('indicators-loading', true);
        document.getElementById('indicators-grid-container').style.display = 'none';

        try {
            // 필터 값 가져오기
            let dateFilter = document.getElementById('indicator-date-filter').value;

            // 날짜가 없으면 오늘 날짜로 설정 (동적으로 최신 날짜 사용)
            if (!dateFilter) {
                const today = new Date().toISOString().split('T')[0];
                dateFilter = today;
                document.getElementById('indicator-date-filter').value = dateFilter;
            }

            // DB에서 지표 데이터 조회
            const response = await fetch(`${this.baseURL}/v1/indicators/grid?date=${dateFilter}`);

            if (response.ok) {
                const data = await response.json();

                if (data && data.length > 0) {
                    this.displayIndicatorsGrid(data);
                    document.getElementById('indicators-grid-container').style.display = 'block';
                } else {
                    this.showNotification('해당 날짜에 지표 데이터가 없습니다', 'info');
                }
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

    displayIndicatorsGrid(indicators) {
        const tbody = document.getElementById('indicators-grid-body');

        // 필터 적용
        const countryFilter = document.getElementById('indicator-country-filter').value;
        const tickerFilter = document.getElementById('indicator-ticker-filter').value.toLowerCase();
        const sectorFilter = document.getElementById('indicator-sector-filter').value;

        let filteredIndicators = indicators.filter(ind => {
            if (countryFilter && ind.country !== countryFilter) return false;
            if (tickerFilter && !(ind.ticker.toLowerCase().includes(tickerFilter) ||
                (ind.company_name && ind.company_name.toLowerCase().includes(tickerFilter)))) return false;
            if (sectorFilter && ind.sector !== sectorFilter) return false;
            return true;
        });

        if (filteredIndicators.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="12" class="text-center text-muted py-4">
                        필터 조건에 맞는 지표 데이터가 없습니다
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = filteredIndicators.map(ind => `
            <tr>
                <td>${ind.country || 'KR'}</td>
                <td><strong>${ind.ticker}</strong></td>
                <td>${ind.company_name || 'N/A'}</td>
                <td>${ind.sector || 'N/A'}</td>
                <td>${ind.date || 'N/A'}</td>
                <td class="text-end">${(ind.close || 0).toLocaleString()}원</td>
                <td class="text-end ${ind.rsi > 70 ? 'text-danger' : ind.rsi < 30 ? 'text-success' : ''}">${(ind.rsi || 0).toFixed(2)}</td>
                <td class="text-end">${(ind.ma_20 || 0).toLocaleString()}</td>
                <td class="text-end">${(ind.ma_50 || 0).toLocaleString()}</td>
                <td class="text-end">${(ind.ma_200 || 0).toLocaleString()}</td>
                <td class="text-end">${(ind.macd || 0).toFixed(2)}</td>
                <td class="text-end">${(ind.bb_position || 0).toFixed(2)}</td>
            </tr>
        `).join('');

        // 업종 필터 옵션 동적 생성
        this.updateIndicatorSectorFilter(indicators);
    }

    updateIndicatorSectorFilter(indicators) {
        const sectorFilter = document.getElementById('indicator-sector-filter');
        const currentValue = sectorFilter.value;

        const sectors = [...new Set(indicators.map(i => i.sector).filter(s => s))];

        sectorFilter.innerHTML = '<option value="">전체</option>' +
            sectors.map(sector => `<option value="${sector}">${sector}</option>`).join('');

        if (currentValue) {
            sectorFilter.value = currentValue;
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

            // 날짜가 없으면 DB의 최신 데이터 날짜 조회
            if (!dateFilter) {
                try {
                    const latestResponse = await fetch(`${this.baseURL}/stocks/latest-date`);
                    if (latestResponse.ok) {
                        const latestData = await latestResponse.json();
                        dateFilter = latestData.latest_date;
                    }
                } catch (e) {
                    console.log('최신 날짜 조회 실패, 오늘 날짜 사용');
                }

                // 최신 날짜 조회 실패 시 오늘 날짜 사용
                if (!dateFilter) {
                    dateFilter = new Date().toISOString().split('T')[0];
                }
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
                <td>
                    <button class="btn btn-success btn-sm" onclick="app.openBuyModal('${signal.ticker}', '${signal.company_name || ''}', ${signal.current_price || 0}, ${signal.target_price || 0}, ${signal.stop_loss_price || 0})">
                        <i class="fas fa-shopping-cart"></i> 매수
                    </button>
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

    // =============================================
    // 보유종목 관련 메서드
    // =============================================

    initHoldingTickerAutocomplete() {
        const holdingTickerInput = document.getElementById('holding-ticker');
        const autocompleteList = document.getElementById('holding-autocomplete-list');

        if (!holdingTickerInput || !autocompleteList) return;

        holdingTickerInput.addEventListener('input', (e) => {
            let value = e.target.value.trim();
            autocompleteList.innerHTML = '';

            if (value.length < 1) {
                autocompleteList.style.display = 'none';
                return;
            }

            const matches = this.stocks.filter(s => {
                const tickerMatch = s.ticker.toUpperCase().includes(value.toUpperCase());
                const nameMatch = s.company_name && s.company_name.toLowerCase().includes(value.toLowerCase());
                return tickerMatch || nameMatch;
            }).slice(0, 10);

            if (matches.length === 0) {
                autocompleteList.style.display = 'none';
                return;
            }

            matches.forEach(match => {
                const item = document.createElement('div');
                item.className = 'px-3 py-2 cursor-pointer';
                item.style.cursor = 'pointer';
                item.style.borderBottom = '1px solid #f0f0f0';
                item.textContent = `${match.ticker} - ${match.company_name || match.ticker}`;

                item.addEventListener('mouseover', () => item.style.backgroundColor = '#f8f9fa');
                item.addEventListener('mouseout', () => item.style.backgroundColor = 'transparent');
                item.addEventListener('click', () => {
                    holdingTickerInput.value = match.ticker;
                    autocompleteList.style.display = 'none';
                });

                autocompleteList.appendChild(item);
            });

            autocompleteList.style.display = 'block';
        });

        document.addEventListener('click', (e) => {
            if (!holdingTickerInput.contains(e.target) && !autocompleteList.contains(e.target)) {
                autocompleteList.style.display = 'none';
            }
        });
    }

    async loadHoldings() {
        this.showLoading('holdings-loading', true);
        document.getElementById('holdings-grid-container').style.display = 'none';

        try {
            // 보유종목 목록 조회
            const response = await fetch(`${this.baseURL}/v1/holdings/`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            // 요약 정보 조회
            const summaryResponse = await fetch(`${this.baseURL}/v1/holdings/summary`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.holdings = await response.json();
                this.displayHoldingsGrid();
                document.getElementById('holdings-grid-container').style.display = 'block';
            } else {
                this.showNotification('보유종목을 불러올 수 없습니다', 'error');
            }

            if (summaryResponse.ok) {
                const summary = await summaryResponse.json();
                this.displayHoldingsSummary(summary);
            }
        } catch (error) {
            console.error('보유종목 로드 오류:', error);
            this.showNotification('보유종목 로드 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('holdings-loading', false);
        }
    }

    displayHoldingsSummary(summary) {
        document.getElementById('summary-total-holdings').textContent = summary.total_holdings;
        document.getElementById('summary-total-value').textContent = summary.total_current_value.toLocaleString() + '원';
        document.getElementById('summary-profit-loss').textContent =
            (summary.total_profit_loss >= 0 ? '+' : '') + summary.total_profit_loss.toLocaleString() + '원';
        document.getElementById('summary-profit-percent').textContent =
            (summary.total_profit_loss_percent >= 0 ? '+' : '') + summary.total_profit_loss_percent.toFixed(2) + '%';
        document.getElementById('summary-stop-loss').textContent = summary.stop_loss_triggered;
        document.getElementById('summary-take-profit').textContent = summary.take_profit_triggered;

        // 수익/손실 카드 색상 변경
        const profitCard = document.getElementById('summary-profit-card');
        if (summary.total_profit_loss >= 0) {
            profitCard.className = 'card bg-success text-white';
        } else {
            profitCard.className = 'card bg-danger text-white';
        }
    }

    displayHoldingsGrid() {
        const tbody = document.getElementById('holdings-grid-body');

        if (this.holdings.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="13" class="text-center text-muted py-4">
                        보유종목이 없습니다. 위 폼에서 종목을 추가해주세요.
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = this.holdings.map(h => {
            const profitClass = h.profit_loss >= 0 ? 'text-success' : 'text-danger';
            const profitSign = h.profit_loss >= 0 ? '+' : '';

            let statusBadge = '';
            if (h.stop_loss_status === 'triggered') {
                statusBadge = '<span class="badge bg-danger">손절도달</span>';
            } else if (h.stop_loss_status === 'warning') {
                statusBadge = '<span class="badge bg-warning text-dark">손절임박</span>';
            } else if (h.take_profit_status === 'triggered') {
                statusBadge = '<span class="badge bg-success">익절도달</span>';
            } else if (h.take_profit_status === 'near') {
                statusBadge = '<span class="badge bg-info">익절임박</span>';
            } else {
                statusBadge = '<span class="badge bg-secondary">안전</span>';
            }

            // 매도 신호 표시
            let signalBadge = '<span class="text-muted">-</span>';
            const signals = this.sellSignalsCache[h.id];
            if (signals && signals.length > 0) {
                const criticalCount = signals.filter(s => s.priority === 'CRITICAL').length;
                const highCount = signals.filter(s => s.priority === 'HIGH').length;
                const mediumCount = signals.filter(s => s.priority === 'MEDIUM').length;

                if (criticalCount > 0) {
                    signalBadge = `<span class="badge bg-danger" style="cursor:pointer" onclick="app.showSellSignalDetail(${h.id})">
                        <i class="fas fa-exclamation-triangle"></i> ${criticalCount} CRITICAL
                    </span>`;
                } else if (highCount > 0) {
                    signalBadge = `<span class="badge bg-warning text-dark" style="cursor:pointer" onclick="app.showSellSignalDetail(${h.id})">
                        <i class="fas fa-exclamation-circle"></i> ${highCount} HIGH
                    </span>`;
                } else if (mediumCount > 0) {
                    signalBadge = `<span class="badge bg-info" style="cursor:pointer" onclick="app.showSellSignalDetail(${h.id})">
                        <i class="fas fa-info-circle"></i> ${mediumCount}
                    </span>`;
                }
            }

            return `
                <tr>
                    <td><strong>${h.ticker}</strong></td>
                    <td>${h.company_name || 'N/A'}</td>
                    <td class="text-end">${h.quantity.toLocaleString()}</td>
                    <td class="text-end">${h.avg_buy_price.toLocaleString()}원</td>
                    <td class="text-end">${h.current_price ? h.current_price.toLocaleString() + '원' : 'N/A'}</td>
                    <td class="text-end">${h.current_value ? h.current_value.toLocaleString() + '원' : 'N/A'}</td>
                    <td class="text-end ${profitClass}">${profitSign}${h.profit_loss ? h.profit_loss.toLocaleString() : 0}원</td>
                    <td class="text-end ${profitClass}">${profitSign}${h.profit_loss_percent ? h.profit_loss_percent.toFixed(2) : 0}%</td>
                    <td class="text-end text-danger">${h.stop_loss_price ? h.stop_loss_price.toLocaleString() + '원' : '-'}</td>
                    <td class="text-end text-success">${h.take_profit_price ? h.take_profit_price.toLocaleString() + '원' : '-'}</td>
                    <td>${statusBadge}</td>
                    <td>${signalBadge}</td>
                    <td>
                        <button class="btn btn-outline-primary btn-sm" onclick="app.editHolding(${h.id})" title="수정">
                            <i class="fas fa-edit"></i>
                        </button>
                        <button class="btn btn-outline-info btn-sm" onclick="app.checkSellSignal(${h.id})" title="매도 신호 확인">
                            <i class="fas fa-chart-line"></i>
                        </button>
                        <button class="btn btn-outline-danger btn-sm" onclick="app.deleteHolding(${h.id})" title="삭제">
                            <i class="fas fa-trash"></i>
                        </button>
                    </td>
                </tr>
            `;
        }).join('');
    }

    async handleAddHolding(e) {
        e.preventDefault();

        const ticker = document.getElementById('holding-ticker').value.trim();
        const quantity = parseInt(document.getElementById('holding-quantity').value);
        const avgPrice = parseFloat(document.getElementById('holding-avg-price').value);
        const buyDate = document.getElementById('holding-buy-date').value;
        const stopLossPct = parseFloat(document.getElementById('holding-stop-loss-pct').value) || null;
        const takeProfitPct = parseFloat(document.getElementById('holding-take-profit-pct').value) || null;
        const memo = document.getElementById('holding-memo').value.trim() || null;

        if (!ticker || !quantity || !avgPrice || !buyDate) {
            this.showNotification('필수 항목을 모두 입력해주세요', 'warning');
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/v1/holdings/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({
                    ticker: ticker,
                    quantity: quantity,
                    avg_buy_price: avgPrice,
                    buy_date: buyDate,
                    stop_loss_percent: stopLossPct,
                    take_profit_percent: takeProfitPct,
                    memo: memo
                })
            });

            if (response.ok) {
                this.showNotification('보유종목이 추가되었습니다', 'success');
                // 폼 초기화
                document.getElementById('holding-add-form').reset();
                document.getElementById('holding-buy-date').value = new Date().toISOString().split('T')[0];
                // 목록 새로고침
                await this.loadHoldings();
                // 폼 접기
                const collapseEl = document.getElementById('addHoldingForm');
                const collapse = bootstrap.Collapse.getInstance(collapseEl);
                if (collapse) collapse.hide();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '보유종목 추가에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('보유종목 추가 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        }
    }

    async editHolding(holdingId) {
        const holding = this.holdings.find(h => h.id === holdingId);
        if (!holding) return;

        const newStopLoss = prompt('손절 퍼센트를 입력하세요 (예: -5):', holding.stop_loss_percent || '');
        const newTakeProfit = prompt('익절 퍼센트를 입력하세요 (예: 10):', holding.take_profit_percent || '');
        const newMemo = prompt('메모를 입력하세요:', holding.memo || '');

        const updateData = {};
        if (newStopLoss !== null && newStopLoss !== '') {
            updateData.stop_loss_percent = parseFloat(newStopLoss);
        }
        if (newTakeProfit !== null && newTakeProfit !== '') {
            updateData.take_profit_percent = parseFloat(newTakeProfit);
        }
        if (newMemo !== null) {
            updateData.memo = newMemo;
        }

        if (Object.keys(updateData).length === 0) {
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/v1/holdings/${holdingId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify(updateData)
            });

            if (response.ok) {
                this.showNotification('보유종목이 수정되었습니다', 'success');
                await this.loadHoldings();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '보유종목 수정에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('보유종목 수정 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        }
    }

    async deleteHolding(holdingId) {
        if (!confirm('정말로 이 보유종목을 삭제하시겠습니까?')) {
            return;
        }

        try {
            const response = await fetch(`${this.baseURL}/v1/holdings/${holdingId}`, {
                method: 'DELETE',
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.showNotification('보유종목이 삭제되었습니다', 'success');
                await this.loadHoldings();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '보유종목 삭제에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('보유종목 삭제 오류:', error);
            this.showNotification('네트워크 오류가 발생했습니다', 'error');
        }
    }

    // =============================================
    // 매도 신호 관련 메서드
    // =============================================

    async checkAllSellSignals() {
        if (!this.currentUser) {
            this.showNotification('로그인이 필요합니다', 'warning');
            return;
        }

        this.showLoading('holdings-loading', true);

        try {
            const response = await fetch(`${this.baseURL}/v1/sell-signals/check/${this.currentUser.id}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const summary = await response.json();

                // 캐시 업데이트
                this.sellSignalsCache = {};
                if (summary.holdings_with_signals) {
                    summary.holdings_with_signals.forEach(hs => {
                        this.sellSignalsCache[hs.holding.holding_id] = hs.signals;
                    });
                }

                // 그리드 새로고침
                this.displayHoldingsGrid();

                // 결과 알림
                const total = summary.critical_signals + summary.high_signals + summary.medium_signals;
                if (total > 0) {
                    this.showNotification(
                        `${total}개의 매도 신호가 발견되었습니다. (긴급: ${summary.critical_signals}, 높음: ${summary.high_signals}, 중간: ${summary.medium_signals})`,
                        summary.critical_signals > 0 ? 'error' : 'warning'
                    );
                } else {
                    this.showNotification('현재 발생한 매도 신호가 없습니다.', 'success');
                }
            } else {
                this.showNotification('매도 신호 확인에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('매도 신호 확인 오류:', error);
            this.showNotification('매도 신호 확인 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('holdings-loading', false);
        }
    }

    async checkSellSignal(holdingId) {
        this.showLoading('holdings-loading', true);

        try {
            const response = await fetch(`${this.baseURL}/v1/sell-signals/holding/${holdingId}`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                const data = await response.json();
                this.sellSignalsCache[holdingId] = data.signals;

                // 그리드 새로고침
                this.displayHoldingsGrid();

                if (data.signals.length > 0) {
                    this.showSellSignalDetail(holdingId);
                } else {
                    this.showNotification('현재 발생한 매도 신호가 없습니다.', 'info');
                }
            } else {
                this.showNotification('매도 신호 확인에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('매도 신호 확인 오류:', error);
            this.showNotification('매도 신호 확인 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('holdings-loading', false);
        }
    }

    showSellSignalDetail(holdingId) {
        const holding = this.holdings.find(h => h.id === holdingId);
        const signals = this.sellSignalsCache[holdingId] || [];

        if (!holding) {
            this.showNotification('보유종목 정보를 찾을 수 없습니다', 'error');
            return;
        }

        const profitClass = holding.profit_loss_percent >= 0 ? 'text-success' : 'text-danger';
        const profitSign = holding.profit_loss_percent >= 0 ? '+' : '';

        let modalContent = `
            <div class="mb-4">
                <h5>${holding.ticker} - ${holding.company_name || 'N/A'}</h5>
                <div class="row text-center">
                    <div class="col">
                        <div class="text-muted">현재가</div>
                        <div class="fs-5 fw-bold">${holding.current_price ? holding.current_price.toLocaleString() + '원' : 'N/A'}</div>
                    </div>
                    <div class="col">
                        <div class="text-muted">평균매수가</div>
                        <div class="fs-5">${holding.avg_buy_price.toLocaleString()}원</div>
                    </div>
                    <div class="col">
                        <div class="text-muted">수익률</div>
                        <div class="fs-5 fw-bold ${profitClass}">
                            ${profitSign}${holding.profit_loss_percent ? holding.profit_loss_percent.toFixed(2) : 0}%
                        </div>
                    </div>
                    <div class="col">
                        <div class="text-muted">보유수량</div>
                        <div class="fs-5">${holding.quantity.toLocaleString()}주</div>
                    </div>
                </div>
            </div>
        `;

        if (signals.length === 0) {
            modalContent += `
                <div class="alert alert-success">
                    <i class="fas fa-check-circle"></i> 현재 발생한 매도 신호가 없습니다.
                </div>
            `;
        } else {
            modalContent += `
                <h6><i class="fas fa-bell"></i> 감지된 매도 신호 (${signals.length}개)</h6>
                <div class="table-responsive">
                    <table class="table table-sm table-bordered">
                        <thead class="table-light">
                            <tr>
                                <th>우선순위</th>
                                <th>신호 유형</th>
                                <th>신뢰도</th>
                                <th>청산 비율</th>
                            </tr>
                        </thead>
                        <tbody>
            `;

            signals.forEach(s => {
                let priorityBadge = '';
                if (s.priority === 'CRITICAL') {
                    priorityBadge = '<span class="badge bg-danger">CRITICAL</span>';
                } else if (s.priority === 'HIGH') {
                    priorityBadge = '<span class="badge bg-warning text-dark">HIGH</span>';
                } else if (s.priority === 'MEDIUM') {
                    priorityBadge = '<span class="badge bg-info">MEDIUM</span>';
                } else {
                    priorityBadge = '<span class="badge bg-secondary">LOW</span>';
                }

                modalContent += `
                    <tr>
                        <td>${priorityBadge}</td>
                        <td>
                            <strong>${s.signal_type}</strong><br>
                            <small class="text-muted">${s.reason}</small><br>
                            <small class="text-primary">${s.recommended_action}</small>
                        </td>
                        <td class="text-center">${(s.confidence * 100).toFixed(0)}%</td>
                        <td class="text-center">${s.exit_percent}%</td>
                    </tr>
                `;
            });

            modalContent += `
                        </tbody>
                    </table>
                </div>
            `;

            // 권고사항 요약
            const criticalSignals = signals.filter(s => s.priority === 'CRITICAL');
            const highSignals = signals.filter(s => s.priority === 'HIGH');

            if (criticalSignals.length > 0) {
                modalContent += `
                    <div class="alert alert-danger">
                        <i class="fas fa-exclamation-triangle"></i>
                        <strong>긴급 조치 필요!</strong> ${criticalSignals.length}개의 긴급 신호가 발생했습니다.
                        즉시 매도를 고려하세요.
                    </div>
                `;
            } else if (highSignals.length > 0) {
                modalContent += `
                    <div class="alert alert-warning">
                        <i class="fas fa-exclamation-circle"></i>
                        <strong>주의!</strong> ${highSignals.length}개의 높은 우선순위 신호가 발생했습니다.
                        부분 매도 또는 손절 조정을 고려하세요.
                    </div>
                `;
            }
        }

        document.getElementById('sell-signal-modal-body').innerHTML = modalContent;

        const modal = new bootstrap.Modal(document.getElementById('sellSignalModal'));
        modal.show();
    }

    // =============================================
    // 매수 실행 관련 메서드
    // =============================================

    openBuyModal(ticker, companyName, currentPrice, targetPrice, stopLossPrice) {
        // 모달에 데이터 설정
        document.getElementById('buy-modal-ticker').textContent = `${ticker} - ${companyName}`;
        document.getElementById('buy-modal-price').textContent = currentPrice.toLocaleString() + '원';
        document.getElementById('buy-modal-target').textContent = targetPrice.toLocaleString() + '원';
        document.getElementById('buy-modal-stoploss').textContent = stopLossPrice.toLocaleString() + '원';

        // hidden 필드에 값 저장
        document.getElementById('buy-modal-ticker-value').value = ticker;
        document.getElementById('buy-modal-price-value').value = currentPrice;
        document.getElementById('buy-modal-target-value').value = targetPrice;
        document.getElementById('buy-modal-stoploss-value').value = stopLossPrice;
        document.getElementById('buy-modal-company-name').value = companyName;

        // 입력 필드 초기화
        document.getElementById('buy-modal-quantity').value = '';
        document.getElementById('buy-modal-memo').value = '';
        document.getElementById('buy-modal-total').textContent = '0원';

        // 수량 변경 시 총액 계산
        const quantityInput = document.getElementById('buy-modal-quantity');
        quantityInput.oninput = () => {
            const quantity = parseInt(quantityInput.value) || 0;
            const total = quantity * currentPrice;
            document.getElementById('buy-modal-total').textContent = total.toLocaleString() + '원';
        };

        // 모달 열기
        const modal = new bootstrap.Modal(document.getElementById('buyExecuteModal'));
        modal.show();
    }

    async executeBuy() {
        const ticker = document.getElementById('buy-modal-ticker-value').value;
        const currentPrice = parseFloat(document.getElementById('buy-modal-price-value').value);
        const targetPrice = parseFloat(document.getElementById('buy-modal-target-value').value);
        const stopLossPrice = parseFloat(document.getElementById('buy-modal-stoploss-value').value);
        const quantity = parseInt(document.getElementById('buy-modal-quantity').value);
        const memo = document.getElementById('buy-modal-memo').value;

        if (!quantity || quantity < 1) {
            this.showNotification('매수 수량을 입력해주세요', 'warning');
            return;
        }

        // 손절/익절 퍼센트 계산
        const stopLossPercent = ((stopLossPrice - currentPrice) / currentPrice * 100).toFixed(2);
        const takeProfitPercent = ((targetPrice - currentPrice) / currentPrice * 100).toFixed(2);

        try {
            const response = await fetch(`${this.baseURL}/v1/holdings/`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${this.token}`
                },
                body: JSON.stringify({
                    ticker: ticker,
                    quantity: quantity,
                    avg_buy_price: currentPrice,
                    buy_date: new Date().toISOString().split('T')[0],
                    stop_loss_price: stopLossPrice,
                    stop_loss_percent: parseFloat(stopLossPercent),
                    take_profit_price: targetPrice,
                    take_profit_percent: parseFloat(takeProfitPercent),
                    memo: memo || `매수 신호 기반 매수 (목표: ${targetPrice.toLocaleString()}원)`
                })
            });

            if (response.ok) {
                // 모달 닫기
                const modal = bootstrap.Modal.getInstance(document.getElementById('buyExecuteModal'));
                modal.hide();

                this.showNotification(
                    `${ticker} ${quantity}주 매수가 보유종목에 등록되었습니다!`,
                    'success'
                );

                // 보유종목 탭으로 이동
                const holdingsTab = document.getElementById('holdings-tab');
                const tabTrigger = new bootstrap.Tab(holdingsTab);
                tabTrigger.show();

                // 보유종목 새로고침
                await this.loadHoldings();
            } else {
                const error = await response.json();
                this.showNotification(error.detail || '매수 등록에 실패했습니다', 'error');
            }
        } catch (error) {
            console.error('매수 실행 오류:', error);
            this.showNotification('매수 실행 중 오류가 발생했습니다', 'error');
        }
    }
}

// 앱 초기화
const app = new StockTradingApp();