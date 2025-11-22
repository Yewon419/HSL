class StockTradingApp {
    constructor() {
        // 환경별 API URL 자동 감지
        const hostname = window.location.hostname;
        const port = window.location.port;

        if (hostname === 'localhost' || hostname === '127.0.0.1') {
            // 개발 환경
            this.baseURL = 'http://localhost:8000/api';
        } else {
            // 운영 환경: 현재 접속한 호스트:포트 사용
            this.baseURL = `http://${hostname}:${port}/api`;
        }

        this.token = localStorage.getItem('access_token');
        this.currentUser = null;
        this.stocks = [];
        this.priceChart = null;
        this.volumeChart = null;
        this.currentChartData = null;
        this.currentIndicatorData = null;
        this.indicatorsData = [];
        this.currentPage = 1;
        this.pageSize = 30;
        this.selectedTicker = null;
        this.selectedIndicatorTicker = null;
        this.currentFocus = -1;

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

        // 홈 버튼
        document.getElementById('home-btn').addEventListener('click', (e) => {
            e.preventDefault();
            const stocksTab = document.getElementById('stocks-tab');
            if (stocksTab) {
                const tab = new bootstrap.Tab(stocksTab);
                tab.show();
            }
        });

        // 로그아웃
        document.getElementById('logout-btn').addEventListener('click', () => this.logout());

        // 종목 추가 폼
        document.getElementById('add-stock-form').addEventListener('submit', (e) => this.handleAddStock(e));

        // 새로고침 버튼
        document.getElementById('refresh-stocks').addEventListener('click', () => this.loadStocks());

        // 차트 관련 이벤트
        const chartInput = document.getElementById('chart-ticker-input');
        chartInput.addEventListener('input', (e) => this.handleChartAutocomplete(e));
        chartInput.addEventListener('keydown', (e) => this.handleChartKeydown(e));
        document.getElementById('load-chart-btn').addEventListener('click', () => this.loadChart());

        // 기간 선택 타입 변경
        document.getElementById('chart-period-type').addEventListener('change', (e) => {
            const isCustom = e.target.value === 'custom';
            document.getElementById('preset-period-container').style.display = isCustom ? 'none' : 'block';
            document.getElementById('custom-period-container').style.display = isCustom ? 'block' : 'none';

            // 직접 선택 모드일 때 기본 날짜 설정
            if (isCustom) {
                const endDate = new Date();
                const startDate = new Date();
                startDate.setMonth(startDate.getMonth() - 1);

                document.getElementById('chart-end-date').valueAsDate = endDate;
                document.getElementById('chart-start-date').valueAsDate = startDate;
            }
        });

        // 자동완성 외부 클릭 시 닫기
        document.addEventListener('click', (e) => {
            if (!e.target.matches('#chart-ticker-input')) {
                this.closeAllAutocomplete();
            }
        });

        // 지표 토글 버튼
        document.getElementById('toggle-indicators-btn').addEventListener('click', () => {
            const togglePanel = document.getElementById('indicator-toggles');
            togglePanel.style.display = togglePanel.style.display === 'none' ? 'block' : 'none';
        });

        // 차트 업데이트 버튼
        document.getElementById('update-chart-btn').addEventListener('click', () => this.updateChartWithIndicators());

        // 이동평균선 세트 체크박스
        document.getElementById('toggle-sma-all').addEventListener('change', (e) => {
            // 현재 차트를 다시 로드하여 이동평균선 포함/제외
            this.updateChartWithIndicators();
        });

        // 지표 분석 관련 이벤트
        document.getElementById('apply-indicator-filter').addEventListener('click', () => {
            this.applyIndicatorFilter();
        });
        document.getElementById('reset-indicator-filter').addEventListener('click', () => {
            this.resetIndicatorFilters();
        });
        document.getElementById('refresh-indicators').addEventListener('click', () => {
            this.currentPage = 1;
            this.loadIndicatorsGrid();
        });
        document.getElementById('back-to-grid').addEventListener('click', () => this.showIndicatorsGrid());

        // 지표 분석 종목코드/명 자동완성
        const indicatorInput = document.getElementById('indicator-ticker-filter');
        indicatorInput.addEventListener('input', (e) => this.handleIndicatorAutocomplete(e));
        indicatorInput.addEventListener('keydown', (e) => this.handleIndicatorKeydown(e));

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
                } else if (targetId === '#indicators-pane') {
                    // 지표 분석 탭 진입 시 자동 로드
                    this.loadIndicatorsGrid();
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
            const response = await fetch(`${this.baseURL}/stocks/?limit=10000`, {
                headers: {
                    'Authorization': `Bearer ${this.token}`
                }
            });

            if (response.ok) {
                this.stocks = await response.json();
                console.log('Stocks loaded:', this.stocks.length);
                this.displayStocks();
                this.updateTickerSelects();
            } else {
                console.error('Failed to load stocks, status:', response.status);
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
            'signals-ticker-select'
        ];

        selects.forEach(selectId => {
            const select = document.getElementById(selectId);
            if (!select) return; // select 요소가 없으면 스킵
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

    handleChartAutocomplete(e) {
        const input = e.target;
        const val = input.value.trim();

        this.closeAllAutocomplete();

        if (!val || val.length < 1) {
            return;
        }

        this.currentFocus = -1;

        const autocompleteList = document.getElementById('chart-autocomplete-list');
        autocompleteList.innerHTML = '';

        // 디버깅: stocks 배열 확인
        console.log('Stocks array length:', this.stocks.length);
        console.log('Search term:', val);

        // 종목 검색
        const matches = this.stocks.filter(stock => {
            const ticker = stock.ticker.toLowerCase();
            const name = (stock.company_name || '').toLowerCase();
            const searchTerm = val.toLowerCase();
            return ticker.includes(searchTerm) || name.includes(searchTerm);
        }).slice(0, 10); // 최대 10개만 표시

        if (matches.length === 0) {
            autocompleteList.innerHTML = '<div style="padding: 10px; color: #6c757d;">검색 결과가 없습니다</div>';
            return;
        }

        matches.forEach(stock => {
            const div = document.createElement('div');
            div.innerHTML = `<strong>${stock.ticker}</strong> - ${stock.company_name || 'N/A'}`;
            div.addEventListener('click', () => {
                input.value = `${stock.ticker} - ${stock.company_name}`;
                this.selectedTicker = stock.ticker;
                this.closeAllAutocomplete();
            });
            autocompleteList.appendChild(div);
        });
    }

    handleChartKeydown(e) {
        const autocompleteList = document.getElementById('chart-autocomplete-list');
        let items = autocompleteList.getElementsByTagName('div');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.currentFocus++;
            this.addActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.currentFocus--;
            this.addActive(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.currentFocus > -1 && items[this.currentFocus]) {
                // 자동완성 항목 선택
                items[this.currentFocus].click();
            } else {
                // 직접 입력한 경우 자동완성 닫고 차트 로드
                this.closeAllAutocomplete();
                this.loadChart();
            }
        }
    }

    addActive(items) {
        if (!items || items.length === 0) return;
        this.removeActive(items);
        if (this.currentFocus >= items.length) this.currentFocus = 0;
        if (this.currentFocus < 0) this.currentFocus = items.length - 1;
        items[this.currentFocus].classList.add('autocomplete-active');
    }

    removeActive(items) {
        for (let i = 0; i < items.length; i++) {
            items[i].classList.remove('autocomplete-active');
        }
    }

    closeAllAutocomplete() {
        const chartAutocompleteList = document.getElementById('chart-autocomplete-list');
        if (chartAutocompleteList) {
            chartAutocompleteList.innerHTML = '';
        }
        const indicatorAutocompleteList = document.getElementById('indicator-autocomplete-list');
        if (indicatorAutocompleteList) {
            indicatorAutocompleteList.innerHTML = '';
        }
        this.currentFocus = -1;
    }

    viewChart(ticker) {
        const chartTab = document.getElementById('charts-tab');
        const tabTrigger = new bootstrap.Tab(chartTab);
        tabTrigger.show();

        // 종목 정보 찾기
        const stock = this.stocks.find(s => s.ticker === ticker);
        if (stock) {
            document.getElementById('chart-ticker-input').value = `${stock.ticker} - ${stock.company_name}`;
            this.selectedTicker = ticker;
            setTimeout(() => this.loadChart(), 100);
        }
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
        // 선택된 티커 가져오기 (자동완성에서 선택된 값 또는 직접 입력된 값)
        let ticker = this.selectedTicker;

        if (!ticker) {
            const inputValue = document.getElementById('chart-ticker-input').value.trim();
            if (!inputValue) {
                this.showNotification('종목을 선택해주세요', 'warning');
                return;
            }

            // 입력값에서 티커 추출 (예: "005930.KS - Samsung Electronics" -> "005930.KS")
            const match = inputValue.match(/^([\w.]+)/);
            if (match) {
                const possibleTicker = match[1];
                // 티커로 검색 (정확한 매칭 또는 부분 매칭)
                const foundByTicker = this.stocks.find(s =>
                    s.ticker === possibleTicker ||
                    s.ticker.toLowerCase() === possibleTicker.toLowerCase() ||
                    s.ticker.startsWith(possibleTicker)
                );

                if (foundByTicker) {
                    ticker = foundByTicker.ticker;
                } else {
                    // 종목명으로 검색 (정확한 매칭 우선, 그 다음 부분 매칭)
                    const searchTerm = inputValue.toLowerCase();
                    const exactMatch = this.stocks.find(s =>
                        s.company_name && s.company_name.toLowerCase() === searchTerm
                    );

                    if (exactMatch) {
                        ticker = exactMatch.ticker;
                    } else {
                        const partialMatch = this.stocks.find(s =>
                            s.company_name && s.company_name.toLowerCase().includes(searchTerm)
                        );

                        if (partialMatch) {
                            ticker = partialMatch.ticker;
                        } else {
                            this.showNotification(`"${inputValue}" 종목을 찾을 수 없습니다. 자동완성 목록에서 선택해주세요.`, 'warning');
                            console.log('Available stocks:', this.stocks.length);
                            return;
                        }
                    }
                }
            }
        }

        // 선택된 기간 가져오기
        const periodType = document.getElementById('chart-period-type').value;
        let apiUrl;

        if (periodType === 'custom') {
            const startDate = document.getElementById('chart-start-date').value;
            const endDate = document.getElementById('chart-end-date').value;

            if (!startDate || !endDate) {
                this.showNotification('시작일과 종료일을 선택해주세요', 'warning');
                return;
            }

            if (new Date(startDate) > new Date(endDate)) {
                this.showNotification('시작일은 종료일보다 이전이어야 합니다', 'warning');
                return;
            }

            apiUrl = `${this.baseURL}/stocks/${ticker}/prices?start_date=${startDate}&end_date=${endDate}`;
        } else {
            const period = document.getElementById('chart-period-select').value || 30;
            apiUrl = `${this.baseURL}/stocks/${ticker}/prices?days=${period}`;
        }

        this.showLoading('chart-loading', true);
        document.getElementById('chart-container').style.display = 'none';
        document.getElementById('toggle-indicators-btn').style.display = 'none';
        document.getElementById('indicator-toggles').style.display = 'none';

        try {
            // ticker가 유효한지 최종 확인
            if (!ticker || ticker === 'null' || ticker === 'undefined') {
                console.error('Invalid ticker:', ticker);
                this.showNotification('유효하지 않은 종목 코드입니다', 'error');
                this.showLoading('chart-loading', false);
                return;
            }

            const [priceResponse, indicatorResponse] = await Promise.all([
                fetch(apiUrl, {
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
        if (this.rsiChart) {
            this.rsiChart.destroy();
            this.rsiChart = null;
        }
        if (this.stochasticChart) {
            this.stochasticChart.destroy();
            this.stochasticChart = null;
        }
        if (this.macdChart) {
            this.macdChart.destroy();
            this.macdChart = null;
        }

        // 모든 지표 차트 숨김
        document.getElementById('rsi-chart-row').style.display = 'none';
        document.getElementById('stochastic-chart-row').style.display = 'none';
        document.getElementById('macd-chart-row').style.display = 'none';

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
            console.log('First data item:', sortedData[0]);
            
            // 레이블(날짜) 배열 생성
            const labels = sortedData.map(item => {
                const date = new Date(item.date);
                return `${date.getMonth() + 1}/${date.getDate()}`;
            });

            // 캔들스틱 데이터 준비 (OHLC)
            const candlestickData = sortedData.map(item => ({
                x: new Date(item.date).getTime(),
                o: item.open || item.open_price || item.close || item.close_price,
                h: item.high || item.high_price || item.close || item.close_price,
                l: item.low || item.low_price || item.close || item.close_price,
                c: item.close || item.close_price
            }));

            console.log('Candlestick data:', candlestickData.slice(0, 3), '...');
            console.log('Total price points:', candlestickData.length);
            console.log('Price range:', Math.min(...candlestickData.map(p => p.c)), '-', Math.max(...candlestickData.map(p => p.c)));

        // 기본 데이터셋 설정 (캔들스틱)
        const datasets = [
            {
                label: '주가',
                type: 'candlestick',
                data: candlestickData,
                color: {
                    up: 'rgb(255, 99, 132)',      // 상승: 빨간색
                    down: 'rgb(54, 162, 235)',     // 하락: 파란색
                    unchanged: 'rgb(128, 128, 128)' // 동일
                }
            }
        ];

        // 선택된 지표 추가
        const indicators = this.getSelectedIndicators();
        
        if (indicators.includes('sma20')) {
            const sma20 = this.calculateSMA(sortedData, 20);
            const sma20Data = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: sma20[idx]
            })).filter(d => d.y !== null);

            datasets.push({
                label: 'SMA 20',
                type: 'line',
                data: sma20Data,
                borderColor: 'rgb(255, 206, 86)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false
            });
        }

        if (indicators.includes('sma50')) {
            const sma50 = this.calculateSMA(sortedData, 50);
            const sma50Data = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: sma50[idx]
            })).filter(d => d.y !== null);

            datasets.push({
                label: 'SMA 50',
                type: 'line',
                data: sma50Data,
                borderColor: 'rgb(153, 102, 255)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false
            });
        }

        if (indicators.includes('sma200')) {
            const sma200 = this.calculateSMA(sortedData, 200);
            const sma200Data = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: sma200[idx]
            })).filter(d => d.y !== null);

            datasets.push({
                label: 'SMA 200',
                type: 'line',
                data: sma200Data,
                borderColor: 'rgb(75, 192, 192)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false
            });
        }

        if (indicators.includes('ema20')) {
            const ema20 = this.calculateEMA(sortedData, 20);
            const ema20Data = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: ema20[idx]
            })).filter(d => d.y !== null);

            datasets.push({
                label: 'EMA 20',
                type: 'line',
                data: ema20Data,
                borderColor: 'rgb(255, 159, 64)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                borderDash: [5, 5]
            });
        }

        // 볼린저 밴드 (20일 기준, 2 표준편차)
        if (indicators.includes('bb')) {
            const bb = this.calculateBollingerBands(sortedData, 20, 2);

            const upperData = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: bb.upper[idx]
            })).filter(d => d.y !== null);

            const middleData = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: bb.middle[idx]
            })).filter(d => d.y !== null);

            const lowerData = sortedData.map((item, idx) => ({
                x: new Date(item.date).getTime(),
                y: bb.lower[idx]
            })).filter(d => d.y !== null);

            datasets.push({
                label: 'BB Upper',
                type: 'line',
                data: upperData,
                borderColor: 'rgba(255, 193, 7, 0.8)',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            });
            datasets.push({
                label: 'BB Middle',
                type: 'line',
                data: middleData,
                borderColor: 'rgba(255, 193, 7, 0.6)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false,
                borderDash: [3, 3]
            });
            datasets.push({
                label: 'BB Lower',
                type: 'line',
                data: lowerData,
                borderColor: 'rgba(255, 193, 7, 0.8)',
                backgroundColor: 'rgba(255, 193, 7, 0.1)',
                borderWidth: 1,
                pointRadius: 0,
                fill: false
            });
        }

            // 기존 차트가 있으면 제거
            if (this.priceChart) {
                this.priceChart.destroy();
            }

            // 차트 생성 (캔들스틱 차트)
            console.log('Creating candlestick chart...');
            console.log('Datasets:', datasets);

            this.priceChart = new Chart(chartContext, {
            type: 'candlestick',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        min: new Date(sortedData[0].date).getTime(),
                        max: new Date(sortedData[sortedData.length - 1].date).getTime(),
                        title: {
                            display: true,
                            text: '날짜'
                        }
                    },
                    y: {
                        beginAtZero: false,
                        title: {
                            display: false
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
                                if (context.dataset.type === 'candlestick') {
                                    const point = context.raw;
                                    return [
                                        '시가: ' + (point.o || 0).toLocaleString() + '원',
                                        '고가: ' + (point.h || 0).toLocaleString() + '원',
                                        '저가: ' + (point.l || 0).toLocaleString() + '원',
                                        '종가: ' + (point.c || 0).toLocaleString() + '원'
                                    ];
                                }
                                const value = context.parsed.y;
                                return context.dataset.label + ': ' + value.toLocaleString() + '원';
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

        // X축 범위 계산 (모든 차트에서 동일하게 사용)
        const minDate = new Date(sortedData[0].date).getTime();
        const maxDate = new Date(sortedData[sortedData.length - 1].date).getTime();

        // 거래량 차트 (항상 표시)
        this.displayVolumeChart(sortedData, labels, minDate, maxDate);

        // 선택된 지표에 따라 추가 차트 표시
        const selectedIndicators = this.getSelectedIndicators();

        if (selectedIndicators.includes('rsi')) {
            this.displayRSIChart(sortedData, minDate, maxDate);
        }

        if (selectedIndicators.includes('macd')) {
            this.displayMACDChart(sortedData, minDate, maxDate);
        }

        if (selectedIndicators.includes('stochastic')) {
            this.displayStochasticChart(sortedData, minDate, maxDate);
        }

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

    displayVolumeChart(data, labels, minDate, maxDate) {
        document.getElementById('volume-chart-row').style.display = 'block';
        const ctx = document.getElementById('volume-chart').getContext('2d');

        if (this.volumeChart) {
            this.volumeChart.destroy();
        }

        // 거래량 데이터를 {x, y} 형식으로 변환
        const volumeData = data.map(item => ({
            x: new Date(item.date).getTime(),
            y: item.volume || 0
        }));

        // 거래량 이동평균 계산
        const volumeArray = data.map(item => item.volume || 0);
        const sma20 = this.calculateSMA(volumeArray, 20);
        const sma60 = this.calculateSMA(volumeArray, 60);

        const sma20Data = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: sma20[idx]
        })).filter(d => d.y !== null);

        const sma60Data = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: sma60[idx]
        })).filter(d => d.y !== null);

        const datasets = [{
            label: '거래량',
            type: 'bar',
            data: volumeData,
            backgroundColor: 'rgba(54, 162, 235, 0.5)',
            borderColor: 'rgba(54, 162, 235, 1)',
            borderWidth: 1,
            yAxisID: 'y'
        }];

        // 20일 평균선 추가
        if (sma20Data.length > 0) {
            datasets.push({
                label: '20일 평균',
                type: 'line',
                data: sma20Data,
                borderColor: 'rgb(255, 99, 132)',
                backgroundColor: 'rgba(255, 99, 132, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            });
        }

        // 60일 평균선 추가
        if (sma60Data.length > 0) {
            datasets.push({
                label: '60일 평균',
                type: 'line',
                data: sma60Data,
                borderColor: 'rgb(75, 192, 192)',
                backgroundColor: 'rgba(75, 192, 192, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                fill: false,
                yAxisID: 'y'
            });
        }

        this.volumeChart = new Chart(ctx, {
            type: 'bar',
            data: {
                datasets: datasets
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        min: minDate,
                        max: maxDate,
                        display: false  // x축 날짜 숨김
                    },
                    y: {
                        title: {
                            display: false
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
                                return context.dataset.label + ': ' + context.parsed.y.toLocaleString();
                            }
                        }
                    }
                }
            }
        });
    }

    displayRSIChart(data, minDate, maxDate) {
        document.getElementById('rsi-chart-row').style.display = 'block';
        const ctx = document.getElementById('rsi-chart').getContext('2d');

        if (this.rsiChart) {
            this.rsiChart.destroy();
        }

        // RSI 계산
        const rsi = this.calculateRSI(data, 14);
        const signal = this.calculateRSISignal(rsi, 9);

        // 데이터를 {x, y} 형식으로 변환
        const rsiData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: rsi[idx]
        })).filter(d => d.y !== null);

        const signalData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: signal[idx]
        })).filter(d => d.y !== null);

        this.rsiChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: 'RSI (14)',
                        data: rsiData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: 'Signal (9)',
                        data: signalData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        min: minDate,
                        max: maxDate,
                        display: false
                    },
                    y: {
                        min: 0,
                        max: 100,
                        title: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(0);
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
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                yMin: 70,
                                yMax: 70,
                                borderColor: 'rgba(255, 99, 132, 0.5)',
                                borderWidth: 1,
                                borderDash: [5, 5]
                            },
                            line2: {
                                type: 'line',
                                yMin: 30,
                                yMax: 30,
                                borderColor: 'rgba(54, 162, 235, 0.5)',
                                borderWidth: 1,
                                borderDash: [5, 5]
                            }
                        }
                    }
                }
            }
        });
    }

    displayStochasticChart(data, minDate, maxDate) {
        document.getElementById('stochastic-chart-row').style.display = 'block';
        const ctx = document.getElementById('stochastic-chart').getContext('2d');

        if (this.stochasticChart) {
            this.stochasticChart.destroy();
        }

        // Stochastic 계산
        const stochastic = this.calculateStochastic(data, 14, 3);

        // 데이터를 {x, y} 형식으로 변환
        const kData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: stochastic.k[idx]
        })).filter(d => d.y !== null);

        const dData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: stochastic.d[idx]
        })).filter(d => d.y !== null);

        this.stochasticChart = new Chart(ctx, {
            type: 'line',
            data: {
                datasets: [
                    {
                        label: '%K',
                        data: kData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    },
                    {
                        label: '%D',
                        data: dData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        min: minDate,
                        max: maxDate,
                        display: false
                    },
                    y: {
                        min: 0,
                        max: 100,
                        title: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(0);
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
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                            }
                        }
                    },
                    annotation: {
                        annotations: {
                            line1: {
                                type: 'line',
                                yMin: 80,
                                yMax: 80,
                                borderColor: 'rgba(255, 99, 132, 0.5)',
                                borderWidth: 1,
                                borderDash: [5, 5]
                            },
                            line2: {
                                type: 'line',
                                yMin: 20,
                                yMax: 20,
                                borderColor: 'rgba(54, 162, 235, 0.5)',
                                borderWidth: 1,
                                borderDash: [5, 5]
                            }
                        }
                    }
                }
            }
        });
    }

    displayMACDChart(data, minDate, maxDate) {
        document.getElementById('macd-chart-row').style.display = 'block';
        const ctx = document.getElementById('macd-chart').getContext('2d');

        if (this.macdChart) {
            this.macdChart.destroy();
        }

        // MACD 계산
        const macd = this.calculateMACD(data, 12, 26, 9);

        // 데이터를 {x, y} 형식으로 변환
        const macdData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: macd.macdLine[idx]
        })).filter(d => d.y !== null);

        const signalData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: macd.signalLine[idx]
        })).filter(d => d.y !== null);

        const histogramData = data.map((item, idx) => ({
            x: new Date(item.date).getTime(),
            y: macd.histogram[idx]
        })).filter(d => d.y !== null);

        this.macdChart = new Chart(ctx, {
            type: 'bar',
            data: {
                datasets: [
                    {
                        label: 'MACD (12,26)',
                        type: 'line',
                        data: macdData,
                        borderColor: 'rgb(255, 99, 132)',
                        backgroundColor: 'rgba(255, 99, 132, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Signal (9)',
                        type: 'line',
                        data: signalData,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.1)',
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Histogram',
                        type: 'bar',
                        data: histogramData,
                        backgroundColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? 'rgba(75, 192, 192, 0.5)' : 'rgba(255, 99, 132, 0.5)';
                        },
                        borderColor: function(context) {
                            const value = context.parsed.y;
                            return value >= 0 ? 'rgb(75, 192, 192)' : 'rgb(255, 99, 132)';
                        },
                        borderWidth: 1,
                        yAxisID: 'y'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                layout: {
                    padding: {
                        left: 0,
                        right: 0,
                        top: 0,
                        bottom: 0
                    }
                },
                scales: {
                    x: {
                        type: 'time',
                        time: {
                            unit: 'day',
                            displayFormats: {
                                day: 'MM/dd'
                            }
                        },
                        min: minDate,
                        max: maxDate,
                        display: false
                    },
                    y: {
                        title: {
                            display: false
                        },
                        ticks: {
                            callback: function(value) {
                                return value.toFixed(2);
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
                                return context.dataset.label + ': ' + context.parsed.y.toFixed(2);
                            }
                        }
                    }
                }
            }
        });
    }

    getSelectedIndicators() {
        const indicators = [];

        // 이동평균선 세트 체크
        const smaAll = document.getElementById('toggle-sma-all');
        if (smaAll && smaAll.checked) {
            indicators.push('sma20', 'sma50', 'sma200');
        }

        // 나머지 개별 지표들
        const checkboxes = document.querySelectorAll('.indicator-toggle:checked');
        checkboxes.forEach(cb => {
            if (!indicators.includes(cb.value)) {
                indicators.push(cb.value);
            }
        });

        return indicators;
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
                    const price = data[i - j].close || data[i - j].close_price;
                    sum += price;
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
            const price = data[i].close || data[i].close_price;
            sum += price;
        }
        let ema = sum / Math.min(period, data.length);

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                result.push(null);
            } else if (i === period - 1) {
                result.push(ema);
            } else {
                const price = data[i].close || data[i].close_price;
                ema = (price - ema) * multiplier + ema;
                result.push(ema);
            }
        }
        return result;
    }

    calculateBollingerBands(data, period = 20, stdDev = 2) {
        const upper = [];
        const middle = [];
        const lower = [];

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                upper.push(null);
                middle.push(null);
                lower.push(null);
            } else {
                // SMA 계산 (중간 밴드)
                let sum = 0;
                for (let j = 0; j < period; j++) {
                    const price = data[i - j].close || data[i - j].close_price;
                    sum += price;
                }
                const sma = sum / period;

                // 표준편차 계산
                let variance = 0;
                for (let j = 0; j < period; j++) {
                    const price = data[i - j].close || data[i - j].close_price;
                    variance += Math.pow(price - sma, 2);
                }
                const std = Math.sqrt(variance / period);

                middle.push(sma);
                upper.push(sma + (stdDev * std));
                lower.push(sma - (stdDev * std));
            }
        }

        return { upper, middle, lower };
    }

    calculateRSI(data, period = 14) {
        const rsi = [];
        const gains = [];
        const losses = [];

        for (let i = 0; i < data.length; i++) {
            if (i === 0) {
                rsi.push(null);
                continue;
            }

            const currentPrice = data[i].close || data[i].close_price;
            const prevPrice = data[i - 1].close || data[i - 1].close_price;
            const change = currentPrice - prevPrice;

            gains.push(change > 0 ? change : 0);
            losses.push(change < 0 ? Math.abs(change) : 0);

            if (i < period) {
                rsi.push(null);
            } else if (i === period) {
                // 첫 번째 RSI 계산 (단순 평균)
                const avgGain = gains.slice(0, period).reduce((a, b) => a + b, 0) / period;
                const avgLoss = losses.slice(0, period).reduce((a, b) => a + b, 0) / period;
                const rs = avgLoss === 0 ? 100 : avgGain / avgLoss;
                rsi.push(100 - (100 / (1 + rs)));
            } else {
                // 이후 RSI 계산 (이동 평균)
                const prevAvgGain = (gains.slice(i - period, i - 1).reduce((a, b) => a + b, 0) * (period - 1) + gains[i - 1]) / period;
                const prevAvgLoss = (losses.slice(i - period, i - 1).reduce((a, b) => a + b, 0) * (period - 1) + losses[i - 1]) / period;
                const rs = prevAvgLoss === 0 ? 100 : prevAvgGain / prevAvgLoss;
                rsi.push(100 - (100 / (1 + rs)));
            }
        }

        return rsi;
    }

    calculateRSISignal(rsi, period = 9) {
        const signal = [];

        for (let i = 0; i < rsi.length; i++) {
            if (i < period - 1 || rsi[i] === null) {
                signal.push(null);
            } else {
                let sum = 0;
                let count = 0;
                for (let j = 0; j < period; j++) {
                    if (rsi[i - j] !== null) {
                        sum += rsi[i - j];
                        count++;
                    }
                }
                signal.push(count > 0 ? sum / count : null);
            }
        }

        return signal;
    }

    calculateStochastic(data, kPeriod = 14, dPeriod = 3) {
        const k = [];
        const d = [];

        for (let i = 0; i < data.length; i++) {
            if (i < kPeriod - 1) {
                k.push(null);
                d.push(null);
            } else {
                // K% 계산
                const recentData = data.slice(i - kPeriod + 1, i + 1);
                const highestHigh = Math.max(...recentData.map(item => item.high || item.high_price || item.close || item.close_price));
                const lowestLow = Math.min(...recentData.map(item => item.low || item.low_price || item.close || item.close_price));
                const currentClose = data[i].close || data[i].close_price;

                const kValue = lowestLow === highestHigh ? 50 : ((currentClose - lowestLow) / (highestHigh - lowestLow)) * 100;
                k.push(kValue);

                // D% 계산 (K의 이동평균)
                if (i < kPeriod + dPeriod - 2) {
                    d.push(null);
                } else {
                    const recentK = k.slice(i - dPeriod + 1, i + 1).filter(v => v !== null);
                    const dValue = recentK.reduce((a, b) => a + b, 0) / recentK.length;
                    d.push(dValue);
                }
            }
        }

        return { k, d };
    }

    calculateEMA(data, period) {
        const ema = [];
        const multiplier = 2 / (period + 1);

        for (let i = 0; i < data.length; i++) {
            if (i < period - 1) {
                ema.push(null);
            } else if (i === period - 1) {
                // 첫 EMA는 SMA로 시작
                const sum = data.slice(i - period + 1, i + 1)
                    .reduce((acc, item) => acc + (item.close || item.close_price), 0);
                ema.push(sum / period);
            } else {
                // EMA = (현재가 * multiplier) + (이전 EMA * (1 - multiplier))
                const currentPrice = data[i].close || data[i].close_price;
                const prevEMA = ema[i - 1];
                ema.push((currentPrice - prevEMA) * multiplier + prevEMA);
            }
        }

        return ema;
    }

    calculateMACD(data, fastPeriod = 12, slowPeriod = 26, signalPeriod = 9) {
        // EMA 계산
        const emaFast = this.calculateEMA(data, fastPeriod);
        const emaSlow = this.calculateEMA(data, slowPeriod);

        // MACD Line 계산
        const macdLine = [];
        for (let i = 0; i < data.length; i++) {
            if (emaFast[i] === null || emaSlow[i] === null) {
                macdLine.push(null);
            } else {
                macdLine.push(emaFast[i] - emaSlow[i]);
            }
        }

        // Signal Line 계산 (MACD의 EMA)
        const signalLine = [];
        const macdData = data.map((item, idx) => ({
            ...item,
            close: macdLine[idx]
        }));

        const multiplier = 2 / (signalPeriod + 1);
        let validMacdStart = macdLine.findIndex(v => v !== null);

        for (let i = 0; i < macdLine.length; i++) {
            if (i < validMacdStart + signalPeriod - 1) {
                signalLine.push(null);
            } else if (i === validMacdStart + signalPeriod - 1) {
                // 첫 Signal은 MACD의 SMA
                const validMacd = macdLine.slice(validMacdStart, i + 1).filter(v => v !== null);
                const sum = validMacd.reduce((a, b) => a + b, 0);
                signalLine.push(sum / validMacd.length);
            } else {
                // Signal EMA 계산
                if (macdLine[i] !== null && signalLine[i - 1] !== null) {
                    signalLine.push((macdLine[i] - signalLine[i - 1]) * multiplier + signalLine[i - 1]);
                } else {
                    signalLine.push(null);
                }
            }
        }

        // Histogram 계산
        const histogram = [];
        for (let i = 0; i < data.length; i++) {
            if (macdLine[i] === null || signalLine[i] === null) {
                histogram.push(null);
            } else {
                histogram.push(macdLine[i] - signalLine[i]);
            }
        }

        return { macdLine, signalLine, histogram };
    }

    // 지표 분석 관련 메서드
    async loadIndicatorsGrid() {
        this.showLoading('indicators-loading', true);
        document.getElementById('indicators-grid-container').style.display = 'none';

        try {
            // 필터 값 가져오기
            let dateFilter = document.getElementById('indicator-date-filter').value;

            // 날짜가 없으면 2025-10-02로 설정
            if (!dateFilter) {
                dateFilter = '2025-10-02';
                document.getElementById('indicator-date-filter').value = dateFilter;
            }

            // DB에서 지표 데이터 조회
            const response = await fetch(`http://localhost:8000/api/v1/indicators/grid?date=${dateFilter}`);

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
        const tickerInput = document.getElementById('indicator-ticker-filter');
        const tickerFilterRaw = tickerInput.value.trim();
        const sectorFilter = document.getElementById('indicator-sector-filter').value;

        // ticker 추출 (자동완성 선택 시 ticker만 들어가지만, 수동 입력을 위해 추출 로직 유지)
        let tickerFilter = tickerFilterRaw.toLowerCase();

        let filteredIndicators = indicators.filter(ind => {
            if (countryFilter && ind.country !== countryFilter) return false;
            if (tickerFilter && !(ind.ticker.toLowerCase().includes(tickerFilter) ||
                (ind.company_name && ind.company_name.toLowerCase().includes(tickerFilter)))) return false;
            if (sectorFilter && ind.sector !== sectorFilter) return false;
            return true;
        });

        // 전체 데이터 저장
        this.indicatorsData = filteredIndicators;

        if (filteredIndicators.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="18" class="text-center text-muted py-4">
                        필터 조건에 맞는 지표 데이터가 없습니다
                    </td>
                </tr>
            `;
            this.renderPagination(0);
            return;
        }

        // 페이징 처리
        const totalPages = Math.ceil(filteredIndicators.length / this.pageSize);
        const startIndex = (this.currentPage - 1) * this.pageSize;
        const endIndex = startIndex + this.pageSize;
        const paginatedData = filteredIndicators.slice(startIndex, endIndex);

        tbody.innerHTML = paginatedData.map(ind => {
            // RSI 신호에 따른 색상
            const rsiColor = ind.rsi_signal === '매수' ? 'text-success' : ind.rsi_signal === '매도' ? 'text-danger' : '';

            // Stochastic 신호에 따른 색상
            const stochColor = ind.stoch_signal === '골든' ? 'text-success' : ind.stoch_signal === '데드' ? 'text-danger' : '';

            // 순매수/순매도에 따른 색상
            const foreignColor = ind.foreign_net > 0 ? 'text-success' : ind.foreign_net < 0 ? 'text-danger' : '';
            const institutionColor = ind.institution_net > 0 ? 'text-success' : ind.institution_net < 0 ? 'text-danger' : '';
            const individualColor = ind.individual_net > 0 ? 'text-success' : ind.individual_net < 0 ? 'text-danger' : '';

            // 볼륨 변동에 따른 색상
            const volumeChangeColor = ind.volume_change > 0 ? 'text-success' : ind.volume_change < 0 ? 'text-danger' : '';

            return `
            <tr style="cursor: pointer;" onclick="app.loadTickerMonthlyData('${ind.ticker}', '${ind.company_name || ind.ticker}')">
                <td>${ind.country || 'KR'}</td>
                <td><strong>${ind.ticker}</strong></td>
                <td>${ind.company_name || 'N/A'}</td>
                <td>${ind.sector || 'N/A'}</td>
                <td>${ind.date || 'N/A'}</td>
                <td class="text-end">${(ind.open_price || 0).toLocaleString()}원</td>
                <td class="text-end">${(ind.high_price || 0).toLocaleString()}원</td>
                <td class="text-end">${(ind.low_price || 0).toLocaleString()}원</td>
                <td class="text-end">${(ind.close_price || 0).toLocaleString()}원</td>
                <td class="text-end">${(ind.volume || 0).toLocaleString()}</td>
                <td class="text-end ${volumeChangeColor}">
                    ${ind.volume_change >= 0 ? '+' : ''}${(ind.volume_change || 0).toLocaleString()}
                </td>
                <td class="text-center ${rsiColor}">
                    <span class="badge bg-${ind.rsi_signal === '매수' ? 'success' : ind.rsi_signal === '매도' ? 'danger' : 'secondary'}">${ind.rsi_signal}</span>
                    <small> ${(ind.rsi || 0).toFixed(2)}</small>
                </td>
                <td class="text-center">
                    <span class="badge bg-${ind.trend === '정배열' ? 'primary' : ind.trend === '역배열' ? 'warning' : ind.trend === '단기상승' ? 'info' : ind.trend === '단기하락' ? 'danger' : 'secondary'}">${ind.trend}</span>
                </td>
                <td class="text-end">${(ind.macd || 0).toFixed(4)}</td>
                <td class="text-center ${stochColor}">
                    <span class="badge bg-${ind.stoch_signal === '골든' ? 'success' : ind.stoch_signal === '데드' ? 'danger' : 'secondary'}">${ind.stoch_signal}</span>
                    <small> K:${(ind.stoch_k || 0).toFixed(2)} D:${(ind.stoch_d || 0).toFixed(2)}</small>
                </td>
                <td class="text-end ${foreignColor}" style="font-size: 0.85em;">
                    ${ind.foreign_net >= 0 ? '+' : ''}${(ind.foreign_net || 0).toLocaleString()}
                </td>
                <td class="text-end ${institutionColor}" style="font-size: 0.85em;">
                    ${ind.institution_net >= 0 ? '+' : ''}${(ind.institution_net || 0).toLocaleString()}
                </td>
                <td class="text-end ${individualColor}" style="font-size: 0.85em;">
                    ${ind.individual_net >= 0 ? '+' : ''}${(ind.individual_net || 0).toLocaleString()}
                </td>
            </tr>
            `;
        }).join('');

        // 페이징 렌더링
        this.renderPagination(totalPages);

        // 업종 필터 옵션 동적 생성
        this.updateIndicatorSectorFilter(indicators);
    }

    renderPagination(totalPages) {
        const pagination = document.getElementById('indicators-pagination');
        if (totalPages <= 1) {
            pagination.innerHTML = '';
            return;
        }

        let paginationHTML = '';

        // 이전 버튼
        paginationHTML += `
            <li class="page-item ${this.currentPage === 1 ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.changePage(${this.currentPage - 1}); return false;">이전</a>
            </li>
        `;

        // 페이지 번호
        const maxVisible = 5;
        let startPage = Math.max(1, this.currentPage - Math.floor(maxVisible / 2));
        let endPage = Math.min(totalPages, startPage + maxVisible - 1);

        if (endPage - startPage < maxVisible - 1) {
            startPage = Math.max(1, endPage - maxVisible + 1);
        }

        for (let i = startPage; i <= endPage; i++) {
            paginationHTML += `
                <li class="page-item ${this.currentPage === i ? 'active' : ''}">
                    <a class="page-link" href="#" onclick="app.changePage(${i}); return false;">${i}</a>
                </li>
            `;
        }

        // 다음 버튼
        paginationHTML += `
            <li class="page-item ${this.currentPage === totalPages ? 'disabled' : ''}">
                <a class="page-link" href="#" onclick="app.changePage(${this.currentPage + 1}); return false;">다음</a>
            </li>
        `;

        pagination.innerHTML = paginationHTML;
    }

    changePage(page) {
        this.currentPage = page;
        this.displayIndicatorsGrid(this.indicatorsData);
    }

    showIndicatorsGrid() {
        document.getElementById('indicators-grid-container').style.display = 'block';
        document.getElementById('indicators-monthly-container').style.display = 'none';
    }

    applyIndicatorFilter() {
        const tickerInput = document.getElementById('indicator-ticker-filter');
        const tickerValue = tickerInput.value.trim();

        // ticker가 입력되어 있으면 한달치 데이터 표시
        if (tickerValue) {
            let ticker = this.selectedIndicatorTicker;
            let companyName = '';
            let stock = null;

            // selectedIndicatorTicker가 없으면 input value에서 검색
            if (!ticker) {
                const searchTerm = tickerValue.toLowerCase();

                // 1. 먼저 ticker 완전 일치 검색
                stock = this.stocks.find(s => s.ticker.toLowerCase() === searchTerm);

                // 2. company_name 완전 일치 검색
                if (!stock) {
                    stock = this.stocks.find(s => s.company_name && s.company_name.toLowerCase() === searchTerm);
                }

                // 3. "005930 - 삼성전자" 형식에서 ticker 추출
                if (!stock) {
                    const match = tickerValue.match(/^([\w.]+)/);
                    if (match) {
                        const extractedTicker = match[1];
                        stock = this.stocks.find(s => s.ticker.toLowerCase() === extractedTicker.toLowerCase());
                    }
                }

                // 4. ticker 부분 일치 검색 (시작 부분)
                if (!stock) {
                    stock = this.stocks.find(s => s.ticker.toLowerCase().startsWith(searchTerm));
                }

                // 5. company_name 부분 일치 검색 (포함)
                if (!stock) {
                    stock = this.stocks.find(s => s.company_name && s.company_name.toLowerCase().includes(searchTerm));
                }

                if (stock) {
                    ticker = stock.ticker;
                }
            } else {
                // selectedIndicatorTicker가 있으면 stocks에서 찾기
                stock = this.stocks.find(s => s.ticker === ticker);
            }

            if (ticker) {
                companyName = stock ? (stock.company_name || ticker) : ticker;
                this.loadTickerMonthlyData(ticker, companyName);
            } else {
                this.showNotification('종목을 찾을 수 없습니다. 종목 코드 또는 종목명을 확인해주세요.', 'warning');
            }
        } else {
            // ticker가 없으면 전체 목록 표시
            this.currentPage = 1;
            this.loadIndicatorsGrid();
        }
    }

    resetIndicatorFilters() {
        // 필터 초기화
        document.getElementById('indicator-country-filter').value = '';
        document.getElementById('indicator-ticker-filter').value = '';
        document.getElementById('indicator-date-filter').value = '';
        document.getElementById('indicator-sector-filter').value = '';
        this.selectedIndicatorTicker = null;

        // 자동완성 목록 닫기
        this.closeAllAutocomplete();

        // 전체 종목 표시
        this.currentPage = 1;
        this.loadIndicatorsGrid();
    }

    handleIndicatorAutocomplete(e) {
        const input = e.target;
        const val = input.value.trim();

        this.closeAllAutocomplete();

        if (!val || val.length < 1) {
            return;
        }

        this.currentFocus = -1;

        const autocompleteList = document.getElementById('indicator-autocomplete-list');
        autocompleteList.innerHTML = '';

        // 종목 검색
        const matches = this.stocks.filter(stock => {
            const ticker = stock.ticker.toLowerCase();
            const name = (stock.company_name || '').toLowerCase();
            const searchTerm = val.toLowerCase();
            return ticker.includes(searchTerm) || name.includes(searchTerm);
        }).slice(0, 10); // 최대 10개만 표시

        if (matches.length === 0) {
            autocompleteList.innerHTML = '<div style="padding: 10px; color: #6c757d;">검색 결과가 없습니다</div>';
            return;
        }

        matches.forEach(stock => {
            const div = document.createElement('div');
            div.innerHTML = `<strong>${stock.ticker}</strong> - ${stock.company_name || 'N/A'}`;
            div.addEventListener('click', () => {
                input.value = `${stock.ticker} - ${stock.company_name}`;
                this.selectedIndicatorTicker = stock.ticker;
                this.closeAllAutocomplete();
                // 자동완성 선택 시 바로 조회
                this.applyIndicatorFilter();
            });
            autocompleteList.appendChild(div);
        });
    }

    handleIndicatorKeydown(e) {
        const autocompleteList = document.getElementById('indicator-autocomplete-list');
        let items = autocompleteList.getElementsByTagName('div');

        if (e.key === 'ArrowDown') {
            e.preventDefault();
            this.currentFocus++;
            this.addActive(items);
        } else if (e.key === 'ArrowUp') {
            e.preventDefault();
            this.currentFocus--;
            this.addActive(items);
        } else if (e.key === 'Enter') {
            e.preventDefault();
            if (this.currentFocus > -1 && items[this.currentFocus]) {
                // 자동완성 항목 선택
                items[this.currentFocus].click();
            } else {
                // 직접 입력한 경우 조회 실행
                this.closeAllAutocomplete();
                this.applyIndicatorFilter();
            }
        }
    }

    async loadTickerMonthlyData(ticker, companyName) {
        try {
            this.showLoading('indicators-loading', true);

            const response = await fetch(`${this.baseURL}/v1/indicators/monthly/${ticker}?days=30`);

            if (response.ok) {
                const data = await response.json();
                this.displayMonthlyData(ticker, companyName, data);
            } else {
                this.showNotification('1달 데이터를 불러올 수 없습니다', 'error');
            }
        } catch (error) {
            console.error('1달 데이터 로드 오류:', error);
            this.showNotification('데이터 로드 중 오류가 발생했습니다', 'error');
        } finally {
            this.showLoading('indicators-loading', false);
        }
    }

    displayMonthlyData(ticker, companyName, data) {
        document.getElementById('indicators-grid-container').style.display = 'none';
        document.getElementById('indicators-monthly-container').style.display = 'block';
        document.getElementById('monthly-title').innerHTML = `<i class="fas fa-chart-area"></i> ${ticker} - ${companyName} (최근 30일)`;

        const tbody = document.getElementById('indicators-monthly-body');

        if (data.length === 0) {
            tbody.innerHTML = `
                <tr>
                    <td colspan="14" class="text-center text-muted py-4">
                        데이터가 없습니다
                    </td>
                </tr>
            `;
            return;
        }

        tbody.innerHTML = data.map(item => {
            const rsiColor = item.rsi_signal === '매수' ? 'text-success' : item.rsi_signal === '매도' ? 'text-danger' : '';
            const stochColor = item.stoch_signal === '골든' ? 'text-success' : item.stoch_signal === '데드' ? 'text-danger' : '';
            const foreignColor = item.foreign_net > 0 ? 'text-success' : item.foreign_net < 0 ? 'text-danger' : '';
            const institutionColor = item.institution_net > 0 ? 'text-success' : item.institution_net < 0 ? 'text-danger' : '';
            const individualColor = item.individual_net > 0 ? 'text-success' : item.individual_net < 0 ? 'text-danger' : '';
            const volumeChangeColor = item.volume_change > 0 ? 'text-success' : item.volume_change < 0 ? 'text-danger' : '';

            return `
                <tr>
                    <td>${item.date}</td>
                    <td class="text-end">${(item.open_price || 0).toLocaleString()}원</td>
                    <td class="text-end">${(item.high_price || 0).toLocaleString()}원</td>
                    <td class="text-end">${(item.low_price || 0).toLocaleString()}원</td>
                    <td class="text-end">${(item.close_price || 0).toLocaleString()}원</td>
                    <td class="text-end">${(item.volume || 0).toLocaleString()}</td>
                    <td class="text-end ${volumeChangeColor}">
                        ${item.volume_change >= 0 ? '+' : ''}${(item.volume_change || 0).toLocaleString()}
                    </td>
                    <td class="text-center ${rsiColor}">
                        <span class="badge bg-${item.rsi_signal === '매수' ? 'success' : item.rsi_signal === '매도' ? 'danger' : 'secondary'}">${item.rsi_signal}</span>
                        <small> ${(item.rsi || 0).toFixed(2)}</small>
                    </td>
                    <td class="text-center">
                        <span class="badge bg-${item.trend === '정배열' ? 'primary' : item.trend === '역배열' ? 'warning' : item.trend === '단기상승' ? 'info' : item.trend === '단기하락' ? 'danger' : 'secondary'}">${item.trend}</span>
                    </td>
                    <td class="text-end">${(item.macd || 0).toFixed(4)}</td>
                    <td class="text-center ${stochColor}">
                        <span class="badge bg-${item.stoch_signal === '골든' ? 'success' : item.stoch_signal === '데드' ? 'danger' : 'secondary'}">${item.stoch_signal}</span>
                        <small> K:${(item.stoch_k || 0).toFixed(2)} D:${(item.stoch_d || 0).toFixed(2)}</small>
                    </td>
                    <td class="text-end ${foreignColor}" style="font-size: 0.85em;">
                        ${item.foreign_net >= 0 ? '+' : ''}${(item.foreign_net || 0).toLocaleString()}
                    </td>
                    <td class="text-end ${institutionColor}" style="font-size: 0.85em;">
                        ${item.institution_net >= 0 ? '+' : ''}${(item.institution_net || 0).toLocaleString()}
                    </td>
                    <td class="text-end ${individualColor}" style="font-size: 0.85em;">
                        ${item.individual_net >= 0 ? '+' : ''}${(item.individual_net || 0).toLocaleString()}
                    </td>
                </tr>
            `;
        }).join('');
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

            // 날짜가 없으면 2025-10-02로 설정 (현재 데이터가 있는 날짜)
            if (!dateFilter) {
                dateFilter = '2025-10-02';
                document.getElementById('signal-date-filter').value = dateFilter;
            }

            // API 호출 - /api/trading/signals/all 엔드포인트 사용
            const url = `http://localhost:8000/api/trading/signals/all?target_date=${dateFilter}`;

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